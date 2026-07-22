"""Ollama 本地 LLM provider(默认 provider,完全离线)。

触发方式:
- ``LLM_PROVIDER=ollama``
- Ollama 服务在 ``http://127.0.0.1:11434``(默认)

依赖:
- ``ollama>=0.3.0`` Python SDK(lazy import,只装 ``media_to_doc[llm]`` extras 才可用)

参考:TDD §4.2 + PROJECT_DESCRIPTION.md §3.3 ollama 行。

注意(W14-B):``_ensure_client`` 构造 ``ollama.Client`` 时透传
``trust_env=False`` 给内部 httpx,防止公司 VPN 父 shell 设的
``HTTP_PROXY`` / ``HTTPS_PROXY`` / ``all_proxy`` 把 localhost 调用劫持到
代理并触发 SSL handshake 失败。详见 feedback memory
``feedback_proxy_env_pollution.md``。
"""

from __future__ import annotations

import os

from .base import BaseLLMProvider

# ─────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3:14b"
# Ollama 内置可见模型(SDK 不可用时的回退列表)
FALLBACK_MODELS: list[str] = [
  "qwen3:14b",
  "qwen3:8b",
  "qwen2.5:14b",
  "llama3.1:8b",
  "gemma3:4b",
]


# ─────────────────────────────────────────────────────────────
# Provider
# ─────────────────────────────────────────────────────────────


class OllamaProvider(BaseLLMProvider):
  """Ollama 本地推理 provider。

  Parameters
  ----------
  model : str | None
    模型名,默认 ``qwen3:14b``
  base_url : str | None
    Ollama 服务地址,默认 ``$OLLAMA_HOST`` 或 ``http://127.0.0.1:11434``
  temperature / max_tokens / timeout_seconds
    通用参数,见 :class:`BaseLLMProvider`
  """

  def __init__(
    self,
    *,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    timeout_seconds: int = 600,
    base_url: str | None = None,
    num_ctx: int | None = None,
  ) -> None:
    super().__init__(
      model=model or DEFAULT_MODEL,
      temperature=temperature,
      max_tokens=max_tokens,
      timeout_seconds=timeout_seconds,
    )
    self._base_url = base_url or os.environ.get("OLLAMA_HOST") or DEFAULT_BASE_URL
    self._num_ctx = num_ctx  # None → Ollama 默认(常 4096);显式给大值可扩到 32k/128k
    self._client: object | None = None  # lazy init

  @property
  def name(self) -> str:
    return "ollama"

  def list_models(self) -> list[str]:
    """列出 Ollama 服务上已下载的模型(SDK 不可用时返回 fallback 列表)。"""
    try:
      client = self._ensure_client()
    except ImportError:
      return list(FALLBACK_MODELS)

    try:
      response = client.list()  # type: ignore[attr-defined]
      models: list[str] = []
      # SDK 返回 ListResponse;每个 model 有 .model 属性
      for entry in getattr(response, "models", []) or []:
        model_id = getattr(entry, "model", None) or getattr(entry, "name", None)
        if model_id:
          models.append(str(model_id))
      return models or list(FALLBACK_MODELS)
    except Exception:
      # 服务未运行 / 网络问题 → 返回 fallback(避免阻塞配置阶段)
      return list(FALLBACK_MODELS)

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
    options: dict[str, object] = {
      "temperature": temperature,
      "num_predict": max_tokens,
    }
    if self._num_ctx is not None:
      options["num_ctx"] = self._num_ctx
    response = client.chat(  # type: ignore[attr-defined]
      model=model or self.model or DEFAULT_MODEL,
      messages=[{"role": "user", "content": prompt}],
      options=options,
    )
    # SDK 0.3+ 返回 ChatResponse; message.content 是文本
    message = getattr(response, "message", None)
    if message is not None:
      content = getattr(message, "content", "")
      return str(content).strip()
    # 兜底:老 SDK 返回 dict
    if isinstance(response, dict):
      msg = response.get("message") or {}
      return str(msg.get("content", "")).strip()
    return str(response).strip()

  # ── 内部 ────────────────────────────────────────────────

  def _ensure_client(self) -> object:
    """lazy init Ollama 客户端(失败抛清晰 ImportError)。

    透传 ``trust_env=False`` 给内部 httpx,这样 httpx 不会读
    ``HTTP_PROXY`` / ``HTTPS_PROXY`` / ``all_proxy`` 等环境变量,避免
    公司 VPN 父 shell 把 localhost:11434 调用劫持到代理。
    详见 feedback memory ``feedback_proxy_env_pollution.md``。
    """
    if self._client is not None:
      return self._client
    try:
      import ollama  # type: ignore[import-untyped]
    except ImportError as exc:
      raise ImportError(
        "OllamaProvider 需要 ollama Python SDK。安装方式:"
        "uv add 'media_to_doc[llm]' 或 uv add ollama"
      ) from exc
    self._client = ollama.Client(host=self._base_url, trust_env=False)
    return self._client


__all__ = [
  "OllamaProvider",
  "DEFAULT_BASE_URL",
  "DEFAULT_MODEL",
]
