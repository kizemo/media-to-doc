"""OllamaProvider mock 测试。

要点:
- monkeypatch ``_ensure_client`` 注入假 client
- 测 chat / list_models / 缺 SDK 时的 ImportError
"""

from __future__ import annotations

import pytest

from media_to_doc.llm import ollama as ollama_mod
from media_to_doc.llm.ollama import (
  DEFAULT_BASE_URL,
  DEFAULT_MODEL,
  FALLBACK_MODELS,
  OllamaProvider,
)

# ─────────────────────────────────────────────────────────────
# 假 client fixture
# ─────────────────────────────────────────────────────────────


class _FakeOllamaMessage:
  def __init__(self, content: str) -> None:
    self.content = content


class _FakeOllamaResponse:
  def __init__(self, content: str) -> None:
    self.message = _FakeOllamaMessage(content)


class _FakeOllamaModelEntry:
  def __init__(self, name: str) -> None:
    self.model = name


class _FakeOllamaListResponse:
  def __init__(self, names: list[str]) -> None:
    self.models = [_FakeOllamaModelEntry(n) for n in names]


class _FakeOllamaClient:
  """最小 ollama SDK 模拟。"""

  def __init__(
    self,
    *,
    chat_reply: str = "hello from ollama",
    models: list[str] | None = None,
    raise_chat: Exception | None = None,
    raise_list: Exception | None = None,
  ) -> None:
    self._chat_reply = chat_reply
    self._models = models or ["qwen3:14b", "llama3.1:8b"]
    self._raise_chat = raise_chat
    self._raise_list = raise_list
    self.last_chat_kwargs: dict[str, object] = {}

  def chat(self, *, model: str, messages: list[dict[str, str]], options: dict[str, object]):
    self.last_chat_kwargs = {"model": model, "messages": messages, "options": options}
    if self._raise_chat:
      raise self._raise_chat
    return _FakeOllamaResponse(self._chat_reply)

  def list(self) -> _FakeOllamaListResponse:
    if self._raise_list:
      raise self._raise_list
    return _FakeOllamaListResponse(self._models)


def _patched_provider(monkeypatch, fake: _FakeOllamaClient) -> OllamaProvider:
  """monkeypatch ollama.Client 使其返回 fake。"""
  monkeypatch.setattr(ollama_mod, "_try_load_rapidocr", None, raising=False)  # 不污染

  def fake_ensure_client(self: OllamaProvider) -> _FakeOllamaClient:
    self._client = fake
    return fake

  monkeypatch.setattr(OllamaProvider, "_ensure_client", fake_ensure_client)
  return OllamaProvider(model="qwen3:14b")


# ─────────────────────────────────────────────────────────────
# 常量 + 默认值
# ─────────────────────────────────────────────────────────────


def test_constants_are_sane() -> None:
  assert DEFAULT_BASE_URL == "http://127.0.0.1:11434"
  assert DEFAULT_MODEL == "qwen3:14b"
  assert "qwen3:14b" in FALLBACK_MODELS


def test_provider_default_initialization() -> None:
  p = OllamaProvider()
  assert p.name == "ollama"
  assert p.model == DEFAULT_MODEL
  assert p._base_url == DEFAULT_BASE_URL


def test_provider_custom_base_url_from_env(monkeypatch) -> None:
  monkeypatch.setenv("OLLAMA_HOST", "http://gpu-server.local:11434")
  p = OllamaProvider()
  assert p._base_url == "http://gpu-server.local:11434"


def test_provider_explicit_base_url_overrides_env(monkeypatch) -> None:
  monkeypatch.setenv("OLLAMA_HOST", "http://from-env:11434")
  p = OllamaProvider(base_url="http://explicit:11434")
  assert p._base_url == "http://explicit:11434"


# ─────────────────────────────────────────────────────────────
# chat
# ─────────────────────────────────────────────────────────────


