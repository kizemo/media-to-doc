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


# ─────────────────────────────────────────────────────────────
# W14-D:HTTP_PROXY pollution 防护 — trust_env=False 透传到 httpx
# ─────────────────────────────────────────────────────────────

# 8 个 proxy env vars(W13-C 已固化为 baseline,详见 feedback memory
# ``feedback_proxy_env_pollution.md``)
PROXY_ENV_VARS = (
  "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
  "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy",
)


def test_ensure_client_passes_trust_env_false_to_anthropic_sdk(monkeypatch) -> None:
  """W14-D:_ensure_client 构造 Anthropic 客户端时必须透传
  http_client=httpx.Client(trust_env=False)。

  与 W14-B Ollama 同模式(commit 427d963),防止公司 VPN 父 shell 设的
  HTTP_PROXY/HTTPS_PROXY/all_proxy 把 api.anthropic.com 调用劫持到代理
  并触发 SSL handshake 失败。anthropic SDK 接受 ``http_client`` 参数
  (SDK ≥ 0.20),我们透传一个 ``trust_env=False`` 的 httpx.Client。
  """
  import sys
  import types

  import httpx

  captured: dict[str, object] = {}

  class _CaptureClient:
    def __init__(self, **kwargs: object) -> None:
      captured.update(kwargs)
      self.messages = self

    def create(self, **kwargs: object) -> _FakeAnthropicResponse:
      return _FakeAnthropicResponse(["ok"])

  fake_anthropic = types.ModuleType("anthropic")
  fake_anthropic.Anthropic = _CaptureClient  # type: ignore[attr-defined]
  monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

  p = AnthropicProvider(api_key="sk-x", model="claude-sonnet-4-6")
  p._client = None
  client = p._ensure_client()

  assert isinstance(client, _CaptureClient)
  assert "http_client" in captured, (
    "AnthropicProvider._ensure_client 必须给 Anthropic 传 http_client 参数,"
    " 否则 SDK 内部 httpx 会读 HTTP_PROXY 等 env vars"
  )
  http_client = captured["http_client"]
  assert isinstance(http_client, httpx.Client)
  assert http_client.trust_env is False, (
    "Anthropic 透传的 http_client 必须 trust_env=False"
  )


def test_ensure_client_unaffected_by_proxy_env_vars(monkeypatch) -> None:
  """W14-D:即使父 shell 设有 proxy vars,_ensure_client 仍能正常构造 client。

  验证 trust_env=False 真的让内部 httpx 忽略 HTTP_PROXY 等 — 因为我们用的是
  capture client,真正起决定作用的是 trust_env=False 已被传入(上一个测试已
  单独验证);这里再补一层集成:即使 env 被设满 proxy vars,构造路径不抛错。
  """
  import sys
  import types

  for var in PROXY_ENV_VARS:
    monkeypatch.setenv(var, "http://127.0.0.1:49223")

  captured: dict[str, object] = {}

  class _CaptureClient:
    def __init__(self, **kwargs: object) -> None:
      captured.update(kwargs)
      self.messages = self

    def create(self, **kwargs: object) -> _FakeAnthropicResponse:
      return _FakeAnthropicResponse(["ok"])

  fake_anthropic = types.ModuleType("anthropic")
  fake_anthropic.Anthropic = _CaptureClient  # type: ignore[attr-defined]
  monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

  p = AnthropicProvider(api_key="sk-x")
  p._client = None
  # 不抛 SSL / proxy error 即视为通过
  client = p._ensure_client()
  assert isinstance(client, _CaptureClient)
  assert "http_client" in captured
  assert captured["http_client"].trust_env is False


def test_ensure_client_idempotent_after_first_init(monkeypatch) -> None:
  """_ensure_client 第一次构造后,后续调用复用 self._client,不再传 kwargs。

  回归保护:若有人把 trust_env=False 漏写到 _ensure_client 之外的地方,
  这条测试还能确保客户端只构造一次(不会重复传 kwargs)。
  """
  import sys
  import types

  call_count = {"n": 0}

  class _CountingClient:
    def __init__(self, **kwargs: object) -> None:
      call_count["n"] += 1
      self.kwargs = dict(kwargs)
      self.messages = self

    def create(self, **kwargs: object) -> _FakeAnthropicResponse:
      return _FakeAnthropicResponse(["ok"])

  fake_anthropic = types.ModuleType("anthropic")
  fake_anthropic.Anthropic = _CountingClient  # type: ignore[attr-defined]
  monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

  p = AnthropicProvider(api_key="sk-x")
  p._client = None
  client1 = p._ensure_client()
  client2 = p._ensure_client()
  assert client1 is client2
  assert call_count["n"] == 1
