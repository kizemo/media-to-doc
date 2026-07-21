"""merge_lectures 测试(W12-D 新增)。

覆盖:
- strip_leading_index:序号前缀去除
- discover_lecture_files:扫讲义文件,_cleaned 优先
- merge_lectures:合并多份讲义,文件名 = 第一个 stem 去序号,序号全局重排
- 图片路径重写:`<stem>/images/<file>` → `<merged>/images/<stem>_<file>`
- 章节降级 + 加 part 标题
- HTML 渲染(用 longdoc.render_final_html)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from media_to_doc.pipeline.merge_lectures import (
  FusionChapter,
  FusionPlan,
  FusionSource,
  _parse_fusion_plan,
  apply_fusion_plan,
  chapters_summary,
  discover_lecture_files,
  merge_lectures,
  strip_leading_index,
)


def _seed_lecture(
  out_dir: Path,
  stem: str,
  body: str,
  with_images: bool = False,
) -> Path:
  """在 ``out_dir/<stem>_cleaned.md`` 写一个最小讲义。

  ``with_images=True`` 时建 ``<stem>/images/`` 子目录,放 2 张 png。
  """
  out_dir.mkdir(parents=True, exist_ok=True)
  md_path = out_dir / f"{stem}_cleaned.md"
  md_path.write_text(body, encoding="utf-8")
  if with_images:
    img_dir = out_dir / stem / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    for i in range(2):
      (img_dir / f"gen_{i}.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
  return md_path


# ─────────────────────────────────────────────────────────────
# strip_leading_index
# ─────────────────────────────────────────────────────────────


def test_strip_leading_index_with_underscore() -> None:
  assert strip_leading_index("01_先精准后放大") == "先精准后放大"


def test_strip_leading_index_with_dash() -> None:
  assert strip_leading_index("02-拉新成交") == "拉新成交"


def test_strip_leading_index_with_space() -> None:
  assert strip_leading_index("03 全站爆款") == "全站爆款"


def test_strip_leading_index_no_prefix() -> None:
  assert strip_leading_index("全站运营") == "全站运营"


def test_strip_leading_index_only_index() -> None:
  # `"03"` 无分隔符 → regex 不匹配,保留原值
  assert strip_leading_index("03") == "03"


def test_strip_leading_index_with_trailing_space() -> None:
  # 用户视频 "01_xxx .mp4" 末尾有空格的 stem
  assert strip_leading_index("01_先精准后放大 ") == "先精准后放大"


# ─────────────────────────────────────────────────────────────
# discover_lecture_files
# ─────────────────────────────────────────────────────────────


def test_discover_lecture_files_prefers_cleaned(tmp_path: Path) -> None:
  """``_cleaned.md`` 优先于同名 ``.md``。"""
  out_dir = tmp_path / "out"
  _seed_lecture(out_dir, "01_video", "# V1\n正文")
  (out_dir / "01_video.md").write_text("# V1 raw", encoding="utf-8")

  files = discover_lecture_files(out_dir)
  assert len(files) == 1
  path, stem = files[0]
  assert stem == "01_video"
  assert path.name == "01_video_cleaned.md"


def test_discover_lecture_files_fallback_to_md(tmp_path: Path) -> None:
  """无 ``_cleaned.md`` 时回退到 ``.md``。"""
  out_dir = tmp_path / "out"
  out_dir.mkdir(parents=True, exist_ok=True)
  (out_dir / "video_a.md").write_text("# A", encoding="utf-8")
  (out_dir / "video_b.md").write_text("# B", encoding="utf-8")
  files = discover_lecture_files(out_dir)
  assert len(files) == 2
  assert {stem for _, stem in files} == {"video_a", "video_b"}


def test_discover_lecture_files_skips_merged(tmp_path: Path) -> None:
  """跳过 ``_merged.md`` 产物(避免自我合并)。"""
  out_dir = tmp_path / "out"
  _seed_lecture(out_dir, "v1", "# V1")
  _seed_lecture(out_dir, "merged_merged", "# 合并产物")
  files = discover_lecture_files(out_dir)
  assert {stem for _, stem in files} == {"v1"}


def test_discover_lecture_files_sorted_natural(tmp_path: Path) -> None:
  out_dir = tmp_path / "out"
  _seed_lecture(out_dir, "10_ten", "# 10")
  _seed_lecture(out_dir, "2_two", "# 2")
  _seed_lecture(out_dir, "1_one", "# 1")
  files = discover_lecture_files(out_dir)
  stems = [s for _, s in files]
  # 自然排序:1 < 2 < 10
  assert stems == ["1_one", "2_two", "10_ten"]


def test_discover_lecture_files_empty_dir_returns_empty(tmp_path: Path) -> None:
  """空目录(无 .md):返回空 list(由 merge_lectures 统一抛错)。"""
  out_dir = tmp_path / "out"
  out_dir.mkdir(parents=True, exist_ok=True)
  assert discover_lecture_files(out_dir) == []


def test_merge_lectures_empty_dir_raises(tmp_path: Path) -> None:
  """``merge_lectures`` 在空目录抛 FileNotFoundError。"""
  out_dir = tmp_path / "out"
  out_dir.mkdir(parents=True, exist_ok=True)
  with pytest.raises(FileNotFoundError, match="没有找到讲义文件"):
    merge_lectures(out_dir)


# ─────────────────────────────────────────────────────────────
# merge_lectures — 核心
# ─────────────────────────────────────────────────────────────


def _md_template(stem: str, h1: str) -> str:
  """单视频讲义模板:H1 + 2 H2 + 图片引用。"""
  return (
    f"# {h1}\n"
    f"\n"
    f"## 引言\n"
    f"\n"
    f"正文段落 A。\n"
    f"\n"
    f"![Image]({stem}/images/gen_0.png)\n"
    f"\n"
    f"## 结论\n"
    f"\n"
    f"正文段落 B。\n"
    f"\n"
    f"![Image]({stem}/images/gen_1.png)\n"
  )


def test_merge_lectures_basic_two_videos(tmp_path: Path) -> None:
  out_dir = tmp_path / "output_final"
  _seed_lecture(
    out_dir, "01_先精准后放大", _md_template("01_先精准后放大", "先精准后放大"),
    with_images=True,
  )
  _seed_lecture(
    out_dir, "02_拉新成交", _md_template("02_拉新成交", "拉新成交"),
    with_images=True,
  )

  result = merge_lectures(out_dir)
  # merged_name = 第一个 stem 去序号
  assert result.merged_name == "先精准后放大"
  assert result.merged_md is not None and result.merged_md.exists()
  assert result.merged_html is not None and result.merged_html.exists()
  # 2 视频 × 2 张图 = 4 张复制
  assert result.copied_images == 4

  merged_text = result.merged_md.read_text(encoding="utf-8")
  # H1 保留
  assert merged_text.startswith("# 先精准后放大\n")
  # 第二个视频的标题被包成"第二部分:..."
  assert "## 第二部分:" in merged_text
  # 图片路径重写
  assert "images/01_先精准后放大_gen_0.png" in merged_text
  assert "images/02_拉新成交_gen_0.png" in merged_text


def test_merge_lectures_uses_explicit_merged_name(tmp_path: Path) -> None:
  out_dir = tmp_path / "output_final"
  _seed_lecture(out_dir, "01_v1", _md_template("01_v1", "V1"))
  _seed_lecture(out_dir, "02_v2", _md_template("02_v2", "V2"))

  result = merge_lectures(out_dir, merged_name="培训综合")
  assert result.merged_name == "培训综合"
  assert result.merged_md is not None
  assert result.merged_md.name == "培训综合_cleaned.md"


def test_merge_lectures_raises_on_single_lecture(tmp_path: Path) -> None:
  out_dir = tmp_path / "output_final"
  _seed_lecture(out_dir, "01_only", _md_template("01_only", "Only"))
  with pytest.raises(ValueError, match="无需合并"):
    merge_lectures(out_dir)


def test_merge_lectures_no_html(tmp_path: Path) -> None:
  out_dir = tmp_path / "output_final"
  _seed_lecture(out_dir, "01_a", _md_template("01_a", "A"))
  _seed_lecture(out_dir, "02_b", _md_template("02_b", "B"))

  result = merge_lectures(out_dir, no_html=True)
  assert result.merged_md is not None and result.merged_md.exists()
  assert result.merged_html is None


def test_merge_lectures_chapter_reordering(tmp_path: Path) -> None:
  """每个视频的 H2 降级为 H3,顶层加 part 标题。"""
  out_dir = tmp_path / "output_final"
  _seed_lecture(out_dir, "01_first", _md_template("01_first", "First"))
  _seed_lecture(out_dir, "02_second", _md_template("02_second", "Second"))

  result = merge_lectures(out_dir)
  text = result.merged_md.read_text(encoding="utf-8")
  # 第一个视频 H1 → "## 第一部分:First"
  assert "## 第一部分:First" in text
  # 第二个视频 H1 → "## 第二部分:Second"
  assert "## 第二部分:Second" in text
  # 第二个视频的 H2 → H3
  assert "### 引言" in text
  assert "### 结论" in text


def test_merge_lectures_creates_manifest(tmp_path: Path) -> None:
  out_dir = tmp_path / "output_final"
  _seed_lecture(out_dir, "01_a", _md_template("01_a", "A"))
  _seed_lecture(out_dir, "02_b", _md_template("02_b", "B"))

  result = merge_lectures(out_dir)
  manifest = out_dir / f"{result.merged_name}_merge_manifest.json"
  assert manifest.exists()
  import json as _json
  data = _json.loads(manifest.read_text(encoding="utf-8"))
  assert data["merged_name"] == "a"  # 去除序号
  assert len(data["source_files"]) == 2
  assert data["copied_images"] == 0


def test_merge_lectures_images_copied_with_prefix(tmp_path: Path) -> None:
  """图片复制到 ``<merged>/images/<original_stem>_*.png``,避免多视频同名冲突。"""
  out_dir = tmp_path / "output_final"
  _seed_lecture(out_dir, "01_a", _md_template("01_a", "A"), with_images=True)
  _seed_lecture(out_dir, "02_b", _md_template("02_b", "B"), with_images=True)

  result = merge_lectures(out_dir)
  merged_images = out_dir / result.merged_name / "images"
  assert merged_images.exists()
  # 4 张图,命名带前缀
  names = sorted(p.name for p in merged_images.glob("*.png"))
  assert "01_a_gen_0.png" in names
  assert "01_a_gen_1.png" in names
  assert "02_b_gen_0.png" in names
  assert "02_b_gen_1.png" in names


def test_merge_lectures_html_includes_mermaid_cdn(tmp_path: Path) -> None:
  """合并产物 HTML 含 v1.0.1 mermaid.js CDN(render_final_html 复用)。"""
  out_dir = tmp_path / "output_final"
  _seed_lecture(out_dir, "01_a", _md_template("01_a", "A"))
  _seed_lecture(out_dir, "02_b", _md_template("02_b", "B"))

  result = merge_lectures(out_dir)
  html = result.merged_html.read_text(encoding="utf-8")
  assert "cdn.jsdelivr.net/npm/mermaid" in html
  assert "mermaid.initialize" in html


# ─────────────────────────────────────────────────────────────
# chapters_summary + apply_fusion_plan(W12-D 章节融合)
# ─────────────────────────────────────────────────────────────


class _FakeFusionProvider:
  """Mock LLM provider:返回固定 fusion_plan JSON(可控测试)。"""

  def __init__(self, response_text: str = "") -> None:
    self.response_text = response_text
    self.calls: list[str] = []

  @property
  def name(self) -> str:
    return "fake-fusion"

  @property
  def model(self) -> str:
    return "fake-model"

  def chat(self, prompt: str, **_kwargs: Any) -> Any:
    from media_to_doc.llm.base import ChatResponse

    self.calls.append(prompt)
    return ChatResponse(
      text=self.response_text,
      model=self.model,
      provider=self.name,
      duration_seconds=0.01,
    )


def test_chapters_summary_extracts_h2_chapters() -> None:
  """chapters_summary 提取 H2 章节 + 摘要(前 800 字符)。"""
  md = (
    "# V1\n"
    "\n"
    "## 引言\n"
    "\n"
    "这是引言段落,介绍本章核心观点。\n"
    "\n"
    "## 主体一\n"
    "\n"
    "主体内容,展开论述。\n"
    "\n"
    "## 主体二\n"
    "\n"
    "更多内容。\n"
  )
  summaries = chapters_summary(md, video_name="V1")
  assert len(summaries) == 3
  assert summaries[0].chapter == "引言"
  assert summaries[0].video == "V1"
  assert "引言段落" in summaries[0].summary
  assert summaries[1].chapter == "主体一"
  assert summaries[2].chapter == "主体二"


def test_chapters_summary_skips_code_blocks() -> None:
  """代码块围栏内的 ``##`` 不当作章节边界。"""
  md = (
    "# V1\n"
    "\n"
    "## 真章节\n"
    "\n"
    "```python\n"
    "## fake_chapter_in_code\n"
    "x = 1\n"
    "```\n"
    "\n"
    "## 第二个真章节\n"
  )
  summaries = chapters_summary(md, video_name="V1")
  assert [s.chapter for s in summaries] == ["真章节", "第二个真章节"]


