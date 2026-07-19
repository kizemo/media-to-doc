"""``media_to_doc.cli`` 单元测试(W6)。

策略:用 ``monkeypatch`` 替换 :func:`runner.run_pipeline` 让 CLI 不真正跑
11 stage,只验证 CLI 的参数解析 / inbox 隔离 / work_dir 派生 / state 派生 /
JSON 输出等行为。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from media_to_doc import cli
from media_to_doc.cli import app
from media_to_doc.config import WorkflowConfig
from media_to_doc.state import STAGE_ORDER, State

# CliRunner(mix_stderr=True) 不被 typer 0.12+ 支持 → eprint 走 stdout,
# 这样所有输出统一在 result.stdout,断言简单
runner = CliRunner()


def _invoke(args: list[str]) -> object:
  return runner.invoke(app, args)

# ─────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────


def _fake_run_pipeline(
  inbox: Path | None,
  work: Path,
  config: WorkflowConfig | None = None,
  *,
  skip_completed: bool = True,
  stop_after: str | None = None,
) -> Any:
  """替换 ``run_pipeline`` 的 stub:模拟 inbox 派生 + 写 state.json。

  模拟 :func:`runner.run_pipeline` 的关键行为:
  - load 或 new state
  - inbox=None → 从 state.inbox_path 派生
  - 写回 inbox_path + state.save
  - 返回真 :class:`PipelineResult`(避免 MagicMock 的 attr access 怪异)
  """
  from media_to_doc.pipeline.runner import PipelineResult

  state_path = work / "state.json"
  state = State.load(state_path) if state_path.exists() else State.new(course=work.name or "test")

  if inbox is None:
    if state.inbox_path:
      inbox = Path(state.inbox_path)
    else:
      raise ValueError(
        "inbox 缺省且 state.json 未记录 inbox_path;"
        "首次跑请用 ``mtd run <inbox_dir>`` 而非 ``mtd resume``"
      )
  inbox = inbox.resolve()

  if state.inbox_path != str(inbox):
    state.inbox_path = str(inbox)
    state.save(state_path)

  # mark 全部 11 stage 为 completed(让 is_success=True,避免 CLI 抛 exit 1)
  for stage_name in STAGE_ORDER:
    state.mark(stage_name, "completed")
  state.save(state_path)

  return PipelineResult(
    state=state,
    completed=list(STAGE_ORDER),
    failed=[],
    duration_seconds=0.1,
  )


def _patch_runner(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
  """monkeypatch run_pipeline,返回 captured_calls 列表收集调用。

  注意:captured 记录的是 **派生后** 的 inbox(即 state.inbox_path 派生或 caller 传),
  这样测试断言与真实 run_pipeline 行为一致。
  """
  captured: list[dict[str, Any]] = []

  def fake(
    inbox: Path | None,
    work: Path,
    config: WorkflowConfig | None = None,
    *,
    skip_completed: bool = True,
    stop_after: str | None = None,
  ) -> Any:
    result = _fake_run_pipeline(
      inbox, work, config,
      skip_completed=skip_completed, stop_after=stop_after,
    )
    # captured 存派生后的 inbox(与真 run_pipeline 一致)
    captured.append({
      "inbox": result.state.inbox_path and Path(result.state.inbox_path),
      "work": work,
      "config": config,
      "skip_completed": skip_completed,
      "stop_after": stop_after,
    })
    return result

  monkeypatch.setattr(cli, "run_pipeline", fake)
  return captured


# ─────────────────────────────────────────────────────────────
# mtd run
# ─────────────────────────────────────────────────────────────


def test_run_creates_state_and_work_dir(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """``mtd run <inbox>`` 默认 work=<inbox>/output + 创建 state.json。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "lec.mp4").write_bytes(b"")
  captured = _patch_runner(monkeypatch)

  result = _invoke( ["run", str(inbox), "--no-isolate"])

  assert result.exit_code == 0, result.stdout
  assert len(captured) == 1
  assert captured[0]["inbox"] == inbox.resolve()
  assert captured[0]["work"] == (inbox / "output").resolve()
  assert (inbox / "output" / "state.json").exists()


def test_run_with_work_dir_override(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """``--work-dir`` 覆盖默认 work 路径。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "lec.mp4").write_bytes(b"")
  custom = tmp_path / "my_run"
  captured = _patch_runner(monkeypatch)

  result = runner.invoke(
    app, ["run", str(inbox), "--work-dir", str(custom), "--no-isolate"],
  )

  assert result.exit_code == 0
  assert captured[0]["work"] == custom.resolve()


def test_run_llm_and_imagegen_overrides(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """``--llm`` / ``--llm-model`` / ``--imagegen`` / ``--longdoc-llm`` 覆盖 config。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "lec.mp4").write_bytes(b"")
  captured = _patch_runner(monkeypatch)

  result = _invoke( [
    "run", str(inbox), "--no-isolate",
    "--llm", "anthropic",
    "--llm-model", "claude-sonnet-4-6",
    "--imagegen", "skip",
    "--longdoc-llm", "anthropic",
  ])

  assert result.exit_code == 0
  cfg = captured[0]["config"]
  assert cfg.llm.provider == "anthropic"
  assert cfg.llm.model == "claude-sonnet-4-6"
  assert cfg.imagegen.provider == "skip"
  assert cfg.pipeline.longdoc_llm_provider == "anthropic"


