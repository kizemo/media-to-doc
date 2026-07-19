"""LE L1 健康度 + LE L3 沉淀层的对外查询入口(W8 落地)。

封装 :mod:`media_to_doc.logger.learnings` 的内部函数,提供两个对外的查询接口:

- :func:`get_run_metrics` — 读单个 ``work_dir`` 的 :class:`PipelineRun` 元数据,
  含 11 stage 状态 + quality + llm_health + gatekeeper_passed
- :func:`list_runs` — 扫 ``workspace_root/work/`` 下所有 ``pipeline_run.json``,
  按 mtime 倒序返回每个 run 的摘要(course / finished_at / duration / gatekeeper_passed)

供:
- MCP ``get_run_metrics`` / ``list_runs`` 工具(W8 新增)
- CLI ``mtd health`` 命令(未来,Phase 8)
- UI Learnings 页(Phase 2)

参考:_research/LE_DESIGN.md §3.5 健康度度量 + §4 反模式。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..logger import (
  PipelineRun,
  assess_llm_health,
  escalate_recurring_errors,
)
from ..paths import WORKSPACE_ROOT
from ..state import State


def get_run_metrics(work_dir: str | Path) -> dict[str, Any]:
  """读单个 ``work_dir`` 的 LE 沉淀元数据。

  Parameters
  ----------
  work_dir : str | Path
    单个课程的工作目录(含 ``state.json`` 与 ``pipeline_run.json``)

  Returns
  -------
  dict
    含 ``course`` / ``inbox_path`` / ``started_at`` / ``finished_at`` /
    ``duration_seconds`` / ``gatekeeper_passed`` / ``stages`` (11 项) /
    ``quality`` / ``llm_health`` / ``escalated_pattern_keys``

  Raises
  ------
  FileNotFoundError
    ``state.json`` 或 ``pipeline_run.json`` 不存在
  """
  work = Path(work_dir).expanduser().resolve()
  state_path = work / "state.json"
  run_path = work / "pipeline_run.json"

  if not state_path.exists():
    raise FileNotFoundError(f"state.json 不存在: {state_path}")
  if not run_path.exists():
    raise FileNotFoundError(
      f"pipeline_run.json 不存在: {run_path}\n"
      f"(可能 pipeline 未跑完,或 LE L3 finalize 失败)"
    )

  # 调度状态(W4 state.json)
  state = State.load(state_path)
  # LE 沉淀(W8 pipeline_run.json)
  pipeline_run = PipelineRun.load(run_path)

  # 扫描当前 work 的 ERRORS.md 找已知 Pattern-Key
  errors_file = work / "ERRORS.md"
  pattern_keys: list[str] = []
  if errors_file.exists():
    import re as _re

    content = errors_file.read_text(encoding="utf-8")
    pattern_keys = _re.findall(r"\*\*Pattern-Key\*\*: `(.+?)`", content)

  return {
    "course": state.course,
    "inbox_path": state.inbox_path,
    "state": {
      "started_at": state.started_at,
      "updated_at": state.updated_at,
      "current_stage": state.current_stage,
      "is_complete": state.is_complete(),
      "stages": {
        name: {
          "status": ss.status,
          "started_at": ss.started_at,
          "finished_at": ss.finished_at,
          "error": ss.error,
        }
        for name, ss in state.stages.items()
      },
    },
    "pipeline_run": {
      "started_at": pipeline_run.started_at,
      "finished_at": pipeline_run.finished_at,
      "duration_seconds": round(pipeline_run.duration_seconds, 2),
      "gatekeeper_passed": pipeline_run.gatekeeper_passed,
      "quality": pipeline_run.quality,
      "llm_health": pipeline_run.llm_health,
      "stages": [
        {
          "stage": r.stage,
          "status": r.status,
          "duration_seconds": round(r.duration_seconds, 2),
          "error": r.error,
          "output_paths": r.output_paths,
        }
        for r in pipeline_run.stages
      ],
    },
    "errors": {
      "pattern_keys": pattern_keys,
      "count": len(pattern_keys),
      "file": str(errors_file) if errors_file.exists() else None,
    },
  }


def list_runs(
  workspace_root: str | Path | None = None,
  *,
  limit: int = 20,
) -> dict[str, Any]:
  """扫 workspace_root 下所有 run,按 mtime 倒序返回摘要。

  Parameters
  ----------
  workspace_root : str | Path | None
    workspace 根(默认全局 :data:`WORKSPACE_ROOT`)
  limit : int
    最多返回多少 run(默认 20)

  Returns
  -------
  dict
    含 ``workspace`` / ``total_runs`` / ``runs`` (list of dict, 每个含
    ``course`` / ``work_dir`` / ``started_at`` / ``finished_at`` /
    ``duration_seconds`` / ``gatekeeper_passed`` / ``stages_completed`` /
    ``stages_total`` / ``llm_failure_rate``)

  Notes
  -----
  - ``work_root`` = ``<workspace_root>/work``
  - 跳过无 ``state.json`` 或 ``pipeline_run.json`` 的目录(不完整 run)
  - 若无任何 run,返回 ``total_runs=0`` + 空列表
  """
  ws_root = (
    Path(workspace_root).expanduser().resolve()
    if workspace_root is not None
    else WORKSPACE_ROOT.resolve()
  )
  work_root = ws_root / "work"

  if not work_root.exists():
    return {
      "workspace": str(ws_root),
      "work_root": str(work_root),
      "total_runs": 0,
      "runs": [],
      "llm_health_global": {
        "total_runs": 0,
        "total_llm_calls": 0,
        "total_llm_failures": 0,
        "llm_failure_rate": 0.0,
        "providers": {},
        "recommendation": None,
      },
    }

  runs: list[dict[str, Any]] = []
  for run_file in sorted(
    work_root.rglob("pipeline_run.json"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
  )[:limit]:
    try:
      data = json.loads(run_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
      continue

    work_dir = run_file.parent
    # 同步读 state.json 拿 inbox_path 与 course
    state_path = work_dir / "state.json"
    course = data.get("course", work_dir.name)
    inbox_path: str | None = None
    if state_path.exists():
      try:
        state = State.load(state_path)
        course = state.course
        inbox_path = state.inbox_path
      except (json.JSONDecodeError, KeyError, OSError):
        pass

    quality = data.get("quality", {})
    llm_health_data = data.get("llm_health", {})
    total_calls = llm_health_data.get("total_calls", 0)
    total_failures = llm_health_data.get("total_failures", 0)
    llm_failure_rate = (
      (total_failures / total_calls) if total_calls else 0.0
    )

    runs.append({
      "course": course,
      "work_dir": str(work_dir),
      "inbox_path": inbox_path,
      "started_at": data.get("started_at"),
      "finished_at": data.get("finished_at"),
      "duration_seconds": round(data.get("duration_seconds", 0.0), 2),
      "gatekeeper_passed": data.get("gatekeeper_passed", False),
      "stages_completed": quality.get("completed", 0),
      "stages_failed": quality.get("failed", 0),
      "stages_total": quality.get("total_stages", 0),
      "llm_failure_rate": round(llm_failure_rate, 4),
    })

  # LLM 健康度(全局,跨 run)
  llm_global = assess_llm_health(work_root)

  return {
    "workspace": str(ws_root),
    "work_root": str(work_root),
    "total_runs": len(runs),
    "runs": runs,
    "llm_health_global": llm_global,
  }


def get_escalated_errors(
  workspace_root: str | Path | None = None,
  *,
  threshold: int = 3,
) -> dict[str, Any]:
  """手动触发 Pattern-Key 扫描与晋升(供 MCP / CLI 调试用)。

  Parameters
  ----------
  workspace_root : str | Path | None
    workspace 根(默认全局 :data:`WORKSPACE_ROOT`)
  threshold : int
    重复次数阈值(默认 3)

  Returns
  -------
  dict
    含 ``workspace`` / ``learnings_file`` / ``escalated`` (新晋升的 Pattern-Key 列表)
  """
  from ..paths import project_root as _project_root

  ws_root = (
    Path(workspace_root).expanduser().resolve()
    if workspace_root is not None
    else WORKSPACE_ROOT.resolve()
  )
  work_root = ws_root / "work"
  learnings_root = _project_root() / ".learnings"

  escalated = escalate_recurring_errors(
    work_root, learnings_root, threshold=threshold
  )

  return {
    "workspace": str(ws_root),
    "work_root": str(work_root),
    "learnings_file": str(learnings_root / "ERRORS.md"),
    "threshold": threshold,
    "escalated": escalated,
  }


__all__ = [
  "get_run_metrics",
  "list_runs",
  "get_escalated_errors",
]
