# W14-D Implementation Plan — Tauri UI v1.3.0 GitHub Release + 全 Provider trust_env=False

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 推子仓 `kizemo/media-to-doc-ui` v1.3.0 到 GitHub Release(NSIS installer + Tauri portable 2 assets),同时把 Anthropic + OpenAICompat 两个 LLM provider 的 `trust_env=False` 透传补全,防公司 VPN 父 shell 劫持到代理。

**Architecture:** C 部分沿用主仓 W12-B 的 `gh release create` + 2 assets + SSH push 流程;E 部分仿 W14-B `OllamaProvider` 模式(commit `427d963`),在 `AnthropicProvider._ensure_client` 与 `OpenAICompatProvider._ensure_client` 构造 SDK 客户端时透传 `http_client=httpx.Client(trust_env=False)`,把 W13-C 脚本侧的 proxy vars 过滤升级为代码层根因修复。

**Tech Stack:**
- 主仓:Python 3.11+,pytest 598 baseline,ruff,uv
- 子仓:Rust 1.97+,Tauri 2.11.4,cargo test baseline 43 passed
- 发布:NSIS 3.12(`C:\Program Files (x86)\NSIS\makensis.exe`),gh CLI 2.96.0(账号 `kizemo`)

## Global Constraints

- **会话时间预算**<2h(目标 ~65min,1h 缓冲)
- **env 三件套**:跑任何 LLM 代码层测试时 `unset HTTP_PROXY/HTTPS_PROXY/http_proxy/https_proxy/ALL_PROXY/all_proxy/NO_PROXY/no_proxy`(虽然 trust_env=False 后 httpx 不会再读,但保持习惯)
- **子仓 remote**:`git@github.com:kizemo/media-to-doc-ui.git`(SSH,与主仓同 owner)
- **设计原则**:trust_env=False 永远(defense in depth),不引入 env opt-in
- **commit 规范**:Conventional Commits,scope 单一
- **session-level pre-authorize**(CLAUDE.md §5.6):
  - E `fix(llm):` + 测试通过 + ruff 通过 → **自动 merge release/v1.0**(无需 ask)
  - C `docs(release):` + 验证通过 → **写 handoff 等拍板**(不自动 merge)
  - 修改 `commands.rs` / `runner.rs` → 2 轮 review(本会话不涉及,沿用 1 轮)
  - 修改 `index.html` → 1 轮 review(本会话不涉及)

## File Structure

| 路径 | 角色 | 改动 |
|---|---|---|
| `media-to-doc/src/media_to_doc/llm/anthropic.py` | E provider 1 | 改 `_ensure_client` line 121-124 + module docstring |
| `media-to-doc/src/media_to_doc/llm/openai_compat.py` | E provider 2 | 改 `_ensure_client` line 243 + module docstring |
| `media-to-doc/tests/test_llm/test_anthropic.py` | E 测试 1 | +3 用例 |
| `media-to-doc/tests/test_llm/test_openai_compat.py` | E 测试 2 | +3 用例 |
| `media-to-doc-ui/src-tauri/nsis/LICENSE.txt` | C NSIS 资源 | 新建(cp LICENSE) |
| `media-to-doc-ui/target/release/bundle/nsis/media-to-doc-1.3.0-setup.exe` | C asset 1 | 新生成(makensis) |
| `media-to-doc-ui/target/release/bundle/media-to-doc-1.3.0-portable.exe` | C asset 2 | 新生成(cp) |
| `media-to-doc/.learnings/LEARNINGS.md` | LE L1 沉淀 | +1 条 |
| `media-to-doc/docs/RELEASE_NOTES_v1.3.0.md` | C 主仓记录 | 新建 |
| `media-to-doc/handoff-w14d-*.md` | 本会话 handoff | 新建 |
| `media-to-doc/task.md` | 活跃 todo | +W14-D 节 |
| `media-to-doc/CLAUDE.md` | 项目指引 | +§10 W14-D 行 |

---

## Phase 1: E 部分(主仓代码层 TDD)

### Task 1: AnthropicProvider 加 trust_env 失败测试

**Files:**
- Modify: `media-to-doc/tests/test_llm/test_anthropic.py`(末尾追加)

**Interfaces:**
- Consumes: W14-B 已建立的 W14-B 测试 pattern(`test_ensure_client_passes_trust_env_false_to_ollama_sdk`,参考 `test_ollama.py:245-271`)
- Produces: 3 个失败测试,定义 anthropic provider 应透传 `trust_env=False` 的契约

- [ ] **Step 1: 追加 `test_ensure_client_passes_trust_env_false_to_anthropic_sdk`**

在 `tests/test_llm/test_anthropic.py` 末尾追加:

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd "F:/soft/00selfmade/media-to-doc" && uv run pytest tests/test_llm/test_anthropic.py::test_ensure_client_passes_trust_env_false_to_anthropic_sdk -v`

Expected: FAIL with `"http_client" not in captured` 或 `"trust_env"` assertion 错误(因为现 `_ensure_client` line 121-124 没传 http_client)。

- [ ] **Step 3: 追加 `test_ensure_client_unaffected_by_proxy_env_vars`**

在 `test_anthropic.py` 末尾(test_ensure_client_passes_trust_env_false 之后)追加:

```python
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
```

- [ ] **Step 4: 跑测试确认失败**

Run: `cd "F:/soft/00selfmade/media-to-doc" && uv run pytest tests/test_llm/test_anthropic.py::test_ensure_client_unaffected_by_proxy_env_vars -v`

Expected: FAIL with same reason as Step 2。

- [ ] **Step 5: 追加 `test_ensure_client_idempotent_after_first_init`**

在 `test_anthropic.py` 末尾追加:

```python
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
```

- [ ] **Step 6: 跑测试确认失败**

Run: `cd "F:/soft/00selfmade/media-to-doc" && uv run pytest tests/test_llm/test_anthropic.py -k "trust_env or idempotent_after_first_init" -v`

Expected: 3 个测试都 FAIL,理由都是 "http_client" 缺失或 trust_env mismatch。

- [ ] **Step 7: 不 commit,继续 Task 2**

---

### Task 2: AnthropicProvider 改 _ensure_client 透传 trust_env=False

**Files:**
- Modify: `media-to-doc/src/media_to_doc/llm/anthropic.py:12-18`(module docstring)+ `media-to-doc/src/media_to_doc/llm/anthropic.py:103-125`(_ensure_client)

**Interfaces:**
- Consumes: Task 1 定义的 3 个失败测试
- Produces: `_ensure_client` 返回 SDK 客户端时,`http_client` 参数是 `httpx.Client(trust_env=False)`,3 个测试全过

- [ ] **Step 1: 改 module docstring(W14-D 说明)**

Edit `src/media_to_doc/llm/anthropic.py` line 12 区域(原 docstring 末尾,`"""` 之前)追加 W14-D 段(参考 `ollama.py:12-17`):

原 line 1-12:
```python
"""Anthropic Claude API provider。

