"""OpenAI 兼容 provider + 注册表测试。

覆盖:
- PRESETS 7 个厂商
- OpenAICompatProvider preset/base_url 模式
- 工厂 get_provider + register_provider
- list_models preset 静态列表 / SDK 自动发现 / 失败兜底
- _chat_impl 解析 OpenAI SDK 返回
"""

from __future__ import annotations

import pytest

from media_to_doc.llm import (
  PROVIDERS,
  get_provider,
  register_provider,
)
from media_to_doc.llm.base import BaseLLMProvider
from media_to_doc.llm.openai_compat import PRESETS, OpenAICompatProvider

# ─────────────────────────────────────────────────────────────
# 假 client
# ─────────────────────────────────────────────────────────────


class _FakeChoice:
  def __init__(self, content: str) -> None:
    self.message = _FakeMessage(content)


class _FakeMessage:
  def __init__(self, content: str) -> None:
    self.content = content


class _FakeOpenAIChatResponse:
  def __init__(self, content: str) -> None:
    self.choices = [_FakeChoice(content)]


class _FakeOpenAIModelEntry:
  def __init__(self, model_id: str) -> None:
    self.id = model_id


class _FakeOpenAIListResponse:
  def __init__(self, ids: list[str]) -> None:
    self.data = [_FakeOpenAIModelEntry(i) for i in ids]


class _FakeOpenAIClient:
  def __init__(
    self,
    *,
    reply: str = "ok",
    models: list[str] | None = None,
    raise_chat: Exception | None = None,
    raise_list: Exception | None = None,
  ) -> None:
    self._reply = reply
    self._models = models or []
    self._raise_chat = raise_chat
    self._raise_list = raise_list
    self.chat = _FakeChatNamespace(self)
    self.models = _FakeModelsNamespace(self)
    self.last_init_kwargs: dict[str, object] = {}


class _FakeChatNamespace:
  def __init__(self, parent: _FakeOpenAIClient) -> None:
    self._parent = parent
    self.completions = _FakeCompletionsNamespace(parent)


class _FakeCompletionsNamespace:
  def __init__(self, parent: _FakeOpenAIClient) -> None:
    self._parent = parent
    self.last_kwargs: dict[str, object] = {}

  def create(self, **kwargs: object) -> _FakeOpenAIChatResponse:
    self.last_kwargs = kwargs
    if self._parent._raise_chat:
      raise self._parent._raise_chat
    return _FakeOpenAIChatResponse(self._parent._reply)


class _FakeModelsNamespace:
  def __init__(self, parent: _FakeOpenAIClient) -> None:
    self._parent = parent

  def list(self) -> _FakeOpenAIListResponse:
    if self._parent._raise_list:
      raise self._parent._raise_list
    return _FakeOpenAIListResponse(self._parent._models)


def _patched_provider(
  monkeypatch,
  fake: _FakeOpenAIClient,
  *,
  preset: str | None = "minimax",
  base_url: str | None = None,
  api_key: str = "sk-test",
) -> OpenAICompatProvider:
  p = OpenAICompatProvider(
    api_key=api_key,
    base_url=base_url,
    preset=preset,
    model="preset-model",
  )

  def fake_ensure_client(self: OpenAICompatProvider) -> _FakeOpenAIClient:
    self._client = fake
    return fake

  monkeypatch.setattr(OpenAICompatProvider, "_ensure_client", fake_ensure_client)
  return p


# ─────────────────────────────────────────────────────────────
# PRESETS
# ─────────────────────────────────────────────────────────────


def test_presets_contains_seven_vendors() -> None:
  """TDD 规定 7 个厂商 preset。"""
  expected = {"minimax", "deepseek", "zhipu", "moonshot", "openrouter", "dashscope", "hunyuan"}
  assert set(PRESETS.keys()) == expected


def test_presets_each_have_base_url() -> None:
  for name, cfg in PRESETS.items():
    assert "base_url" in cfg, f"{name} 缺 base_url"
    assert cfg["base_url"].startswith("http"), f"{name} base_url 不是 http"


def test_presets_openrouter_has_no_static_models() -> None:
  """openrouter 列表是动态的(自动发现)。"""
  assert PRESETS["openrouter"]["models"] == []