def test_chapters_summary_truncates_long_body() -> None:
  """超过 max_summary_chars 字符的章节被截断到 max + "…" 。"""
  long_text = "x" * 1000
  md = f"# V\n\n## Big\n\n{long_text}\n"
  summaries = chapters_summary(md, max_summary_chars=100, video_name="V")
  assert len(summaries[0].summary) == 101  # 100 字符 + "…"
  assert summaries[0].summary.endswith("…")


def test_parse_fusion_plan_basic() -> None:
  """_parse_fusion_plan 解析标准 JSON 输出。"""
  raw = '{"chapters": [{"title": "融合 1", "sources": [{"video": "v1", "chapter": "c1"}]}]}'
  plan = _parse_fusion_plan(raw)
  assert len(plan.chapters) == 1
  assert plan.chapters[0].title == "融合 1"
  assert plan.chapters[0].sources[0].video == "v1"
  assert plan.chapters[0].sources[0].chapter == "c1"
  assert plan.chapters[0].sources[0].include == "all"  # default


def test_parse_fusion_plan_with_fence() -> None:
  """容错:接受 ````json``` 围栏包裹。"""
  raw = '```json\n{"chapters": [{"title": "X", "sources": [{"video": "a", "chapter": "b"}]}]}\n```'
  plan = _parse_fusion_plan(raw)
  assert plan.chapters[0].title == "X"