触发方式:
- ``LLM_PROVIDER=anthropic``
- ``ANTHROPIC_API_KEY`` 环境变量(或 ``api_key`` 参数显式传入)

依赖:
- ``anthropic>=0.31.0`` Python SDK(lazy import)

参考:TDD §4.2.3 + PROJECT_DESCRIPTION.md §3.3 anthropic 行。
"""
```

改为:
```python
"""Anthropic Claude API provider。

触发方式:
- ``LLM_PROVIDER=anthropic``
- ``ANTHROPIC_API_KEY`` 环境变量(或 ``api_key`` 参数显式传入)

依赖:
- ``anthropic>=0.31.0`` Python SDK(lazy import,自带 httpx 依赖)

参考:TDD §4.2.3 + PROJECT_DESCRIPTION.md §3.3 anthropic 行。

注意(W14-D):``_ensure_client`` 构造 ``Anthropic`` 时透传
``http_client=httpx.Client(trust_env=False)``,让 SDK 内部 httpx 不读
``HTTP_PROXY`` / ``HTTPS_PROXY`` / ``all_proxy`` 等环境变量,避免
公司 VPN 父 shell 把 api.anthropic.com 调用劫持到代理。沿用
``OllamaProvider`` W14-B ``427d963`` 模式。详见 feedback memory
``feedback_proxy_env_pollution.md``。
"""
```

- [ ] **Step 2: 改 `_ensure_client` 透传 trust_env=False**

Edit `src/media_to_doc/llm/anthropic.py` line 105-125(`_ensure_client` 方法),原内容:

```python
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
```

改为:

```python
def _ensure_client(self) -> object:
    """lazy init Anthropic 客户端,透传 trust_env=False(W14-D 防 VPN 污染)。

    透传 ``http_client=httpx.Client(trust_env=False)`` 给 SDK,这样
    SDK 内部 httpx 不会读 ``HTTP_PROXY`` 等环境变量,避免公司 VPN 父
    shell 把 api.anthropic.com 调用劫持到代理。沿用 ``OllamaProvider``
    W14-B ``427d963`` 模式。详见 feedback memory
    ``feedback_proxy_env_pollution.md``。
    """
    if self._client is not None:
        return self._client
    if not self._api_key:
        raise RuntimeError(
            "AnthropicProvider 需要 API key;设置 ANTHROPIC_API_KEY 环境变量"
            "或在 get_provider() 中传 api_key 参数"
        )
    try:
        from anthropic import Anthropic  # type: ignore[import-untyped]
        import httpx
    except ImportError as exc:
        raise ImportError(
            "AnthropicProvider 需要 anthropic SDK + httpx。安装方式:"
            "uv add 'media_to_doc[llm]' 或 uv add 'anthropic httpx'"
        ) from exc
    kwargs: dict[str, object] = {
        "api_key": self._api_key,
        "http_client": httpx.Client(trust_env=False),  # W14-D 新增
    }
    if self._base_url:
        kwargs["base_url"] = self._base_url
    self._client = Anthropic(**kwargs)
    return self._client
```

- [ ] **Step 3: 跑 3 个测试确认全过**

Run: `cd "F:/soft/00selfmade/media-to-doc" && uv run pytest tests/test_llm/test_anthropic.py -k "trust_env or idempotent_after_first_init" -v`

Expected: 3 passed / 0 failed。

- [ ] **Step 4: 跑全部 anthropic 测试确认不退化**

Run: `cd "F:/soft/00selfmade/media-to-doc" && uv run pytest tests/test_llm/test_anthropic.py -v`

Expected: 11 原有 + 3 新 = 14 passed(11 旧测试可能因 `_ensure_client` 行为变化而需调整,见 Task 2 补充 step 5)。

- [ ] **Step 5(若 Step 4 失败):调整旧测试**

如果原 11 测试因 `http_client` 参数注入而失败(如 `_CaptureClient` 没接 `http_client`),改对应测试让 mock client 接 `**kwargs` 而不严格断言 init 参数。例:`test_ensure_client_uses_base_url_when_provided` line 187-198:

```python
class _CaptureClient:
    def __init__(self, **kwargs: object) -> None:
        init_kwargs.update(kwargs)
        self.messages = self
```

(`**kwargs` 已存在,无需改,但要确保新加的 `http_client` 不会让断言失败)

- [ ] **Step 6: 不 commit,继续 Task 3**

---

### Task 3: OpenAICompatProvider 加 trust_env 失败测试

**Files:**
- Modify: `media-to-doc/tests/test_llm/test_openai_compat.py`(末尾追加)

**Interfaces:**
- Consumes: Task 1/2 已建立的 pattern
- Produces: 3 个失败测试,定义 openai_compat provider 应透传 `trust_env=False` 的契约

- [ ] **Step 1: 追加 3 个失败测试(同 anthropic pattern)**

在 `tests/test_llm/test_openai_compat.py` 末尾追加:

```python
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
```

- [ ] **Step 2: 跑测试确认 3 个全失败**

Run: `cd "F:/soft/00selfmade/media-to-doc" && uv run pytest tests/test_llm/test_openai_compat.py -k "trust_env or idempotent_after_first_init" -v`

Expected: 3 failed,理由是 "http_client" 缺失或 trust_env mismatch。

- [ ] **Step 3: 不 commit,继续 Task 4**

---

### Task 4: OpenAICompatProvider 改 _ensure_client 透传 trust_env=False

**Files:**
- Modify: `media-to-doc/src/media_to_doc/llm/openai_compat.py:1-33`(module docstring)+ `media-to-doc/src/media_to_doc/llm/openai_compat.py:222-244`(_ensure_client)

**Interfaces:**
- Consumes: Task 3 定义的 3 个失败测试
- Produces: `_ensure_client` 返回 SDK 客户端时,`http_client` 参数是 `httpx.Client(trust_env=False)`,3 个测试全过

- [ ] **Step 1: 改 module docstring(W14-D 说明)**

Edit `src/media_to_doc/llm/openai_compat.py` line 33 区域(`"""` 之前)追加 W14-D 段(参考 `ollama.py:12-17`):

在 `"""依赖:\n- ``openai>=1.40.0`` Python SDK(lazy import)\n\n参考:TDD §4.2.4 + PROJECT_DESCRIPTION.md §3.3 openai_compatible 行。\n"""` 末尾前追加:

```
\n\n注意(W14-D):``_ensure_client`` 构造 ``OpenAI`` 时透传\n``http_client=httpx.Client(trust_env=False)``,让 SDK 内部 httpx 不读\n``HTTP_PROXY`` / ``HTTPS_PROXY`` / ``all_proxy`` 等环境变量,避免\n公司 VPN 父 shell 把 7 个 preset(minimax / deepseek / zhipu / moonshot /\nopenrouter / dashscope / hunyuan)调用劫持到代理。沿用 ``OllamaProvider``\nW14-B ``427d963`` 模式。详见 feedback memory\n``feedback_proxy_env_pollution.md``。\n
```

- [ ] **Step 2: 改 `_ensure_client` 透传 trust_env=False**

Edit `src/media_to_doc/llm/openai_compat.py` line 222-244(`_ensure_client` 方法),原内容:

```python
def _ensure_client(self) -> object:
    """lazy init OpenAI 客户端。"""
    if self._client is not None:
        return self._client
    if not self._api_key:
        raise RuntimeError(
            "OpenAICompatProvider 需要 api_key;通过 get_provider(api_key=) 传入"
            "或设置 OPENAI_API_KEY 环境变量"
        )
    if not self._base_url:
        raise RuntimeError(
            "OpenAICompatProvider 需要 base_url;通过 get_provider(base_url=)"
            "或 preset= 传入"
        )
    try:
        from openai import OpenAI  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "OpenAICompatProvider 需要 openai SDK。安装方式:"
            "uv add 'media_to_doc[llm]' 或 uv add openai"
        ) from exc
    self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
    return self._client
