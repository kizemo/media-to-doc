"""longdoc stage 测试。

要点:
- 验证分块(15000 CJK 字符 / 段落边界)
- 验证规则清理(LLM skip 模式):去时间戳 / 合并空行
- 验证 slugify + unique slug
- 验证 TOC HTML 生成
- 验证 HTML 渲染(锚点 / 内嵌 CSS / print stylesheet)
- 验证 manifest 写出 + 统计字段
- 验证 source_md 缺失抛 FileNotFoundError
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from media_to_doc.pipeline import longdoc as ld
from media_to_doc.pipeline.chapters import Chapter, ChaptersReport
from media_to_doc.pipeline.longdoc import (
  LongDocResult,
  PurificationStats,
  process_long_doc,
  render_final_html,
)

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


def _seed_chapters(work: Path, video: str = "course-x") -> None:
  chapters_dir = work / "chapters"
  chapters_dir.mkdir(parents=True, exist_ok=True)
  r = ChaptersReport(
    video=video,
    provider="fake",
    model="fm",
    chapters=[Chapter(idx=1, title="第一章", summary="简介",
                      start_seconds=0.0, end_seconds=60.0)],
  )
  r.save(chapters_dir / "chapters.json")


def _seed_rendered_md(work: Path, stem: str, body: str) -> Path:
  """模拟 render 阶段的输出位置:``<work>/chapters/raw/<stem>.md``(与 render 一致)。"""
  raw_dir = work / "chapters" / "raw"
  raw_dir.mkdir(parents=True, exist_ok=True)
  md_path = raw_dir / f"{stem}.md"
  md_path.write_text(body, encoding="utf-8")
  return md_path


def _make_provider() -> Any:
  """与 chapters/draft 测试同构的 ``_FakeProvider`` 模式(不真调 LLM)。"""

  class _FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self) -> None:
      self.calls: list[str] = []

    def chat(self, prompt: str, **_kwargs: Any) -> Any:
      from media_to_doc.llm.base import ChatResponse

      self.calls.append(prompt)
      return ChatResponse(
        text="净化后正文",
        model=self.model,
        provider=self.name,
        duration_seconds=0.01,
      )

  return _FakeProvider()


# ─────────────────────────────────────────────────────────────
# 工具:slug / 标题提取 / unique slug
# ─────────────────────────────────────────────────────────────


def test_slugify_chinese() -> None:
  s = ld._slugify("达摩盘选品技巧")
  assert s  # 仅校验非空


def test_slugify_strips_punct() -> None:
  assert ld._slugify("Hello, World!") == "hello-world"


def test_slugify_empty_fallback() -> None:
  assert ld._slugify("") == "section"
  assert ld._slugify("---") == "section"


def test_extract_headings_skips_code_blocks() -> None:
  md = (
    "# 标题 1\n"
    "```\n# not a heading\n```\n"
    "## 标题 2\n"
    "  ~~~\n### also not\n  ~~~\n"
    "### 标题 3\n"
  )
  out = ld._extract_headings(md)
  levels = [lvl for lvl, _, _ in out]
  assert levels == [1, 2, 3]
  assert out[0][1] == "标题 1"
  assert out[1][1] == "标题 2"
  assert out[2][1] == "标题 3"


def test_extract_headings_empty() -> None:
  assert ld._extract_headings("") == []


def test_assign_unique_slugs_appends_index() -> None:
  headings = [(1, "重复", "重复"), (2, "重复", "重复"), (1, "唯一", "唯一")]
  out = ld._assign_unique_slugs(headings)
  anchors = [a for _, _, _, a in out]
  assert anchors == ["重复", "重复-1", "唯一"]


def test_build_toc_html_includes_h1_h2() -> None:
  items = [(1, "一级 A", "a"), (2, "二级 B", "b"), (2, "二级 C", "c")]
  html = ld._build_toc_html(items)
  assert "<nav class=\"toc\">" in html
  assert "目录" in html
  assert html.count("<a href=") == 3
  assert "a\">一级 A" in html or "a\">一级 A" in html


def test_build_toc_html_empty() -> None:
  assert ld._build_toc_html([]) == ""


def test_html_escape_specials() -> None:
  out = ld._html_escape('<a href="x">&')
  assert "&lt;" in out and "&gt;" in out and "&amp;" in out and "&quot;" in out


# ─────────────────────────────────────────────────────────────
# 工具:分块
# ─────────────────────────────────────────────────────────────


def test_split_into_chunks_short_text_single_chunk() -> None:
  text = "短文本"
  out = ld._split_into_chunks(text, chunk_size=15000)
  assert out == [text]


def test_split_into_chunks_respects_paragraph_boundary() -> None:
  # 100 段落,每段 200 字 → 总 20000 字,应分 2 块
  para = "x" * 200
  text = "\n\n".join([para] * 100)
  out = ld._split_into_chunks(text, chunk_size=15000)
  assert len(out) == 2
  # 每块应只含完整段落(不含半截)
  for chunk in out:
    assert "x" * 200 in chunk  # 完整段


def test_split_into_chunks_merges_small_tail() -> None:
  # 3 段:2 大段 + 1 小段 → 大段之间分,小段合并到前一块
  big1 = "a" * 10000
  big2 = "b" * 10000
  small = "c" * 100
  text = f"{big1}\n\n{big2}\n\n{small}"
  out = ld._split_into_chunks(text, chunk_size=15000, min_chunk_size=2000)
  assert len(out) == 2  # 末块小,合并到前一块


def test_split_into_chunks_handles_huge_paragraph() -> None:
  # 单段 20000 字 > chunk_size → 强制按字符切
  para = "x" * 20000
  out = ld._split_into_chunks(para, chunk_size=5000)
  assert len(out) == 4
  assert all(len(c) == 5000 for c in out)


def test_split_into_chunks_empty() -> None:
  assert ld._split_into_chunks("") == []


def test_count_cjk_counts_only_cjk() -> None:
  text = "中文 hello 世界"
  # 4 个 CJK 字符
  assert ld._count_cjk(text) == 4


# ─────────────────────────────────────────────────────────────
# 规则清理(LLM skip 模式)
# ─────────────────────────────────────────────────────────────


def test_rule_clean_strips_timestamp_lines() -> None:
  text = "前段\n[   0.50s -   1.20s] 时间戳\n后段"
  cleaned, stats = ld._rule_clean_text(text)
  assert "时间戳" not in cleaned
  assert "前段" in cleaned and "后段" in cleaned
  assert "strip_timestamp_lines" in stats.rules_applied


def test_rule_clean_collapses_blank_lines() -> None:
  text = "a\n\n\n\n\nb"
  cleaned, stats = ld._rule_clean_text(text)
  assert "\n\n\n" not in cleaned
  assert "collapse_blank_lines" in stats.rules_applied


def test_rule_clean_noop_on_clean_text() -> None:
  text = "干净的文本\n\n第二段"
  cleaned, stats = ld._rule_clean_text(text)
  assert "noop" in stats.rules_applied
  assert cleaned == text.strip() + "\n"


def test_rule_clean_retention_rate_calculated() -> None:
  text = "a\n[0.5s - 1.0s] discard\nb"
  _, stats = ld._rule_clean_text(text)
  assert 0.0 < stats.retention_rate < 1.0
  assert stats.chars_input > stats.chars_output


# ─────────────────────────────────────────────────────────────
# 公开 API:process_long_doc(skip LLM)
# ─────────────────────────────────────────────────────────────


def test_process_long_doc_skip_llm_writes_cleaned_and_html(
  tmp_path: Path,
) -> None:
  work = tmp_path
  _seed_chapters(work, video="lesson-01")
  body = (
    "# 第一章\n\n"
    "正文段一\n\n"
    "[ 0.00s - 10.00s] 时间戳应被剥离\n\n"
    "正文段二\n\n"
  )
  _seed_rendered_md(work, "lesson-01", body)

  result = process_long_doc(work, None)  # provider=None → skip LLM

  assert result.source_md is not None and result.source_md.exists()
  assert result.cleaned_md is not None and result.cleaned_md.exists()
  assert result.final_html is not None and result.final_html.exists()
  assert result.provider == "skip"
  assert "时间戳应被剥离" not in result.cleaned_md.read_text(encoding="utf-8")
  # HTML 应含标题 + TOC + 内嵌 CSS
  html = result.final_html.read_text(encoding="utf-8")
  assert "<!doctype html>" in html
  assert "<title>" in html
  assert "lesson-01" in html  # title
  assert "@media print" in html  # print stylesheet
  # stats
  assert result.stats.chunks_total >= 1
  assert result.stats.chars_input > 0


def test_process_long_doc_skip_llm_via_provider_name(
  tmp_path: Path,
) -> None:
  """provider.name='skip' 也走规则清理。"""
  work = tmp_path
  _seed_chapters(work, video="l2")
  _seed_rendered_md(work, "l2", "# 标题\n\n正文\n\n")

  class _SkipProvider:
    name = "skip"
    model = ""

    def chat(self, prompt: str, **_kwargs: Any) -> Any:
      raise AssertionError("skip provider 不该被调用")

  result = process_long_doc(work, _SkipProvider())  # type: ignore[arg-type]
  assert result.provider == "skip"
  assert result.cleaned_md is not None and result.cleaned_md.exists()


def test_process_long_doc_uses_llm_when_provider_given(
  tmp_path: Path,
) -> None:
  work = tmp_path
  _seed_chapters(work, video="l3")
  _seed_rendered_md(work, "l3", "# 标题\n\n原始正文\n\n")

  provider = _make_provider()
  result = process_long_doc(work, provider)  # type: ignore[arg-type]

  assert result.provider == "fake"
  assert result.model == "fake-model"
  # LLM 应被调过
  assert len(provider.calls) >= 1
  # 净化后内容应来自 LLM 返回
  assert "净化后正文" in result.cleaned_md.read_text(encoding="utf-8")


def test_process_long_doc_missing_source_raises(tmp_path: Path) -> None:
  work = tmp_path
  _seed_chapters(work, video="missing")
  # 没 _seed_rendered_md → source 不存在
  with pytest.raises(FileNotFoundError, match="找不到源 markdown"):
    process_long_doc(work, None)


def test_process_long_doc_empty_source_raises(tmp_path: Path) -> None:
  work = tmp_path
  _seed_chapters(work, video="empty")
  _seed_rendered_md(work, "empty", "   \n\n  ")
  with pytest.raises(ValueError, match="为空"):
    process_long_doc(work, None)


def test_process_long_doc_explicit_source_md(tmp_path: Path) -> None:
  """显式传 source_md,跳过 chapters.json 派生。"""
  work = tmp_path
  md = tmp_path / "external.md"
  md.write_text("# X\n\nBody\n", encoding="utf-8")
  result = process_long_doc(
    work, None, source_md=md, output_dir=tmp_path / "out", output_stem="ext"
  )
  assert result.source_md == md
  assert result.cleaned_md is not None
  assert result.cleaned_md.name == "ext_cleaned.md"


def test_process_long_doc_no_html(tmp_path: Path) -> None:
  work = tmp_path
  _seed_chapters(work, video="l-no-html")
  _seed_rendered_md(work, "l-no-html", "# 标题\n\n正文\n")
  result = process_long_doc(work, None, write_html=False)
  assert result.cleaned_md is not None and result.cleaned_md.exists()
  # final_html 在 write_html=False 时仍返回路径,但文件可能不存在
  # (LongDocResult.final_html 只在文件存在时填 — 见 process_long_doc 实现)


# ─────────────────────────────────────────────────────────────
# 公开 API:render_final_html
# ─────────────────────────────────────────────────────────────


def test_render_final_html_creates_anchors_and_toc(tmp_path: Path) -> None:
  md = tmp_path / "test_cleaned.md"
  md.write_text(
    "# 主标题\n\n"
    "## 第一章\n\n正文\n\n"
    "## 第二章\n\n更多\n\n"
    "## 第一章\n\n重复标题\n",
    encoding="utf-8",
  )
  out = render_final_html(md, title="测试课程")
  assert out.exists()
  html = out.read_text(encoding="utf-8")
  assert "测试课程" in html
  # TOC 应有 4 个 H1/H2 链接
  assert html.count("<a href=\"#") >= 4
  # 重名 slug 应加 -1 后缀
  assert 'id="第一章-1"' in html
  # 内嵌 CSS + print
  assert "<style>" in html
  assert "@media print" in html
  # 暗色模式
  assert "prefers-color-scheme: dark" in html


def test_render_final_html_default_title_strips_cleaned_suffix(
  tmp_path: Path,
) -> None:
  md = tmp_path / "my-course_cleaned.md"
  md.write_text("# my-course\n\nbody", encoding="utf-8")
  out = render_final_html(md)
  html = out.read_text(encoding="utf-8")
  assert "<title>my-course</title>" in html


def test_render_final_html_default_title_keeps_stem(tmp_path: Path) -> None:
  md = tmp_path / "no_suffix.md"
  md.write_text("# Title\n\nbody", encoding="utf-8")
  out = render_final_html(md)
  html = out.read_text(encoding="utf-8")
  assert "<title>no_suffix</title>" in html


def test_render_final_html_missing_source_raises(tmp_path: Path) -> None:
  with pytest.raises(FileNotFoundError):
    render_final_html(tmp_path / "nope.md")


# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


def test_purification_stats_to_dict() -> None:
  s = PurificationStats(
    chunks_total=3, chars_input=100, chars_output=80, retention_rate=0.8
  )
  d = s.to_dict()
  assert d["chunks_total"] == 3
  assert d["chars_input"] == 100
  assert d["chars_output"] == 80
  assert d["retention_rate"] == 0.8


def test_long_doc_result_save_manifest(tmp_path: Path) -> None:
  r = LongDocResult(
    video="x", course_title="x",
    source_md=tmp_path / "x.md",
    cleaned_md=tmp_path / "x_cleaned.md",
    final_html=None,
    provider="skip",
    model="",
    stats=PurificationStats(chunks_total=1, chars_input=10, chars_output=10),
  )
  manifest = tmp_path / "manifest.json"
  r.save_manifest(manifest)
  assert manifest.exists()
  import json as _json
  data = _json.loads(manifest.read_text(encoding="utf-8"))
  assert data["video"] == "x"
  assert data["provider"] == "skip"
  assert data["stats"]["chunks_total"] == 1
