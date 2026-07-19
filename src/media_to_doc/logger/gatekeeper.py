"""LE L2 审核层 — Gatekeeper(W8 落地)。

实现关键节点的机器可验证检查。
参考 ``_research/LE_DESIGN.md`` §3.2。

核心原则:停止条件 = 机器可验证命令,绝不"感觉差不多"。

W8 适配:产物布局从原型 ``inbox/raw/lecture.md`` 迁移到
``<work>/chapters/raw/<stem>.md`` + ``<work>/output_final.html``(W3 render 后)。

接口对比:
- 原型:``gatekeeper_check(inbox, work)`` — 两参数,产物在 inbox 内
- W8:``gatekeeper_check(work)`` — 单参数,产物在 work 内
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .pipeline_logger import GatekeeperResult


def _resolve_lecture_path(work: Path) -> Path | None:
  """从 ``<work>/chapters/chapters.json`` 派生 ``<work>/chapters/raw/<stem>.md``。"""
  chapters_json = work / "chapters" / "chapters.json"
  if not chapters_json.exists():
    return None
  try:
    data = json.loads(chapters_json.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return None
  stem = (data.get("video") or "").strip() or "output"
  return work / "chapters" / "raw" / stem / f"{stem}.md"


def _resolve_final_html(work: Path) -> Path:
  """最终 HTML 路径(``<work>/output_final.html``)。"""
  return work / "output_final.html"


def gatekeeper_check(work: Path) -> GatekeeperResult:
  """LE L2 审核层:4 项关键节点检查(W8 适配新产物布局)。

  检查项(全部机器可验证):
  1. chapters.json 存在 + render 产物 ``<stem>.md`` 存在且非空
  2. ``<stem>.md`` 至少 1 个 H1 + 3 个 H2 章节
  3. ``<work>/output_final.html`` 存在且 > 1000 bytes(longdoc 净化产物)
  4. 所有 image_refs 真实存在(允许无图场景)

  Returns
  -------
  GatekeeperResult
    含 ``ok`` / ``issues`` / ``checks_passed`` / ``checks_failed``
  """
  issues: list[str] = []
  passed: list[str] = []
  failed: list[str] = []

  lecture_md = _resolve_lecture_path(work)

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
  final_html = _resolve_final_html(work)
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
    missing: list[str] = []
    for ref in image_refs:
      # 候选位置:完整路径 / 同目录 basename / images 子目录 basename
      # (兼容 md-link `images/foo.png` 与 wiki-link `![[foo.png]]` 两种风格)
      basename = Path(ref).name
      candidates = [
        lecture_dir / ref,                       # 原路径
        lecture_dir / basename,                  # 同目录
        lecture_dir / "images" / basename,       # images 子目录(W3 render 默认)
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
