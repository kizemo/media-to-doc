"""verify stage 测试。

要点:
- 验证 4 项机器可检查:
  1. markdown 产物存在性(rendered .md / cleaned .md / final .html)
  2. 章节完整性(chapters.json 章节对应 chapter_NN.md)
  3. 图像引用校验(所有 .png 引用文件存在)
  4. HTML 结构(<title> / 唯一 H1 / <img> 含 alt)
- 验证 verify.json 写入 + 整体 passed 标志
- 验证 CheckResult / VerifyReport 数据类
- 验证 _collect_image_refs 工具(wiki-link + md img 两种语法)
"""

from __future__ import annotations

import json
from pathlib import Path

from media_to_doc.pipeline import verify as vf
from media_to_doc.pipeline.chapters import Chapter, ChaptersReport
from media_to_doc.pipeline.verify import (
  CheckResult,
  VerifyReport,
  verify_pipeline,
)

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


def _seed_chapters_json(
  work: Path, video: str = "course-x", count: int = 2
) -> None:
  chapters_dir = work / "chapters"
  chapters_dir.mkdir(parents=True, exist_ok=True)
  chapters = [
    Chapter(
      idx=i,
      title=f"第 {i} 章",
      summary=f"摘要 {i}",
      start_seconds=float(i * 100),
      end_seconds=float(i * 100 + 60),
      key_points=[f"要点 {i}"],
    )
    for i in range(1, count + 1)
  ]
  ChaptersReport(video=video, provider="fake", model="fm", chapters=chapters).save(
    chapters_dir / "chapters.json"
  )


def _seed_drafts(
  work: Path, stem: str = "course-x", *, count: int = 2, with_image: bool = True
) -> Path:
  drafts = work / "chapters" / "raw" / stem
  drafts.mkdir(parents=True, exist_ok=True)
  for i in range(1, count + 1):
    body = f"## 第 {i} 章\n\n正文段\n"
    if with_image and i == 1:
      body += "![[gen_abc.png]]\n"
    (drafts / f"chapter_{i:02d}.md").write_text(
      f"# 第 {i} 章\n\n> 摘要\n\n---\n\n{body}", encoding="utf-8"
    )
  return drafts


def _seed_images(drafts: Path, names: list[str]) -> None:
  img_dir = drafts / "images"
  img_dir.mkdir(parents=True, exist_ok=True)
  for n in names:
    (img_dir / n).write_bytes(b"\x89PNG\r\n\x1a\n")


def _seed_outputs(
  drafts: Path,
  stem: str,
  *,
  cleaned: bool = True,
  html: bool = True,
  with_images: list[str] | None = None,
) -> None:
  """写 rendered .md / cleaned .md / final.html,可选。"""
  rendered = f"# 主标题\n\n## 第一章\n\n![]({stem}/images/gen_abc.png)\n"
  (drafts / f"{stem}.md").write_text(rendered, encoding="utf-8")
  if cleaned:
    (drafts / f"{stem}_cleaned.md").write_text(rendered, encoding="utf-8")
  if html:
    (drafts / f"{stem}_final.html").write_text(
      "<!doctype html><html><head><title>主标题</title></head>"
      "<body><h1>主标题</h1>"
      f'<p><img src="{stem}/images/gen_abc.png" alt="x"></p>'
      "</body></html>",
      encoding="utf-8",
    )
  if with_images:
    _seed_images(drafts, with_images)


# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


def test_check_result_to_dict() -> None:
  c = CheckResult(
    name="t", passed=False, detail="d", failures=["f1"], warnings=["w1"]
  )
  d = c.to_dict()
  assert d["name"] == "t"
  assert d["passed"] is False
  assert d["detail"] == "d"
  assert d["failures"] == ["f1"]
  assert d["warnings"] == ["w1"]


def test_verify_report_aggregates_failures_and_warnings() -> None:
  c1 = CheckResult(name="a", passed=True, failures=[])
  c2 = CheckResult(
    name="b", passed=False, failures=["b 失败 1", "b 失败 2"], warnings=["b 警告"]
  )
  c3 = CheckResult(name="c", passed=True, warnings=["c 警告"])
  r = VerifyReport(video="v", course_title="v", overall_passed=False,
                   checks=[c1, c2, c3])
  assert r.failures == ["[b] b 失败 1", "[b] b 失败 2"]
  assert r.warnings == ["[b] b 警告", "[c] c 警告"]


def test_verify_report_save(tmp_path: Path) -> None:
  r = VerifyReport(
    video="x", course_title="x", overall_passed=True, checks=[]
  )
  p = tmp_path / "verify.json"
  r.save(p)
  assert p.exists()
  data = json.loads(p.read_text(encoding="utf-8"))
  assert data["overall_passed"] is True
  assert data["video"] == "x"
  assert data["failures"] == []
  assert data["warnings"] == []


# ─────────────────────────────────────────────────────────────
# _collect_image_refs
# ─────────────────────────────────────────────────────────────


