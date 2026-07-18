"""LLM Provider 抽象基类 + 通用数据类。

设计动机:
- 11 阶段流水线中,chapters / draft / longdoc 都依赖 LLM,需要一个统一入口
- 多个厂商(本地 Ollama / Anthropic / OpenAI 兼容)协议不同,需抽象隔离
- LE L1 健康度评估需要按 provider 维度统计调用/失败,基类自动累积

参考:TDD §4.2.1 ``BaseLLMProvider`` 伪代码。
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


@dataclass
class ChatMessage:
  """一条对话消息。

  Attributes
  ----------
  role : str
    ``"system"`` / ``"user"`` / ``"assistant"``
  content : str
    文本内容
  """

  role: str
  content: str

  def to_dict(self) -> dict[str, str]:
    return {"role": self.role, "content": self.content}


@dataclass
class ChatResponse:
  """LLM 调用结果。

  Attributes
  ----------
  text : str
    模型回复文本
  model : str
    实际使用的模型名(空字符串表示 provider 未指定)
  provider : str
    provider 名(``ollama`` / ``anthropic`` / ``openai_compatible``)
  duration_seconds : float
    单次调用耗时
  prompt_tokens : int | None
    输入 token 数(若 provider 返回)
  completion_tokens : int | None
    输出 token 数(若 provider 返回)
  """

  text: str
  model: str
  provider: str
  duration_seconds: float
  prompt_tokens: int | None = None
  completion_tokens: int | None = None


class HealthStatus(StrEnum):
  """健康度等级(LE L1 health() 评估用)。

  - ``HEALTHY``:失败率 < 10%
  - ``DEGRADED``:失败率 10-30%
  - ``UNHEALTHY``:失败率 > 30%(建议切换 fallback provider)
  - ``UNKNOWN``:无任何调用记录
  """

  HEALTHY = "healthy"
  DEGRADED = "degraded"
  UNHEALTHY = "unhealthy"
  UNKNOWN = "unknown"


@dataclass
class HealthReport:
  """健康度报告(:meth:`BaseLLMProvider.health` 返回值)。"""

  status: HealthStatus
  total_calls: int
  total_failures: int
  failure_rate: float
  last_failure: str | None = None

  def to_dict(self) -> dict[str, object]:
    return {
      "status": self.status.value,
      "total_calls": self.total_calls,
      "total_failures": self.total_failures,
      "failure_rate": round(self.failure_rate, 4),
      "last_failure": self.last_failure,
    }


# ─────────────────────────────────────────────────────────────
# 基类
# ─────────────────────────────────────────────────────────────


class BaseLLMProvider(ABC):
  """所有 LLM provider 的抽象基类。

  子类必须实现:
  - :attr:`name` 属性(provider 名,如 ``"ollama"``)
  - :meth:`list_models` 返回该 provider 支持的模型列表
  - :meth:`_chat_impl` 真正执行协议调用,返回纯文本

  子类**不应**覆盖 :meth:`chat`(已含计时 + 错误统计),
  也**不应**覆盖 :meth:`health`(已封装统计逻辑)。
  """

  def __init__(
    self,
    *,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    timeout_seconds: int = 600,
  ) -> None:
    self.model = model
    self.temperature = temperature
    self.max_tokens = max_tokens
    self.timeout_seconds = timeout_seconds
    # 内部健康度统计(LE L1 health() 消费)
    self._calls: int = 0
    self._failures: int = 0
    self._last_failure: str | None = None

  # ── 子类必须实现 ────────────────────────────────────────

  @property
  @abstractmethod
  def name(self) -> str:
    """provider 短名(``ollama`` / ``anthropic`` / ``openai_compatible``)。"""
    raise NotImplementedError

  @abstractmethod
  def list_models(self) -> list[str]:
    """列出该 provider 支持的模型 ID。"""
    raise NotImplementedError

  @abstractmethod
  def _chat_impl(
    self,
    prompt: str,
    *,
    model: str | None,
    temperature: float,
    max_tokens: int,
    timeout_seconds: int,
  ) -> str:
    """子类真正调用 LLM 协议的私有方法,返回纯文本回复。"""
    raise NotImplementedError

  # ── 统一入口 ────────────────────────────────────────────

  def chat(
    self,
    prompt: str,
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
  ) -> ChatResponse:
    """单轮对话:返回 :class:`ChatResponse`(含耗时 + token 统计)。

    子类**不应**覆盖本方法,统一走 :meth:`_chat_impl` + 内部统计。
    """
    used_model = model or self.model or ""
    used_temp = temperature if temperature is not None else self.temperature
    used_tokens = max_tokens if max_tokens is not None else self.max_tokens
    timeout = self.timeout_seconds

    self._calls += 1
    start = time.monotonic()
    try:
      text = self._chat_impl(
        prompt,
        model=used_model or None,
        temperature=used_temp,
        max_tokens=used_tokens,
        timeout_seconds=timeout,
      )
    except Exception as exc:
      self._failures += 1
      self._last_failure = f"{type(exc).__name__}: {exc}"
      raise
    duration = time.monotonic() - start

    return ChatResponse(
      text=text,
      model=used_model,
      provider=self.name,
      duration_seconds=duration,
    )

  def chat_text(self, prompt: str, **kwargs: object) -> str:
    """便捷方法:只返回文本。"""
    return self.chat(prompt, **kwargs).text  # type: ignore[arg-type]

  # ── 健康度评估 ──────────────────────────────────────────

  def health(self) -> HealthReport:
    """根据历史调用 / 失败计数评估健康度。

    阈值(LE L1 默认):
    - ``HEALTHY``:失败率 < 10%
    - ``DEGRADED``:10% ≤ 失败率 < 30%
    - ``UNHEALTHY``:失败率 ≥ 30%
    - ``UNKNOWN``:无任何调用
    """
    if self._calls == 0:
      return HealthReport(
        status=HealthStatus.UNKNOWN,
        total_calls=0,
        total_failures=0,
        failure_rate=0.0,
      )
    rate = self._failures / self._calls
    if rate < 0.1:
      status = HealthStatus.HEALTHY
    elif rate < 0.3:
      status = HealthStatus.DEGRADED
    else:
      status = HealthStatus.UNHEALTHY
    return HealthReport(
      status=status,
      total_calls=self._calls,
      total_failures=self._failures,
      failure_rate=rate,
      last_failure=self._last_failure,
    )

  def reset_stats(self) -> None:
    """清空统计(测试 / 切 provider 时用)。"""
    self._calls = 0
    self._failures = 0
    self._last_failure = None

  # ── 调试用 ──────────────────────────────────────────────

  def __repr__(self) -> str:
    return (
      f"<{type(self).__name__} name={self.name!r} "
      f"model={self.model!r} calls={self._calls} failures={self._failures}>"
    )


__all__ = [
  "ChatMessage",
  "ChatResponse",
  "HealthStatus",
  "HealthReport",
  "BaseLLMProvider",
]
