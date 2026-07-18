"""AnthropicProvider mock 测试。

要点:
- monkeypatch ``_ensure_client`` 注入假 client
- 测 chat / list_models / API key 缺失时报错 / 缺 SDK 时 ImportError
"""

from __future__ import annotations

import pytest

from media_to_doc.llm.anthropic import (
  DEFAULT_MODEL,
  SUPPORTED_MODELS,
  AnthropicProvider,
)

# ─────────────────────────────────────────────────────────────
# 假 client
# ─────────────────────────────────────────────────────────────


class _FakeTextBlock:
  def __init__(self, text: str) -> None:
    self.text = text


class _FakeAnthropicResponse:
  def __init__(self, texts: list[str]) -> None:
    self.content = [_FakeTextBlock(t) for t in texts]


class _FakeAnthropicClient:
  def __init__(
    self,
    *,
    reply: str = "reply from claude",
    raise_chat: Exception | None = None,
  ) -> None:
    self._reply = reply
    self._raise_chat = raise_chat
    self.last_kwargs: dict[str, object] = {}

  @property
  def messages(self) -> _FakeMessagesNamespace:
    return _FakeMessagesNamespace(self)


class _FakeMessagesNamespace:
  def __init__(self, parent: _FakeAnthropicClient) -> None:
    self._parent = parent

  def create(self, **kwargs: object) -> _FakeAnthropicResponse:
    self._parent.last_kwargs = kwargs
    if self._parent._raise_chat:
      raise self._parent._raise_chat
    return _FakeAnthropicResponse([self._parent._reply])


def _patched_provider(monkeypatch, fake: _FakeAnthropicClient) -> AnthropicProvider:
  p = AnthropicProvider(api_key="sk-test", model="claude-sonnet-4-6")

  def fake_ensure_client(self: AnthropicProvider) -> _FakeAnthropicClient:
    self._client = fake
    return fake

  monkeypatch.setattr(AnthropicProvider, "_ensure_client", fake_ensure_client)
  return p


# ─────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────


def test_constants_are_sane() -> None:
  assert DEFAULT_MODEL == "claude-sonnet-4-6"
  assert "claude-opus-4-7" in SUPPORTED_MODELS
  assert "claude-haiku-4-5" in SUPPORTED_MODELS


def test_provider_default_initialization() -> None:
  p = AnthropicProvider(api_key="sk-test")
  assert p.name == "anthropic"
  assert p.model == DEFAULT_MODEL


def test_provider_reads_api_key_from_env(monkeypatch) -> None:
  monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-env")
  p = AnthropicProvider()
  assert p._api_key == "sk-from-env"


def test_provider_explicit_api_key_overrides_env(monkeypatch) -> None:
  monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
  p = AnthropicProvider(api_key="sk-explicit")
  assert p._api_key == "sk-explicit"


# ─────────────────────────────────────────────────────────────
# chat
# ─────────────────────────────────────────────────────────────


def test_chat_returns_concatenated_text_blocks(monkeypatch) -> None:
  fake = _FakeAnthropicClient(reply="hello\nworld")
  p = _patched_provider(monkeypatch, fake)
  resp = p.chat("hi")
  assert resp.text == "hello\nworld"
  assert resp.provider == "anthropic"
  assert p._calls == 1


def test_chat_propagates_exception_and_records_failure(monkeypatch) -> None:
  fake = _FakeAnthropicClient(raise_chat=RuntimeError("API quota exceeded"))
  p = _patched_provider(monkeypatch, fake)
  with pytest.raises(RuntimeError, match="quota"):
    p.chat("hi")
  assert p._failures == 1


def test_chat_passes_model_and_temperature(monkeypatch) -> None:
  fake = _FakeAnthropicClient()
  p = _patched_provider(monkeypatch, fake)
  p.chat(
    "hi",
    temperature=0.7,
    max_tokens=2048,
  )
  kwargs = fake.last_kwargs
  assert kwargs["model"] == "claude-sonnet-4-6"
  assert kwargs["temperature"] == 0.7
  assert kwargs["max_tokens"] == 2048
  assert kwargs["messages"] == [{"role": "user", "content": "hi"}]


# ─────────────────────────────────────────────────────────────
# list_models
# ─────────────────────────────────────────────────────────────


def test_list_models_returns_supported() -> None:
  p = AnthropicProvider(api_key="sk-test")
  assert p.list_models() == SUPPORTED_MODELS


# ─────────────────────────────────────────────────────────────
# _ensure_client 错误处理
# ─────────────────────────────────────────────────────────────


def test_ensure_client_raises_when_api_key_missing(monkeypatch) -> None:
  """api_key 缺失时,即使 SDK 已装也抛 RuntimeError(无 key 不应静默)。"""
  monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
  p = AnthropicProvider()
  p._client = None
  with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
    p._ensure_client()


def test_ensure_client_raises_import_error_when_sdk_missing(monkeypatch) -> None:
  """SDK 缺失时抛 ImportError(信息含安装提示)。"""
  import builtins

  original_import = builtins.__import__

  def fake_import(name: str, *args: object, **kwargs: object) -> object:
    if name == "anthropic":
      raise ImportError("simulated no anthropic SDK")
    return original_import(name, *args, **kwargs)

  monkeypatch.setattr(builtins, "__import__", fake_import)
  p = AnthropicProvider(api_key="sk-test")
  p._client = None

  with pytest.raises(ImportError, match="anthropic SDK"):
    p._ensure_client()


def test_ensure_client_uses_base_url_when_provided(monkeypatch) -> None:
  """传 base_url 时 client 初始化应带上。"""
  import sys
  import types

  init_kwargs: dict[str, object] = {}

  class _CaptureClient:
    def __init__(self, **kwargs: object) -> None:
      init_kwargs.update(kwargs)
      self.messages = self

    def create(self, **kwargs: object) -> _FakeAnthropicResponse:
      return _FakeAnthropicResponse(["ok"])

  # 注入 fake anthropic module,让 ``from anthropic import Anthropic`` 拿到它
  fake_mod = types.ModuleType("anthropic")
  fake_mod.Anthropic = _CaptureClient  # type: ignore[attr-defined]
  monkeypatch.setitem(sys.modules, "anthropic", fake_mod)

  p = AnthropicProvider(api_key="sk-x", base_url="http://proxy:8080")
  p._client = None
  client = p._ensure_client()
  assert isinstance(client, _CaptureClient)
  assert init_kwargs["api_key"] == "sk-x"
  assert init_kwargs["base_url"] == "http://proxy:8080"
