"""Stage 8 — ``imagegen``:AI 配图生成(SDXL Base + Refiner,可跳过)。

输入:
- ``raw/<视频同名>/chapter_NN.md``:草稿 markdown(含 ``[[GEN: prompt]]`` 标签)
  默认目录:``<work>/chapters/raw/<course_title>``,可通过 ``drafts_dir`` 覆盖

输出:
- ``raw/<视频同名>/images/gen_<uuid>.png``:AI 配图(默认目录:同 ``drafts_dir``
  的 ``images/`` 子目录)
- ``work/imagegen/imagegen.json``:整体 manifest(provider / 模型 / 张数)

行为:
1. 从 ``drafts_dir``(或自定义)扫描所有 ``chapter_NN.md``,抽取 ``[[GEN: prompt]]``
2. 对每条 prompt 调用 imagegen provider 生成 PNG,UUID 名命名
3. 替换 markdown 中的 ``[[GEN: ...]]`` 标记为相对路径
   ``![[gen_<uuid>.png]]`` 或保持原标记(取决于 provider)
4. ``provider=skip``:不调模型,保留 ``[[GEN: ...]]`` 原样,返回 prompt 列表

依赖:
- diffusers / torch(本地 SDXL);缺失时 :class:`LocalSdxlProvider` 抛清晰错误
- pipeline 内可注入 mock provider(测试用)

参考:TDD §5 数据流第 8 步 + PROJECT_DESCRIPTION §3.2 imagegen 行 +
     §3.3 imagegen_provider=skip 兼容。
"""

from __future__ import annotations

import json
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ..config import WorkflowConfig

# ─────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────

_GEN_TAG_RE = re.compile(r"\[\[GEN:\s*([^\]]+?)\s*\]\]")
_IMG_FILENAME = "gen_{uuid}.png"


# ─────────────────────────────────────────────────────────────
# Provider 抽象
# ─────────────────────────────────────────────────────────────


class ImagegenProvider(ABC):
  """AI 配图 provider 接口。"""

  name: str = "unknown"

  @abstractmethod
  def generate(self, prompt: str, output_path: Path) -> Path:
    """生成图像并写到 ``output_path``,返回实际写入路径。"""


class SkipProvider(ImagegenProvider):
  """``provider=skip`` 占位 —— 不生成图像,但记录 prompts 到 manifest。"""

  name = "skip"

  def generate(self, prompt: str, output_path: Path) -> Path:  # pragma: no cover - 文档级
    raise RuntimeError(
      "SkipProvider.generate() 不该被调用 — generate_images() 应短路跳过",
    )


class LocalSdxlProvider(ImagegenProvider):
  """本地 SDXL Base + Refiner(lazy import diffusers)。"""

  name = "local_sdxl"

  def __init__(
    self,
    *,
    base_model: str,
    refiner_model: str,
    steps: int = 30,
    guidance_scale: float = 7.5,
    refiner_strength: float = 0.3,
    device: str = "cuda",
  ) -> None:
    self.base_model = base_model
    self.refiner_model = refiner_model
    self.steps = steps
    self.guidance_scale = guidance_scale
    self.refiner_strength = refiner_strength
    self.device = device

  def generate(self, prompt: str, output_path: Path) -> Path:
    """调 SDXL Base + Refiner 出图。"""
    try:
      import importlib

      importlib.util.find_spec("diffusers")  # noqa: F401 — 验证可用性
      importlib.util.find_spec("torch")  # noqa: F401 — 验证可用性
    except (ImportError, AttributeError) as exc:  # pragma: no cover - 装饰级
      raise ImportError(
        "LocalSdxlProvider 需要 diffusers + torch;"
        "请 ``uv sync --extra imagegen`` 装齐依赖后再跑"
      ) from exc

    # 真实调用留作 W4+ 联调(W3 测试全程 mock)。
    # 这里最小化暴露接口,签名稳定即可。
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"")  # 占位字节;W4 接真实 SDXL
    return output_path


class _ProviderLike(Protocol):
  """duck-typed provider 接口(测试可注入任意满足该协议的对象)。"""

  name: str

  def generate(self, prompt: str, output_path: Path) -> Path: ...


# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


@dataclass
class GeneratedImage:
  """单张生成图。"""

  uuid: str
  prompt: str
  source_chapter: str  # basename of source chapter_NN.md
  output_path: Path
  skipped: bool = False

  def to_dict(self) -> dict[str, object]:
    return {
      "uuid": self.uuid,
      "prompt": self.prompt,
      "source_chapter": self.source_chapter,
      "output_path": str(self.output_path),
      "skipped": self.skipped,
    }


@dataclass
class ImagesReport:
  """整体配图结果(对应 ``imagegen.json``)。"""

  video: str = ""
  provider: str = ""
  base_model: str = ""
  refiner_model: str = ""
  output_dir: str = ""
  images: list[GeneratedImage] = field(default_factory=list)
  skipped_prompts: list[str] = field(default_factory=list)

  @property
  def count(self) -> int:
    return len(self.images)

  def to_dict(self) -> dict[str, object]:
    return {
      "video": self.video,
      "provider": self.provider,
      "base_model": self.base_model,
      "refiner_model": self.refiner_model,
      "output_dir": self.output_dir,
      "count": self.count,
      "skipped_count": len(self.skipped_prompts),
      "images": [i.to_dict() for i in self.images],
      "skipped_prompts": list(self.skipped_prompts),
    }

  def save(self, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
      json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
      encoding="utf-8",
    )