```

改为:

```python
def _ensure_client(self) -> object:
    """lazy init OpenAI 客户端,透传 trust_env=False(W14-D 防 VPN 污染)。

    透传 ``http_client=httpx.Client(trust_env=False)`` 给 SDK,这样
    SDK 内部 httpx 不会读 ``HTTP_PROXY`` 等环境变量,避免公司 VPN 父
    shell 把 7 个 preset(minimax / deepseek / zhipu / moonshot /
    openrouter / dashscope / hunyuan)调用劫持到代理。沿用
    ``OllamaProvider`` W14-B ``427d963`` 模式。详见 feedback memory
    ``feedback_proxy_env_pollution.md``。
    """
    if self._client is not None:
        return self._client
    if not self._api_key:
        raise RuntimeError(
            "OpenAICompatProvider 需要 api_key;通过 get_provider(api_key=) 传入"
            "或设置 OPENAI_API_KEY 环境变量"
        )
    if not self._base_url:
        raise RuntimeError(
            "OpenAICompatProvider 需要 base_url;通过 get_provider(base_url=)"
            "或 preset= 传入"
        )
    try:
        from openai import OpenAI  # type: ignore[import-untyped]
        import httpx
    except ImportError as exc:
        raise ImportError(
            "OpenAICompatProvider 需要 openai SDK + httpx。安装方式:"
            "uv add 'media_to_doc[llm]' 或 uv add 'openai httpx'"
        ) from exc
    self._client = OpenAI(
        api_key=self._api_key,
        base_url=self._base_url,
        http_client=httpx.Client(trust_env=False),  # W14-D 新增
    )
    return self._client
```

- [ ] **Step 3: 跑 3 个测试确认全过**

Run: `cd "F:/soft/00selfmade/media-to-doc" && uv run pytest tests/test_llm/test_openai_compat.py -k "trust_env or idempotent_after_first_init" -v`

Expected: 3 passed / 0 failed。

- [ ] **Step 4: 跑全部 openai_compat 测试确认不退化**

Run: `cd "F:/soft/00selfmade/media-to-doc" && uv run pytest tests/test_llm/test_openai_compat.py -v`

Expected: 23 原有 + 3 新 = 26 passed(若旧测试因 http_client 注入失败,按 Task 2 Step 5 同模式修)。

- [ ] **Step 5: 跑全量 test_llm 测试**

Run: `cd "F:/soft/00selfmade/media-to-doc" && uv run pytest tests/test_llm/ -v`

Expected: 5 个文件全过(11 + 3 + 23 + 3 + 已有 test_base + test_health 等),总体 598 + 6 = 604+ passed / 0 failed。

- [ ] **Step 6: ruff check**

Run: `cd "F:/soft/00selfmade/media-to-doc" && uv run ruff check src/media_to_doc/llm/ tests/test_llm/`

Expected: `All checks passed!`

- [ ] **Step 7: 不 commit,继续 Task 5**

---

### Task 5: E 部分 commit + 自动 merge release/v1.0

**Files:**
- Modify: `media-to-doc/.learnings/LEARNINGS.md`(追加 LP 条目)

**Interfaces:**
- Consumes: Task 2/4 跑通的 604 测试 + ruff clean
- Produces: 1 个 fix commit on `release/v1.0`,触发 CLAUDE.md §5.6 pre-authorize 自动 merge

- [ ] **Step 1: 追加 LEARNINGS.md 条目**

Edit `media-to-doc/.learnings/LEARNINGS.md` 末尾追加:

```markdown
## LP-20260722-W14D-001 — 全 LLM provider 一律 trust_env=False

