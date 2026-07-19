"""``media_to_doc.pipeline.runner`` 单元测试。

策略:
- STAGE_FUNCS 注入假 stage(替换 audio/asr/frames),不依赖重依赖
- verify 状态加载/保存/跳过行为
- 错误传递

W10-C 新增:StageContext.metrics / LLM providers 自动注册 /
``_aggregate_llm_health`` 全覆盖。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from media_to_doc.config import WorkflowConfig
from media_to_doc.llm.base import ChatResponse, HealthReport, HealthStatus
from media_to_doc.pipeline.runner import (
  STAGE_FUNCS,
  PipelineResult,
  StageContext,
  _aggregate_llm_health,
  run_pipeline,
  run_stage,
)
from media_to_doc.state import STAGE_ORDER, State

# ─────────────────────────────────────────────────────────────
# STAGE_FUNCS 完整性
# ─────────────────────────────────────────────────────────────


def test_stage_funcs_covers_all_11_stages() -> None:
  """STAGE_FUNCS 必须覆盖 STAGE_ORDER 全部 11 个 stage。"""
  assert set(STAGE_FUNCS.keys()) == set(STAGE_ORDER)
  assert len(STAGE_FUNCS) == 11


def test_stage_funcs_implemented_stages_present() -> None:
  """W1 实装的 3 个 stage 必须是真实函数。"""
  from media_to_doc.pipeline import asr, audio, frames

  assert STAGE_FUNCS["audio"] is audio.prepare_audio
  assert STAGE_FUNCS["asr"] is asr.transcribe
  assert STAGE_FUNCS["frames"] is frames.extract_keyframes


def test_stage_funcs_no_unimplemented_remains() -> None:
  """W4 状态:全部 11 个 stage 都是真实实现,无 NotImplementedError 占位。"""
  from media_to_doc.pipeline.runner import _not_implemented_stage

  for stage, func in STAGE_FUNCS.items():
    assert func is not _not_implemented_stage, f"{stage} 仍是占位"
    assert callable(func), f"{stage} 不可调用"


def test_stage_funcs_real_stages_resolve() -> None:
  """W4 实装的全部 11 个 stage 必须都是真函数(非 _not_implemented_stage)。"""
  from media_to_doc.pipeline.runner import _not_implemented_stage

  real_stages = (
    "audio", "asr", "frames", "ocr", "asr_correct",
    "chapters", "draft", "imagegen", "render",
    "longdoc", "verify",
  )
  assert set(real_stages) == set(STAGE_ORDER)
  for stage in real_stages:
    func = STAGE_FUNCS[stage]
    assert func is not _not_implemented_stage, f"{stage} 仍是占位"
    assert callable(func)


def test_longdoc_wrapper_resolves_to_real_longdoc_module() -> None:
  """``longdoc`` stage 必须指向 :mod:`longdoc` 真函数(:func:`process_long_doc`)。"""
  from media_to_doc.pipeline import longdoc

  assert STAGE_FUNCS["longdoc"] is longdoc.process_long_doc or callable(
    STAGE_FUNCS["longdoc"]
  )
  # 通过 wrapper 调时是 _longdoc_wrapper,真实函数是 longdoc.process_long_doc
  from media_to_doc.pipeline import runner as runner_mod

  assert hasattr(runner_mod, "_longdoc_wrapper")


def test_verify_stage_resolves_to_real_verify_module() -> None:
  """``verify`` stage 必须指向 :mod:`verify` 真函数(:func:`verify_pipeline`)。"""
  from media_to_doc.pipeline import verify

  assert STAGE_FUNCS["verify"] is verify.verify_pipeline


# ─────────────────────────────────────────────────────────────
# run_stage:单 stage + 状态机
# ─────────────────────────────────────────────────────────────


def _patch_invoke(monkeypatch: pytest.MonkeyPatch, name_to_fn: dict[str, object]) -> None:
  """用替代函数替换 _invoke_stage(为不同 stage 分发)。

  测试用的函数签名:``fn(stage: str, ctx: StageContext) -> object``
  真实内部签名是 ``_invoke_stage(stage, func, ctx)``,所以下发的 dispatcher
  会丢弃 ``func`` 参数再调用用户函数。
  """
  import media_to_doc.pipeline.runner as runner_mod

  def patched(stage: str, func: object, ctx: StageContext) -> object:
    if stage in name_to_fn:
      return name_to_fn[stage](stage, ctx)
    raise NotImplementedError(stage)

  monkeypatch.setattr(runner_mod, "_invoke_stage", patched)


def test_run_stage_marks_running_then_completed(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """run_stage 必须按 running → completed 推进 state。"""
  state = State.new(course="t")
  state.save(tmp_path / "state.json")

  def fake_audio(stage: str, ctx: StageContext) -> Path:
    return ctx.work / "audio.wav"

  _patch_invoke(monkeypatch, {"audio": fake_audio})

  ctx = StageContext(
    inbox=tmp_path / "inbox",
    work=tmp_path,
    config=WorkflowConfig(),
  )

  stage_state = run_stage("audio", ctx, state)
  assert stage_state.status == "completed"

  saved = State.load(tmp_path / "state.json")
  assert saved.stages["audio"].status == "completed"


def test_run_stage_skips_completed(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """已完成的 stage → 跳过,不调用函数。"""
  state = State.new(course="t")
  state.mark("audio", "completed")
  state.save(tmp_path / "state.json")

  def fake_audio(stage: str, ctx: StageContext) -> Path:
    raise RuntimeError("should not be called")

  _patch_invoke(monkeypatch, {"audio": fake_audio})

  ctx = StageContext(inbox=tmp_path / "inbox", work=tmp_path, config=WorkflowConfig())
  run_stage("audio", ctx, state)  # 不应抛
  saved = State.load(tmp_path / "state.json")
  assert saved.stages["audio"].status == "completed"


def test_run_stage_marks_failed_on_exception(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """stage 抛异常 → state.mark(failed) + 异常上抛。"""
  state = State.new(course="t")
  state.save(tmp_path / "state.json")

  def boom(stage: str, ctx: StageContext) -> None:
    raise RuntimeError("explode")

  _patch_invoke(monkeypatch, {"audio": boom})

  ctx = StageContext(inbox=tmp_path / "inbox", work=tmp_path, config=WorkflowConfig())

  with pytest.raises(RuntimeError, match="explode"):
    run_stage("audio", ctx, state)

  saved = State.load(tmp_path / "state.json")
  assert saved.stages["audio"].status == "failed"
  assert "RuntimeError" in (saved.stages["audio"].error or "")


def test_run_stage_unknown_raises_keyerror(tmp_path: Path) -> None:
  """未知 stage → KeyError。"""
  state = State.new(course="t")
  ctx = StageContext(inbox=tmp_path / "inbox", work=tmp_path, config=WorkflowConfig())

  with pytest.raises(KeyError, match="未知 stage"):
    run_stage("nonexistent", ctx, state)


# ─────────────────────────────────────────────────────────────
# run_pipeline:端到端
# ─────────────────────────────────────────────────────────────


def _audio_only_invoke(stage: str, func: object, ctx: StageContext) -> object:
  """仅 audio 注入真行为,asr/frames 仍抛 NotImplementedError。"""
  if stage == "audio":
    (ctx.work / "asr").mkdir(parents=True, exist_ok=True)
    (ctx.work / "asr" / "audio.wav").write_bytes(b"")
    return ctx.work / "asr" / "audio.wav"
  raise NotImplementedError(stage)


def _all_three_invoke(stage: str, func: object, ctx: StageContext) -> object:
  """三个 W1 stage 都 mock。"""
  if stage == "audio":
    (ctx.work / "asr").mkdir(parents=True, exist_ok=True)
    (ctx.work / "asr" / "audio.wav").write_bytes(b"")
    return ctx.work / "asr" / "audio.wav"
  if stage == "asr":
    (ctx.work / "asr" / "transcript.jsonl").write_text(
      '{"start": 0.0, "end": 1.0, "text": "x"}\n',
      encoding="utf-8",
    )
    return ctx.work / "asr" / "transcript.jsonl"
  if stage == "frames":
    img_dir = ctx.img_dir or (ctx.inbox / "img")
    img_dir.mkdir(parents=True, exist_ok=True)
    return []
  raise NotImplementedError(stage)


def test_run_pipeline_audio_only(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """run_pipeline 跑 audio 真实 + asr/frames 通过 stop_after 跳过。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "course.mp4").write_bytes(b"")
  work = tmp_path / "work"

  import media_to_doc.pipeline.runner as runner_mod
  monkeypatch.setattr(runner_mod, "_invoke_stage", _audio_only_invoke)

  result = run_pipeline(inbox, work, stop_after="audio")

  assert isinstance(result, PipelineResult)
  assert "audio" in result.completed
  assert (work / "state.json").exists()