def test_collect_image_refs_wikilink_and_md() -> None:
  text = (
    "前段 ![[gen_aaa.png]] 中段 "
    "![Image](course/images/gen_bbb.png) 尾段"
  )
  refs = vf._collect_image_refs(text)
  assert ("Image", "gen_aaa.png") in refs
  assert ("Image", "course/images/gen_bbb.png") in refs


def test_collect_image_refs_empty() -> None:
  assert vf._collect_image_refs("") == []
  assert vf._collect_image_refs("纯文本无图") == []


# ─────────────────────────────────────────────────────────────
# 工具
# ─────────────────────────────────────────────────────────────


def test_resolve_drafts_dir_missing_chapters_returns_none(tmp_path: Path) -> None:
  assert vf._resolve_drafts_dir(tmp_path) is None


def test_resolve_drafts_dir_derives_from_chapters_json(tmp_path: Path) -> None:
  work = tmp_path
  _seed_chapters_json(work, video="lesson-9")
  _seed_drafts(work, stem="lesson-9", count=1, with_image=False)
  drafts = vf._resolve_drafts_dir(work)
  assert drafts == work / "chapters" / "raw" / "lesson-9"


# ─────────────────────────────────────────────────────────────
# Check 1: outputs_exist
# ─────────────────────────────────────────────────────────────


def test_outputs_exist_all_present(tmp_path: Path) -> None:
  drafts = _seed_drafts(tmp_path, stem="x", count=1, with_image=False)
  _seed_outputs(drafts, "x")
  r = vf._check_outputs_exist(drafts, "x")
  assert r.passed is True
  assert r.failures == []


def test_outputs_exist_missing_cleaned(tmp_path: Path) -> None:
  drafts = _seed_drafts(tmp_path, stem="x", count=1, with_image=False)
  # 不写 cleaned 和 html
  (drafts / "x.md").write_text("# x", encoding="utf-8")
  r = vf._check_outputs_exist(drafts, "x")
  assert r.passed is False
  assert any("cleaned .md" in f for f in r.failures)
  assert any("final .html" in f for f in r.failures)


def test_outputs_exist_no_drafts_dir(tmp_path: Path) -> None:
  r = vf._check_outputs_exist(None, "x")
  assert r.passed is False
  assert any("drafts_dir 不存在" in f for f in r.failures)


# ─────────────────────────────────────────────────────────────
# Check 2: chapters_complete
# ─────────────────────────────────────────────────────────────


def test_chapters_complete_all_present(tmp_path: Path) -> None:
  work = tmp_path
  _seed_chapters_json(work, video="x", count=3)
  _seed_drafts(work, stem="x", count=3, with_image=False)
  r = vf._check_chapters_complete(work, work / "chapters" / "raw" / "x")
  assert r.passed is True
  assert r.failures == []


def test_chapters_complete_missing_chapter_md(tmp_path: Path) -> None:
  work = tmp_path
  _seed_chapters_json(work, video="x", count=3)
  _seed_drafts(work, stem="x", count=2, with_image=False)  # 缺 chapter_03
  r = vf._check_chapters_complete(work, work / "chapters" / "raw" / "x")
  assert r.passed is False
  assert any("第 3 章" in f for f in r.failures)


def test_chapters_complete_no_chapters_json(tmp_path: Path) -> None:
  r = vf._check_chapters_complete(tmp_path, None)
  assert r.passed is False
  assert any("缺少 chapters.json" in f for f in r.failures)


# ─────────────────────────────────────────────────────────────
# Check 3: image_refs
# ─────────────────────────────────────────────────────────────


def test_image_refs_all_resolve(tmp_path: Path) -> None:
  work = tmp_path
  drafts = _seed_drafts(work, stem="x", count=2, with_image=True)
  _seed_images(drafts, ["gen_abc.png"])
  _seed_outputs(drafts, "x", with_images=["gen_abc.png"])
  r = vf._check_image_refs(drafts, drafts / "x.md", drafts / "x_cleaned.md")
  assert r.passed is True
  assert "missing=0" in r.detail


def test_image_refs_missing_file_fails(tmp_path: Path) -> None:
  work = tmp_path
  drafts = _seed_drafts(work, stem="x", count=1, with_image=True)
  # 不 seed images → gen_abc.png 不存在
  (drafts / "x.md").write_text("![[gen_abc.png]]\n", encoding="utf-8")
  r = vf._check_image_refs(drafts, drafts / "x.md", None)
  assert r.passed is False
  assert any("gen_abc.png" in f for f in r.failures)


def test_image_refs_no_md_warns(tmp_path: Path) -> None:
  work = tmp_path
  drafts = _seed_drafts(work, stem="x", count=1, with_image=False)
  r = vf._check_image_refs(drafts, None, None)
  assert r.passed is True
  assert any("没有可校验的 markdown" in w for w in r.warnings)


