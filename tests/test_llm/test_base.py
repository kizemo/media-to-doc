"""LLM 抽象基类测试。

覆盖:
- 数据类 to_dict
- HealthStatus 阈值
- BaseLLMProvider 错误统计 + health()
- chat() 入口计时 + chat_text() 便捷方法
- 子类最小实现即可测
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from media_to_doc.llm.base import (
  BaseLLMProvider,
  ChatMessage,
  ChatResponse,
  HealthReport,
  HealthStatus,
)

# ─────────────────────────────────────────────────────────────
# 测试用最小 provider
# ─────────────────────────────────────────────────────────────


class _FakeProvider(BaseLLMProvider):
  """测试用:模拟可控 _chat_impl。"""

  def __init__(self, *, fail_times: int = 0, reply: str = "ok", **kwargs: Any) -> None:
    super().__init__(**kwargs)
    self._fail_times = fail_times
    self._reply = reply
    self._invocation_count = 0

  @property
  def name(self) -> str:
    return "fake"

  def list_models(self) -> list[str]:
    return ["fake-model-a", "fake-model-b"]

  def _chat_impl(
    self,
    prompt: str,
    *,
    model: str | None,
    temperature: float,
    max_tokens: int,
    timeout_seconds: int,
  ) -> str:
    self._invocation_count += 1
    if self._invocation_count <= self._fail_times:
      raise RuntimeError(f"simulated failure #{self._invocation_count}")
    return self._reply


# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


def test_chat_message_to_dict() -> None:
  msg = ChatMessage(role="user", content="hello")
  assert msg.to_dict() == {"role": "user", "content": "hello"}


def test_chat_response_defaults() -> None:
  r = ChatResponse(text="x", model="m", provider="p", duration_seconds=1.5)
  assert r.text == "x"
  assert r.prompt_tokens is None
  assert r.completion_tokens is None


def test_health_report_to_dict() -> None:
  r = HealthReport(
    status=HealthStatus.HEALTHY,
    total_calls=10,
    total_failures=1,
    failure_rate=0.1,
  )
  payload = r.to_dict()
  assert payload["status"] == "healthy"
  assert payload["total_calls"] == 10
  assert payload["failure_rate"] == 0.1


# ─────────────────────────────────────────────────────────────
# HealthStatus 枚举
# ─────────────────────────────────────────────────────────────


def test_health_status_values() -> None:
  assert HealthStatus.HEALTHY.value == "healthy"
  assert HealthStatus.DEGRADED.value == "degraded"
  assert HealthStatus.UNHEALTHY.value == "unhealthy"
  assert HealthStatus.UNKNOWN.value == "unknown"


# ─────────────────────────────────────────────────────────────
# BaseLLMProvider 行为
# ─────────────────────────────────────────────────────────────


def test_abstract_cannot_instantiate() -> None:
  """BaseLLMProvider 不能直接实例化(必须有 name / list_models / _chat_impl)。"""
  with pytest.raises(TypeError):
    BaseLLMProvider()  # type: ignore[abstract]


def test_provider_health_unknown_when_no_calls() -> None:
  p = _FakeProvider()
  h = p.health()
  assert h.status == HealthStatus.UNKNOWN
  assert h.total_calls == 0
  assert h.total_failures == 0
  assert h.failure_rate == 0.0
  assert h.last_failure is None


def test_provider_chat_returns_response_and_increments_stats() -> None:
  p = _FakeProvider(reply="hello world")
  resp = p.chat("hi")
  assert isinstance(resp, ChatResponse)
  assert resp.text == "hello world"
  assert resp.provider == "fake"
  assert resp.model == "" or resp.model is not None
  assert resp.duration_seconds >= 0.0
  assert p._calls == 1
  assert p._failures == 0
  h = p.health()
  assert h.status == HealthStatus.HEALTHY
  assert h.total_calls == 1


def test_provider_chat_records_failure_and_propagates() -> None:
  p = _FakeProvider(fail_times=2, reply="never")
  with pytest.raises(RuntimeError, match="simulated failure #1"):
    p.chat("hi")
  with pytest.raises(RuntimeError, match="simulated failure #2"):
    p.chat("hi")
  # 第 3 次成功
  resp = p.chat("hi")
  assert resp.text == "never"
  assert p._calls == 3
  assert p._failures == 2
  h = p.health()
  assert h.total_calls == 3
  assert h.total_failures == 2
  # 2/3 ≈ 0.666 > 0.3 → UNHEALTHY
  assert h.status == HealthStatus.UNHEALTHY
  assert h.last_failure is not None
  assert "RuntimeError" in h.last_failure


def test_provider_health_degraded_threshold() -> None:
  """失败率 10%-30% → DEGRADED。"""
  p = _FakeProvider(fail_times=2, reply="ok")
  for _ in range(2):
    with pytest.raises(RuntimeError):
      p.chat("hi")
  for _ in range(18):
    p.chat("hi")
  # 2 / 20 = 0.1 → 边界值,Python `< 0.1` 判断 HEALTHY;< 0.3 包含 0.1+ → DEGRADED
  h = p.health()
  assert h.total_calls == 20
  assert h.total_failures == 2
  assert h.failure_rate == pytest.approx(0.1)
  assert h.status == HealthStatus.DEGRADED


def test_provider_chat_text_convenience() -> None:
  p = _FakeProvider(reply="just text")
  assert p.chat_text("anything") == "just text"


def test_provider_resets_stats() -> None:
  p = _FakeProvider(reply="ok")
  p.chat("a")
  p.chat("b")
  assert p._calls == 2
  p.reset_stats()
  assert p._calls == 0
  assert p._failures == 0
  assert p._last_failure is None


def test_provider_repr_contains_name_and_counters() -> None:
  p = _FakeProvider(reply="ok", model="test-model")
  r = repr(p)
  assert "FakeProvider" in r
  assert "fake" in r
  assert "calls=0" in r


def test_provider_chat_uses_default_model_when_none() -> None:
  """model=None 且 self.model=None → used_model 为空串(不抛错)。"""
  p = _FakeProvider(reply="x", model=None)
  # init 时 model 传 None → 内部 self.model = None
  resp = p.chat("hi")
  assert resp.text == "x"
  assert resp.model == ""


def test_provider_chat_measures_duration() -> None:
  """chat() 返回的 duration_seconds 应 >= 0(计时非负)。"""
  p = _FakeProvider(reply="x")
  start = time.monotonic()
  resp = p.chat("hi")
  elapsed = time.monotonic() - start
  assert 0.0 <= resp.duration_seconds <= elapsed + 0.1