def test_parse_fusion_plan_skips_empty_sources() -> None:
  """sources 为空的章节被跳过(LLM 输出容错)。"""
  raw = '{"chapters": [{"title": "Empty", "sources": []}, {"title": "OK", "sources": [{"video": "v", "chapter": "c"}]}]}'
  plan = _parse_fusion_plan(raw)
  assert len(plan.chapters) == 1
  assert plan.chapters[0].title == "OK"


def test_apply_fusion_plan_writes_chapter_titles() -> None:
  """apply_fusion_plan 按 fusion_plan 重写 H1 标题(融合章节名)。"""
  plan = FusionPlan(
    chapters=[
      FusionChapter(
        title="融合策略 1",
        sources=[FusionSource(video="01_v1", chapter="原章节 1")],
      ),
    ]
  )
  sources = {
    "01_v1": "# v1\n\n## 原章节 1\n\n内容 A。\n\n## 无关\n\n其他。\n",
  }
  out = apply_fusion_plan(plan, sources, "merged_name")
  assert "## 融合策略 1" in out
  assert "## 原章节 1" not in out  # 不应该直接出现原 H2
  assert "内容 A。" in out
  # 无关章节不应该被引用
  assert "其他。" not in out


def test_apply_fusion_plan_includes_first_n() -> None:
  """include="first_n:2" 截取前 2 段。"""
  plan = FusionPlan(
    chapters=[
      FusionChapter(
        title="X",
        sources=[FusionSource(video="v1", chapter="ch1", include="first_n:2")],
      ),
    ]
  )
  sources = {
    "v1": "# v1\n\n## ch1\n\n段 1。\n\n段 2。\n\n段 3。\n\n段 4。\n",
  }
  out = apply_fusion_plan(plan, sources, "merged")
  assert "段 1。" in out
  assert "段 2。" in out
  assert "段 3。" not in out
  assert "段 4。" not in out