def test_presets_minimax_includes_text01() -> None:
  assert "MiniMax-Text-01" in PRESETS["minimax"]["models"]


# ─────────────────────────────────────────────────────────────
# 初始化
# ─────────────────────────────────────────────────────────────


def test_init_with_preset_resolves_base_url_and_first_model() -> None:
  p = OpenAICompatProvider(api_key="sk-x", preset="deepseek")
  assert p._base_url == "https://api.deepseek.com/v1"
  assert p.model == "deepseek-chat"  # preset 第一个


def test_init_with_explicit_base_url() -> None:
  p = OpenAICompatProvider(
    api_key="sk-x",
    base_url="https://internal.corp/v1",
    model="my-model",
  )
  assert p._base_url == "https://internal.corp/v1"
  assert p.model == "my-model"


def test_init_with_unknown_preset_raises() -> None:
  with pytest.raises(KeyError, match="unknown-vendor"):
    OpenAICompatProvider(api_key="sk-x", preset="unknown-vendor")


def test_init_openrouter_with_no_model_keeps_none() -> None:
  """openrouter 没有静态列表时,model 保持 None(让 endpoint 选)。"""
  p = OpenAICompatProvider(api_key="sk-x", preset="openrouter")
  assert p._base_url == "https://openrouter.ai/api/v1"
  assert p.model is None
  assert p._preset_models == []


# ─────────────────────────────────────────────────────────────
# list_models
# ─────────────────────────────────────────────────────────────


def test_list_models_returns_preset_static_list(monkeypatch) -> None:
  p = OpenAICompatProvider(api_key="sk-x", preset="minimax")
  models = p.list_models()
  assert "MiniMax-Text-01" in models
  assert "abab6.5s-chat" in models


def test_list_models_falls_back_to_sdk_discovery(monkeypatch) -> None:
  fake = _FakeOpenAIClient(models=["discovered-a", "discovered-b"])
  p = _patched_provider(monkeypatch, fake, preset=None, base_url="https://x/v1")
  models = p.list_models()
  assert models == ["discovered-a", "discovered-b"]


def test_list_models_returns_empty_when_sdk_fails(monkeypatch) -> None:
  """SDK 自动发现失败 + 无 preset 静态列表 → 返回空。"""
  fake = _FakeOpenAIClient(raise_list=ConnectionError("api down"))
  # 用 preset=None 让 _preset_models 为空,走 SDK 自动发现路径
  p = _patched_provider(monkeypatch, fake, preset=None, base_url="https://x/v1")
  models = p.list_models()
  assert models == []


# ─────────────────────────────────────────────────────────────
# chat
# ─────────────────────────────────────────────────────────────


def test_chat_extracts_text_from_completion(monkeypatch) -> None:
  fake = _FakeOpenAIClient(reply="MiniMax reply content")
  p = _patched_provider(monkeypatch, fake)
  resp = p.chat("hi")
  assert resp.text == "MiniMax reply content"
  assert resp.provider == "openai_compatible"
  assert p._calls == 1
  # 验证传给 SDK 的参数
  ns = fake.chat.completions
  assert ns.last_kwargs["model"] == "preset-model"
  assert ns.last_kwargs["messages"] == [{"role": "user", "content": "hi"}]
  assert ns.last_kwargs["temperature"] == 0.3
  assert ns.last_kwargs["max_tokens"] == 4096


def test_chat_propagates_sdk_exception(monkeypatch) -> None:
  fake = _FakeOpenAIClient(raise_chat=RuntimeError("rate limit"))
  p = _patched_provider(monkeypatch, fake)
  with pytest.raises(RuntimeError, match="rate limit"):
    p.chat("hi")
  assert p._failures == 1


def test_chat_returns_empty_when_no_choices(monkeypatch) -> None:
  class _EmptyResponse:
    choices: list[object] = []

  class _EmptyCompletions:
    def create(self, **kwargs: object) -> _EmptyResponse:
      return _EmptyResponse()

  class _ChatNs:
    completions = _EmptyCompletions()

    @property
    def chat(self) -> _ChatNs:
      return self

  p = OpenAICompatProvider(api_key="sk-x", preset="minimax")

  def fake_ensure(self: OpenAICompatProvider) -> object:
    self._client = _ChatNs()
    return self._client

  monkeypatch.setattr(OpenAICompatProvider, "_ensure_client", fake_ensure)
  resp = p.chat("hi")
  assert resp.text == ""


