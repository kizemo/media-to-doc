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

import pytest

from media_to_doc.pipeline.merge_lectures import (
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