def test_apply_fusion_plan_summary_only() -> None:
  """include="summary" 仅显示引用提示,不搬正文。"""
  plan = FusionPlan(
    chapters=[
      FusionChapter(
        title="X",
        sources=[FusionSource(video="v1", chapter="ch1", include="summary")],
      ),
    ]
  )
  sources = {"v1": "# v1\n\n## ch1\n\n关键内容 A。\n"}
  out = apply_fusion_plan(plan, sources, "merged")
  assert "关键内容 A。" not in out
  assert "`v1`" in out  # 引用提示保留


def test_apply_fusion_plan_fuzzy_matching() -> None:
  """LLM 返回的章节名与原文略不同时,fuzzy 匹配找到最接近的。"""
  plan = FusionPlan(
    chapters=[
      FusionChapter(
        title="X",
        sources=[FusionSource(video="v1", chapter="课程开场与介绍")],  # 略不同
      ),
    ]
  )
  sources = {"v1": "# v1\n\n## 课程开场介绍\n\n内容。\n"}
  out = apply_fusion_plan(plan, sources, "merged")
  # fuzzy 匹配成功,内容被引用
  assert "内容。" in out
  assert "(源未找到" not in out


def test_apply_fusion_plan_unmatched_chapter_falls_back() -> None:
  """完全找不到的章节降级到 fallback 提示。"""
  plan = FusionPlan(
    chapters=[
      FusionChapter(
        title="X",
        sources=[FusionSource(video="v1", chapter="完全不存在的章节 xyz")],
      ),
    ]
  )
  sources = {"v1": "# v1\n\n## 另一章节\n\n内容。\n"}
  out = apply_fusion_plan(plan, sources, "merged")
  assert "(源未找到" in out
  assert "内容。" not in out


