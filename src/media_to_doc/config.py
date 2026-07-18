"""media_to_doc 配置管理(``WorkflowConfig`` 数据类 + YAML 加载)。

Phase 0 占位:仅定义数据类与最简 YAML 加载。
Phase 1 起逐步添加:字段校验 / 环境变量覆盖 / DPAPI 加密 / provider 注册表。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from .paths import CONFIG_FILE

# ─────────────────────────────────────────────────────────────
# 类型别名(便于静态检查与 IDE 提示)
# ─────────────────────────────────────────────────────────────

LLMProviderName = Literal["ollama", "anthropic", "openai_compatible"]
ImagegenProviderName = Literal["local_sdxl", "skip"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


# ─────────────────────────────────────────────────────────────
# WorkflowConfig — 主配置数据类
# ─────────────────────────────────────────────────────────────


@dataclass
class LLMConfig:
  """LLM provider 配置。"""

  provider: LLMProviderName = "ollama"
  model: str = "qwen3:14b"
  fallback_providers: list[str] = field(default_factory=lambda: ["anthropic"])
  temperature: float = 0.3
  max_tokens: int = 4096
  timeout_seconds: int = 600

  # 加密 API key 存储路径(Windows DPAPI,Phase 2 实装)
  api_key_ref: str | None = None
  base_url: str | None = None


@dataclass
class ImagegenConfig:
  """AI 配图 provider 配置。"""

  provider: ImagegenProviderName = "local_sdxl"
  base_model: str = "stabilityai/stable-diffusion-xl-base-1.0"
  refiner_model: str = "stabilityai/stable-diffusion-xl-refiner-1.0"
  steps: int = 30
  guidance_scale: float = 7.5


@dataclass
class PathsConfig:
  """路径覆盖(默认见 ``paths.py``)。"""

  workspace: str | None = None
  models_cache: str | None = None


@dataclass
class PipelineConfig:
  """流水线行为配置。"""

  default_chunk_size: int = 15000  # CJK chars
  default_ocr_threshold: float = 0.5
  default_asr_window_seconds: int = 8
  skip_longdoc: bool = False


@dataclass
class WorkflowConfig:
  """media_to_doc 主配置(TDD §5.2)。"""

  llm: LLMConfig = field(default_factory=LLMConfig)
  imagegen: ImagegenConfig = field(default_factory=ImagegenConfig)
  paths: PathsConfig = field(default_factory=PathsConfig)
  pipeline: PipelineConfig = field(default_factory=PipelineConfig)
  log_level: LogLevel = "INFO"

  # ── 序列化 ──────────────────────────────────────────────

  def to_dict(self) -> dict[str, Any]:
    return asdict(self)

  def to_yaml(self) -> str:
    return yaml.safe_dump(
      self.to_dict(),
      allow_unicode=True,
      sort_keys=False,
      default_flow_style=False,
    )

  # ── 持久化 ──────────────────────────────────────────────

  def save(self, path: Path | None = None) -> Path:
    """保存到 YAML 文件,返回实际写入路径。"""
    target = path or CONFIG_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(self.to_yaml(), encoding="utf-8")
    return target

  # ── 反序列化 ──────────────────────────────────────────────

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> WorkflowConfig:
    """从 dict 构造(深嵌套构造)。"""
    return cls(
      llm=LLMConfig(**data.get("llm", {})),
      imagegen=ImagegenConfig(**data.get("imagegen", {})),
      paths=PathsConfig(**data.get("paths", {})),
      pipeline=PipelineConfig(**data.get("pipeline", {})),
      log_level=data.get("log_level", "INFO"),
    )

  @classmethod
  def load(cls, path: Path | None = None) -> WorkflowConfig:
    """从 YAML 文件加载,文件不存在返回默认值。"""
    target = path or CONFIG_FILE
    if not target.exists():
      return cls()
    data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    return cls.from_dict(data)


__all__ = [
  "LLMProviderName",
  "ImagegenProviderName",
  "LogLevel",
  "LLMConfig",
  "ImagegenConfig",
  "PathsConfig",
  "PipelineConfig",
  "WorkflowConfig",
]