def test_chat_returns_message_content(monkeypatch) -> None:
  fake = _FakeOllamaClient(chat_reply="你好世界")
  p = _patched_provider(monkeypatch, fake)

  resp = p.chat("hi")
  assert resp.text == "你好世界"
  assert resp.provider == "ollama"
  assert p._calls == 1
  # 验证传给 SDK 的参数
  kwargs = fake.last_chat_kwargs
  assert kwargs["model"] == "qwen3:14b"
  assert kwargs["messages"] == [{"role": "user", "content": "hi"}]
  options = kwargs["options"]
  assert options["temperature"] == 0.3  # 默认
  assert options["num_predict"] == 4096  # 默认


def test_chat_propagates_exception_and_records_failure(monkeypatch) -> None:
  fake = _FakeOllamaClient(raise_chat=ConnectionError("ollama offline"))
  p = _patched_provider(monkeypatch, fake)

  with pytest.raises(ConnectionError, match="ollama offline"):
    p.chat("hi")

  assert p._calls == 1
  assert p._failures == 1
  assert p._last_failure is not None
  assert "ConnectionError" in p._last_failure


def test_chat_supports_dict_response(monkeypatch) -> None:
  """老 SDK 可能返回 dict 而不是 Response 对象。"""

  class _DictClient:
    def chat(self, **kwargs: object) -> dict[str, object]:
      return {"message": {"role": "assistant", "content": "from dict"}}

  p = OllamaProvider(model="x")
  monkeypatch.setattr(p, "_ensure_client", lambda self=p: _DictClient())
  resp = p.chat("hi")
  assert resp.text == "from dict"


# ─────────────────────────────────────────────────────────────
# list_models
# ─────────────────────────────────────────────────────────────


def test_list_models_uses_sdk(monkeypatch) -> None:
  fake = _FakeOllamaClient(models=["qwen3:14b", "llama3.1:8b", "gemma3:4b"])
  p = _patched_provider(monkeypatch, fake)

  models = p.list_models()
  assert models == ["qwen3:14b", "llama3.1:8b", "gemma3:4b"]


def test_list_models_falls_back_when_service_down(monkeypatch) -> None:
  fake = _FakeOllamaClient(raise_list=ConnectionError("offline"))
  p = _patched_provider(monkeypatch, fake)
  # list_models 应该捕获 SDK 异常,返回 fallback 列表
  models = p.list_models()
  assert "qwen3:14b" in models


def test_list_models_fallback_when_sdk_missing(monkeypatch) -> None:
  """SDK 缺失时 list_models 不抛 ImportError,而返回 fallback。"""
  p = OllamaProvider(model="x")

  def raise_import(self: OllamaProvider) -> object:
    raise ImportError("no ollama SDK")

  monkeypatch.setattr(OllamaProvider, "_ensure_client", raise_import)
  models = p.list_models()
  assert "qwen3:14b" in models


# ─────────────────────────────────────────────────────────────
# _ensure_client
# ─────────────────────────────────────────────────────────────


def test_ensure_client_raises_clear_error_when_sdk_missing(monkeypatch) -> None:
  """SDK 缺失时 _ensure_client 抛清晰 ImportError(安装提示)。"""
  p = OllamaProvider(model="x")
  p._client = None

  # monkeypatch sys.modules 让 import ollama 失败
  import sys

  monkeypatch.setitem(sys.modules, "ollama", None)
  # 上面只对 from ollama import ... 起作用;这里要 raise ImportError
  # 改成 monkeypatch _try_load_rapidocr 不适用,改用直接删 module

  # 实际:用 builtin.__import__ 拦截
  import builtins

  original_import = builtins.__import__

  def fake_import(name: str, *args: object, **kwargs: object) -> object:
    if name == "ollama":
      raise ImportError("simulated no ollama SDK")
    return original_import(name, *args, **kwargs)

  monkeypatch.setattr(builtins, "__import__", fake_import)

  with pytest.raises(ImportError, match="ollama Python SDK"):
    p._ensure_client()