def test_merge_lectures_with_fusion_provider(tmp_path: Path) -> None:
  """fusion_provider 提供时,走 LLM 融合路径(而非硬切)。"""
  out_dir = tmp_path / "output_final"
  _seed_lecture(out_dir, "01_first", _md_template("01_first", "First"))
  _seed_lecture(out_dir, "02_second", _md_template("02_second", "Second"))

  fusion_plan_json = (
    '{"chapters": ['
    '{"title": "融合策略 A", "sources": ['
    '{"video": "01_first", "chapter": "引言"},'
    '{"video": "02_second", "chapter": "引言"}'
    ']},'
    '{"title": "融合策略 B", "sources": ['
    '{"video": "01_first", "chapter": "结论"},'
    '{"video": "02_second", "chapter": "结论"}'
    ']}'
    ']}'
  )
  provider = _FakeFusionProvider(response_text=fusion_plan_json)
  result = merge_lectures(out_dir, fusion_provider=provider)

  # 验证 LLM 被调过
  assert len(provider.calls) == 1
  # 验证融合标题出现
  text = result.merged_md.read_text(encoding="utf-8")
  assert "## 融合策略 A" in text
  assert "## 融合策略 B" in text
  # 验证硬切的 "第一部分" / "第二部分" 没出现
  assert "## 第一部分" not in text
  assert "## 第二部分" not in text
  # 图片仍要复制
  assert result.copied_images == 0  # 本测试没 _with_images