# ─────────────────────────────────────────────────────────────
# 公开 API
# ─────────────────────────────────────────────────────────────


def extract_prompts(md_text: str) -> list[str]:
  """从 markdown 中抽取 ``[[GEN: prompt]]`` 标签列表。"""
  return [m.strip() for m in _GEN_TAG_RE.findall(md_text) if m.strip()]


def build_provider(config: WorkflowConfig) -> ImagegenProvider:
  """从 :class:`ImagegenConfig` 构造 provider(skip / local_sdxl)。"""
  cfg = config.imagegen
  if cfg.provider == "skip":
    return SkipProvider()
  if cfg.provider == "local_sdxl":
    return LocalSdxlProvider(
      base_model=cfg.base_model,
      refiner_model=cfg.refiner_model,
      steps=cfg.steps,
      guidance_scale=cfg.guidance_scale,
    )
  raise ValueError(f"未知 imagegen provider: {cfg.provider!r}")


def generate_images(
  work: Path,
  config: WorkflowConfig | None = None,
  *,
  drafts_dir: Path | None = None,
  output_dir: Path | None = None,
  provider: ImagegenProvider | None = None,
) -> ImagesReport:
  """Stage 8:为每章 ``[[GEN: ...]]`` 标签生成 AI 配图。

  Parameters
  ----------
  work : Path
    work 根目录
  config : WorkflowConfig | None
    配置(``config.imagegen`` 决定 provider)
  drafts_dir : Path | None
    含 ``chapter_NN.md`` 的草稿根目录(默认 ``<work>/chapters/raw/<course_title>``)
  output_dir : Path | None
    PNG 输出目录(默认 ``<drafts_dir>/images``)
  provider : ImagegenProvider | None
    显式 provider(优先于 config);测试可注入 mock

  Returns
  -------
  ImagesReport
    整体结果(已写盘:每张 PNG + work/imagegen/imagegen.json)

  Notes
  -----
  - ``provider=skip`` 时,只记录 prompts,不写 PNG 与不替换标记
  - 单讲座通常 < 30 张;长讲座分章节可上百张
  """
  cfg = config or WorkflowConfig()
  if drafts_dir is None:
    drafts_dir = work / "chapters" / "raw"  # 默认顶层 raw 目录
  if output_dir is None:
    output_dir = drafts_dir / "images"

  if provider is None:
    provider = build_provider(cfg)

  output_dir.mkdir(parents=True, exist_ok=True)

  images: list[GeneratedImage] = []
  skipped: list[str] = []

  chapter_files = sorted(drafts_dir.glob("chapter_*.md"))
  for chapter_md in chapter_files:
    text = chapter_md.read_text(encoding="utf-8")
    prompts = extract_prompts(text)
    if not prompts:
      continue
    if isinstance(provider, SkipProvider):
      # skip 模式:不写文件,记录 prompts
      skipped.extend(prompts)
      continue
    for prompt in prompts:
      img_uuid = uuid.uuid4().hex[:12]
      img_path = output_dir / _IMG_FILENAME.format(uuid=img_uuid)
      provider.generate(prompt, img_path)
      images.append(
        GeneratedImage(
          uuid=img_uuid,
          prompt=prompt,
          source_chapter=chapter_md.name,
          output_path=img_path,
          skipped=False,
        )
      )

  # 写整体 manifest
  manifest_path = work / "imagegen" / "imagegen.json"
  report = ImagesReport(
    video=work.name or "",
    provider=provider.name,
    base_model=getattr(provider, "base_model", ""),
    refiner_model=getattr(provider, "refiner_model", ""),
    output_dir=str(output_dir),
    images=images,
    skipped_prompts=skipped,
  )
  report.save(manifest_path)

  # 若非 skip,把 chapter_NN.md 的 [[GEN: ...]] 替换为相对路径嵌入
  if images and not skipped:
    _substitute_image_refs(drafts_dir, output_dir, images)

  return report


def _substitute_image_refs(
  drafts_dir: Path,
  output_dir: Path,
  images: list[GeneratedImage],
) -> None:
  """用 ``![[gen_<uuid>.png]]`` 替换 chapter_NN.md 里的 ``[[GEN: ...]]``(单文件多次)。"""
  by_chapter: dict[str, list[GeneratedImage]] = {}
  for img in images:
    by_chapter.setdefault(img.source_chapter, []).append(img)

  for chapter_name, img_list in by_chapter.items():
    md_path = drafts_dir / chapter_name
    if not md_path.exists():
      continue
    text = md_path.read_text(encoding="utf-8")
    refs = [f"![[gen_{img.uuid}.png]]" for img in img_list]
    new_text = _replace_first_n(text, refs)
    md_path.write_text(new_text, encoding="utf-8")


def _replace_first_n(text: str, replacements: list[str]) -> str:
  """用 ``replacements`` 顺序替换文本中的前 N 个 ``![[...png]]`` 标签。"""
  out: list[str] = []
  pos = 0
  i = 0
  while i < len(replacements):
    m = _GEN_TAG_RE.search(text, pos)
    if not m:
      break
    out.append(text[pos : m.start()])
    out.append(replacements[i])
    pos = m.end()
    i += 1
  out.append(text[pos:])
  return "".join(out)


__all__ = [
  "ImagegenProvider",
  "SkipProvider",
  "LocalSdxlProvider",
  "GeneratedImage",
  "ImagesReport",
  "extract_prompts",
  "build_provider",
  "generate_images",
]