def test_run_pipeline_creates_state_json(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """首次跑 → 新建 state.json。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "course.mp4").write_bytes(b"")

  import media_to_doc.pipeline.runner as runner_mod
  monkeypatch.setattr(runner_mod, "_invoke_stage", _audio_only_invoke)

  work = tmp_path / "work"
  run_pipeline(inbox, work, stop_after="audio")

  state_path = work / "state.json"
  assert state_path.exists()
  data = json.loads(state_path.read_text(encoding="utf-8"))
  assert data["stages"]["audio"]["status"] == "completed"
  assert data["stages"]["asr"]["status"] == "pending"


def test_run_pipeline_resume_from_state(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """已有 state.json → 跳过已完成,resume 语义。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "course.mp4").write_bytes(b"")
  work = tmp_path / "work"

  state = State.new(course="t")
  state.mark("audio", "completed")
  state.save(work / "state.json")

  called = {"audio": 0}

  def fake_audio(stage: str, ctx: StageContext) -> Path:
    called["audio"] += 1
    (ctx.work / "asr").mkdir(parents=True, exist_ok=True)
    (ctx.work / "asr" / "audio.wav").write_bytes(b"")
    return ctx.work / "asr" / "audio.wav"

  def resume_invoke(stage: str, func: object, ctx: StageContext) -> object:
    if stage == "audio":
      return fake_audio(stage, ctx)
    raise NotImplementedError(stage)

  import media_to_doc.pipeline.runner as runner_mod
  monkeypatch.setattr(runner_mod, "_invoke_stage", resume_invoke)

  run_pipeline(inbox, work, stop_after="audio", skip_completed=True)

  # audio 已 completed → 被跳过,不会被调用
  assert called["audio"] == 0