def test_merge_lectures_fusion_falls_back_on_error(tmp_path: Path) -> None:
  """LLM fusion 失败(fallback_on_error=True)→ 降级到硬切。"""
  out_dir = tmp_path / "output_final"
  _seed_lecture(out_dir, "01_a", _md_template("01_a", "A"))
  _seed_lecture(out_dir, "02_b", _md_template("02_b", "B"))

  class _BrokenProvider(_FakeFusionProvider):
    def chat(self, prompt: str, **_kwargs: Any) -> Any:
      raise RuntimeError("LLM down")

  result = merge_lectures(out_dir, fusion_provider=_BrokenProvider())
  text = result.merged_md.read_text(encoding="utf-8")
  # 降级到硬切,应含 "## 第一部分" / "## 第二部分"
  assert "## 第一部分" in text
  assert "## 第二部分" in text


def test_merge_lectures_fusion_raises_without_fallback(tmp_path: Path) -> None:
  """fallback_on_error=False 时,LLM 失败直接抛错。"""
  out_dir = tmp_path / "output_final"
  _seed_lecture(out_dir, "01_a", _md_template("01_a", "A"))
  _seed_lecture(out_dir, "02_b", _md_template("02_b", "B"))

  class _BrokenProvider(_FakeFusionProvider):
    def chat(self, prompt: str, **_kwargs: Any) -> Any:
      raise RuntimeError("LLM down")

  with pytest.raises(RuntimeError, match="LLM down"):
    merge_lectures(
      out_dir, fusion_provider=_BrokenProvider(), fallback_on_error=False,
    )


def test_merge_lectures_fusion_with_images(tmp_path: Path) -> None:
  """fusion 模式 + images → 仍正常复制图片(共享代码路径)。"""
  out_dir = tmp_path / "output_final"
  _seed_lecture(
    out_dir, "01_a", _md_template("01_a", "A"), with_images=True,
  )
  _seed_lecture(
    out_dir, "02_b", _md_template("02_b", "B"), with_images=True,
  )
  fusion_json = (
    '{"chapters": ['
    '{"title": "Combined", "sources": ['
    '{"video": "01_a", "chapter": "引言"},'
    '{"video": "02_b", "chapter": "引言"}'
    ']}'
    ']}'
  )
  provider = _FakeFusionProvider(response_text=fusion_json)
  result = merge_lectures(out_dir, fusion_provider=provider)
  # 4 张图应复制
  assert result.copied_images == 4


def test_merge_lectures_fusion_prompt_contains_summaries(tmp_path: Path) -> None:
  """fusion prompt 包含所有视频的简化版。"""
  out_dir = tmp_path / "output_final"
  _seed_lecture(out_dir, "01_alpha", _md_template("01_alpha", "Alpha"))
  _seed_lecture(out_dir, "02_beta", _md_template("02_beta", "Beta"))

  provider = _FakeFusionProvider(
    response_text='{"chapters": [{"title": "X", "sources": [{"video": "01_alpha", "chapter": "引言"}]}]}',
  )
  merge_lectures(out_dir, fusion_provider=provider)
  # 验证 LLM 被调,prompt 含两个视频
  prompt = provider.calls[0]
  assert "01_alpha" in prompt
  assert "02_beta" in prompt
  assert "引言" in prompt
