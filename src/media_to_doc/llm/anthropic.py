"""Anthropic Claude API provider。

触发方式:
- ``LLM_PROVIDER=anthropic``
- ``ANTHROPIC_API_KEY`` 环境变量(或 ``api_key`` 参数显式传入)

依赖:
- ``anthropic>=0.31.0`` Python SDK(lazy import)

参考:TDD §4.2.3 + PROJECT_DESCRIPTION.md §3.3 anthropic 行。
"""

from __future__ import annotations

import os

from .base import BaseLLMProvider

# ─────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────

DEFAULT_MODEL = "claude-sonnet-4-6"
# Claude 4.x 系列(2026-07 当前推荐)
SUPPORTED_MODELS: list[str] = [
  "claude-opus-4-7",
  "claude-sonnet-4-6",
  "claude-haiku-4-5",
]


# ─────────────────────────────────────────────────────────────
# Provider
# ─────────────────────────────────────────────────────────────


class AnthropicProvider(BaseLLMProvider):
  """Anthropic Claude provider。

  Parameters
  ----------
  api_key : str | None
    Anthropic API key;默认读 ``$ANTHROPIC_API_KEY``
  base_url : str | None
    自定义 endpoint(代理 / Bedrock 兼容层)
  model : str | None
    模型名,默认 ``claude-sonnet-4-6``
  """

  def __init__(
    self,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    timeout_seconds: int = 600,
  ) -> None:
    super().__init__(
      model=model or DEFAULT_MODEL,
      temperature=temperature,
      max_tokens=max_tokens,
      timeout_seconds=timeout_seconds,
    )
    self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    self._base_url = base_url
    self._client: object | None = None  # lazy init

  @property
  def name(self) -> str:
    return "anthropic"

  def list_models(self) -> list[str]:
    return list(SUPPORTED_MODELS)

  def _chat_impl(
    self,
    prompt: str,
    *,
    model: str | None,
    temperature: float,
    max_tokens: int,
    timeout_seconds: int,
  ) -> str:
    client = self._ensure_client()
    response = client.messages.create(  # type: ignore[attr-defined]
      model=model or self.model or DEFAULT_MODEL,
      max_tokens=max_tokens,
      messages=[{"role": "user", "content": prompt}],
      temperature=temperature,
      timeout=timeout_seconds,
    )
    # SDK 返回 Message;content 是 list[ContentBlock];取 text 字段
    content = getattr(response, "content", None) or []
    parts: list[str] = []
    for block in content:
      text = getattr(block, "text", None)
      if text:
        parts.append(str(text))
    return "\n".join(parts).strip()

  # ── 内部 ────────────────────────────────────────────────

  def _ensure_client(self) -> object:
    """lazy init Anthropic 客户端。"""
    if self._client is not None:
      return self._client
    if not self._api_key:
      raise RuntimeError(
        "AnthropicProvider 需要 API key;设置 ANTHROPIC_API_KEY 环境变量"
        "或在 get_provider() 中传 api_key 参数"
      )
    try:
      from anthropic import Anthropic  # type: ignore[import-untyped]
    except ImportError as exc:
      raise ImportError(
        "AnthropicProvider 需要 anthropic SDK。安装方式:"
        "uv add 'media_to_doc[llm]' 或 uv add anthropic"
      ) from exc
    kwargs: dict[str, object] = {"api_key": self._api_key}
    if self._base_url:
      kwargs["base_url"] = self._base_url
    self._client = Anthropic(**kwargs)
    return self._client


__all__ = [
  "AnthropicProvider",
  "DEFAULT_MODEL",
  "SUPPORTED_MODELS",
]
