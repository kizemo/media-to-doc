"""LE L1 核心模块 — PipelineLogger(W8 落地)。

LE 沉淀层 + 执行层核心:
- 即时记忆:`<work>/memory/YYYY-MM-DD.md`(每 stage 一行)
- 运行时错误:`<work>/ERRORS.md`(完整 traceback + Pattern-Key)
- 末尾元数据:`<work>/pipeline_run.json`(全 stage 聚合 + quality + llm_health)

上下文管理器 :func:`timed_stage` 是 L1 执行层核心,
自动捕获 stage 耗时 / 异常 / 上下文。

参考:
- ``_research/LE_DESIGN.md`` §3.1
- ``_research/le_prototype/pipeline_logger.py``(原型,23 测试)
"""

from __future__ import annotations

import json
import re
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────


@dataclass
class StageRecord:
  """单个 stage 的执行记录。"""

  stage: str
  started_at: str  # ISO 格式
  finished_at: str | None
  duration_seconds: float
  status: str  # running | completed | failed | skipped
  error: str | None = None
  output_paths: list[str] = field(default_factory=list)
  metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineRun:
  """一次完整 pipeline run 的元数据。"""

  course: str
  started_at: str
  finished_at: str | None
  duration_seconds: float
  stages: list[StageRecord]
  quality: dict[str, Any] = field(default_factory=dict)
  llm_health: dict[str, Any] = field(default_factory=dict)
  gatekeeper_passed: bool = False

  def to_dict(self) -> dict[str, Any]:
    return asdict(self)

  def save(self, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
      json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
      encoding="utf-8",
    )

  @classmethod
  def load(cls, path: Path) -> PipelineRun:
    data = json.loads(path.read_text(encoding="utf-8"))
    stages = [StageRecord(**s) for s in data.pop("stages", [])]
    return cls(stages=stages, **data)


@dataclass
class GatekeeperResult:
  """LE L2 审核层产出。"""

  ok: bool
  issues: list[str] = field(default_factory=list)
  checks_passed: list[str] = field(default_factory=list)
  checks_failed: list[str] = field(default_factory=list)

  def __bool__(self) -> bool:
    return self.ok


# ─────────────────────────────────────────────────────────────
# PipelineLogger
# ─────────────────────────────────────────────────────────────


class PipelineLogger:
  """LE 沉淀层主入口。

  负责:
  - 即时记忆:`<work>/memory/YYYY-MM-DD.md`(每 stage 一行)
  - 运行时错误:`<work>/ERRORS.md`(完整 traceback + Pattern-Key)
  - 末尾元数据:`<work>/pipeline_run.json`(全 stage 聚合)
  """

  def __init__(self, work_dir: Path, course: str) -> None:
    self.work_dir = work_dir
    self.course = course
    self.memory_dir = work_dir / "memory"
    self.memory_dir.mkdir(parents=True, exist_ok=True)
    self.run_file = work_dir / "pipeline_run.json"
    self.errors_file = work_dir / "ERRORS.md"
    self._stages: list[StageRecord] = []
    self._start = datetime.now()
    self._today = self._start.strftime("%Y-%m-%d")
    self._memory_file = self.memory_dir / f"{self._today}.md"
    self._init_memory_file()

  # ─── 即时记忆 ─────────────────────────────────────

  def _init_memory_file(self) -> None:
    """初始化今日 memory 文件,带 markdown 表头。"""
    if not self._memory_file.exists():
      self._memory_file.write_text(
        f"# Memory {self._today} — {self.course}\n\n"
        "| Stage | Started | Duration | Status | Output | Notes |\n"
        "|---|---|---|---|---|---|\n",
        encoding="utf-8",
      )

  def append_stage(self, record: StageRecord) -> None:
    """LE 即时记忆:每 stage 追加一行到 memory 文件。"""
    self._stages.append(record)
    row = (
      f"| {record.stage} "
      f"| {record.started_at[11:19]} "  # HH:MM:SS
      f"| {record.duration_seconds:.1f}s "
      f"| {record.status} "
      f"| {','.join(Path(p).name for p in record.output_paths)} "
      f"| {(record.error or '').replace(chr(10), ' ')[:80]} |\n"
    )
    with self._memory_file.open("a", encoding="utf-8") as f:
      f.write(row)

  # ─── 运行时错误 ───────────────────────────────────

  def write_error(self, stage: str, exc: BaseException) -> str:
    """运行时错误 → ERRORS.md。Returns:Pattern-Key(供跨 run 聚合)。"""
    pattern_key = _extract_pattern_key(exc)
    ts = datetime.now().isoformat(timespec="seconds")
    tb = "".join(
      traceback.format_exception(type(exc), exc, exc.__traceback__)
    )[:2000]
    entry = (
      f"\n## [{ts}] {stage} — {pattern_key}\n\n"
      f"**Type**: `{type(exc).__name__}`\n"
      f"**Message**: {exc}\n"
      f"**Traceback**:\n```\n{tb}\n```\n"
      f"**Pattern-Key**: `{pattern_key}`\n"
    )
    self.errors_file.parent.mkdir(parents=True, exist_ok=True)
    with self.errors_file.open("a", encoding="utf-8") as f:
      f.write(entry)
    return pattern_key

  # ─── 末尾元数据 ───────────────────────────────────

  def finalize(
    self,
    gatekeeper_result: GatekeeperResult | None = None,
    llm_health: dict[str, Any] | None = None,
  ) -> PipelineRun:
    """写 pipeline_run.json + 末尾摘要。"""
    run = PipelineRun(
      course=self.course,
      started_at=self._start.isoformat(timespec="seconds"),
      finished_at=datetime.now().isoformat(timespec="seconds"),
      duration_seconds=(datetime.now() - self._start).total_seconds(),
      stages=self._stages,
      quality=self._compute_quality(),
      llm_health=llm_health or {},
      gatekeeper_passed=bool(gatekeeper_result and gatekeeper_result.ok),
    )
    run.save(self.run_file)

    summary = (
      f"\n---\n\n"
      f"**Run finished**: {run.finished_at}\n"
      f"**Total duration**: {run.duration_seconds:.1f}s\n"
      f"**Stages**: {run.quality['completed']}/{run.quality['total_stages']} "
      f"completed, {run.quality['failed']} failed\n"
      f"**Gatekeeper**: {'PASS' if run.gatekeeper_passed else 'FAIL'}\n"
    )
    with self._memory_file.open("a", encoding="utf-8") as f:
      f.write(summary)
    return run

  # ─── 内部辅助 ─────────────────────────────────────

  def _compute_quality(self) -> dict[str, Any]:
    """聚合指标。"""
    total = len(self._stages)
    completed = sum(1 for s in self._stages if s.status == "completed")
    failed = sum(1 for s in self._stages if s.status == "failed")
    skipped = sum(1 for s in self._stages if s.status == "skipped")
    return {
      "total_stages": total,
      "completed": completed,
      "failed": failed,
      "skipped": skipped,
      "completion_rate": (completed / total) if total else 0.0,
      "total_duration_seconds": sum(s.duration_seconds for s in self._stages),
    }