def test_image_refs_no_drafts_dir_fails(tmp_path: Path) -> None:
  r = vf._check_image_refs(None, None, None)
  assert r.passed is False


# ─────────────────────────────────────────────────────────────
# Check 4: html_structure
# ─────────────────────────────────────────────────────────────


def test_html_structure_valid(tmp_path: Path) -> None:
  html = tmp_path / "x_final.html"
  html.write_text(
    "<!doctype html><html><head><title>主标题</title></head>"
    "<body><h1>主标题</h1>"
    '<p><img src="x.png" alt="A"></p>'
    "</body></html>",
    encoding="utf-8",
  )
  r = vf._check_html_structure(html)
  assert r.passed is True


def test_html_structure_missing_title_fails(tmp_path: Path) -> None:
  html = tmp_path / "x_final.html"
  html.write_text(
    "<!doctype html><html><head></head><body><h1>x</h1></body></html>",
    encoding="utf-8",
  )
  r = vf._check_html_structure(html)
  assert r.passed is False
  assert any("<title>" in f for f in r.failures)


def test_html_structure_multiple_h1_fails(tmp_path: Path) -> None:
  html = tmp_path / "x_final.html"
  html.write_text(
    "<!doctype html><html><head><title>x</title></head>"
    "<body><h1>a</h1><h1>b</h1></body></html>",
    encoding="utf-8",
  )
  r = vf._check_html_structure(html)
  assert r.passed is False
  assert any("H1 不唯一" in f for f in r.failures)


def test_html_structure_img_without_alt_fails(tmp_path: Path) -> None:
  html = tmp_path / "x_final.html"
  html.write_text(
    "<!doctype html><html><head><title>x</title></head>"
    "<body><h1>x</h1><p><img src='x.png'></p></body></html>",
    encoding="utf-8",
  )
  r = vf._check_html_structure(html)
  assert r.passed is False
  assert any("alt" in f for f in r.failures)


def test_html_structure_missing_file_fails(tmp_path: Path) -> None:
  r = vf._check_html_structure(tmp_path / "nope.html")
  assert r.passed is False
  assert any("缺失" in f for f in r.failures)


# ─────────────────────────────────────────────────────────────
# 公开 API: verify_pipeline
# ─────────────────────────────────────────────────────────────


def test_verify_pipeline_all_pass(tmp_path: Path) -> None:
  work = tmp_path
  _seed_chapters_json(work, video="x", count=2)
  drafts = _seed_drafts(work, stem="x", count=2, with_image=True)
  _seed_outputs(drafts, "x", with_images=["gen_abc.png"])
  report = verify_pipeline(work)
  assert report.overall_passed is True
  assert report.video == "x"
  assert report.course_title == "x"
  assert len(report.checks) == 4
  assert all(c.passed for c in report.checks)
  # 报告应已写盘
  report_path = work / "verify" / "verify.json"
  assert report_path.exists()


def test_verify_pipeline_missing_outputs_fails(tmp_path: Path) -> None:
  work = tmp_path
  _seed_chapters_json(work, video="y", count=1)
  _seed_drafts(work, stem="y", count=1, with_image=True)
  # 不写 outputs
  report = verify_pipeline(work)
  assert report.overall_passed is False
  # outputs_exist + image_refs 失败
  failed_names = [c.name for c in report.checks if not c.passed]
  assert "outputs_exist" in failed_names


def test_verify_pipeline_explicit_paths(tmp_path: Path) -> None:
  work = tmp_path
  alt_work = tmp_path / "alt"
  _seed_chapters_json(alt_work, video="z", count=1)
  drafts = _seed_drafts(alt_work, stem="z", count=1, with_image=False)
  _seed_outputs(drafts, "z", with_images=["gen_abc.png"])
  report = verify_pipeline(
    work,  # work 路径与实际产物目录无关
    chapters_dir=alt_work / "chapters",
    drafts_dir=drafts,
    output_stem="z",
  )
  assert report.overall_passed is True


def test_verify_pipeline_no_write_report(tmp_path: Path) -> None:
  work = tmp_path
  _seed_chapters_json(work, video="a", count=1)
  _seed_drafts(work, stem="a", count=1, with_image=False)
  drafts = work / "chapters" / "raw" / "a"
  _seed_outputs(drafts, "a", with_images=["gen_abc.png"])
  report = verify_pipeline(work, write_report=False)
  assert report.overall_passed is True
  assert not (work / "verify" / "verify.json").exists()


def test_verify_pipeline_default_drafts_dir(tmp_path: Path) -> None:
  """未传 drafts_dir 时,自动从 chapters.json 派生。"""
  work = tmp_path
  _seed_chapters_json(work, video="d", count=1)
  drafts = _seed_drafts(work, stem="d", count=1, with_image=False)
  _seed_outputs(drafts, "d", with_images=["gen_abc.png"])
  report = verify_pipeline(work)
  assert report.course_title == "d"
  assert report.overall_passed is True