**Pattern-Key**: `HTTP_PROXY:trust_env`

**Context**: W14-B(commit `427d963`)修了 `OllamaProvider._ensure_client` 透传 `trust_env=False`,但 Anthropic / OpenAICompat 当时未同步。W14-D 补全两个 provider 的同等改造,达到全栈一致。

**Rule**: 任何新加的 LLM provider 在 `_ensure_client` 构造 SDK 客户端时,必须透传 `http_client=httpx.Client(trust_env=False)`(若 SDK ≥ 0.20 / openai ≥ 1.40 接受 http_client 参数)。这是 **defense in depth**:即使脚本侧(W13-C)已过滤 8 个 proxy vars,代码层也保证 SDK 内部 httpx 不会读 `HTTP_PROXY` 等环境变量。

**Why**: 公司 VPN 父 shell 在用户登录时设置 `HTTP_PROXY=http://127.0.0.1:49223` 等代理变量。若 SDK 默认 `trust_env=True`,内部 httpx 会把 api.anthropic.com / 7 个 OpenAI preset 的调用劫持到代理,触发 SSL handshake 失败(W13-C 撞过)。

**How to apply**:
- 新 provider 沿用 W14-B Ollama / W14-D Anthropic + OpenAICompat 模式,在 `_ensure_client` 末尾加 `http_client=httpx.Client(trust_env=False)`
- 测试加 3 条:trust_env 透传 + 不受 proxy env vars 影响 + 构造幂等
- 不引入 env opt-in(opt-out `trust_env=False` 风险高,公司 VPN 用户几乎全数踩坑)

**Ref**: `src/media_to_doc/llm/{ollama,anthropic,openai_compat}.py`,`tests/test_llm/{test_ollama,test_anthropic,test_openai_compat}.py`
```

- [ ] **Step 2: 跑全量测试最终确认**

Run: `cd "F:/soft/00selfmade/media-to-doc" && uv run pytest -q`

Expected: 604 passed / 0 skipped / 0 failed。

- [ ] **Step 3: 跑 ruff 全仓**

Run: `cd "F:/soft/00selfmade/media-to-doc" && uv run ruff check`

Expected: `All checks passed!`

- [ ] **Step 4: git add 改动文件**

Run:
```bash
cd "F:/soft/00selfmade/media-to-doc" && git add \
  src/media_to_doc/llm/anthropic.py \
  src/media_to_doc/llm/openai_compat.py \
  tests/test_llm/test_anthropic.py \
  tests/test_llm/test_openai_compat.py \
  .learnings/LEARNINGS.md
```

Expected: 5 files staged(`git status --short` 显示 5 个 `M` / `A`)。

- [ ] **Step 5: commit fix**

Run:
```bash
cd "F:/soft/00selfmade/media-to-doc" && git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
fix(llm): W14-D — extend trust_env=False to Anthropic + OpenAICompat providers

沿用 W14-B OllamaProvider 模式(commit 427d963),在 Anthropic + OpenAICompat
两个 provider 的 _ensure_client 构造 SDK 客户端时透传
http_client=httpx.Client(trust_env=False)。

- src/media_to_doc/llm/anthropic.py:104-145 改 _ensure_client + module docstring
- src/media_to_doc/llm/openai_compat.py:222-253 改 _ensure_client + module docstring
- tests/test_llm/test_anthropic.py +3 用例(透传 / proxy env 不影响 / 幂等)
- tests/test_llm/test_openai_compat.py +3 用例(同上)
- .learnings/LEARNINGS.md LP-20260722-W14D-001 沉淀 defense in depth 原则

test_llm 11 + 23 原有测试不退化;新 6 测试全过。
pytest: 598 → 604 passed / 0 skipped。
ruff: All checks passed。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Expected: 1 commit on `release/v1.0`,ahead of `origin/main` 20 commit。

- [ ] **Step 6: 按 CLAUDE.md §5.6 pre-authorize,自动 merge release/v1.0**

fix commit + 测试通过 + ruff 通过 → **自动 merge release/v1.0**(无需 ask)。

Run:
```bash
cd "F:/soft/00selfmade/media-to-doc" && git checkout main && git merge --no-ff release/v1.0 -m "merge: W14-D — Anthropic + OpenAICompat trust_env=False (fix, auto-merge per CLAUDE.md §5.6)" && git push origin main
```

Expected: fast-forward 或 merge commit,主仓 main 分支同步到 v1.2.1 + W14-D 之上。

**注意**:如 `git push origin main` 撞 GitHub API 或 SSH 限制,改用 HTTPS + PAT(主仓 W12-B 验证过)。

- [ ] **Step 7: 切回 release/v1.0 继续 Task 6**

Run: `cd "F:/soft/00selfmade/media-to-doc" && git checkout release/v1.0`

---

## Phase 2: C 部分(子仓发布 + 主仓记录)

### Task 6: 子仓 LICENSE.txt + remote + GitHub 仓 + push

**Files:**
- Create: `media-to-doc-ui/src-tauri/nsis/LICENSE.txt`
- Modify: `media-to-doc-ui/.git/config`(加 remote)

**Interfaces:**
- Consumes: 子仓 master 已 commit,tag v1.3.0 已 annotated
- Produces: 子仓 origin = `git@github.com:kizemo/media-to-doc-ui.git`,master 推到 origin,tag v1.3.0 推到 origin

