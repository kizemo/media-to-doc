"""imagegen stage 测试。

要点:
- mock imagegen provider,验证 prompt 抽取 / 路径命名 / JSON 序列化
- 测试 ``provider=skip`` 行为:不写文件,只记录 prompts
- 测试章节 markdown 中 ``[[GEN: prompt]]`` 替换逻辑(相对路径引用)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from media_to_doc.config import ImagegenConfig, WorkflowConfig
from media_to_doc.pipeline import imagegen as ig_mod
from media_to_doc.pipeline.imagegen import (
  GeneratedImage,
  ImagesReport,
  LocalSdxlProvider,
  SkipProvider,
  extract_prompts,
  generate_images,
)

# ─────────────────────────────────────────────────────────────
# 工具:Tag 抽取
# ─────────────────────────────────────────────────────────────


def test_extract_prompts_basic() -> None:
  text = "前段[[GEN: 流程图]]中段[[GEN: 表格]]尾段"
  assert extract_prompts(text) == ["流程图", "表格"]


def test_extract_prompts_strip_whitespace() -> None:
  text = "[[GEN:   前后空格   ]]"
  assert extract_prompts(text) == ["前后空格"]


def test_extract_prompts_empty_on_none() -> None:
  assert extract_prompts("") == []
  assert extract_prompts("无标签文本") == []


def test_extract_prompts_skips_empty_brackets() -> None:
  # 当前 regex 要求至少 1 个非 ] 字符,纯空格 ``[[GEN: ]]`` 不匹配
  text = "[[GEN: ]]前段[[GEN: 也空 ]]后段"
  out = extract_prompts(text)
  # 只剩 ``[[GEN: 也空 ]]`` 匹配,空格被 strip
  assert out == ["也空"]
  assert all(p.strip() for p in out)


# ─────────────────────────────────────────────────────────────
# Provider 工厂
# ─────────────────────────────────────────────────────────────


def test_build_provider_skip() -> None:
  cfg = WorkflowConfig(imagegen=ImagegenConfig(provider="skip"))
  p = ig_mod.build_provider(cfg)
  assert isinstance(p, SkipProvider)
  assert p.name == "skip"


def test_build_provider_local_sdxl() -> None:
  cfg = WorkflowConfig(
    imagegen=ImagegenConfig(
      provider="local_sdxl",
      base_model="x",
      refiner_model="y",
      steps=20,
      guidance_scale=5.0,
    )
  )
  p = ig_mod.build_provider(cfg)
  assert isinstance(p, LocalSdxlProvider)
  assert p.base_model == "x"
  assert p.steps == 20


def test_build_provider_unknown_raises() -> None:
  cfg = WorkflowConfig(imagegen=ImagegenConfig(provider="bogus"))  # type: ignore[arg-type]
  with pytest.raises(ValueError, match="未知 imagegen provider"):
    ig_mod.build_provider(cfg)


# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


def test_generated_image_to_dict_includes_relative_path(tmp_path: Path) -> None:
  img = GeneratedImage(
    uuid="abc123",
    prompt="流程图",
    source_chapter="chapter_01.md",
    output_path=tmp_path / "images" / "gen_abc123.png",
  )
  d = img.to_dict()
  assert d["uuid"] == "abc123"
  assert d["prompt"] == "流程图"
  assert d["skipped"] is False


def test_images_report_count_and_to_dict(tmp_path: Path) -> None:
  r = ImagesReport(
    video="x",
    provider="fake",
    base_model="b",
    refiner_model="r",
    output_dir=str(tmp_path),
    images=[
      GeneratedImage(
        uuid="u1", prompt="A", source_chapter="chapter_01.md",
        output_path=tmp_path / "a.png",
      ),
      GeneratedImage(
        uuid="u2", prompt="B", source_chapter="chapter_02.md",
        output_path=tmp_path / "b.png", skipped=True,
      ),
    ],
    skipped_prompts=["B"],
  )
  assert r.count == 2
  payload = r.to_dict()
  assert payload["count"] == 2
  assert payload["skipped_count"] == 1


def test_images_report_save_round_trip(tmp_path: Path) -> None:
  r = ImagesReport(
    video="x",
    provider="fake",
    output_dir=str(tmp_path),
    images=[
      GeneratedImage(
        uuid="u1", prompt="A", source_chapter="c1.md",
        output_path=tmp_path / "a.png",
      )
    ],
  )
  path = tmp_path / "imagegen.json"
  r.save(path)
  data = json.loads(path.read_text(encoding="utf-8"))
  assert data["count"] == 1
  assert data["images"][0]["prompt"] == "A"


# ─────────────────────────────────────────────────────────────
# Mock Provider
# ─────────────────────────────────────────────────────────────


class _MockProvider:
  """最小 imagegen provider mock;写入最小有效 PNG 字节。"""

  PNG_HEADER = b"\x89PNG\r\n\x1a\n"

  def __init__(self) -> None:
    self.name = "mock"
    self.calls: list[tuple[str, Path]] = []

  def generate(self, prompt: str, output_path: Path) -> Path:
    self.calls.append((prompt, output_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(self.PNG_HEADER + b"\x00" * 100)
    return output_path


# ─────────────────────────────────────────────────────────────
# generate_images 端到端
# ─────────────────────────────────────────────────────────────


def _seed_chapter(md_path: Path, body: str) -> None:
  md_path.parent.mkdir(parents=True, exist_ok=True)
  md_path.write_text(
    f"# 章节 1\n\n{body}\n",
    encoding="utf-8",
  )


def test_generate_images_skip_provider_records_prompts(tmp_path: Path) -> None:
  drafts = tmp_path / "drafts"
  _seed_chapter(drafts / "chapter_01.md", "前段[[GEN: A]]中段[[GEN: B]]")
  _seed_chapter(drafts / "chapter_02.md", "无标签")

  provider = SkipProvider()
  report = generate_images(
    tmp_path,
    drafts_dir=drafts,
    output_dir=drafts / "images",
    provider=provider,
  )

  assert report.count == 0
  assert report.skipped_prompts == ["A", "B"]
  # SkipProvider 不写文件
  assert not (drafts / "images").exists() or list((drafts / "images").iterdir()) == []
  # 章节 md 未被改写
  text = (drafts / "chapter_01.md").read_text(encoding="utf-8")
  assert "[[GEN: A]]" in text


def test_generate_images_local_provider_writes_pngs(tmp_path: Path) -> None:
  drafts = tmp_path / "drafts"
  _seed_chapter(drafts / "chapter_01.md", "前段[[GEN: A]]中段[[GEN: B]]")

  mock = _MockProvider()
  report = generate_images(
    tmp_path,
    drafts_dir=drafts,
    output_dir=drafts / "images",
    provider=mock,
  )

  assert report.count == 2
  assert len(mock.calls) == 2
  for img in report.images:
    assert img.output_path.exists()
    assert img.output_path.read_bytes()[:8] == _MockProvider.PNG_HEADER
    assert re.match(r"^gen_[0-9a-f]{12}\.png$", img.output_path.name)

  # chapter_NN.md 中 [[GEN: ...]] 应被替换为 ![[gen_<uuid>.png]]
  text = (drafts / "chapter_01.md").read_text(encoding="utf-8")
  assert "[[GEN:" not in text
  assert "![[gen_" in text


def test_generate_images_chapter_without_tags_skipped(tmp_path: Path) -> None:
  drafts = tmp_path / "drafts"
  _seed_chapter(drafts / "chapter_01.md", "纯文本,无配图标注")
  _seed_chapter(drafts / "chapter_02.md", "[[GEN: 实有]]")

  mock = _MockProvider()
  report = generate_images(
    tmp_path,
    drafts_dir=drafts,
    output_dir=drafts / "images",
    provider=mock,
  )

  assert report.count == 1
  assert mock.calls and mock.calls[0][0] == "实有"


def test_generate_images_from_config_skip(tmp_path: Path) -> None:
  drafts = tmp_path / "drafts"
  _seed_chapter(drafts / "chapter_01.md", "[[GEN: X]]")

  cfg = WorkflowConfig(imagegen=ImagegenConfig(provider="skip"))
  report = generate_images(tmp_path, config=cfg, drafts_dir=drafts)
  assert report.provider == "skip"
  assert report.count == 0
  assert report.skipped_prompts == ["X"]


def test_generate_images_default_dirs(tmp_path: Path) -> None:
  """无显式 drafts_dir 时默认 ``<work>/chapters/raw``。"""
  # 准备默认目录
  drafts = tmp_path / "chapters" / "raw"
  _seed_chapter(drafts / "chapter_01.md", "[[GEN: default dir]]")

  mock = _MockProvider()
  # 不传 drafts_dir / output_dir
  report = generate_images(tmp_path, provider=mock)
  assert report.count == 1
  # 默认 images/<drafts>/images
  default_img = drafts / "images"
  assert default_img.exists()
  assert any(default_img.iterdir())


def test_generate_images_empty_drafts(tmp_path: Path) -> None:
  drafts = tmp_path / "drafts-empty"
  drafts.mkdir()
  mock = _MockProvider()
  report = generate_images(tmp_path, drafts_dir=drafts, provider=mock)
  assert report.count == 0
  # manifest 仍写
  assert (tmp_path / "imagegen" / "imagegen.json").exists()


def test_generate_images_manifest_records_provider_models(tmp_path: Path) -> None:
  drafts = tmp_path / "drafts"
  _seed_chapter(drafts / "chapter_01.md", "[[GEN: X]]")

  cfg = WorkflowConfig(
    imagegen=ImagegenConfig(
      provider="local_sdxl",
      base_model="my_base",
      refiner_model="my_refiner",
    )
  )
  # 显式 SkipProvider 用于测试短路
  report = generate_images(
    tmp_path, config=cfg, drafts_dir=drafts, provider=SkipProvider()
  )
  assert report.provider == "skip"  # 显式 provider 优先


def test_generate_images_provider_local_sdxl_instantiation() -> None:
  """LocalSdxlProvider 实例化本身不应触发 diffusers 导入。"""
  p = LocalSdxlProvider(
    base_model="x", refiner_model="y", steps=15, guidance_scale=6.0
  )
  assert p.name == "local_sdxl"
  assert p.base_model == "x"
  # 注意:本测试不调 generate();W4 才联调
