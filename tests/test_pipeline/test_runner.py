"""``media_to_doc.pipeline.runner`` 单元测试。

策略:
- STAGE_FUNCS 注入假 stage(替换 audio/asr/frames),不依赖重依赖
- verify 状态加载/保存/跳过行为
- 错误传递
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from media_to_doc.config import WorkflowConfig
from media_to_doc.pipeline.runner import (
  STAGE_FUNCS,
  PipelineResult,
  StageContext,
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


def test_stage_funcs_unimplemented_raise() -> None:
  """W3 状态:longdoc/verify 2 个仍未实装(其余 9 个真实),调用抛 NotImplementedError。"""
  for stage in ("longdoc", "verify"):
    with pytest.raises(NotImplementedError, match=stage):
      STAGE_FUNCS[stage](_stage_name=stage)


def test_stage_funcs_real_stages_resolve() -> None:
  """W3 实装的 9 个 stage 必须是真函数(非 _not_implemented_stage)。"""
  from media_to_doc.pipeline.runner import _not_implemented_stage

  real_stages = (
    "audio", "asr", "frames", "ocr", "asr_correct",
    "chapters", "draft", "imagegen", "render",
  )
  for stage in real_stages:
    func = STAGE_FUNCS[stage]
    assert func is not _not_implemented_stage, f"{stage} 仍是占位"
    assert callable(func)


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