def test_run_pipeline_stop_after_halts(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """stop_after=audio → 跑到 audio 后停下,asr/frames 不调。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "course.mp4").write_bytes(b"")
  work = tmp_path / "work"

  invoked_stages: list[str] = []

  def invoke_with_track(stage: str, func: object, ctx: StageContext) -> object:
    invoked_stages.append(stage)
    if stage == "audio":
      (ctx.work / "asr").mkdir(parents=True, exist_ok=True)
      (ctx.work / "asr" / "audio.wav").write_bytes(b"")
      return ctx.work / "asr" / "audio.wav"
    raise NotImplementedError(stage)

  import media_to_doc.pipeline.runner as runner_mod
  monkeypatch.setattr(runner_mod, "_invoke_stage", invoke_with_track)

  result = run_pipeline(inbox, work, stop_after="audio")

  assert invoked_stages == ["audio"]
  assert result.completed == ["audio"]


def test_run_pipeline_three_stages_end_to_end(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """W1 完整三 stage 端到端(mock 实现)。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "course.mp4").write_bytes(b"")
  work = tmp_path / "work"

  import media_to_doc.pipeline.runner as runner_mod
  monkeypatch.setattr(runner_mod, "_invoke_stage", _all_three_invoke)

  result = run_pipeline(inbox, work, stop_after="frames")

  assert result.completed == ["audio", "asr", "frames"]
  assert result.failed == []
  assert (work / "state.json").exists()
  state = State.load(work / "state.json")
  assert state.stages["frames"].status == "completed"


