"""Stage 11 — ``verify``:门卫 gatekeeper + image_refs 校验。

输入:
- ``<work>/chapters/chapters.json``:章节元数据
- ``<drafts_dir>/chapter_NN.md``:每章节草稿(由 :mod:`draft` 产出)
- ``<drafts_dir>/images/gen_<uuid>.png``:AI 配图
- ``<drafts_dir>/<stem>.md``:render 阶段拼装的 markdown
- ``<drafts_dir>/<stem>_cleaned.md``:longdoc 阶段净化后的 markdown
- ``<drafts_dir>/<stem>_final.html``:longdoc 阶段最终 HTML

输出:
- ``<work>/verify/verify.json``:整体校验报告(``passed`` / ``failed`` /
  ``warnings`` 列表 + 各项检查详情)

校验项(4 项机器可验证):

1. **markdown 存在性** — render / longdoc 阶段的 3 个产物都存在
2. **章节完整性** — ``chapters.json`` 中所有章节对应 ``chapter_NN.md`` 都存在
3. **图像引用校验** — 所有 ``![[gen_xxx.png]]`` 与 ``![Image](...)`` 实际文件都
   存在(否则 fail);缺失 ``![[]]`` 退化为 ``_⚠️ 配图缺失:xxx_`` 的警告
4. **HTML 结构校验** — ``_final.html`` 可解析 / ``<title>`` 与首个 H1 一致 /
   顶层 H1 唯一 / 所有 ``<img>`` 含 alt

依赖:
- :mod:`beautifulsoup4` + :mod:`lxml`([longdoc] extras)
- 复用 :mod:`chapters` 的 :class:`ChaptersReport`

参考:TDD §5 数据流第 11 步 + PROJECT_DESCRIPTION §3.2 verify 行 +
     qa-gates.md §3 Phase 3 · 7 项(HTML 输出)。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .chapters import Chapter, ChaptersReport

# ─────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────

# 默认产物名后缀
_RENDERED_MD_SUFFIX = ".md"
_CLEANED_MD_SUFFIX = "_cleaned.md"
_FINAL_HTML_SUFFIX = "_final.html"

# 图像引用匹配:
# 1. ``![[gen_xxx.png]]`` 草稿 wiki-link
# 2. ``![Image](<stem>/images/gen_xxx.png)`` 拼装后标准 markdown
_WIKILINK_IMG_RE = re.compile(r"!\[\[([^\]]+\.png)\]\]")
_MD_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+\.png)\)")
_GENERIC_PNG_REF_RE = re.compile(r"([\w/_\-\.]+\.png)")

# verify.json 输出位置
_VERIFY_SUBDIR = "verify"
_VERIFY_FILENAME = "verify.json"


# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


@dataclass
class CheckResult:
  """单项检查结果。"""

  name: str
  passed: bool
  detail: str = ""
  failures: list[str] = field(default_factory=list)
  warnings: list[str] = field(default_factory=list)

  def to_dict(self) -> dict[str, Any]:
    return {
      "name": self.name,
      "passed": self.passed,
      "detail": self.detail,
      "failures": list(self.failures),
      "warnings": list(self.warnings),
    }


@dataclass
class VerifyReport:
  """整体校验结果(对应 ``verify.json``)。"""

  video: str = ""
  course_title: str = ""
  overall_passed: bool = True
  checks: list[CheckResult] = field(default_factory=list)

  @property
  def failures(self) -> list[str]:
    """所有 check 的失败项汇总(每项 ``[check_name] message``)。"""
    out: list[str] = []
    for c in self.checks:
      if not c.passed:
        for f in c.failures:
          out.append(f"[{c.name}] {f}")
    return out

  @property
  def warnings(self) -> list[str]:
    out: list[str] = []
    for c in self.checks:
      for w in c.warnings:
        out.append(f"[{c.name}] {w}")
    return out

  def to_dict(self) -> dict[str, Any]:
    return {
      "video": self.video,
      "course_title": self.course_title,
      "overall_passed": self.overall_passed,
      "failures": self.failures,
      "warnings": self.warnings,
      "checks": [c.to_dict() for c in self.checks],
    }

  def save(self, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
      json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
      encoding="utf-8",
    )


# ─────────────────────────────────────────────────────────────
# 工具:章节报告加载(与 render.py / draft.py 一致;W5 抽 chapters_io)
# ─────────────────────────────────────────────────────────────


def _load_chapters_report(path: Path) -> ChaptersReport:
  """从 ``chapters.json`` 反序列化。"""
  data = json.loads(path.read_text(encoding="utf-8"))
  chapters: list[Chapter] = []
  for raw in data.get("chapters", []):
    payload = {k: v for k, v in raw.items() if k != "duration_seconds"}
    chapters.append(Chapter(**payload))
  return ChaptersReport(
    video=data.get("video", ""),
    provider=data.get("provider", ""),
    model=data.get("model", ""),
    chapters=chapters,
  )


def _resolve_drafts_dir(work: Path) -> Path | None:
  """``<work>/chapters/raw/<video_stem>`` 派生(读 chapters.json 的 video)。"""
  chapters_json = work / "chapters" / "chapters.json"
  if not chapters_json.exists():
    return None
  data = json.loads(chapters_json.read_text(encoding="utf-8"))
  stem = (data.get("video") or "").strip() or "output"
  candidate = work / "chapters" / "raw" / stem
  return candidate if candidate.exists() else None


# ─────────────────────────────────────────────────────────────
# Check 1:markdown 存在性
# ─────────────────────────────────────────────────────────────


def _check_outputs_exist(
  drafts_dir: Path | None,
  stem: str,
) -> CheckResult:
  """校验 ``<stem>.md`` / ``<stem>_cleaned.md`` / ``<stem>_final.html`` 都存在。"""
  result = CheckResult(
    name="outputs_exist",
    passed=True,
    detail=f"drafts_dir={drafts_dir}, stem={stem}",
  )
  if drafts_dir is None:
    result.passed = False
    result.failures.append("drafts_dir 不存在(无法定位 render / longdoc 产物)")
    return result

  expected = [
    (drafts_dir / f"{stem}{_RENDERED_MD_SUFFIX}", "rendered .md"),
    (drafts_dir / f"{stem}{_CLEANED_MD_SUFFIX}", "cleaned .md"),
    (drafts_dir / f"{stem}{_FINAL_HTML_SUFFIX}", "final .html"),
  ]
  for path, label in expected:
    if not path.exists():
      result.passed = False
      result.failures.append(f"缺少 {label}:{path}")
  return result


# ─────────────────────────────────────────────────────────────
# Check 2:章节完整性
# ─────────────────────────────────────────────────────────────


def _check_chapters_complete(
  work: Path,
  drafts_dir: Path | None,
  chapters_dir: Path | None = None,
) -> CheckResult:
  """校验 ``chapters.json`` 中所有章节对应 ``chapter_NN.md`` 都存在。"""
  result = CheckResult(
    name="chapters_complete",
    passed=True,
    detail=f"work={work}",
  )
  c_dir = chapters_dir or (work / "chapters")
  chapters_json = c_dir / "chapters.json"
  if not chapters_json.exists():
    result.passed = False
    result.failures.append(f"缺少 chapters.json:{chapters_json}")
    return result
  if drafts_dir is None:
    result.passed = False
    result.failures.append("drafts_dir 不存在,无法校验章节草稿")
    return result

  report = _load_chapters_report(chapters_json)
  for ch in report.chapters:
    expected = drafts_dir / f"chapter_{ch.idx:02d}.md"
    if not expected.exists():
      result.passed = False
      result.failures.append(f"第 {ch.idx} 章草稿缺失:{expected}")
  if not report.chapters:
    result.warnings.append("chapters.json 章节列表为空")
  return result


# ─────────────────────────────────────────────────────────────
# Check 3:图像引用校验
# ─────────────────────────────────────────────────────────────


def _collect_image_refs(md_text: str) -> list[tuple[str, str]]:
  """从 markdown 文本提取所有 png 引用,返回 ``(alt, ref)`` 列表。

  支持两种语法:
  - ``![[gen_xxx.png]]`` — wiki-link(草稿 + 净化前)
  - ``![alt](path/gen_xxx.png)`` — 标准 markdown(拼装 / 净化后)
  """
  out: list[tuple[str, str]] = []
  for m in _WIKILINK_IMG_RE.finditer(md_text):
    out.append(("Image", m.group(1).strip()))
  for m in _MD_IMG_RE.finditer(md_text):
    out.append((m.group(1).strip(), m.group(2).strip()))
  return out


def _check_image_refs(
  drafts_dir: Path | None,
  rendered_md: Path | None,
  cleaned_md: Path | None,
) -> CheckResult:
  """校验所有图像引用的实际文件都存在。

  拼装后的 md 引用形如 ``<stem>/images/gen_xxx.png`` → 在
  ``<drafts_dir>/images/gen_xxx.png`` 找。
  草稿 wiki-link 引用形如 ``gen_xxx.png`` → 在 ``<drafts_dir>/images/gen_xxx.png`` 找。
  """
  result = CheckResult(
    name="image_refs",
    passed=True,
    detail="",
  )
  if drafts_dir is None:
    result.passed = False
    result.failures.append("drafts_dir 不存在,无法校验图像引用")
    return result

  images_dir = drafts_dir / "images"
  sources_checked: list[Path] = []
  if rendered_md and rendered_md.exists():
    sources_checked.append(rendered_md)
  if cleaned_md and cleaned_md.exists():
    sources_checked.append(cleaned_md)
  if not sources_checked:
    result.warnings.append("没有可校验的 markdown(rendered / cleaned 都缺)")
    return result

  total_refs = 0
  missing: list[str] = []
  for src in sources_checked:
    text = src.read_text(encoding="utf-8")
    for _alt, ref in _collect_image_refs(text):
      total_refs += 1
      # ref 可能是 ``<stem>/images/gen_xxx.png`` 或 ``images/gen_xxx.png`` 或
      # ``gen_xxx.png``(草稿 wiki-link)
      filename = ref.rsplit("/", 1)[-1]
      if not filename.endswith(".png"):
        continue
      target = images_dir / filename
      if not target.exists():
        missing.append(f"{src.name} → {ref}")

  if missing:
    result.passed = False
    result.failures.extend(missing[:50])  # 防止报告过大
    if len(missing) > 50:
      result.failures.append(f"... 还有 {len(missing) - 50} 个缺失图像(已截断)")

  result.detail = (
    f"total_refs={total_refs}, images_dir={images_dir}, missing={len(missing)}"
  )
  return result


# ─────────────────────────────────────────────────────────────
# Check 4:HTML 结构
# ─────────────────────────────────────────────────────────────


def _check_html_structure(
  final_html: Path | None,
) -> CheckResult:
  """校验 ``_final.html`` 可解析 / ``<title>`` 与首个 H1 一致 / 顶层 H1 唯一 /
  所有 ``<img>`` 含 alt。
  """
  result = CheckResult(
    name="html_structure",
    passed=True,
    detail="",
  )
  if final_html is None or not final_html.exists():
    result.passed = False
    result.failures.append(f"final HTML 缺失:{final_html}")
    return result

  try:
    from bs4 import BeautifulSoup  # type: ignore[import-not-found]
  except ImportError as exc:
    raise ImportError(
      "verify 需要 beautifulsoup4;请 `uv add media_to_doc[longdoc]`"
    ) from exc

  html_text = final_html.read_text(encoding="utf-8")
  soup = BeautifulSoup(html_text, "lxml")

  # 1. <title>
  title_tag = soup.find("title")
  if title_tag is None or not (title_tag.text or "").strip():
    result.passed = False
    result.failures.append("<title> 缺失或为空")
    title_text = ""
  else:
    title_text = title_tag.text.strip()

  # 2. 顶层 H1 唯一
  h1_tags = soup.find_all("h1")
  if len(h1_tags) == 0:
    result.passed = False
    result.failures.append("顶层 H1 缺失")
  elif len(h1_tags) > 1:
    result.passed = False
    result.failures.append(f"顶层 H1 不唯一(共 {len(h1_tags)} 个)")

  # 3. <title> 与首个 H1 一致
  if h1_tags:
    first_h1 = (h1_tags[0].text or "").strip()
    if title_text and first_h1 and first_h1 not in title_text and title_text not in first_h1:
      result.warnings.append(
        f"<title>={title_text!r} 与首个 H1={first_h1!r} 不一致"
      )

  # 4. 所有 <img> 含 alt
  imgs = soup.find_all("img")
  for img in imgs:
    if not img.get("alt"):
      src = img.get("src", "<no src>")
      result.passed = False
      result.failures.append(f"<img src={src}> 缺少 alt 属性")

  result.detail = (
    f"h1_count={len(h1_tags)}, img_count={len(imgs)}, title={title_text!r}"
  )
  return result


# ─────────────────────────────────────────────────────────────
# 公开 API
# ─────────────────────────────────────────────────────────────


def verify_pipeline(
  work: Path,
  *,
  chapters_dir: Path | None = None,
  drafts_dir: Path | None = None,
  output_stem: str | None = None,
  write_report: bool = True,
) -> VerifyReport:
  """Stage 11:跑 4 项机器可验证检查,输出 :class:`VerifyReport` + 可选写
  ``<work>/verify/verify.json``。

  Parameters
  ----------
  work : Path
    work 根目录
  chapters_dir : Path | None
    ``chapters.json`` 所在目录(默认 ``<work>/chapters``)
  drafts_dir : Path | None
    草稿/产物目录(默认从 chapters.json 派生)
  output_stem : str | None
    产物文件 stem(默认 ``drafts_dir.name``)
  write_report : bool
    是否写 ``<work>/verify/verify.json``(默认 True)

  Returns
  -------
  VerifyReport
    整体校验结果(已落盘:verify.json)
  """
  c_dir = chapters_dir or (work / "chapters")
  chapters_json = c_dir / "chapters.json"
  if drafts_dir is None and chapters_json.exists():
    drafts_dir = _resolve_drafts_dir(work)
  if output_stem is None and drafts_dir is not None:
    output_stem = drafts_dir.name
  if output_stem is None:
    output_stem = "output"

  rendered_md = (
    drafts_dir / f"{output_stem}{_RENDERED_MD_SUFFIX}" if drafts_dir else None
  )
  cleaned_md = (
    drafts_dir / f"{output_stem}{_CLEANED_MD_SUFFIX}" if drafts_dir else None
  )
  final_html = (
    drafts_dir / f"{output_stem}{_FINAL_HTML_SUFFIX}" if drafts_dir else None
  )

  # 视频名(chapters.json 派生)
  video = ""
  if chapters_json.exists():
    data = json.loads(chapters_json.read_text(encoding="utf-8"))
    video = (data.get("video") or "").strip()

  checks: list[CheckResult] = [
    _check_outputs_exist(drafts_dir, output_stem),
    _check_chapters_complete(work, drafts_dir, chapters_dir=c_dir),
    _check_image_refs(drafts_dir, rendered_md, cleaned_md),
    _check_html_structure(final_html),
  ]

  overall_passed = all(c.passed for c in checks)
  report = VerifyReport(
    video=video,
    course_title=output_stem,
    overall_passed=overall_passed,
    checks=checks,
  )

  if write_report:
    report.save(work / _VERIFY_SUBDIR / _VERIFY_FILENAME)

  return report


__all__ = [
  "CheckResult",
  "VerifyReport",
  "verify_pipeline",
]
