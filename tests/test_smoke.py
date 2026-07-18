"""Phase 0 smoke test — 验证包导入与 CLI 基础可用。

Phase 1 起,各模块配套独立测试文件,本文件仅保留"项目能跑通"的最少检查。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from media_to_doc import __version__, cli
from media_to_doc.config import WorkflowConfig
from media_to_doc.paths import (
  CONFIG_FILE,
  INBOX_DIR,
  WORK_DIR,
  WORKSPACE_ROOT,
)
from media_to_doc.state import STAGE_ORDER, State

# ─────────────────────────────────────────────────────────────
# 包元信息
# ─────────────────────────────────────────────────────────────


def test_version_is_0_1_0() -> None:
  """首版本号必须是 0.1.0。"""
  assert __version__ == "0.1.0"


def test_stage_order_has_11_stages() -> None:
  """11 阶段流水线顺序必须稳定。"""
  assert len(STAGE_ORDER) == 11
  assert STAGE_ORDER[0] == "audio"
  assert STAGE_ORDER[-1] == "verify"
  # 关键中间 stage
  for stage in ["asr", "chapters", "draft", "render", "longdoc"]:
    assert stage in STAGE_ORDER


# ─────────────────────────────────────────────────────────────
# 路径常量
# ─────────────────────────────────────────────────────────────


def test_paths_resolve() -> None:
  """路径常量必须可解析(不强制存在,但必须是 Path 对象)。"""
  assert isinstance(WORKSPACE_ROOT, Path)
  assert isinstance(INBOX_DIR, Path)
  assert isinstance(WORK_DIR, Path)
  assert isinstance(CONFIG_FILE, Path)
  assert INBOX_DIR.parent == WORKSPACE_ROOT
  assert WORK_DIR.parent == WORKSPACE_ROOT


# ─────────────────────────────────────────────────────────────
# WorkflowConfig
# ─────────────────────────────────────────────────────────────


def test_default_workflow_config() -> None:
  """默认配置必须可用,字段类型正确。"""
  cfg = WorkflowConfig()
  assert cfg.llm.provider == "ollama"
  assert cfg.llm.model == "qwen3:14b"
  assert cfg.imagegen.provider == "local_sdxl"
  assert cfg.log_level == "INFO"


def test_workflow_config_yaml_roundtrip(tmp_path: Path) -> None:
  """YAML 序列化往返不丢失字段。"""
  cfg = WorkflowConfig()
  cfg.llm.temperature = 0.7
  cfg.imagegen.provider = "skip"
  target = tmp_path / "config.yaml"
  cfg.save(target)

  loaded = WorkflowConfig.load(target)
  assert loaded.llm.temperature == 0.7
  assert loaded.imagegen.provider == "skip"


# ─────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────


def test_state_new_initializes_all_stages() -> None:
  """新 State 必须包含全部 11 个 stage,初始 pending。"""
  state = State.new(course="test-course")
  assert state.course == "test-course"
  assert len(state.stages) == 11
  for stage_state in state.stages.values():
    assert stage_state.status == "pending"


def test_state_mark_running_then_completed() -> None:
  """mark() 必须正确推进状态。"""
  state = State.new(course="test")
  state.mark("audio", "running")
  assert state.stages["audio"].status == "running"
  assert state.current_stage == "audio"

  state.mark("audio", "completed")
  assert state.stages["audio"].status == "completed"
  # 完成后 current_stage 推进到下一个 pending
  assert state.current_stage == "asr"


def test_state_save_and_load_roundtrip(tmp_path: Path) -> None:
  """State JSON 持久化往返一致。"""
  state = State.new(course="test")
  state.mark("audio", "completed")
  target = tmp_path / "state.json"
  state.save(target)
  loaded = State.load(target)
  assert loaded.course == "test"
  assert loaded.stages["audio"].status == "completed"


def test_state_next_stage_skips_completed() -> None:
  """next_stage() 必须跳过已完成的 stage。"""
  state = State.new(course="test")
  state.mark("audio", "completed")
  assert state.next_stage() == "asr"
  state.mark("asr", "completed")
  assert state.next_stage() == "frames"


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────


runner = CliRunner()


def test_cli_version() -> None:
  """``mtd version`` 输出 0.1.0。"""
  result = runner.invoke(cli.app, ["version"])
  assert result.exit_code == 0
  assert "0.1.0" in result.stdout


def test_cli_help() -> None:
  """``mtd --help`` 显示命令帮助。"""
  result = runner.invoke(cli.app, ["--help"])
  assert result.exit_code == 0
  assert "media-to-doc" in result.stdout.lower() or "讲义" in result.stdout


def test_cli_paths() -> None:
  """``mtd paths`` 输出关键路径。"""
  result = runner.invoke(cli.app, ["paths"])
  assert result.exit_code == 0
  assert "workspace" in result.stdout.lower()


def test_cli_run_not_implemented(tmp_path: Path) -> None:
  """``mtd run`` 尚未实装(Phase 1),必须返回非零退出码。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  result = runner.invoke(cli.app, ["run", str(inbox)])
  assert result.exit_code == 1
  assert "尚未实装" in result.stdout or "Phase 1" in result.stdout


# ─────────────────────────────────────────────────────────────
# 端到端 CLI 调用(uv run mtd --version)
# ─────────────────────────────────────────────────────────────


def test_uv_run_mtd_version() -> None:
  """完整端到端:通过 subprocess 调 ``mtd --version``。"""
  if sys.platform.startswith("win"):
    cmd = ["uv", "run", "mtd", "--version"]
  else:
    cmd = ["uv", "run", "mtd", "--version"]

  repo_root = Path(__file__).resolve().parent.parent
  result = subprocess.run(
    cmd,
    cwd=repo_root,
    capture_output=True,
    text=True,
    timeout=60,
  )
  assert result.returncode == 0, f"stdout={result.stdout} stderr={result.stderr}"
  assert "0.1.0" in result.stdout