# ─────────────────────────────────────────────────────────────
# W10-C:StageContext.metrics / LLM provider 自动注册 / llm_health 聚合
# ─────────────────────────────────────────────────────────────


class _FakeLLMProvider:
  """轻量 fake LLM provider,模拟 ``BaseLLMProvider`` 关键接口。

  与真 provider 的关键差异:**不依赖** torch / Ollama / Anthropic SDK。
  只实现 ``name`` / ``model`` / ``chat()`` / ``health()``,足以让
  ``_aggregate_llm_health`` / StageContext.metrics 注册链路端到端跑通。
  """

  def __init__(
    self,
    name: str = "fake",
    *,
    model: str = "fake-model",
    calls: int = 0,
    failures: int = 0,
    chat_text: str = "ok",
    chat_raises: Exception | None = None,
  ) -> None:
    self.name = name
    self.model = model
    self._calls = calls
    self._failures = failures
    self._last_failure: str | None = None
    self._chat_text = chat_text
    self._chat_raises = chat_raises

  def chat(self, prompt: str, **_: object) -> ChatResponse:
    self._calls += 1
    if self._chat_raises is not None:
      self._failures += 1
      raise self._chat_raises
    return ChatResponse(
      text=self._chat_text,
      model=self.model,
      provider=self.name,
      duration_seconds=0.001,
    )

  def health(self) -> HealthReport:
    rate = (self._failures / self._calls) if self._calls else 0.0
    status = (
      HealthStatus.UNKNOWN if self._calls == 0
      else HealthStatus.HEALTHY if rate < 0.1
      else HealthStatus.DEGRADED if rate < 0.3
      else HealthStatus.UNHEALTHY
    )
    return HealthReport(
      status=status,
      total_calls=self._calls,
      total_failures=self._failures,
      failure_rate=rate,
      last_failure=self._last_failure,
    )


def test_stage_context_has_metrics_with_default() -> None:
  """StageContext 默认带 ``metrics={"llm_providers": {}}`` 字段(W10-C)。"""
  ctx = StageContext(
    inbox=Path("/x"), work=Path("/y"), config=WorkflowConfig(),
  )
  assert ctx.metrics == {"llm_providers": {}}


def test_stage_context_metrics_field_independent_per_instance() -> None:
  """两个 ctx 实例不应共享 metrics 字典(避免 cross-test 污染)。"""
  ctx_a = StageContext(
    inbox=Path("/x"), work=Path("/y"), config=WorkflowConfig(),
  )
  ctx_b = StageContext(
    inbox=Path("/x"), work=Path("/y"), config=WorkflowConfig(),
  )
  ctx_a.metrics["llm_providers"]["chapters"] = "fake"
  assert "chapters" not in ctx_b.metrics["llm_providers"]