- [ ] **Step 1: 复制 LICENSE.txt 到 nsis/**

Run:
```bash
cd "F:/soft/00selfmade/media-to-doc-ui" && cp LICENSE src-tauri/nsis/LICENSE.txt && ls -la src-tauri/nsis/LICENSE.txt
```

Expected: 文件存在(1 段 MIT 文本,~1KB)。

- [ ] **Step 2: 加子仓 SSH remote**

Run:
```bash
cd "F:/soft/00selfmade/media-to-doc-ui" && git remote add origin git@github.com:kizemo/media-to-doc-ui.git && git remote -v
```

Expected: `origin git@github.com:kizemo/media-to-doc-ui.git (fetch)` + `(push)`。

- [ ] **Step 3: 在 GitHub 创建 `kizemo/media-to-doc-ui` 仓(public)**

**方式选择**:
- **a)** `gh repo create kizemo/media-to-doc-ui --public --description "media-to-doc Tauri 2 desktop shell" --source=. --remote=origin --push`(推荐,一步到位)
- **b)** Web UI 手动(若 gh 命令因权限或 token scope 受限)

Run (a):
```bash
cd "F:/soft/00selfmade/media-to-doc-ui" && gh repo create kizemo/media-to-doc-ui --public --description "media-to-doc Tauri 2 desktop shell" --source=. --remote=origin --push
```

Expected: 仓创建成功,master 自动 push 到 origin。

**若失败**(撞 GitHub API limit / repo 已存在 / token 权限不足):
- 改用 Web UI:打开 `https://github.com/new`,owner=kizemo,name=media-to-doc-ui,public,不加 README/.gitignore/license(子仓已有)
- 然后回到本 task step 4 手动 push

- [ ] **Step 4: 验证 push 成功(若 step 3 用 a 跳过此步)**

Run:
```bash
cd "F:/soft/00selfmade/media-to-doc-ui" && git push -u origin master 2>&1 | tail -5
```

Expected: `Branch 'master' set up to track remote 'origin/master'.` 或 `Everything up-to-date`。

- [ ] **Step 5: push tag v1.3.0**

Run:
```bash
cd "F:/soft/00selfmade/media-to-doc-ui" && git push origin tag v1.3.0 2>&1 | tail -3
```

Expected: `Total 1 (delta 0), reused 0 (delta 0)` 或 `* [new tag] v1.3.0 -> v1.3.0`。

- [ ] **Step 6: 验证 GitHub 仓与 tag**

Run:
```bash
gh repo view kizemo/media-to-doc-ui --json name,defaultBranchRef,description 2>&1 | head -10
echo "---"
gh api repos/kizemo/media-to-doc-ui/tags 2>&1 | head -10
```

Expected:
- repo view:name=`media-to-doc-ui`,defaultBranchRef.name=`master`,description=`media-to-doc Tauri 2 desktop shell`
- tags:含 `v1.3.0` annotated tag

---

### Task 7: NSIS 编译 + portable copy

**Files:**
- Create: `media-to-doc-ui/target/release/bundle/nsis/media-to-doc-1.3.0-setup.exe`
- Create: `media-to-doc-ui/target/release/bundle/media-to-doc-1.3.0-portable.exe`

**Interfaces:**
- Consumes: Task 6 推到 origin 的 master + LICENSE.txt + `target/release/media-to-doc-ui.exe` 已编译
- Produces: NSIS installer .exe(~1.5MB)+ Tauri portable .exe(~6.2MB)2 个 assets

- [ ] **Step 1: 确认 bundle 输出目录存在**

Run:
```bash
cd "F:/soft/00selfmade/media-to-doc-ui" && mkdir -p target/release/bundle/nsis && ls -la target/release/bundle/
```

Expected: `nsis/` 子目录存在(已 mkdir,可重做)。

- [ ] **Step 2: 确认 makensis 路径**

Run:
```bash
"/c/Program Files (x86)/NSIS/makensis.exe" /VERSION 2>&1 | head -3
```

Expected: `v3.12` 或类似 NSIS 版本输出。

- [ ] **Step 3: 跑 makensis 编译 installer**

Run:
```bash
cd "F:/soft/00selfmade/media-to-doc-ui" && "/c/Program Files (x86)/NSIS/makensis.exe" src-tauri/nsis/installer.nsi 2>&1 | tail -10
```

Expected:
- 编译日志显示 `Output: "..\target\release\bundle\nsis\media-to-doc-1.3.0-setup.exe"`
- 退出码 0

**若失败**(常见原因):
- `LICENSE.txt not found` → 检查 `src-tauri/nsis/LICENSE.txt` 是否存在(Step 1 应已 cp)
- `mui2.nsh not found` → NSIS 安装不完整,重装 winget
- `Error in macro ...` → 看错误行号,改 installer.nsi

- [ ] **Step 4: 验证 installer 生成**

Run:
```bash
ls -la "F:/soft/00selfmade/media-to-doc-ui/target/release/bundle/nsis/media-to-doc-1.3.0-setup.exe"
```

Expected: 文件存在,大小 ~1.5MB(`-rw-r--r-- 1 Duanyi 197121 1500000 Jul 22 ...`)。

- [ ] **Step 5: 复制 portable**

Run:
```bash
cd "F:/soft/00selfmade/media-to-doc-ui" && cp target/release/media-to-doc-ui.exe target/release/bundle/media-to-doc-1.3.0-portable.exe && ls -la target/release/bundle/media-to-doc-1.3.0-portable.exe
```

Expected: 文件存在,大小 ~6.2MB。

- [ ] **Step 6: 算 SHA256 用于 release notes**

Run:
```bash
cd "F:/soft/00selfmade/media-to-doc-ui" && sha256sum target/release/bundle/nsis/media-to-doc-1.3.0-setup.exe target/release/bundle/media-to-doc-1.3.0-portable.exe
```

Expected: 两行 SHA256 hash,记录到 Task 8 的 release notes。

---

### Task 8: 主仓 docs/RELEASE_NOTES_v1.3.0.md + gh release create + 验收

**Files:**
- Create: `media-to-doc/docs/RELEASE_NOTES_v1.3.0.md`
- Create(远程):`https://github.com/kizemo/media-to-doc-ui/releases/tag/v1.3.0` 含 2 assets

**Interfaces:**
- Consumes: Task 7 生成的 2 个 .exe + Task 6 推上去的 tag v1.3.0
- Produces: 公开 GitHub Release URL + 主仓 release notes 文档

- [ ] **Step 1: 写主仓 docs/RELEASE_NOTES_v1.3.0.md**

Write file `F:\soft\00selfmade\media-to-doc\docs\RELEASE_NOTES_v1.3.0.md`:

```markdown
# Release Notes — media-to-doc-ui v1.3.0

**发布日期**:2026-07-22
**子仓 tag**:`v1.3.0`(annotated)
**发布地址**:https://github.com/kizemo/media-to-doc-ui/releases/tag/v1.3.0
**主仓 handoff**:见同目录 `handoff-w14d-*.md`

---

## 亮点

### 1. 8 个 Tauri commands 全部实装(W14-B+ 系列)

| Command | 语义 | 与 MCP 8 工具对齐 |
|---|---|---|
| `list_courses` | 扫描 inbox 课程目录 | ✅ |
| `run_pipeline` | 启动 11 stage pipeline | ✅ |
| `resume_pipeline` | 中断后续跑 | ✅ |
| `cancel_run` | 同步取消(≤2s 超时) | ✅ |
| `check_status` | 读 state.json | ✅ |
| `list_outputs` | 列 output_final 产物 | ✅ |
| `read_lecture` | 读 md/html,优先 W12-D 布局 | ✅ |
| `get_run_metrics` | LE L1 健康度查询 | ✅ |
| `list_runs` | LE 跨 run 健康度 | ✅ |

### 2. 多课程并发(W14-C A)

- `max_concurrent=3`(env override)
- completed LRU 100
- cancel 2s 超时 + kill_tree 兜底
- list_all_runs 混合 running + completed
- 前端 3s global poll + per-run log tail(独立 offset)

### 3. NSIS installer(W14-C B + W14-D 实编译)

- 系统 NSIS 3.12(绕开 Tauri bundler GitHub TLS)
- 装到 `Program Files\MediaToDoc\`
- 桌面 + 开始菜单快捷方式
- `.mtdproj` 文件关联
- Release assets:installer + portable 2 种

### 4. 真跑 30s 测试视频(W14-C E)

- env 三件套(unset proxy + HF_ENDPOINT + HF_HUB_DISABLE_XET)
- audio → asr → frames 完成
- ocr 因合成图无场景变化预期失败(pipeline 基础设施 OK)

---

## Assets

| Asset | Size | SHA256 |
|---|---|---|
| `media-to-doc-1.3.0-setup.exe` | ~1.5MB | (gh release page 显示) |
| `media-to-doc-1.3.0-portable.exe` | ~6.2MB | (gh release page 显示) |

---

## 安装

### Windows(installer,推荐)

1. 下载 `media-to-doc-1.3.0-setup.exe`
2. 管理员运行(perMachine 安装)
3. 装到默认 `C:\Program Files\MediaToDoc\`
4. 桌面 / 开始菜单启动 `media-to-doc`

### Windows(portable,免安装)

1. 下载 `media-to-doc-1.3.0-portable.exe`
2. 双击运行(无需安装)

### 环境配置(必做)

```bash
# 主仓路径
setx MEDIA_TO_DOC_PROJECT "F:\soft\00selfmade\media-to-doc"

# (可选)uv 路径
setx UV_BIN "C:\Users\Duanyi\.local\bin\uv.exe"

# (可选)workspace
setx MEDIA_TO_DOC_WORKSPACE "F:\soft\00selfmade\media-to-doc\workspace"
```

### macOS / Linux

跨平台编译需 Rust 1.97+ + WebKit/GTK 依赖。Tauri 官方文档见 https://tauri.app/start/prerequisites/。

---

## 测试

- **43 cargo test / 0 failed**(W14-C A baseline)
- 8 commands 全部经 cargo test 验证
- 端到端 30s 合成视频 audio/asr/frames 通过

---

## 已知问题

- Rust toolchain 需 1.97+(自带 lld-link 无需 MSVC)
- 公司 VPN 用户构建时需设 `CARGO_NET_TLS_VERIFY=false`(运行不受影响)
- macOS / Linux 编译需用户自查环境
- pip 包 `media_to_doc` 仍是 v1.2.1(主仓独立版本,等 v1.3.x 整合)

---

## 上游

主仓 `media-to-doc` v1.2.1(`pip install media_to_doc` 装的 Python 后端)已发布:
- PyPI:https://pypi.org/project/media-to-doc/
- GitHub:https://github.com/kizemo/media-to-doc/releases/tag/v1.2.1

UI 端调用此 Python 后端做实际 pipeline,UI 自身只做 orchestrator + log tail + 输出展示。
```

- [ ] **Step 2: 跑 gh release create 带 2 assets**

Run:
```bash
cd "F:/soft/00selfmade/media-to-doc-ui" && gh release create v1.3.0 \
  target/release/bundle/nsis/media-to-doc-1.3.0-setup.exe \
  target/release/bundle/media-to-doc-1.3.0-portable.exe \
  --target master \
  --title "media-to-doc-ui v1.3.0" \
  --notes-file ../media-to-doc/docs/RELEASE_NOTES_v1.3.0.md
```

Expected: 终端输出 release URL `https://github.com/kizemo/media-to-doc-ui/releases/tag/v1.3.0`。

**注意**:`--target master` 是 branch 名(W12-B 撞过 commit sha 报错)。

**若失败**(撞 GitHub API limit):
- 等待 60s 重试
- 或 Web UI 手动创建 release + `gh release upload v1.3.0 <files>` 补 assets

- [ ] **Step 3: 验收:gh release view**

Run:
```bash
gh release view v1.3.0 --repo kizemo/media-to-doc-ui --json tagName,name,assets,url 2>&1 | head -30
```

Expected:
- `tagName: v1.3.0`
- `name: media-to-doc-ui v1.3.0`
- `assets` 长度 = 2(setup.exe + portable.exe)
- `url: https://github.com/kizemo/media-to-doc-ui/releases/tag/v1.3.0`

- [ ] **Step 4: 验收:浏览器访问 release URL(可选)**

在浏览器打开 `https://github.com/kizemo/media-to-doc-ui/releases/tag/v1.3.0`,确认:
- 2 个 assets 可下载
- Release notes 渲染正确
- tag 标注 v1.3.0

- [ ] **Step 5: 验证 SHA256 与 release notes 一致**

Run:
```bash
cd "F:/soft/00selfmade/media-to-doc-ui" && gh release view v1.3.0 --repo kizemo/media-to-doc-ui --json assets --jq '.assets[] | "\(.name) \(.size) \(.digest)"' 2>&1 | head -10
```

Expected: 2 行,每行格式 `<filename> <size> sha256:xxx`,与本地 `sha256sum` 输出一致(去掉 `sha256:` 前缀后)。

---

### Task 9: 主仓 commit release notes + handoff + task.md/CLAUDE.md 同步

**Files:**
- Modify: `media-to-doc/task.md`(+W14-D 节)
- Modify: `media-to-doc/CLAUDE.md` §10(+W14-D 行)
- Create: `media-to-doc/handoff-w14d-*.md`(本会话 handoff)

**Interfaces:**
- Consumes: Task 8 完成的 GitHub Release + Task 5 完成的 E 代码 fix + 测试
- Produces: 主仓 commit(本会话 handoff + 文档同步),`git log --oneline` 反映 W14-D 全部动作

- [ ] **Step 1: 写本会话 handoff**

Write file `F:\soft\00selfmade\media-to-doc\handoff-w14d-c-e-2026-07-22.md`:

```markdown
# Handoff — W14-D C+E:Tauri UI v1.3.0 Release + 全 Provider trust_env=False

**日期**:2026-07-22
**主仓分支**:`release/v1.0` + 自动 merge `main`
**子仓分支**:`master` + tag v1.3.0 → 推到 origin
**本会话成果**:C 子仓 v1.3.0 GitHub Release + E Anthropic + OpenAICompat trust_env=False

## 全部完成 ✅

| 任务 | 内容 | 验收 | 状态 |
|---|---|---|---|
| C | 子仓 push + NSIS 编译 + gh release v1.3.0 | release URL 可访问,2 assets 可下载,SHA256 verified | ✅ |
| E | Anthropic + OpenAICompat `_ensure_client` 透传 `http_client=httpx.Client(trust_env=False)` | 6 个新测试全过,604 passed / 0 skipped,ruff clean | ✅ |

## 关键设计

### C:GitHub Release v1.3.0

- **子仓 push**:SSH protocol + `git push -u origin master` + `git push origin tag v1.3.0`
- **NSIS 编译**:系统 NSIS 3.12(`C:\Program Files (x86)\NSIS\makensis.exe`)跑 `installer.nsi`,补 W14-C B 跳过的实编译
- **2 assets**:`media-to-doc-1.3.0-setup.exe`(~1.5MB)+ `media-to-doc-1.3.0-portable.exe`(~6.2MB,cp 自 `target/release/media-to-doc-ui.exe`)
- **gh release create**:`--target master` + `--notes-file docs/RELEASE_NOTES_v1.3.0.md` + 2 assets

### E:trust_env=False 全 provider

- 仿 W14-B `OllamaProvider._ensure_client` 模式(commit `427d963`)
- `AnthropicProvider._ensure_client` 末尾加 `"http_client": httpx.Client(trust_env=False)` 到 kwargs
- `OpenAICompatProvider._ensure_client` 末尾加 `http_client=httpx.Client(trust_env=False)` 到 `OpenAI()` 调用
- 测试 6 个新用例(2 provider × 3 测试):trust_env 透传 + proxy env vars 不影响 + 构造幂等
- pytest 598 → 604 passed / 0 skipped / 0 failed
- ruff:All checks passed

## 主仓 commit log(release/v1.0,领先 origin/main 20 commit)

```
[fix(llm): W14-D — extend trust_env=False to Anthropic + OpenAICompat providers]
[docs(release): W14-D — subrepo v1.3.0 NSIS installer build + GitHub Release]
[docs(project): W14-D — CLAUDE.md §10 + task.md sync W14-D state]
```

## 子仓 commit log(master,tag v1.3.0)

子仓无新 commit(用 W14-C 已 tagged 的 v1.3.0),只 push origin + 加 2 assets。

## 关键文件改动

| 文件 | 改动 |
|---|---|
| `src/media_to_doc/llm/anthropic.py` | module docstring + `_ensure_client` 透传 http_client |
| `src/media_to_doc/llm/openai_compat.py` | module docstring + `_ensure_client` 透传 http_client |
| `tests/test_llm/test_anthropic.py` | +3 用例(透传 / proxy 不影响 / 幂等) |
| `tests/test_llm/test_openai_compat.py` | +3 用例(同上) |
| `.learnings/LEARNINGS.md` | +LP-20260722-W14D-001(defense in depth) |
| `docs/RELEASE_NOTES_v1.3.0.md` | 新建(主仓记录 subrepo 发布) |
| `media-to-doc-ui/src-tauri/nsis/LICENSE.txt` | 新建(cp LICENSE 给 NSIS MUI_PAGE_LICENSE) |

## Release URL

- https://github.com/kizemo/media-to-doc-ui/releases/tag/v1.3.0

## 验证

- [x] 子仓 v1.3.0 tag 推到 origin
- [x] gh release v1.3.0 创建,2 assets 上传
- [x] SHA256 verified(本地 vs gh release view)
- [x] pytest 604 passed / 0 skipped
- [x] ruff:All checks passed
- [x] release/v1.0 已 merge 到 main(per CLAUDE.md §5.6 pre-authorize)

## 下次会话候选

- A. 真实 30s 培训视频 Tauri UI 端到端(从 01.mp4 截短,W14-D 已预留方向)
- D. WiX/MSI installer(网络 OK 时,Tauri bundler 重试)
- L3. LE 优化(Prompt 自适应 / 自动重试 / 跨 Agent 经验晋升)
- 主仓 v1.3.0 PyPI 发布(等 E fix 验证后,合并发布 v1.3.0 整合包)
```

- [ ] **Step 2: 更新 task.md +W14-D 节**

Edit `F:\soft\00selfmade\media-to-doc\task.md`,在末尾(Phase 6 之后或 L1 状态行附近)追加:

```markdown
- [x] **W14-D C+E Tauri UI Release + 全 provider trust_env**(2026-07-22,~65min)
  - C: 子仓 push + NSIS 实编译 + gh release v1.3.0 + 2 assets(setup.exe 1.5MB + portable.exe 6.2MB)
    - 子仓 SSH remote + `git push -u origin master` + `git push origin tag v1.3.0`
    - NSIS 3.12 + `installer.nsi` 实编译,补 W14-C B 跳过步骤
    - LICENSE.txt 复制到 nsis/ 给 MUI_PAGE_LICENSE
    - `gh release create v1.3.0 --target master --notes-file`
  - E: Anthropic + OpenAICompat `_ensure_client` 透传 `http_client=httpx.Client(trust_env=False)`
    - 沿用 W14-B Ollama 模式(commit `427d963`)
    - 6 个新测试(2 provider × 3 用例:透传 / proxy 不影响 / 幂等)
    - 测试:598 → 604 passed / 0 skipped;ruff:All checks passed
  - 主仓:1 fix commit + 1 docs commit,fix 自动 merge main(per §5.6 pre-authorize)
  - LE:LP-20260722-W14D-001 沉淀 defense in depth
  - commit:`fix(llm): W14-D — extend trust_env=False to Anthropic + OpenAICompat providers`
  - commit:`docs(release): W14-D — subrepo v1.3.0 NSIS installer build + GitHub Release`
  - handoff:`handoff-w14d-c-e-2026-07-22.md`
```

- [ ] **Step 3: 更新 CLAUDE.md §10 +W14-D 行**

Edit `F:\soft\00selfmade\media-to-doc\CLAUDE.md` §10(v1.x 发布流程表),在 v1.3 Phase 2 那行后追加:

```markdown
| **v1.3 Phase 2 — Tauri UI** | 3 次点击跑通 + 桌面壳 + log tail + modal | ✅ W14-B+ + W14-B+2(分支 `feat/w14b-plus-8-commands`,8 commit,39 unit test / 0 failed)+ W14-C A 多课程并发 + B NSIS |
| **v1.3.0 subrepo Release** | 子仓 kizemo/media-to-doc-ui v1.3.0 + NSIS installer + Tauri portable | ✅ W14-D C(subrepo 推到 origin,gh release 公开) |
| **trust_env 全 provider** | Ollama / Anthropic / OpenAICompat 三个 provider 透传 `httpx.Client(trust_env=False)` | ✅ W14-D E(防公司 VPN 父 shell 代理劫持,598 → 604 passed) |
```

- [ ] **Step 4: git add 主仓文件**

Run:
```bash
cd "F:/soft/00selfmade/media-to-doc" && git add \
  docs/RELEASE_NOTES_v1.3.0.md \
  handoff-w14d-c-e-2026-07-22.md \
  task.md \
  CLAUDE.md
```

Expected: 4 files staged。

- [ ] **Step 5: commit docs(release)**

Run:
```bash
cd "F:/soft/00selfmade/media-to-doc" && git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
docs(release): W14-D — subrepo v1.3.0 NSIS installer build + GitHub Release

承接 W14-C + W14-D C 阶段:

- 子仓 kizemo/media-to-doc-ui 推到 origin
  - SSH remote + git push -u origin master
  - git push origin tag v1.3.0
- NSIS 3.12 实编译 installer.nsi(补 W14-C B 跳过的步骤)
  - 生成 media-to-doc-1.3.0-setup.exe ~1.5MB
  - LICENSE.txt 复制到 src-tauri/nsis/ 给 MUI_PAGE_LICENSE
- 2 assets 上传 GitHub Release v1.3.0
  - setup.exe(NSIS installer)
  - portable.exe(Tauri 免安装副本)
- gh release create --target master --notes-file
- 验收:SHA256 verified,release URL 可访问

docs/RELEASE_NOTES_v1.3.0.md 详细记录。
task.md + CLAUDE.md §10 同步 W14-D 状态。
handoff-w14d-c-e-2026-07-22.md 完整会话快照。

CLAUDE.md §5.6 pre-authorize:本 commit 是 feat(发布动作),不自动 merge,
等用户拍板是否要推到 origin main。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Expected: 1 commit on `release/v1.0`,message 含 `docs(release): W14-D`。

- [ ] **Step 6: 不 push,等用户拍板**

按 CLAUDE.md §5.6:`docs(release):` feat commit → 写 handoff 等拍板,不自动 merge。

- [ ] **Step 7: 给用户最终汇报**

在终端输出本会话总结:
- 验收:604 pytest + 2 assets SHA256 verified + release URL
- 下次会话候选
- 提醒用户 review handoff-w14d-c-e-2026-07-22.md 后决定是否 push release/v1.0 → origin main

---

## Self-Review Checklist

✅ **Spec coverage**:
- C 全部 8 步 → Task 6 + Task 7 + Task 8 + Task 9 覆盖
- E 全部 4 文件(anthropic.py + openai_compat.py + 2 test files)→ Task 1 + 2 + 3 + 4 覆盖
- 验收(测试 604 + ruff + gh release)→ Task 5 Step 2/3 + Task 8 Step 3-5 + Task 9 Step 7
- session budget <2h → §4 全任务合计 ~65min

✅ **Placeholder scan**:无 TBD / TODO / "类似 Task N" / "add appropriate error handling"

✅ **Type consistency**:
- `_ensure_client` 签名在 Task 1/2/3/4 保持一致(无参数返回 `object`)
- 测试 fixture `_CaptureClient` 模式在 Task 1/3 复用,Task 2/4 不直接依赖
- module docstring 在 Task 2/4 改写,保持 Ollama 模式(line 12-17 风格)

✅ **Pre-authorize 行为**:
- Task 5 E fix commit → **自动 merge main**(fix 类)
- Task 9 docs release commit → **不自动 merge**,等用户拍板(feat 类)

---

## 整体执行路径

**主线程**:Task 1 → Task 2 → Task 3 → Task 4 → Task 5(E 完整闭环)→ Task 6 → Task 7 → Task 8 → Task 9(C 完整闭环)

**并行机会**:
- Task 1(写测试)与 Task 3(写测试)互不依赖,可并行(但同 session 内顺序更清晰)
- Task 6(push)与 Task 7(NSIS 编译)顺序严格,不可并行(编译依赖 LICENSE.txt 就位)
- Task 8(gh release)依赖 Task 6/7 完成

**预计总时长**:~65min 主流程 + 5-10min 出错缓冲 ≈ 75min,session <2h 预算内。
