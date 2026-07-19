"""LLM provider 抽象层。

支持 3 个 provider,均通过 ``get_provider()`` 工厂按名创建:

- ``ollama``(默认):本地 Ollama(``http://127.0.0.1:11434``)
- ``anthropic``:Anthropic Claude API(``ANTHROPIC_API_KEY`` 环境变量)
- ``openai_compatible``:任何 OpenAI Chat Completions 协议兼容的端点
  (MiniMax / DeepSeek / 智谱 / Moonshot / 混元 / OpenRouter / DashScope 等)

参考:
- TDD §4.2 LLM Provider 抽象
- PROJECT_DESCRIPTION.md §3.3 LLM Provider 矩阵

设计要点:
- 3 个 provider 全部 **lazy import**(缺库时给清晰 ImportError + 安装提示)
- 统一 :meth:`BaseLLMProvider.chat` 入口,内部累积调用/失败计数,
  :meth:`BaseLLMProvider.health` 给 LE L1 健康度评估用
- 不强制要求 stream;W2 chapters 是非流式调用,W3+ 按需补
"""

from __future__ import annotations

from .base import (
  BaseLLMProvider,
  ChatMessage,
  ChatResponse,
  HealthReport,
  HealthStatus,
)
from .openai_compat import OpenAICompatProvider

__all__ = [
  "BaseLLMProvider",
  "ChatMessage",
  "ChatResponse",
  "HealthReport",
  "HealthStatus",
  "PROVIDERS",
  "get_provider",
  "register_provider",
]


# ─────────────────────────────────────────────────────────────
# Provider 注册表(便于 get_provider(name) 工厂调用)
# ─────────────────────────────────────────────────────────────

PROVIDERS: dict[str, type[BaseLLMProvider]] = {}


def register_provider(name: str, cls: type[BaseLLMProvider]) -> None:
  """注册一个 provider(测试 / 插件扩展用)。"""
  PROVIDERS[name] = cls


def get_provider(
  name: str,
  *,
  model: str | None = None,
  api_key: str | None = None,
  base_url: str | None = None,
  temperature: float = 0.3,
  max_tokens: int = 4096,
  timeout_seconds: int = 600,
  preset: str | None = None,
  num_ctx: int | None = None,
) -> BaseLLMProvider:
  """工厂:按名创建 provider 实例。

  Parameters
  ----------
  name : str
    ``ollama`` / ``anthropic`` / ``openai_compatible``
  model : str | None
    默认模型(None 时由 provider 选内置默认)
  api_key / base_url : str | None
    openai_compatible 必填;anthropic 不传时读 ``ANTHROPIC_API_KEY``
  temperature / max_tokens / timeout_seconds
    通用参数(各 provider 内部映射)
  preset : str | None
    ``openai_compatible`` 专用:内置厂商名(MiniMax / deepseek / zhipu /
    moonshot / openrouter / dashscope / hunyuan),传 preset 时自动填 base_url
  num_ctx : int | None
    Ollama 上下文窗口大小(``None`` 用 Ollama 默认);长 transcript 调 LLM
    时建议显式设 32768 / 65536 / 131072 避免 "exceeds context size" 错误

  Returns
  -------
  BaseLLMProvider
    已初始化(provider 内部 lazy import 实际 SDK)
  """
  if name not in PROVIDERS:
    raise KeyError(
      f"未知 LLM provider: {name!r};可选: {sorted(PROVIDERS.keys())}"
    )
  cls = PROVIDERS[name]
  kwargs: dict[str, object] = {
    "model": model,
    "temperature": temperature,
    "max_tokens": max_tokens,
    "timeout_seconds": timeout_seconds,
  }
  if name == "openai_compatible":
    kwargs["api_key"] = api_key
    if preset is not None:
      kwargs["preset"] = preset
    else:
      kwargs["base_url"] = base_url
  elif name == "anthropic":
    kwargs["api_key"] = api_key
    if base_url is not None:
      kwargs["base_url"] = base_url
  elif name == "ollama":
    kwargs["num_ctx"] = num_ctx
  return cls(**kwargs)  # type: ignore[arg-type]


# 延迟注册:避免 import 本模块时触发重依赖
def _register_defaults() -> None:
  from .anthropic import AnthropicProvider
  from .ollama import OllamaProvider

  register_provider("ollama", OllamaProvider)
  register_provider("anthropic", AnthropicProvider)
  register_provider("openai_compatible", OpenAICompatProvider)


_register_defaults()