def test_chapters_wrapper_registers_provider_in_ctx_metrics(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  """``_chapters_wrapper`` 创建 provider 后注册到 ctx.metrics(W10-C)。"""
  import media_to_doc.pipeline.runner as runner_mod

  fake = _FakeLLMProvider(name="ollama", calls=3, failures=0)

  def fake_get_provider(*_args: object, **_kwargs: object) -> _FakeLLMProvider:
    return fake

  monkeypatch.setattr(
    "media_to_doc.llm.get_provider", fake_get_provider,
  )
  # 跳过真 split_chapters(避免依赖 transcript.jsonl)
  monkeypatch.setattr(
    runner_mod, "split_chapters", lambda *a, **kw: None,
  )

  ctx = StageContext(
    inbox=Path("/x"), work=Path("/y"), config=WorkflowConfig(),
  )
  runner_mod._chapters_wrapper(ctx)

  assert ctx.metrics["llm_providers"]["chapters"] is fake


def test_draft_wrapper_registers_provider_in_ctx_metrics(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  """``_draft_wrapper`` 创建 provider 后注册到 ctx.metrics(W10-C)。"""
  import media_to_doc.pipeline.runner as runner_mod

  fake = _FakeLLMProvider(name="anthropic", calls=5, failures=1)

  monkeypatch.setattr(
    "media_to_doc.llm.get_provider", lambda *a, **kw: fake,
  )
  monkeypatch.setattr(
    runner_mod, "generate_drafts", lambda *a, **kw: None,
  )

  ctx = StageContext(
    inbox=Path("/x"), work=Path("/y"), config=WorkflowConfig(),
  )
  runner_mod._draft_wrapper(ctx)

  assert ctx.metrics["llm_providers"]["draft"] is fake


def test_longdoc_wrapper_registers_provider_when_active(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  """``_longdoc_wrapper`` active 时(非 ``skip``)创建 provider 并注册(W10-C)。

  注意:PipelineConfig 默认 ``longdoc_llm_provider="skip"``(W4 CI 离线设计),
  所以测试必须显式改 active 模式才能走真 provider 路径。
  """
  import media_to_doc.pipeline.runner as runner_mod

  fake = _FakeLLMProvider(name="ollama", calls=2, failures=0)

  monkeypatch.setattr(
    "media_to_doc.llm.get_provider", lambda *a, **kw: fake,
  )
  monkeypatch.setattr(
    runner_mod, "process_long_doc", lambda *a, **kw: None,
  )

  cfg = WorkflowConfig()
  cfg.pipeline.longdoc_llm_provider = "ollama"  # 显式切到 active
  ctx = StageContext(
    inbox=Path("/x"), work=Path("/y"), config=cfg,
  )
  runner_mod._longdoc_wrapper(ctx)

  assert ctx.metrics["llm_providers"]["longdoc"] is fake


def test_longdoc_wrapper_skip_does_not_register(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  """``longdoc_llm_provider='skip'`` 时 wrapper 不创建 provider 不注册(W10-C)。"""
  import media_to_doc.pipeline.runner as runner_mod

  # 如果 get_provider 被调用,测试失败(provider 不应被创建)
  def fail_get_provider(*_a: object, **_kw: object) -> _FakeLLMProvider:
    raise AssertionError("skip 模式下不应创建 provider")

  monkeypatch.setattr("media_to_doc.llm.get_provider", fail_get_provider)
  monkeypatch.setattr(
    runner_mod, "process_long_doc", lambda *a, **kw: None,
  )

  cfg = WorkflowConfig()
  cfg.pipeline.longdoc_llm_provider = "skip"
  ctx = StageContext(
    inbox=Path("/x"), work=Path("/y"), config=cfg,
  )
  runner_mod._longdoc_wrapper(ctx)

  assert "longdoc" not in ctx.metrics["llm_providers"]


def test_aggregate_llm_health_merges_multiple_providers() -> None:
  """``_aggregate_llm_health`` 跨多个 provider 聚合,key = stage_name_provider_name。"""
  p1 = _FakeLLMProvider(name="ollama", calls=3, failures=1)
  p2 = _FakeLLMProvider(name="anthropic", calls=2, failures=0)
  p3 = _FakeLLMProvider(name="openai_compatible", calls=5, failures=2)

  metrics = {
    "llm_providers": {
      "chapters": p1, "draft": p2, "longdoc": p3,
    },
  }
  result = _aggregate_llm_health(metrics)

  assert result == {
    "chapters_ollama": {"calls": 3, "failures": 1},
    "draft_anthropic": {"calls": 2, "failures": 0},
    "longdoc_openai_compatible": {"calls": 5, "failures": 2},
  }


def test_aggregate_llm_health_empty_metrics_returns_empty() -> None:
  """空 metrics / 空 llm_providers → 返回 ``{}``(不抛错)。"""
  assert _aggregate_llm_health({}) == {}
  assert _aggregate_llm_health({"llm_providers": {}}) == {}


def test_aggregate_llm_health_handles_provider_health_exception() -> None:
  """某个 provider 的 ``.health()`` 抛错 → 跳过该项,不影响其他聚合。

  失败隔离沿用 W8 PipelineLogger 同款模式(provider.health() 异常不破坏 run_pipeline 返回)。
  """
  p_ok = _FakeLLMProvider(name="ollama", calls=1, failures=0)

  class BoomProvider:
    name = "boom"

    def health(self) -> HealthReport:
      raise RuntimeError("boom")

  metrics = {"llm_providers": {"chapters": p_ok, "draft": BoomProvider()}}
  # 不应抛错
  result = _aggregate_llm_health(metrics)

  assert "chapters_ollama" in result
  assert result["chapters_ollama"] == {"calls": 1, "failures": 0}
  assert "draft_boom" not in result  # 失败隔离:跳过 BoomProvider


def test_aggregate_llm_health_metrics_missing_llm_providers_key() -> None:
  """``metrics["llm_providers"]`` 缺省时也安全(兼容未来 metrics 扩展)。"""
  assert _aggregate_llm_health({"other_key": "value"}) == {}
  assert _aggregate_llm_health({"llm_providers": None}) == {}


def test_run_pipeline_writes_real_llm_health_into_pipeline_run_json(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """端到端:11 stage mock + 3 个 fake provider → ``pipeline_run.json.llm_health`` 非空。

  验证要点:
  1. ``logger.finalize`` 收到真实 ``llm_health``(非空字典)
  2. key 形如 ``{stage_name}_{provider_name}``
  3. ``calls`` / ``failures`` 与 fake provider 的 stats 对齐
  """
  import media_to_doc.pipeline.runner as runner_mod

  fake_chapters = _FakeLLMProvider(name="ollama", calls=3, failures=1)
  fake_draft = _FakeLLMProvider(name="ollama", calls=2, failures=0)
  fake_longdoc = _FakeLLMProvider(name="anthropic", calls=4, failures=2)

  def get_provider_for(*_a: object, **_kw: object) -> _FakeLLMProvider:
    # 按调用顺序返回 chapters / draft / longdoc 各自的 fake
    if not hasattr(get_provider_for, "_i"):
      get_provider_for._i = 0  # type: ignore[attr-defined]
    pool = [fake_chapters, fake_draft, fake_longdoc]
    idx = get_provider_for._i  # type: ignore[attr-defined]
    get_provider_for._i = idx + 1  # type: ignore[attr-defined]
    return pool[idx]

  monkeypatch.setattr(
    "media_to_doc.llm.get_provider", get_provider_for,
  )
  # 跳过真 stage(LLM 调用 + 重依赖)
  monkeypatch.setattr(
    runner_mod, "split_chapters", lambda *a, **kw: None,
  )
  monkeypatch.setattr(
    runner_mod, "generate_drafts", lambda *a, **kw: None,
  )
  monkeypatch.setattr(
    runner_mod, "process_long_doc", lambda *a, **kw: None,
  )

  # 跑一个完整的 run_pipeline(mock 所有非 LLM stage 的实际行为)
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "course.mp4").write_bytes(b"")
  work = tmp_path / "work"

  # 显式切 longdoc 到 active(W4 默认 skip,需要 provider 才能注册)
  cfg = WorkflowConfig()
  cfg.pipeline.longdoc_llm_provider = "ollama"

  # 11 stage 全部 mock:产生最小产物让 verify 通过
  def all_stages(stage: str, func: object, ctx: StageContext) -> object:
    if stage == "audio":
      (ctx.work / "asr").mkdir(parents=True, exist_ok=True)
      (ctx.work / "asr" / "audio.wav").write_bytes(b"")
      return ctx.work / "asr" / "audio.wav"
    if stage == "asr":
      (ctx.work / "asr" / "transcript.jsonl").write_text(
        '{"start": 0.0, "end": 1.0, "text": "x"}\n',
        encoding="utf-8",
      )
      return ctx.work / "asr" / "transcript.jsonl"
    if stage == "frames":
      img_dir = ctx.img_dir or (ctx.inbox / "img")
      img_dir.mkdir(parents=True, exist_ok=True)
      (ctx.work / "frames").mkdir(parents=True, exist_ok=True)
      (ctx.work / "frames" / "keyframes.json").write_text("[]", encoding="utf-8")
      return []
    if stage == "ocr":
      out = ctx.work / "ocr"
      out.mkdir(parents=True, exist_ok=True)
      (out / "ocr_results.json").write_text("[]", encoding="utf-8")
      return out / "ocr_results.json"
    if stage == "asr_correct":
      out = ctx.work / "asr" / "asr_corrected.jsonl"
      out.write_text("", encoding="utf-8")
      return out
    if stage == "chapters":
      # 让 _chapters_wrapper 真跑(注册 provider 到 ctx.metrics),
      # wrapper 内部调 split_chapters — 已被 monkeypatch 成 no-op
      chapters_dir = ctx.work / "chapters"
      chapters_dir.mkdir(parents=True, exist_ok=True)
      func(ctx)
      (chapters_dir / "chapters.json").write_text(
        '{"video": "course", "chapters": [{"title": "T1", "summary": "S", '
        '"start_seconds": 0.0, "end_seconds": 1.0, "key_points": [], '
        '"image_refs": [], "illustrations": []}]}\n',
        encoding="utf-8",
      )
      return chapters_dir / "chapters.json"
    if stage == "draft":
      # 同上:draft wrapper → register provider + 调 generate_drafts(monkeypatch no-op)
      drafts_dir = ctx.work / "chapters" / "raw" / "course"
      drafts_dir.mkdir(parents=True, exist_ok=True)
      func(ctx)
      return drafts_dir
    if stage == "imagegen":
      return None
    if stage == "render":
      return ctx.work / "chapters" / "raw" / "course" / "course.md"
    if stage == "longdoc":
      # 同上:longdoc wrapper → register provider + 调 process_long_doc(monkeypatch no-op)
      func(ctx)
      return ctx.work / "chapters" / "raw" / "course" / "course_final.md"
    if stage == "verify":
      verify_path = ctx.work / "verify.json"
      verify_path.write_text(
        '{"overall_passed": true, "checks": []}\n', encoding="utf-8",
      )
      return verify_path
    raise NotImplementedError(stage)

  monkeypatch.setattr(runner_mod, "_invoke_stage", all_stages)

  result = run_pipeline(
    inbox,
    work,
    config=cfg,
    stop_after="verify",
  )

  # 端到端断言
  assert result.pipeline_run is not None, "LE finalize 应成功"
  assert result.pipeline_run.llm_health == {
    "chapters_ollama": {"calls": 3, "failures": 1},
    "draft_ollama": {"calls": 2, "failures": 0},
    "longdoc_anthropic": {"calls": 4, "failures": 2},
  }

  # pipeline_run.json 落到盘
  on_disk = json.loads(
    (work / "pipeline_run.json").read_text(encoding="utf-8")
  )
  assert on_disk["llm_health"] == {
    "chapters_ollama": {"calls": 3, "failures": 1},
    "draft_ollama": {"calls": 2, "failures": 0},
    "longdoc_anthropic": {"calls": 4, "failures": 2},
  }