# ─────────────────────────────────────────────────────────────
# _ensure_client 错误
# ─────────────────────────────────────────────────────────────


def test_ensure_client_raises_without_api_key() -> None:
  p = OpenAICompatProvider(preset="minimax")
  p._api_key = None
  p._client = None
  with pytest.raises(RuntimeError, match="api_key"):
    p._ensure_client()


def test_ensure_client_raises_without_base_url() -> None:
  p = OpenAICompatProvider(api_key="sk-x", base_url=None, preset=None)
  p._base_url = ""
  p._client = None
  with pytest.raises(RuntimeError, match="base_url"):
    p._ensure_client()


def test_ensure_client_raises_import_error_when_sdk_missing(monkeypatch) -> None:
  import builtins

  original_import = builtins.__import__

  def fake_import(name: str, *args: object, **kwargs: object) -> object:
    if name == "openai":
      raise ImportError("simulated no openai SDK")
    return original_import(name, *args, **kwargs)

  monkeypatch.setattr(builtins, "__import__", fake_import)
  p = OpenAICompatProvider(api_key="sk-x", preset="minimax")
  p._client = None
  with pytest.raises(ImportError, match="openai SDK"):
    p._ensure_client()


# ─────────────────────────────────────────────────────────────
# 工厂 + 注册表
# ─────────────────────────────────────────────────────────────


def test_providers_registry_contains_all_three() -> None:
  assert "ollama" in PROVIDERS
  assert "anthropic" in PROVIDERS
  assert "openai_compatible" in PROVIDERS
  for cls in PROVIDERS.values():
    assert issubclass(cls, BaseLLMProvider)


def test_get_provider_ollama() -> None:
  provider = get_provider("ollama", model="qwen3:8b")
  assert provider.name == "ollama"
  assert provider.model == "qwen3:8b"


def test_get_provider_anthropic() -> None:
  provider = get_provider("anthropic", api_key="sk-test", model="claude-haiku-4-5")
  assert provider.name == "anthropic"
  assert provider._api_key == "sk-test"
  assert provider.model == "claude-haiku-4-5"


def test_get_provider_openai_compatible_with_preset() -> None:
  provider = get_provider(
    "openai_compatible",
    api_key="sk-test",
    preset="minimax",
  )
  assert provider.name == "openai_compatible"
  assert provider._base_url == PRESETS["minimax"]["base_url"]


def test_get_provider_openai_compatible_with_custom_base_url() -> None:
  provider = get_provider(
    "openai_compatible",
    api_key="sk-test",
    base_url="https://internal.corp/v1",
    model="my-model",
  )
  assert provider._base_url == "https://internal.corp/v1"
  assert provider.model == "my-model"


def test_get_provider_unknown_raises() -> None:
  with pytest.raises(KeyError, match="未知 LLM provider"):
    get_provider("does-not-exist")


def test_get_provider_passes_temperature_and_max_tokens() -> None:
  provider = get_provider("ollama", temperature=0.9, max_tokens=8192, timeout_seconds=300)
  assert provider.temperature == 0.9
  assert provider.max_tokens == 8192
  assert provider.timeout_seconds == 300


def test_register_provider_extends_registry() -> None:
  class _CustomProvider(BaseLLMProvider):
    @property
    def name(self) -> str:
      return "custom"

    def list_models(self) -> list[str]:
      return ["custom-1"]

    def _chat_impl(
      self,
      prompt: str,
      *,
      model: str | None,
      temperature: float,
      max_tokens: int,
      timeout_seconds: int,
    ) -> str:
      return "custom reply"

  register_provider("custom", _CustomProvider)
  try:
    assert "custom" in PROVIDERS
    provider = get_provider("custom")
    assert provider.name == "custom"
    assert provider.chat("hi").text == "custom reply"
  finally:
    PROVIDERS.pop("custom", None)


# ─────────────────────────────────────────────────────────────
# W14-D:HTTP_PROXY pollution 防护 — trust_env=False 透传到 httpx
# ─────────────────────────────────────────────────────────────