def test_run_no_longdoc_sets_config_flag(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """``--no-longdoc`` → ``cfg.pipeline.skip_longdoc=True``。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "lec.mp4").write_bytes(b"")
  captured = _patch_runner(monkeypatch)

  result = _invoke( [
    "run", str(inbox), "--no-isolate", "--no-longdoc",
  ])

  assert result.exit_code == 0
  assert captured[0]["config"].pipeline.skip_longdoc is True


def test_run_force_disables_skip_completed(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """``--force`` → ``skip_completed=False``(重跑已完成 stage)。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "lec.mp4").write_bytes(b"")
  captured = _patch_runner(monkeypatch)

  result = runner.invoke(
    app, ["run", str(inbox), "--no-isolate", "--force"],
  )

  assert result.exit_code == 0
  assert captured[0]["skip_completed"] is False


def test_run_stop_after_passthrough(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """``--stop-after`` 透传给 run_pipeline。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "lec.mp4").write_bytes(b"")
  captured = _patch_runner(monkeypatch)

  result = _invoke( [
    "run", str(inbox), "--no-isolate", "--stop-after", "chapters",
  ])

  assert result.exit_code == 0
  assert captured[0]["stop_after"] == "chapters"


def test_run_no_media_returns_error(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """inbox 空(无媒体文件)→ exit code 2 + 友好提示。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  _patch_runner(monkeypatch)

  result = _invoke( ["run", str(inbox)])

  assert result.exit_code == 2
  assert "ERR" in result.stdout or "未找到" in result.stdout


def test_run_isolates_inbox_multivideo(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """inbox 多视频时隔离非目标文件;跑完后恢复。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  target = inbox / "target.mp4"
  other1 = inbox / "other1.mp4"
  other2 = inbox / "subdir" / "other2.mp4"
  other2.parent.mkdir()
  target.write_bytes(b"target")
  other1.write_bytes(b"o1")
  other2.write_bytes(b"o2")
  _patch_runner(monkeypatch)

  result = _invoke( ["run", str(inbox)])

  assert result.exit_code == 0
  # 跑完后隔离文件应恢复
  assert target.exists()
  assert other1.exists()
  assert other2.exists()
  # staging_dir 应清理
  excluded_dirs = list((inbox / "output").glob(".excluded-*"))
  assert excluded_dirs == [], f"staging_dir 未清理: {excluded_dirs}"


def test_run_json_output(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """``--json`` 输出可解析的 JSON(含 course / completed / failed 等字段)。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "lec.mp4").write_bytes(b"")
  _patch_runner(monkeypatch)

  result = _invoke( [
    "run", str(inbox), "--no-isolate", "--json",
  ])

  assert result.exit_code == 0, repr(result.stdout[:300])
  print("STDOUT[:200]:", repr(result.stdout[:200]))
  print("STDOUT[100:200]:", repr(result.stdout[100:200]))
  payload = json.loads(result.stdout)
  assert "course" in payload
  assert "completed" in payload
  assert "stages" in payload
  assert payload["is_success"] is True


def test_run_pipeline_exception_returns_error(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """run_pipeline 抛异常 → CLI exit code 1 + state.json 路径提示。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "lec.mp4").write_bytes(b"")

  def boom(*_a: object, **_kw: object) -> Any:
    raise RuntimeError("pipeline fail")

  monkeypatch.setattr(cli, "run_pipeline", boom)

  result = _invoke( ["run", str(inbox), "--no-isolate"])

  assert result.exit_code == 1
  assert "FAIL" in result.stdout or "RuntimeError" in result.stdout


# ─────────────────────────────────────────────────────────────
# mtd resume
# ─────────────────────────────────────────────────────────────


def _seed_state(work: Path, inbox: Path | None) -> None:
  """在 work 下放一份 state.json,记录 inbox_path(用于 resume 派生)。"""
  state = State.new(course=work.name or "test")
  if inbox is not None:
    state.inbox_path = str(inbox)
  state.mark("audio", "completed")
  state.save(work / "state.json")


def test_resume_uses_state_inbox_path(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """resume 不传 ``--inbox`` → 从 state.inbox_path 派生 inbox。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  work = tmp_path / "work"
  work.mkdir()
  _seed_state(work, inbox)
  captured = _patch_runner(monkeypatch)

  result = _invoke( ["resume", str(work)])

  assert result.exit_code == 0, result.stdout
  assert len(captured) == 1
  assert captured[0]["inbox"] == inbox.resolve()
  assert captured[0]["work"] == work.resolve()


def test_resume_inbox_override(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """``--inbox`` 覆盖 state.json 里记录的 inbox。"""
  inbox1 = tmp_path / "inbox1"
  inbox1.mkdir()
  inbox2 = tmp_path / "inbox2"
  inbox2.mkdir()
  work = tmp_path / "work"
  work.mkdir()
  _seed_state(work, inbox1)
  captured = _patch_runner(monkeypatch)

  result = _invoke( [
    "resume", str(work), "--inbox", str(inbox2),
  ])

  assert result.exit_code == 0
  assert captured[0]["inbox"] == inbox2.resolve()


def test_resume_no_state_json_returns_error(tmp_path: Path) -> None:
  """work 目录无 state.json → exit code 2 + 提示用 mtd run。"""
  work = tmp_path / "work"
  work.mkdir()

  result = _invoke( ["resume", str(work)])

  assert result.exit_code == 2
  assert "state.json" in result.stdout
  assert "mtd run" in result.stdout


def test_resume_force_flag(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """``--force`` → ``skip_completed=False``。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  work = tmp_path / "work"
  work.mkdir()
  _seed_state(work, inbox)
  captured = _patch_runner(monkeypatch)

  result = _invoke( ["resume", str(work), "--force"])

  assert result.exit_code == 0
  assert captured[0]["skip_completed"] is False


# ─────────────────────────────────────────────────────────────
# mtd status
# ─────────────────────────────────────────────────────────────


def test_status_reads_state_json(tmp_path: Path) -> None:
  """``mtd status`` 读 state.json 输出表格。"""
  work = tmp_path / "work"
  work.mkdir()
  state = State.new(course="demo")
  state.mark("audio", "completed")
  state.mark("asr", "failed", error="OOM")
  state.save(work / "state.json")

  result = _invoke( ["status", str(work)])

  assert result.exit_code == 0
  assert "audio" in result.stdout
  assert "asr" in result.stdout
  assert "completed" in result.stdout
  assert "failed" in result.stdout
  assert "OOM" in result.stdout


def test_status_no_state_returns_error(tmp_path: Path) -> None:
  """work 目录无 state.json → exit code 2。"""
  work = tmp_path / "work"
  work.mkdir()

  result = _invoke( ["status", str(work)])

  assert result.exit_code == 2


def test_status_json_output(tmp_path: Path) -> None:
  """``--json`` 输出可解析的 JSON。"""
  work = tmp_path / "work"
  work.mkdir()
  state = State.new(course="demo")
  state.mark("audio", "completed")
  state.save(work / "state.json")

  result = _invoke( ["status", str(work), "--json"])

  assert result.exit_code == 0
  payload = json.loads(result.stdout)
  assert payload["course"] == "demo"
  assert payload["stages"]["audio"]["status"] == "completed"


# ─────────────────────────────────────────────────────────────
# mtd list
# ─────────────────────────────────────────────────────────────


def test_list_scans_inbox(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """``mtd list`` 扫 inbox 列出所有子目录 + 媒体文件。"""
  ws = tmp_path / "ws"
  inbox = ws / "inbox"
  inbox.mkdir(parents=True)
  for name in ("course_a", "course_b"):
    d = inbox / name
    d.mkdir()
    (d / f"{name}.mp4").write_bytes(b"")
  (inbox / "course_a" / "extra.mp4").write_bytes(b"")

  monkeypatch.setattr(cli, "WORKSPACE_ROOT", ws)
  result = _invoke( ["list", "--workspace", str(ws)])

  assert result.exit_code == 0
  assert "course_a" in result.stdout
  assert "course_b" in result.stdout


def test_list_empty_inbox(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """inbox 空目录 → 友好提示,exit 0。"""
  ws = tmp_path / "ws"
  (ws / "inbox").mkdir(parents=True)
  monkeypatch.setattr(cli, "WORKSPACE_ROOT", ws)

  result = _invoke( ["list", "--workspace", str(ws)])

  assert result.exit_code == 0
  assert "inbox 空" in result.stdout


def test_list_json_output(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """``--json`` 输出可解析的 JSON 数组。"""
  ws = tmp_path / "ws"
  inbox = ws / "inbox"
  inbox.mkdir(parents=True)
  (inbox / "c1").mkdir()
  (inbox / "c1" / "v.mp4").write_bytes(b"")
  monkeypatch.setattr(cli, "WORKSPACE_ROOT", ws)

  result = _invoke( [
    "list", "--workspace", str(ws), "--json",
  ])

  assert result.exit_code == 0
  payload = json.loads(result.stdout)
  assert "courses" in payload
  assert payload["courses"][0]["name"] == "c1"
  assert payload["courses"][0]["media_count"] == 1


def test_list_missing_inbox(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """inbox 不存在 → 友好提示,exit 0。"""
  ws = tmp_path / "ws"
  ws.mkdir()
  monkeypatch.setattr(cli, "WORKSPACE_ROOT", ws)

  result = _invoke( ["list", "--workspace", str(ws)])

  assert result.exit_code == 0
  assert "inbox 不存在" in result.stdout
