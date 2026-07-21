"""LE L2 审核层 — Gatekeeper(W8 落地,W11-A 布局对齐)。

实现关键节点的机器可验证检查。
参考 ``_research/LE_DESIGN.md`` §3.2。

核心原则:停止条件 = 机器可验证命令,绝不"感觉差不多"。

W8 适配:产物布局从原型 ``inbox/raw/lecture.md`` 迁移到
``<work>/chapters/raw/<stem>.md`` + ``<work>/chapters/raw/<stem>_final.html``(W3 render + W4 longdoc)。

W11-A 适配:gatekeeper 与 verify 共享布局约定,避免分叉。
- 新布局(W3+,默认):``<work>/chapters/raw/<stem>.md`` + ``<work>/chapters/raw/<stem>_final.html``
- 旧布局(W4 原型):``<work>/chapters/raw/<stem>/<stem>.md`` + ``<work>/output_final.html``

接口对比:
- 原型:``gatekeeper_check(inbox, work)`` — 两参数,产物在 inbox 内
- W8:``gatekeeper_check(work)`` — 单参数,产物在 work 内
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .pipeline_logger import GatekeeperResult


def _resolve_lecture_path(work: Path, final_dir: Path | None = None) -> Path | None:
  """派生 lecture markdown 路径,兼容新旧 + W12-D final_dir 三种布局。

  优先级(返回第一个存在的路径,否则返回新布局路径用于诊断):

  1. **W12-D final_dir**(默认,若提供):``<final_dir>/<stem>.md``
  2. 新布局(W3+):``<work>/chapters/raw/<stem>.md``
  3. 旧布局(W4 原型):``<work>/chapters/raw/<stem>/<stem>.md``

  Parameters
  ----------
  work : Path
    work 根目录
  final_dir : Path | None
    W12-D 新增:最终产物目录(``<work>.parent / "output_final"``)。
    提供时优先查此路径。

  Returns
  -------
  Path | None
    第一个存在的候选路径;若都没有,返回新布局路径(便于诊断);
    若 ``chapters.json`` 不存在则返回 ``None``。
  """
  chapters_json = work / "chapters" / "chapters.json"
  if not chapters_json.exists():
    return None
  try:
    data = json.loads(chapters_json.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return None
  stem = (data.get("video") or "").strip() or "output"

  # W12-D final_dir 布局优先
  if final_dir is not None:
    final_layout = final_dir / f"{stem}.md"
    if final_layout.exists():
      return final_layout

  new_layout = work / "chapters" / "raw" / f"{stem}.md"
  if new_layout.exists():
    return new_layout
  old_layout = work / "chapters" / "raw" / stem / f"{stem}.md"
  if old_layout.exists():
    return old_layout
  # 没有文件存在:返回新布局路径(便于 gatekeeper_check 报"lecture.md not found")
  return new_layout


def _resolve_final_html(work: Path, final_dir: Path | None = None) -> Path:
  """派生最终 HTML 路径,兼容新旧 + W12-D final_dir 三种布局。

  优先级(返回第一个存在的路径,否则返回默认诊断路径):

  1. **W12-D final_dir**(默认,若提供):``<final_dir>/<stem>_final.html``
  2. 新布局(W4+):``<work>/chapters/raw/<stem>_final.html``
  3. 旧布局(W4 原型):``<work>/output_final.html``

  若 ``chapters.json`` 不存在,默认 fallback 为旧布局(向后兼容)。

  Parameters
  ----------
  work : Path
    work 根目录
  final_dir : Path | None
    W12-D 新增:最终产物目录。

  Returns
  -------
  Path
    第一个存在的候选路径;都没有则返回诊断用默认路径。
  """
  chapters_json = work / "chapters" / "chapters.json"
  stem = "output"
  if chapters_json.exists():
    try:
      data = json.loads(chapters_json.read_text(encoding="utf-8"))
      stem = (data.get("video") or "").strip() or "output"
    except (json.JSONDecodeError, OSError):
      stem = "output"

  # W12-D final_dir 布局优先
  if final_dir is not None:
    final_layout = final_dir / f"{stem}_final.html"
    if final_layout.exists():
      return final_layout

  new_layout = work / "chapters" / "raw" / f"{stem}_final.html"
  if new_layout.exists():
    return new_layout
  old_layout = work / "output_final.html"
  if old_layout.exists():
    return old_layout
  # 没有文件存在:返回诊断默认路径(优先用 chapters.json 推断的 stem)
  return new_layout if chapters_json.exists() else old_layout


def _read_video_stem(work: Path) -> str:
  """从 ``chapters.json`` 派生 video stem;解析失败时回退 ``"output"``。"""
  chapters_json = work / "chapters" / "chapters.json"
  if not chapters_json.exists():
    return "output"
  try:
    data = json.loads(chapters_json.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return "output"
  return (data.get("video") or "").strip() or "output"


def _load_final_dir_from_state(work: Path) -> Path | None:
  """W12-D:从 ``state.json`` 读取 ``final_dir`` 字段(供 gatekeeper 路径解析)。"""
  state_path = work / "state.json"
  if not state_path.exists():
    return None
  try:
    import json as _json
    data = _json.loads(state_path.read_text(encoding="utf-8"))
    fd = data.get("final_dir")
    return Path(fd) if fd else None
  except (json.JSONDecodeError, OSError):
    return None


def gatekeeper_check(work: Path) -> GatekeeperResult:
  """LE L2 审核层:4 项关键节点检查(W8 适配新产物布局,W12-D 加 final_dir 优先)。

  检查项(全部机器可验证):
  1. chapters.json 存在 + render 产物 ``<stem>.md`` 存在且非空
  2. ``<stem>.md`` 至少 1 个 H1 + 3 个 H2 章节
  3. 最终 HTML 存在且 > 1000 bytes(longdoc 净化产物)
  4. 所有 image_refs 真实存在(允许无图场景)

  W12-D:从 ``state.final_dir`` 读取最终产物目录(若存在),优先查 final_dir。

  Returns
  -------
  GatekeeperResult
    含 ``ok`` / ``issues`` / ``checks_passed`` / ``checks_failed``
  """
  issues: list[str] = []
  passed: list[str] = []
  failed: list[str] = []

  final_dir = _load_final_dir_from_state(work)
  lecture_md = _resolve_lecture_path(work, final_dir=final_dir)

  # ── Check 1: lecture.md 存在且非空 ──────────────────
  if not lecture_md or not lecture_md.exists():
    issues.append(f"lecture.md not found (resolved={lecture_md})")
    failed.append("lecture_md_exists")
  else:
    passed.append("lecture_md_exists")
    size = lecture_md.stat().st_size
    if size < 100:
      issues.append(f"lecture.md too small ({size} bytes)")
      failed.append("lecture_md_nonempty")
    else:
      passed.append("lecture_md_nonempty")

  # ── Check 2: 章节数(H1 >= 1 + H2 >= 3) ─────────────
  if lecture_md and lecture_md.exists() and lecture_md.stat().st_size >= 100:
    content = lecture_md.read_text(encoding="utf-8")
    h1_count = len(re.findall(r"^# ", content, re.MULTILINE))
    h2_count = len(re.findall(r"^## ", content, re.MULTILINE))
    if h1_count >= 1 and h2_count >= 3:
      passed.append("lecture_chapter_count")
    else:
      issues.append(
        f"chapter count too low: H1={h1_count}, H2={h2_count} "
        "(need H1>=1 and H2>=3)"
      )
      failed.append("lecture_chapter_count")

  # ── Check 3: output_final.html 存在 ─────────────────
  final_html = _resolve_final_html(work, final_dir=final_dir)
  if final_html.exists() and final_html.stat().st_size > 1000:
    passed.append("final_html_exists")
  else:
    size = final_html.stat().st_size if final_html.exists() else 0
    issues.append(f"output_final.html missing or too small (size={size})")
    failed.append("final_html_exists")

  # ── Check 4: image_refs 真实存在 ────────────────────
  if lecture_md and lecture_md.exists() and lecture_md.stat().st_size >= 100:
    content = lecture_md.read_text(encoding="utf-8")
    # wiki-link ![[...]] 与 md ![...](...) 两种语法
    wiki_refs = re.findall(r"!\[\[(.+?)\]\]", content)
    md_refs = re.findall(r"!\[.*?\]\((.+?)\)", content)
    image_refs = wiki_refs + md_refs
    lecture_dir = lecture_md.parent
    # 派生 stem(从 chapters.json)用于推断 <stem>/images/ 子目录
    stem = _read_video_stem(work)
    missing: list[str] = []
    for ref in image_refs:
      # 候选位置(兼容 md-link 与 wiki-link + 新旧布局):
      # 1. 原路径(支持 `<stem>/images/foo.png` md-link)
      # 2. 同目录 basename(支持 `foo.png` wiki-link)
      # 3. images 子目录 basename(W3 render 默认 images/ 旁路)
      # 4. <stem>/images/ 子目录(W3 render 实际布局:images 在 <stem>/ 下)
      basename = Path(ref).name
      candidates = [
        lecture_dir / ref,                       # 原路径
        lecture_dir / basename,                  # 同目录
        lecture_dir / "images" / basename,       # images 子目录
        lecture_dir / stem / "images" / basename,  # <stem>/images/(W3+)
      ]
      if not any(c.exists() for c in candidates):
        missing.append(ref)
    if not image_refs:
      # 没有图片引用不算失败(允许零配图)
      passed.append("image_refs_valid_no_images")
    elif not missing:
      passed.append(f"image_refs_valid({len(image_refs)})")
    else:
      issues.append(
        f"{len(missing)}/{len(image_refs)} image_refs missing: {missing[:3]}"
      )
      failed.append("image_refs_valid")

  return GatekeeperResult(
    ok=len(issues) == 0,
    issues=issues,
    checks_passed=passed,
    checks_failed=failed,
  )


__all__ = [
  "gatekeeper_check",
]
