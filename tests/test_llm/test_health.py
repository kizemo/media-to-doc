"""``media_to_doc.llm.health`` 单元测试(W8)。

覆盖:
- ``get_run_metrics`` 读 state.json + pipeline_run.json + ERRORS.md
- ``list_runs`` 扫 workspace_root 下所有 run,按 mtime 倒序
- ``get_escalated_errors`` 手动触发 Pattern-Key 扫描
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from media_to_doc.llm.health import (
  get_escalated_errors,
  get_run_metrics,
  list_runs,
)

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
  """临时 workspace 根(含 work/ 子目录)。"""
  ws = tmp_path / "workspace"
  (ws / "work").mkdir(parents=True)
  return ws


def _make_run(
  work_dir: Path,
  *,
  course: str,
  finished_at: str,
  gatekeeper_passed: bool = True,
  llm_health: dict[str, dict[str, int]] | None = None,
  stages: list[dict[str, object]] | None = None,
  inbox_path: str | None = None,
) -> None:
  """创建合规的 state.json + pipeline_run.json + ERRORS.md。"""
  work_dir.mkdir(parents=True, exist_ok=True)
  # state.json
  state = {
    "course": course,
    "started_at": "2026-07-19T10:00:00",
    "updated_at": finished_at,
    "current_stage": None,
    "inbox_path": inbox_path,
    "stages": stages or {
      stage: {"name": stage, "status": "completed"} for stage in (
        "audio", "asr", "frames", "ocr", "asr_correct",
        "chapters", "draft", "imagegen", "render", "longdoc", "verify",
      )
    },
  }
  (work_dir / "state.json").write_text(
    json.dumps(state), encoding="utf-8",
  )
  # pipeline_run.json
  run = {
    "course": course,
    "started_at": "2026-07-19T10:00:00",
    "finished_at": finished_at,
    "duration_seconds": 120.0,
    "stages": [],
    "quality": {
      "total_stages": 11, "completed": 11, "failed": 0, "skipped": 0,
      "completion_rate": 1.0, "total_duration_seconds": 120.0,
    },
    "llm_health": llm_health or {},
    "gatekeeper_passed": gatekeeper_passed,
  }
  (work_dir / "pipeline_run.json").write_text(
    json.dumps(run), encoding="utf-8",
  )


# ─────────────────────────────────────────────────────────────
# get_run_metrics
# ─────────────────────────────────────────────────────────────


class TestGetRunMetrics:
  def test_missing_state_json(self, tmp_path: Path) -> None:
    """state.json 不存在 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError, match="state.json"):
      get_run_metrics(tmp_path)

  def test_missing_pipeline_run_json(self, tmp_path: Path) -> None:
    """pipeline_run.json 不存在 → FileNotFoundError。"""
    (tmp_path / "state.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="pipeline_run.json"):
      get_run_metrics(tmp_path)

  def test_returns_combined_metrics(self, tmp_path: Path) -> None:
    """返回 state + pipeline_run + errors 综合元数据。"""
    work_dir = tmp_path / "work"
    _make_run(work_dir, course="course1", finished_at="2026-07-19T10:02:00")

    metrics = get_run_metrics(work_dir)

    assert metrics["course"] == "course1"
    assert "state" in metrics
    assert metrics["state"]["is_complete"] is True
    assert "pipeline_run" in metrics
    assert metrics["pipeline_run"]["gatekeeper_passed"] is True
    assert metrics["pipeline_run"]["quality"]["completed"] == 11
    assert "errors" in metrics
    assert metrics["errors"]["count"] == 0

  def test_includes_errors_pattern_keys(self, tmp_path: Path) -> None:
    """ERRORS.md 存在时,errors.pattern_keys 提取 Pattern-Key。"""
    work_dir = tmp_path / "work"
    _make_run(work_dir, course="c", finished_at="2026-07-19T10:02:00")
    (work_dir / "ERRORS.md").write_text(
      "## [2026-07-19T10:01:00] chapters — Connection:ollama\n\n"
      "**Pattern-Key**: `Connection:ollama`\n\n"
      "## [2026-07-19T10:01:30] draft — Value:template\n\n"
      "**Pattern-Key**: `Value:template`\n",
      encoding="utf-8",
    )
    metrics = get_run_metrics(work_dir)
    assert "Connection:ollama" in metrics["errors"]["pattern_keys"]
    assert "Value:template" in metrics["errors"]["pattern_keys"]
    assert metrics["errors"]["count"] == 2

  def test_includes_inbox_path(self, tmp_path: Path) -> None:
    """inbox_path 从 state.json 读取。"""
    work_dir = tmp_path / "work"
    _make_run(
      work_dir, course="c", finished_at="2026-07-19T10:02:00",
      inbox_path="D:/inbox/c",
    )
    metrics = get_run_metrics(work_dir)
    assert metrics["inbox_path"] == "D:/inbox/c"

  def test_quality_failed_aggregated(self, tmp_path: Path) -> None:
    """quality 含 failed 数。"""
    work_dir = tmp_path / "work"
    _make_run(work_dir, course="c", finished_at="2026-07-19T10:02:00")
    # 改 pipeline_run.json 的 quality
    run_path = work_dir / "pipeline_run.json"
    data = json.loads(run_path.read_text(encoding="utf-8"))
    data["quality"]["failed"] = 3
    data["gatekeeper_passed"] = False
    run_path.write_text(json.dumps(data), encoding="utf-8")
    metrics = get_run_metrics(work_dir)
    assert metrics["pipeline_run"]["quality"]["failed"] == 3
    assert metrics["pipeline_run"]["gatekeeper_passed"] is False


# ─────────────────────────────────────────────────────────────
# list_runs
# ─────────────────────────────────────────────────────────────


class TestListRuns:
  def test_no_workspace_returns_empty(self, tmp_path: Path) -> None:
    """work 目录不存在 → total_runs=0。"""
    ws = tmp_path / "empty_workspace"
    result = list_runs(ws)
    assert result["total_runs"] == 0
    assert result["runs"] == []
    assert result["workspace"] == str(ws)

  def test_no_runs_returns_empty(self, workspace_root: Path) -> None:
    """work/ 存在但无 run → total_runs=0。"""
    result = list_runs(workspace_root)
    assert result["total_runs"] == 0
    assert result["runs"] == []

  def test_lists_runs_sorted_by_mtime(self, workspace_root: Path) -> None:
    """按 mtime 倒序返回每个 run 的摘要。"""
    work_root = workspace_root / "work"
    # 旧 run
    old_dir = work_root / "course-old"
    _make_run(old_dir, course="course-old", finished_at="2026-07-18T10:00:00")
    # 新 run
    new_dir = work_root / "course-new"
    _make_run(new_dir, course="course-new", finished_at="2026-07-19T10:00:00")

    result = list_runs(workspace_root)

    assert result["total_runs"] == 2
    assert len(result["runs"]) == 2
    # 第一个应是最新(course-new)
    assert result["runs"][0]["course"] == "course-new"
    assert result["runs"][1]["course"] == "course-old"

  def test_run_summary_fields(self, workspace_root: Path) -> None:
    """每个 run 摘要含 course / work_dir / gatekeeper_passed / quality。"""
    work_root = workspace_root / "work"
    _make_run(
      work_root / "c",
      course="my-course",
      finished_at="2026-07-19T10:02:00",
      gatekeeper_passed=True,
    )
    result = list_runs(workspace_root)
    run = result["runs"][0]
    assert run["course"] == "my-course"
    assert "work_dir" in run
    assert run["gatekeeper_passed"] is True
    assert run["stages_completed"] == 11
    assert run["stages_failed"] == 0
    assert run["stages_total"] == 11

  def test_aggregates_llm_health_global(self, workspace_root: Path) -> None:
    """跨 run 聚合 llm_health_global。"""
    work_root = workspace_root / "work"
    _make_run(
      work_root / "c1", course="c1", finished_at="2026-07-19T10:02:00",
      llm_health={"ollama": {"calls": 5, "failures": 1}},
    )
    _make_run(
      work_root / "c2", course="c2", finished_at="2026-07-19T11:02:00",
      llm_health={"ollama": {"calls": 5, "failures": 0}},
    )
    result = list_runs(workspace_root)
    health = result["llm_health_global"]
    assert health["total_runs"] == 2
    assert health["total_llm_calls"] == 10
    assert health["total_llm_failures"] == 1
    assert health["llm_failure_rate"] == pytest.approx(0.1)

  def test_limit_caps_results(self, workspace_root: Path) -> None:
    """limit=N → 最多返回 N 个 run(默认 20)。"""
    work_root = workspace_root / "work"
    for i in range(5):
      _make_run(
        work_root / f"c{i}", course=f"c{i}", finished_at="2026-07-19T10:00:00",
      )
    result = list_runs(workspace_root, limit=2)
    assert result["total_runs"] == 2
    assert len(result["runs"]) == 2

  def test_skips_invalid_run_files(self, workspace_root: Path) -> None:
    """损坏的 pipeline_run.json 跳过(不计入 total_runs)。"""
    work_root = workspace_root / "work"
    (work_root / "bad").mkdir(parents=True)
    (work_root / "bad" / "pipeline_run.json").write_text(
      "not json", encoding="utf-8",
    )
    _make_run(
      work_root / "good", course="good", finished_at="2026-07-19T10:00:00",
    )
    result = list_runs(workspace_root)
    assert result["total_runs"] == 1
    assert result["runs"][0]["course"] == "good"


# ─────────────────────────────────────────────────────────────
# get_escalated_errors
# ─────────────────────────────────────────────────────────────


class TestGetEscalatedErrors:
  def test_manually_triggers_escalation(
    self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
  ) -> None:
    """手动触发 Pattern-Key 晋升(返回新晋升的 Pattern-Key)。"""
    ws = tmp_path / "ws"
    work_root = ws / "work"
    work_root.mkdir(parents=True)
    for course in ("c1", "c2", "c3"):
      course_dir = work_root / course
      course_dir.mkdir(parents=True)
      try:
        raise ConnectionError("Ollama")
      except ConnectionError as exc:
        from media_to_doc.logger.learnings import write_runtime_error
        write_runtime_error(course_dir, "chapters", exc)

    # 把 paths.project_root monkeypatch 到 tmp_path
    # (默认 .learnings 在项目根,不在 tmp_path)
    monkeypatch.setattr(
      "media_to_doc.paths.project_root", lambda: tmp_path,
    )

    result = get_escalated_errors(ws)
    assert result["threshold"] == 3
    assert len(result["escalated"]) >= 1
    assert "Connection:ollama" in result["escalated"][0]

  def test_default_workspace_uses_global(self) -> None:
    """不传 workspace_root → 用全局 WORKSPACE_ROOT(不抛错)。"""
    result = get_escalated_errors()
    assert "workspace" in result
    assert "learnings_file" in result
    assert result["threshold"] == 3
