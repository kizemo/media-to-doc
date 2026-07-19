"""``media_to_doc.logger.pipeline_logger`` 单元测试(W8)。

覆盖:
- StageRecord / PipelineRun / GatekeeperResult 数据类序列化
- PipelineLogger 初始化(写 memory 表头 + 内存状态)
- ``append_stage`` 写 memory 行
- ``write_error`` 写 ERRORS.md + 提取 Pattern-Key
- ``finalize`` 写 pipeline_run.json + 末尾摘要
- ``timed_stage`` 上下文管理器(成功 / 失败 / metrics 写入)
- ``_extract_pattern_key`` 稳定性(同根因不同消息)
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import pytest

from media_to_doc.logger.pipeline_logger import (
  GatekeeperResult,
  PipelineLogger,
  PipelineRun,
  StageRecord,
  _extract_pattern_key,
  timed_stage,
)

# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


class TestDataClasses:
  def test_stage_record_is_dataclass(self) -> None:
    """StageRecord 是 dataclass,可直接用 ``dataclasses.asdict`` 序列化。"""
    from dataclasses import asdict

    rec = StageRecord(
      stage="asr",
      started_at="2026-07-19T10:00:00",
      finished_at="2026-07-19T10:01:00",
      duration_seconds=60.0,
      status="completed",
    )
    d = asdict(rec)
    assert d["stage"] == "asr"
    assert d["status"] == "completed"
    assert d["duration_seconds"] == 60.0
    assert d["error"] is None
    assert d["output_paths"] == []

  def test_pipeline_run_save_load_roundtrip(self, tmp_path: Path) -> None:
    """PipelineRun.save → load 字段一致。"""
    run = PipelineRun(
      course="test-course",
      started_at="2026-07-19T10:00:00",
      finished_at="2026-07-19T10:05:00",
      duration_seconds=300.0,
      stages=[
        StageRecord(
          stage="asr",
          started_at="2026-07-19T10:00:00",
          finished_at="2026-07-19T10:01:00",
          duration_seconds=60.0,
          status="completed",
        ),
      ],
      quality={"total_stages": 1, "completed": 1, "failed": 0, "skipped": 0},
      llm_health={"ollama": {"calls": 1, "failures": 0}},
      gatekeeper_passed=True,
    )
    target = tmp_path / "run.json"
    run.save(target)
    loaded = PipelineRun.load(target)
    assert loaded.course == "test-course"
    assert loaded.duration_seconds == 300.0
    assert loaded.gatekeeper_passed is True
    assert len(loaded.stages) == 1
    assert loaded.stages[0].stage == "asr"
    assert loaded.llm_health == {"ollama": {"calls": 1, "failures": 0}}

  def test_gatekeeper_result_bool(self) -> None:
    """GatekeeperResult.__bool__ 等价于 ok。"""
    ok_result = GatekeeperResult(ok=True, issues=[])
    fail_result = GatekeeperResult(ok=False, issues=["x"])
    assert bool(ok_result) is True
    assert bool(fail_result) is False

  def test_gatekeeper_result_default_fields(self) -> None:
    """GatekeeperResult 默认空 issues / passed / failed。"""
    r = GatekeeperResult(ok=True)
    assert r.issues == []
    assert r.checks_passed == []
    assert r.checks_failed == []


# ─────────────────────────────────────────────────────────────
# Pattern-Key 提取
# ─────────────────────────────────────────────────────────────


class TestExtractPatternKey:
  def test_connection_error_same_root(self) -> None:
    """同根因的 ConnectionError(IP 不同)提取相同 Pattern-Key。"""
    exc1 = ConnectionError("Ollama 11434 unreachable")
    exc2 = ConnectionError("Ollama timeout 30s")
    assert _extract_pattern_key(exc1) == _extract_pattern_key(exc2)
    assert _extract_pattern_key(exc1).startswith("Connection:")

  def test_different_exception_types(self) -> None:
    """不同异常类型 → 不同 ShortType 前缀。"""
    a = _extract_pattern_key(ValueError("template missing"))
    b = _extract_pattern_key(FileNotFoundError("image missing"))
    assert a.startswith("Value:")
    assert b.startswith("FileNotFound:")
    assert a != b

  def test_empty_message_returns_unknown(self) -> None:
    """消息为空 → 关键词 unknown。"""
    exc = ValueError("")
    key = _extract_pattern_key(exc)
    assert key == "Value:unknown"

  def test_removes_error_suffix(self) -> None:
    """异常类型去掉 Error 后缀(短 4 字符)→ Connection 而非 ConnectionError。"""
    exc = ConnectionError("msg")
    assert _extract_pattern_key(exc).startswith("Connection:")

  def test_special_chars_stripped(self) -> None:
    """关键词非字母数字字符被剥除。"""
    exc = ValueError("!!! 异常 !!!")
    key = _extract_pattern_key(exc)
    # 关键词 "!!!" 经 lower + 剥非字母数字 → 空 → "unknown"
    assert key.endswith(":unknown")


# ─────────────────────────────────────────────────────────────
# PipelineLogger 初始化 + append_stage
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def work_dir(tmp_path: Path) -> Path:
  """临时 work 目录。"""
  work = tmp_path / "work"
  work.mkdir()
  return work


class TestPipelineLoggerInit:
  def test_init_creates_memory_file_with_header(
    self, work_dir: Path,
  ) -> None:
    """初始化时创建 memory/YYYY-MM-DD.md,带 markdown 表头。"""
    PipelineLogger(work_dir, course="test-course")
    memory_file = work_dir / "memory" / f"{datetime.now():%Y-%m-%d}.md"
    assert memory_file.exists()
    content = memory_file.read_text(encoding="utf-8")
    assert "# Memory" in content
    assert "test-course" in content
    assert "| Stage | Started |" in content

  def test_init_idempotent_no_overwrite(
    self, work_dir: Path,
  ) -> None:
    """重复初始化不会覆盖已有 memory 文件。"""
    PipelineLogger(work_dir, course="test")
    memory_file = work_dir / "memory" / f"{datetime.now():%Y-%m-%d}.md"
    original = memory_file.read_text(encoding="utf-8")

    PipelineLogger(work_dir, course="test")
    again = memory_file.read_text(encoding="utf-8")
    assert original == again  # 没被覆盖

  def test_stages_initialized_empty(
    self, work_dir: Path,
  ) -> None:
    """初始化时 _stages 为空列表。"""
    logger = PipelineLogger(work_dir, course="test")
    assert logger._stages == []

  def test_creates_memory_subdirectory(
    self, work_dir: Path,
  ) -> None:
    """初始化时创建 memory/ 子目录(若不存在)。"""
    assert not (work_dir / "memory").exists()
    PipelineLogger(work_dir, course="test")
    assert (work_dir / "memory").is_dir()


class TestAppendStage:
  def test_append_writes_memory_row(
    self, work_dir: Path,
  ) -> None:
    """append_stage 追加一行到 memory 文件(含 stage / 时间 / 状态)。"""
    logger = PipelineLogger(work_dir, course="test")
    record = StageRecord(
      stage="asr",
      started_at="2026-07-19T10:00:00",
      finished_at="2026-07-19T10:01:00",
      duration_seconds=60.0,
      status="completed",
      output_paths=["work/asr/transcript.jsonl"],
    )
    logger.append_stage(record)
    memory_file = work_dir / "memory" / f"{datetime.now():%Y-%m-%d}.md"
    content = memory_file.read_text(encoding="utf-8")
    assert "| asr |" in content
    assert "completed" in content
    assert "transcript.jsonl" in content

  def test_append_appends_not_overwrites(
    self, work_dir: Path,
  ) -> None:
    """多次 append → 行数累加(不会覆盖)。"""
    logger = PipelineLogger(work_dir, course="test")
    for stage in ("audio", "asr", "frames"):
      logger.append_stage(StageRecord(
        stage=stage,
        started_at="2026-07-19T10:00:00",
        finished_at="2026-07-19T10:00:01",
        duration_seconds=1.0,
        status="completed",
      ))
    memory_file = work_dir / "memory" / f"{datetime.now():%Y-%m-%d}.md"
    content = memory_file.read_text(encoding="utf-8")
    # 3 行 stage + 1 行表头分隔 + 1 行末尾摘要(无)— 至少 4 行 stage
    rows = [line for line in content.split("\n") if line.startswith("| ") and "audio" in line or "asr" in line or "frames" in line]
    assert len(rows) == 3

  def test_append_records_in_memory_list(
    self, work_dir: Path,
  ) -> None:
    """append_stage 同时把 record 加到 _stages(为 finalize 准备)。"""
    logger = PipelineLogger(work_dir, course="test")
    rec = StageRecord(
      stage="asr",
      started_at="2026-07-19T10:00:00",
      finished_at=None,
      duration_seconds=0.0,
      status="running",
    )
    logger.append_stage(rec)
    assert len(logger._stages) == 1
    assert logger._stages[0] is rec


# ─────────────────────────────────────────────────────────────
# write_error → ERRORS.md + Pattern-Key
# ─────────────────────────────────────────────────────────────


class TestWriteError:
  def test_write_error_returns_pattern_key(
    self, work_dir: Path,
  ) -> None:
    """write_error 返回 Pattern-Key(以异常类型 + 关键词)。"""
    logger = PipelineLogger(work_dir, course="test")
    try:
      raise ConnectionError("Ollama 11434 unreachable")
    except ConnectionError as exc:
      pattern_key = logger.write_error("chapters", exc)
    assert pattern_key.startswith("Connection:")

  def test_write_error_creates_errors_file(
    self, work_dir: Path,
  ) -> None:
    """write_error 写入 ERRORS.md(含 type / message / traceback / pattern_key)。"""
    logger = PipelineLogger(work_dir, course="test")
    try:
      raise ValueError("template missing")
    except ValueError as exc:
      logger.write_error("draft", exc)
    errors_file = work_dir / "ERRORS.md"
    assert errors_file.exists()
    content = errors_file.read_text(encoding="utf-8")
    assert "ValueError" in content
    assert "template missing" in content
    assert "Pattern-Key" in content

  def test_write_error_truncates_traceback(
    self, work_dir: Path,
  ) -> None:
    """write_error 把 traceback 截到 2000 字符(避免 ERRORS.md 无限膨胀)。"""
    logger = PipelineLogger(work_dir, course="test")
    # 让 RuntimeError 触发的栈深度足够大,但 message 短(便于测 traceback)
    def deep_call(n: int) -> None:
      if n > 0:
        deep_call(n - 1)
      else:
        raise RuntimeError("simulated")
    try:
      deep_call(50)
    except RuntimeError as exc:
      logger.write_error("render", exc)
    content = (work_dir / "ERRORS.md").read_text(encoding="utf-8")
    # 总 entry 长度(模板约 200 字节 + traceback ≤ 2000 字节)应 < 3000
    assert len(content) < 3500, f"ERRORS.md 异常长 ({len(content)} chars)"


# ─────────────────────────────────────────────────────────────
# timed_stage 上下文管理器
# ─────────────────────────────────────────────────────────────


class TestTimedStage:
  def test_success_marks_completed(
    self, work_dir: Path,
  ) -> None:
    """正常退出 → record.status = completed,append_stage 写 memory。"""
    logger = PipelineLogger(work_dir, course="test")
    with timed_stage(logger, "asr") as ctx:
      time.sleep(0.01)
      ctx.output_paths.append("output.json")
    assert ctx.status == "completed"
    assert ctx.duration_seconds >= 0.01
    assert "output.json" in ctx.output_paths
    assert len(logger._stages) == 1

  def test_failure_marks_failed_and_writes_error(
    self, work_dir: Path,
  ) -> None:
    """异常退出 → record.status = failed + write_error → ERRORS.md + 异常上抛。"""
    logger = PipelineLogger(work_dir, course="test")
    with pytest.raises(ValueError, match="boom"), timed_stage(logger, "draft"):
      raise ValueError("boom")
    assert (work_dir / "ERRORS.md").exists()
    assert len(logger._stages) == 1
    assert logger._stages[0].status == "failed"

  def test_exception_propagates(
    self, work_dir: Path,
  ) -> None:
    """异常会重新抛出(不吞)。"""
    logger = PipelineLogger(work_dir, course="test")
    with pytest.raises(RuntimeError, match="explicit"), timed_stage(logger, "render"):
      raise RuntimeError("explicit")

  def test_metrics_recorded(
    self, work_dir: Path,
  ) -> None:
    """stage 内部写 ctx.metrics → finalize 后保留在 StageRecord。"""
    logger = PipelineLogger(work_dir, course="test")
    with timed_stage(logger, "asr") as ctx:
      ctx.metrics["chunks"] = 42
      ctx.metrics["tokens"] = 1234
    assert logger._stages[0].metrics == {"chunks": 42, "tokens": 1234}


# ─────────────────────────────────────────────────────────────
# finalize → pipeline_run.json
# ─────────────────────────────────────────────────────────────


class TestFinalize:
  def test_finalize_writes_run_json(
    self, work_dir: Path,
  ) -> None:
    """finalize 写 pipeline_run.json + 末尾摘要到 memory。"""
    logger = PipelineLogger(work_dir, course="test")
    with timed_stage(logger, "asr") as ctx:
      ctx.output_paths.append("output.json")
    logger.finalize()
    run_file = work_dir / "pipeline_run.json"
    assert run_file.exists()
    data = json.loads(run_file.read_text(encoding="utf-8"))
    assert data["course"] == "test"
    assert data["quality"]["completed"] == 1
    assert data["quality"]["failed"] == 0
    assert len(data["stages"]) == 1

  def test_finalize_computes_quality(
    self, work_dir: Path,
  ) -> None:
    """finalize 聚合 quality:total / completed / failed / skipped。"""
    logger = PipelineLogger(work_dir, course="test")
    with timed_stage(logger, "audio"):
      pass
    with timed_stage(logger, "asr"):
      pass
    try:
      with timed_stage(logger, "frames"):
        raise RuntimeError("simulated")
    except RuntimeError:
      pass
    run = logger.finalize()
    assert run.quality["total_stages"] == 3
    assert run.quality["completed"] == 2
    assert run.quality["failed"] == 1
    assert run.quality["skipped"] == 0

  def test_finalize_includes_gatekeeper_result(
    self, work_dir: Path,
  ) -> None:
    """finalize 接收 GatekeeperResult → run.gatekeeper_passed 反映 ok 状态。"""
    logger = PipelineLogger(work_dir, course="test")
    with timed_stage(logger, "asr"):
      pass
    ok_gate = GatekeeperResult(ok=True)
    fail_gate = GatekeeperResult(ok=False, issues=["x"])

    run_pass = logger.finalize(gatekeeper_result=ok_gate)
    assert run_pass.gatekeeper_passed is True

    # 重新创建 logger(同一个 work_dir,避免 _stages 累积)
    logger2 = PipelineLogger(work_dir, course="test")
    with timed_stage(logger2, "asr"):
      pass
    run_fail = logger2.finalize(gatekeeper_result=fail_gate)
    assert run_fail.gatekeeper_passed is False

  def test_finalize_includes_llm_health(
    self, work_dir: Path,
  ) -> None:
    """finalize 接收 llm_health dict → 写入 pipeline_run.json。"""
    logger = PipelineLogger(work_dir, course="test")
    with timed_stage(logger, "chapters"):
      pass
    llm = {"ollama": {"calls": 5, "failures": 1}}
    run = logger.finalize(llm_health=llm)
    assert run.llm_health == llm

  def test_finalize_appends_summary_to_memory(
    self, work_dir: Path,
  ) -> None:
    """finalize 在 memory 末尾追加 Run finished / duration / gatekeeper 行。"""
    logger = PipelineLogger(work_dir, course="test")
    with timed_stage(logger, "asr"):
      pass
    logger.finalize()
    memory_file = work_dir / "memory" / f"{datetime.now():%Y-%m-%d}.md"
    content = memory_file.read_text(encoding="utf-8")
    assert "Run finished" in content
    assert "Total duration" in content
    assert "Gatekeeper" in content
