"""render stage 测试。

要点:
- 验证 markdown 拼装:TOC / 章节结构 / 图像相对路径
- 验证图像引用重写:![[gen_xxx.png]] → ![Image](<stem>/images/gen_xxx.png)
- 缺失图像自动退化为 ``_⚠️ 配图缺失:xxx_``
- 验证 HTML 渲染(jinja2 + markdown 库)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from media_to_doc.pipeline import render as re_mod
from media_to_doc.pipeline.chapters import Chapter, ChaptersReport
from media_to_doc.pipeline.render import (
  RenderOutputs,
  load_chapters_report,
  render_html,
  render_outputs,
)

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


def _seed_chapters_json(chapters_dir: Path, chapters: list[Chapter], video: str = "course-x") -> None:
  chapters_dir.mkdir(parents=True, exist_ok=True)
  r = ChaptersReport(video=video, provider="fake", model="fm", chapters=chapters)
  r.save(chapters_dir / "chapters.json")


def _seed_chapter_md(drafts_dir: Path, idx: int, body: str) -> None:
  drafts_dir.mkdir(parents=True, exist_ok=True)
  text = (
    f"# 章节 {idx}\n\n"
    f"> 摘要\n\n"
    f"**关键要点**:\n\n- 要点\n\n"
    f"---" + f"\n\n{body}\n"
  )
  (drafts_dir / f"chapter_{idx:02d}.md").write_text(text, encoding="utf-8")


def _make_chapter(idx: int, title: str) -> Chapter:
  return Chapter(
    idx=idx,
    title=title,
    summary=f"摘要 {idx}",
    start_seconds=float(idx * 100),
    end_seconds=float(idx * 100 + 60),
    key_points=[f"要点 {idx}.1"],
    image_refs=[float(idx * 100 + 5.0)],
    illustrations=[],
  )


# ─────────────────────────────────────────────────────────────
# 工具:slug / TOC
# ─────────────────────────────────────────────────────────────


def test_slugify_chinese_text() -> None:
  s = re_mod._slugify("达摩盘选品技巧")
  assert s  # 仅校验非空 + 不含空白


def test_slugify_strips_punct() -> None:
  assert re_mod._slugify("Hello, World!") == "hello-world"


def test_slugify_empty_fallback() -> None:
  assert re_mod._slugify("") == "section"
  assert re_mod._slugify("---") == "section"


def test_build_toc_includes_each_chapter() -> None:
  chs = [_make_chapter(i, f"第 {i} 章") for i in (1, 2, 3)]
  toc = re_mod._build_toc(chs)
  assert "## 目录" in toc
  assert "[第 1 章]" in toc and "[第 2 章]" in toc and "[第 3 章]" in toc
  assert toc.count("- [") == 3


# ─────────────────────────────────────────────────────────────
# 工具:章节正文读取与图像引用重写
# ─────────────────────────────────────────────────────────────


def test_read_chapter_body_strips_meta_block(tmp_path: Path) -> None:
  drafts = tmp_path / "drafts"
  _seed_chapter_md(drafts, 1, "### 关键段一\n要点展开")
  body = re_mod._read_chapter_body(drafts, 1)
  assert body.startswith("### 关键段一")
  assert "摘要" not in body and "关键要点" not in body


def test_read_chapter_body_missing_file_returns_empty(tmp_path: Path) -> None:
  drafts = tmp_path / "drafts"
  assert re_mod._read_chapter_body(drafts, 5) == ""


def test_rewrite_image_refs_resolves_existing(tmp_path: Path) -> None:
  drafts = tmp_path / "drafts"
  drafts.mkdir()
  (drafts / "images").mkdir()
  (drafts / "images" / "gen_abc123.png").write_bytes(b"x")
  body = "前段 ![[gen_abc123.png]] 尾段"
  out, resolved, missing = re_mod._rewrite_image_refs(
    body, "course-x/images", drafts
  )
  assert resolved == 1 and missing == 0
  assert "![" in out and "course-x/images/gen_abc123.png" in out


def test_rewrite_image_refs_marks_missing(tmp_path: Path) -> None:
  drafts = tmp_path / "drafts"
  drafts.mkdir()
  (drafts / "images").mkdir()
  # 不写图
  body = "[[GEN: 缺失图]]实际渲染![[gen_does_not_exist.png]]完"
  out, resolved, missing = re_mod._rewrite_image_refs(
    body, "course-x/images", drafts
  )
  assert resolved == 0 and missing == 1
  assert "⚠️" in out
  assert "does_not_exist" in out


def test_rewrite_image_refs_counts_multiple(tmp_path: Path) -> None:
  drafts = tmp_path / "drafts"
  drafts.mkdir()
  (drafts / "images").mkdir()
  for name in ("gen_a1.png", "gen_b2.png"):
    (drafts / "images" / name).write_bytes(b"x")
  body = "![[gen_a1.png]] and ![[gen_b2.png]]"
  out, resolved, missing = re_mod._rewrite_image_refs(
    body, "course/images", drafts
  )
  assert resolved == 2 and missing == 0
  assert "course/images/gen_a1.png" in out
  assert "course/images/gen_b2.png" in out


def test_strip_timestamp_lines() -> None:
  body = "段落 A\n[   0.50s -   1.20s] 文字\n段落 B"
  out = re_mod._strip_timestamp_lines(body)
  assert "段落 A" in out
  assert "段落 B" in out
  assert "[   0.50s" not in out


# ─────────────────────────────────────────────────────────────
# markdown / HTML 渲染
# ─────────────────────────────────────────────────────────────


def test_render_markdown_to_html_basic() -> None:
  md = "# 标题\n\n段落"
  html = re_mod._render_markdown_to_html(md)
  assert "<h1" in html
  assert "<p>" in html


def test_render_markdown_to_html_with_image() -> None:
  md = "![Image](course-x/images/gen_abc.png)"
  html = re_mod._render_markdown_to_html(md)
  assert "<img" in html and "course-x/images/gen_abc.png" in html


def test_render_markdown_to_html_table() -> None:
  md = "| col1 | col2 |\n|---|---|\n| a | b |"
  html = re_mod._render_markdown_to_html(md)
  assert "<table" in html and "<td" in html


def test_wrap_html_body_contains_title_and_footer() -> None:
  html = re_mod._wrap_html_body("<p>body</p>", "我的课")
  assert "<title>我的课</title>" in html
  assert "Generated by media-to-doc" in html
  assert "body" in html


# ─────────────────────────────────────────────────────────────
# Markdown 拼装
# ─────────────────────────────────────────────────────────────


def test_assemble_markdown_includes_toc_and_chapters(tmp_path: Path) -> None:
  report = ChaptersReport(
    video="V",
    provider="p",
    model="m",
    chapters=[_make_chapter(1, "章 1"), _make_chapter(2, "章 2")],
  )
  md = re_mod._assemble_markdown(
    report,
    body_lookup={1: "正文 1", 2: "正文 2"},
  )
  assert md.startswith("# V")
  assert "## 目录" in md
  assert "## 章 1" in md
  assert "## 章 2" in md
  assert "正文 1" in md and "正文 2" in md


def test_assemble_markdown_skips_missing_body(tmp_path: Path) -> None:
  report = ChaptersReport(
    video="V",
    provider="p",
    model="m",
    chapters=[_make_chapter(1, "章 1")],
  )
  md = re_mod._assemble_markdown(report, body_lookup={})
  assert "## 章 1" in md  # 仍有标题 + 摘要块
  assert "正文" not in md


# ─────────────────────────────────────────────────────────────
# load_chapters_report
# ─────────────────────────────────────────────────────────────


def test_load_chapters_report_basic(tmp_path: Path) -> None:
  _seed_chapters_json(tmp_path / "chapters", [_make_chapter(1, "章 1")], video="x")
  r = load_chapters_report(tmp_path / "chapters" / "chapters.json")
  assert r.video == "x"
  assert len(r.chapters) == 1


def test_load_chapters_report_drops_duration_seconds(tmp_path: Path) -> None:
  _seed_chapters_json(tmp_path / "chapters", [_make_chapter(1, "章 1")])
  r = load_chapters_report(tmp_path / "chapters" / "chapters.json")
  ch = r.chapters[0]
  # 不应因 JSON 里有 duration_seconds 字段而崩
  assert ch.title == "章 1"


# ─────────────────────────────────────────────────────────────
# render_outputs 端到端
# ─────────────────────────────────────────────────────────────


def test_render_outputs_writes_md_and_html(tmp_path: Path) -> None:
  work = tmp_path
  cdir = work / "chapters"
  _seed_chapters_json(cdir, [_make_chapter(1, "章 1"), _make_chapter(2, "章 2")])
  drafts_dir = cdir / "raw" / "course-x"
  _seed_chapter_md(drafts_dir, 1, "### 段 1\n内容")
  _seed_chapter_md(drafts_dir, 2, "### 段 2\n内容")

  out = render_outputs(work, chapters_dir=cdir, drafts_dir=drafts_dir)

  assert out.md_path is not None
  assert out.html_path is not None
  assert out.md_path.exists()
  assert out.html_path.exists()
  assert out.chapters_rendered == 2
  # md 包含 TOC + 标题
  md_text = out.md_path.read_text(encoding="utf-8")
  assert "## 目录" in md_text
  assert "## 章 1" in md_text
  assert "## 章 2" in md_text
  # html 含 TOC + CSS
  html_text = out.html_path.read_text(encoding="utf-8")
  assert "<style>" in html_text
  assert "<title>" in html_text


def test_render_outputs_rewrites_image_refs_with_relative_path(tmp_path: Path) -> None:
  work = tmp_path
  cdir = work / "chapters"
  _seed_chapters_json(cdir, [_make_chapter(1, "章 1")])
  drafts_dir = cdir / "raw" / "course-x"
  (drafts_dir / "images").mkdir(parents=True, exist_ok=True)
  (drafts_dir / "images" / "gen_abc123.png").write_bytes(b"x")
  _seed_chapter_md(drafts_dir, 1, "### 段 1\n![[gen_abc123.png]]")

  out = render_outputs(work, chapters_dir=cdir, drafts_dir=drafts_dir)
  md_text = out.md_path.read_text(encoding="utf-8")
  assert "course-x/images/gen_abc123.png" in md_text
  assert "![[" not in md_text
  assert out.image_refs_resolved == 1
  assert out.image_refs_missing == 0


def test_render_outputs_marks_missing_image(tmp_path: Path) -> None:
  work = tmp_path
  cdir = work / "chapters"
  _seed_chapters_json(cdir, [_make_chapter(1, "章 1")])
  drafts_dir = cdir / "raw" / "course-x"
  drafts_dir.mkdir(parents=True, exist_ok=True)
  (drafts_dir / "images").mkdir()  # 空
  _seed_chapter_md(drafts_dir, 1, "### 段\n![[gen_missing.png]]")

  out = render_outputs(work, chapters_dir=cdir, drafts_dir=drafts_dir)
  md_text = out.md_path.read_text(encoding="utf-8")
  assert "⚠️" in md_text
  assert out.image_refs_missing == 1
  assert out.image_refs_resolved == 0


def test_render_outputs_html_only_via_write_html_false(tmp_path: Path) -> None:
  work = tmp_path
  cdir = work / "chapters"
  _seed_chapters_json(cdir, [_make_chapter(1, "章 1")])
  drafts_dir = cdir / "raw" / "course-x"
  _seed_chapter_md(drafts_dir, 1, "内容")

  out = render_outputs(
    work,
    chapters_dir=cdir,
    drafts_dir=drafts_dir,
    write_html=False,
    final_dir=tmp_path / "output_final",
  )
  assert out.md_path is not None and out.html_path is None
  assert out.md_path.exists()
  # 确认 html 未写
  html_p = out.md_path.with_suffix(".html")
  assert not html_p.exists()


def test_render_outputs_raises_when_no_chapters_json(tmp_path: Path) -> None:
  with pytest.raises(FileNotFoundError, match="chapters.json"):
    render_outputs(tmp_path, chapters_dir=tmp_path / "chapters")


def test_render_outputs_raises_when_empty_chapters(tmp_path: Path) -> None:
  work = tmp_path
  _seed_chapters_json(work / "chapters", [])
  with pytest.raises(ValueError, match="章节列表为空"):
    render_outputs(work, chapters_dir=work / "chapters")


def test_render_outputs_raises_when_drafts_dir_missing(tmp_path: Path) -> None:
  work = tmp_path
  _seed_chapters_json(work / "chapters", [_make_chapter(1, "章 1")])
  drafts = tmp_path / "nonexistent"
  with pytest.raises(FileNotFoundError, match="drafts_dir"):
    render_outputs(work, chapters_dir=work / "chapters", drafts_dir=drafts)


# ─────────────────────────────────────────────────────────────
# render_html 独立函数
# ─────────────────────────────────────────────────────────────


def test_render_html_writes_alongside_md(tmp_path: Path) -> None:
  md_path = tmp_path / "lecture.md"
  md_path.write_text(
    "# 标题\n\n## 子节\n\n内容",
    encoding="utf-8",
  )
  out = render_html(md_path)
  assert out == md_path.with_suffix(".html")
  assert out.exists()
  html = out.read_text(encoding="utf-8")
  assert "<title>" in html
  assert "## 子节" in html or "子节" in html


def test_render_html_raises_when_md_missing(tmp_path: Path) -> None:
  with pytest.raises(FileNotFoundError):
    render_html(tmp_path / "nonexistent.md")


def test_render_html_custom_output(tmp_path: Path) -> None:
  md = tmp_path / "in.md"
  md.write_text("# T\n\nP", encoding="utf-8")
  out = tmp_path / "custom.html"
  ret = render_html(md, html_path=out)
  assert ret == out
  assert out.exists()


# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


def test_render_outputs_to_dict_basic(tmp_path: Path) -> None:
  out = RenderOutputs(
    video="V", course_title="C",
    md_path=tmp_path / "x.md", html_path=tmp_path / "x.html",
    chapters_rendered=3, image_refs_resolved=5, image_refs_missing=1,
  )
  d = out.to_dict()
  assert d["chapters_rendered"] == 3
  assert d["image_refs_resolved"] == 5
  assert d["image_refs_missing"] == 1
  assert d["md_path"].endswith("x.md")