# 8 个 proxy env vars(W13-C 已固化为 baseline,详见 feedback memory
# ``feedback_proxy_env_pollution.md``)
PROXY_ENV_VARS = (
  "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
  "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy",
)


def test_ensure_client_passes_trust_env_false_to_openai_sdk(monkeypatch) -> None:
  """W14-D:_ensure_client 构造 OpenAI 客户端时必须透传
  http_client=httpx.Client(trust_env=False)。

  与 W14-B Ollama 同模式(commit 427d963),防止公司 VPN 父 shell 设的
  HTTP_PROXY/HTTPS_PROXY/all_proxy 把 7 个 preset(minimax/deepseek/zhipu/
  moonshot/openrouter/dashscope/hunyuan)调用劫持到代理。openai SDK ≥ 1.40
  接受 ``http_client`` 参数,我们透传一个 ``trust_env=False`` 的 httpx.Client。
  """
  import sys
  import types

  import httpx

  captured: dict[str, object] = {}

  class _CaptureClient:
    def __init__(self, **kwargs: object) -> None:
      captured.update(kwargs)
      self.chat = _FakeChatNamespace(_FakeOpenAIClient())
      self.models = _FakeModelsNamespace(_FakeOpenAIClient())

  fake_openai = types.ModuleType("openai")
  fake_openai.OpenAI = _CaptureClient  # type: ignore[attr-defined]
  monkeypatch.setitem(sys.modules, "openai", fake_openai)

  p = OpenAICompatProvider(
    api_key="sk-x",
    preset="minimax",
    model="preset-model",
  )
  p._client = None
  client = p._ensure_client()

  assert isinstance(client, _CaptureClient)
  assert "http_client" in captured, (
    "OpenAICompatProvider._ensure_client 必须给 OpenAI 传 http_client 参数,"
    " 否则 SDK 内部 httpx 会读 HTTP_PROXY 等 env vars"
  )
  http_client = captured["http_client"]
  assert isinstance(http_client, httpx.Client)
  assert http_client.trust_env is False, (
    "OpenAICompat 透传的 http_client 必须 trust_env=False"
  )


def test_ensure_client_unaffected_by_proxy_env_vars(monkeypatch) -> None:
  """W14-D:即使父 shell 设有 proxy vars,_ensure_client 仍能正常构造 client。"""
  import sys
  import types

  for var in PROXY_ENV_VARS:
    monkeypatch.setenv(var, "http://127.0.0.1:49223")

  captured: dict[str, object] = {}

  class _CaptureClient:
    def __init__(self, **kwargs: object) -> None:
      captured.update(kwargs)
      self.chat = _FakeChatNamespace(_FakeOpenAIClient())
      self.models = _FakeModelsNamespace(_FakeOpenAIClient())

  fake_openai = types.ModuleType("openai")
  fake_openai.OpenAI = _CaptureClient  # type: ignore[attr-defined]
  monkeypatch.setitem(sys.modules, "openai", fake_openai)

  p = OpenAICompatProvider(
    api_key="sk-x",
    preset="minimax",
    model="preset-model",
  )
  p._client = None
  client = p._ensure_client()
  assert isinstance(client, _CaptureClient)
  assert "http_client" in captured
  assert captured["http_client"].trust_env is False


def test_ensure_client_idempotent_after_first_init(monkeypatch) -> None:
  """_ensure_client 第一次构造后,后续调用复用 self._client,不再传 kwargs。"""
  import sys
  import types

  call_count = {"n": 0}

  class _CountingClient:
    def __init__(self, **kwargs: object) -> None:
      call_count["n"] += 1
      self.kwargs = dict(kwargs)
      self.chat = _FakeChatNamespace(_FakeOpenAIClient())
      self.models = _FakeModelsNamespace(_FakeOpenAIClient())

  fake_openai = types.ModuleType("openai")
  fake_openai.OpenAI = _CountingClient  # type: ignore[attr-defined]
  monkeypatch.setitem(sys.modules, "openai", fake_openai)

  p = OpenAICompatProvider(
    api_key="sk-x",
    preset="minimax",
    model="preset-model",
  )
  p._client = None
  client1 = p._ensure_client()
  client2 = p._ensure_client()
  assert client1 is client2
  assert call_count["n"] == 1