# ─────────────────────────────────────────────────────────────
# timed_stage 上下文管理器(L1 执行层核心)
# ─────────────────────────────────────────────────────────────


@contextmanager
def timed_stage(logger: PipelineLogger, stage: str) -> Iterator[StageRecord]:
  """LE L1 执行层核心:自动捕获 stage 耗时 / 异常 / 上下文。

  用法::

      logger = PipelineLogger(work, course)
      with timed_stage(logger, "asr") as ctx:
          transcribe(work, cfg)
          ctx.output_paths.append(str(work / "asr/transcript.jsonl"))
          ctx.metrics["tokens"] = 1234

  行为:
  - 正常退出 → ``record.status = "completed"``
  - 异常退出 → ``record.status = "failed"`` + ``logger.write_error`` + 异常上抛
  - 退出时(无论成功失败)→ ``logger.append_stage`` 写 memory 行
  """
  started = datetime.now()
  record = StageRecord(
    stage=stage,
    started_at=started.isoformat(timespec="seconds"),
    finished_at=None,
    duration_seconds=0.0,
    status="running",
  )
  try:
    yield record
    if record.status == "running":
      record.status = "completed"
  except Exception as exc:
    record.status = "failed"
    record.error = f"{type(exc).__name__}: {exc}"
    logger.write_error(stage, exc)
    raise
  finally:
    finished = datetime.now()
    record.finished_at = finished.isoformat(timespec="seconds")
    record.duration_seconds = (finished - started).total_seconds()
    logger.append_stage(record)


# ─────────────────────────────────────────────────────────────
# Pattern-Key 提取(供 logger 与 learnings 共享)
# ─────────────────────────────────────────────────────────────


def _extract_pattern_key(exc: BaseException) -> str:
  """从异常提取稳定的 Pattern-Key(供跨任务聚合)。

  规则:
  - 异常类型名(去掉 ``Error`` 后缀,如 ``ConnectionRefused``)
  - 消息第一个关键词(首个非空 token,截 30 字符)
  - 例:``ConnectionRefused:ollama`` / ``OutOfMemory:whisper``

  为什么不用整个消息:
  - 同一根因的异常消息经常不同(IP、端口、超时值)
  - 关键词能稳定反映根因
  """
  exc_type = type(exc).__name__
  short_type = exc_type.removesuffix("Error")
  msg_tokens = str(exc).split()
  keyword = msg_tokens[0].lower()[:30] if msg_tokens else "unknown"
  keyword = re.sub(r"[^a-z0-9_]", "", keyword) or "unknown"
  return f"{short_type}:{keyword}"


__all__ = [
  "StageRecord",
  "PipelineRun",
  "GatekeeperResult",
  "PipelineLogger",
  "timed_stage",
  "_extract_pattern_key",
]
