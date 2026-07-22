"""OpenAI Chat Completions 协议兼容 provider。

支持 7 个内置厂商 preset(传 ``preset=`` 自动填 ``base_url``):

================== ============================================== ====================
preset             base_url                                       典型模型
================== ============================================== ====================
``minimax``        https://api.minimaxi.com/v1                    MiniMax-Text-01
``deepseek``       https://api.deepseek.com/v1                    deepseek-chat
``zhipu``          https://open.bigmodel.cn/api/paas/v4           glm-4-plus
``moonshot``       https://api.moonshot.cn/v1                     moonshot-v1-128k
``openrouter``     https://openrouter.ai/api/v1                   (自动拉取)
``dashscope``      https://dashscope.aliyuncs.com/compatible-mode/v1  qwen-plus
``hunyuan``        https://hunyuan.tencent.com/v1                 hunyuan-pro
================== ============================================== ====================

也支持自定义 ``base_url``(企业私有部署),用法:

```python
from media_to_doc.llm import get_provider
provider = get_provider(
    "openai_compatible",
    api_key="sk-xxx",
    base_url="https://internal-llm.corp/v1",
    model="qwen2.5-72b",
)
```

依赖:
- ``openai>=1.40.0`` Python SDK(lazy import)

参考:TDD §4.2.4 + PROJECT_DESCRIPTION.md §3.3 openai_compatible 行。

注意(W14-D):``_ensure_client`` 构造 ``OpenAI`` 时透传
``http_client=httpx.Client(trust_env=False)``,让 SDK 内部 httpx 不读
``HTTP_PROXY`` / ``HTTPS_PROXY`` / ``all_proxy`` 等环境变量,避免
公司 VPN 父 shell 把 7 个 preset(minimax / deepseek / zhipu / moonshot /
openrouter / dashscope / hunyuan)调用劫持到代理。沿用 ``OllamaProvider``
W14-B ``427d963`` 模式。详见 feedback memory
``feedback_proxy_env_pollution.md``。
"""

from __future__ import annotations

from .base import BaseLLMProvider

# ─────────────────────────────────────────────────────────────
# 7 个厂商 preset
# ─────────────────────────────────────────────────────────────

PRESETS: dict[str, dict[str, object]] = {
  "minimax": {
    "base_url": "https://api.minimaxi.com/v1",
    "models": [
      "MiniMax-Text-01",
      "MiniMax-VL-01",
      "abab6.5s-chat",
    ],
  },
  "deepseek": {
    "base_url": "https://api.deepseek.com/v1",
    "models": [
      "deepseek-chat",
      "deepseek-reasoner",
      "deepseek-coder",
    ],
  },
  "zhipu": {
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "models": [
      "glm-4-plus",
      "glm-4-0520",
      "glm-4-flash",
    ],
  },
  "moonshot": {
    "base_url": "https://api.moonshot.cn/v1",
    "models": [
      "moonshot-v1-128k",
      "moonshot-v1-32k",
      "moonshot-v1-8k",
    ],
  },
  "openrouter": {
    # 自动发现;不给静态列表
    "base_url": "https://openrouter.ai/api/v1",
    "models": [],
  },
  "dashscope": {
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "models": [
      "qwen-plus",
      "qwen-turbo",
      "qwen-max",
    ],
  },
  "hunyuan": {
    "base_url": "https://hunyuan.tencent.com/v1",
    "models": [
      "hunyuan-pro",
      "hunyuan-standard",
    ],
  },
}


# ─────────────────────────────────────────────────────────────
# Provider
# ─────────────────────────────────────────────────────────────


class OpenAICompatProvider(BaseLLMProvider):
  """OpenAI Chat Completions 协议兼容 provider。

  Parameters
  ----------
  api_key : str | None
    API key(必填,或从 ``OPENAI_API_KEY`` 环境变量读)
  base_url : str | None
    endpoint URL;与 ``preset`` 二选一
  preset : str | None
    内置厂商名(见 :data:`PRESETS`),自动填 base_url
  model : str | None
    模型名;未传时若 preset 有静态列表用第一个,否则留空让 endpoint 自动选
  """

  def __init__(
    self,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    preset: str | None = None,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    timeout_seconds: int = 600,
  ) -> None:
    if preset is not None:
      if preset not in PRESETS:
        raise KeyError(
          f"未知 preset: {preset!r};可选: {sorted(PRESETS.keys())}"
        )
      cfg = PRESETS[preset]
      resolved_base_url = str(cfg["base_url"])
      preset_models = list(cfg.get("models", []))  # type: ignore[arg-type]
      resolved_model = model or (preset_models[0] if preset_models else None)
    else:
      resolved_base_url = base_url or ""
      resolved_model = model

    super().__init__(
      model=resolved_model,
      temperature=temperature,
      max_tokens=max_tokens,
      timeout_seconds=timeout_seconds,
    )
    self._api_key = api_key
    self._base_url = resolved_base_url
    self._preset = preset
    self._preset_models: list[str] = (
      list(PRESETS[preset]["models"]) if preset and PRESETS[preset].get("models") else []  # type: ignore[index]
    )
    self._client: object | None = None  # lazy init

  @property
  def name(self) -> str:
    return "openai_compatible"

  def list_models(self) -> list[str]:
    """列出可用模型。

    - 有 preset 静态列表 → 返回该列表
    - 否则尝试 ``client.models.list()`` 自动发现
    - 失败 → 返回空列表
    """
    if self._preset_models:
      return list(self._preset_models)

    try:
      client = self._ensure_client()
    except (ImportError, RuntimeError):
      return []

    try:
      response = client.models.list()  # type: ignore[attr-defined]
      models: list[str] = []
      for entry in getattr(response, "data", []) or []:
        model_id = getattr(entry, "id", None)
        if model_id:
          models.append(str(model_id))
      return models
    except Exception:
      return []

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
    response = client.chat.completions.create(  # type: ignore[attr-defined]
      model=model or self.model or "",
      messages=[{"role": "user", "content": prompt}],
      temperature=temperature,
      max_tokens=max_tokens,
      timeout=timeout_seconds,
    )
    # SDK 返回 Choice;first.message.content 是文本
    choices = getattr(response, "choices", None) or []
    if not choices:
      return ""
    first = choices[0]
    message = getattr(first, "message", None)
    if message is not None:
      content = getattr(message, "content", "")
      if content:
        return str(content).strip()
    # 兜底:老 SDK 返回 dict
    if isinstance(first, dict):
      msg = first.get("message") or {}
      return str(msg.get("content", "")).strip()
    return ""

  # ── 内部 ────────────────────────────────────────────────

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
      import httpx
      from openai import OpenAI  # type: ignore[import-untyped]
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


__all__ = [
  "OpenAICompatProvider",
  "PRESETS",
]
