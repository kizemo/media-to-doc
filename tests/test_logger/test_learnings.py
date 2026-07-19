"""``media_to_doc.logger.learnings`` 单元测试(W8)。

覆盖:
- ``write_runtime_error`` 写 ERRORS.md + 提取 Pattern-Key
- ``escalate_recurring_errors`` 阈值 + 幂等
- ``assess_llm_health`` 跨 run 统计 + 推荐策略
- ``post_pipeline_hook`` 完整流程(escalate + health)
- ``find_known_pattern_keys`` 已知 Pattern-Key 提取
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from media_to_doc.logger.learnings import (
  assess_llm_health,
  escalate_recurring_errors,
  find_known_pattern_keys,
  post_pipeline_hook,
  write_runtime_error,
)

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
  """临时项目根(含 workspace + .learnings/)。"""
  (tmp_path / "workspace" / "work").mkdir(parents=True)
  (tmp_path / ".learnings").mkdir()
  return tmp_path


@pytest.fixture
def work_dir(tmp_path: Path) -> Path:
  """work/<course>/(单课程)。"""
  work = tmp_path / "work"
  work.mkdir()
  return work


# ─────────────────────────────────────────────────────────────
# write_runtime_error
# ─────────────────────────────────────────────────────────────


class TestWriteRuntimeError:
  def test_writes_errors_md(
    self, work_dir: Path,
  ) -> None:
    """write_runtime_error 写 ERRORS.md(含 type/message/traceback/pattern_key)。"""
    try:
      raise ConnectionError("Ollama 11434 unreachable")
    except ConnectionError as exc:
      write_runtime_error(work_dir, "chapters", exc)
    errors_file = work_dir / "ERRORS.md"
    assert errors_file.exists()
    content = errors_file.read_text(encoding="utf-8")
    assert "ConnectionError" in content
    assert "Ollama 11434 unreachable" in content
    assert "Pattern-Key" in content

  def test_returns_pattern_key(
    self, work_dir: Path,
  ) -> None:
    """返回 Pattern-Key(以异常类型 + 关键词)。"""
    try:
      raise ValueError("template missing")
    except ValueError as exc:
      key = write_runtime_error(work_dir, "draft", exc)
    assert key.startswith("Value:")
    assert "template" in key


# ─────────────────────────────────────────────────────────────
# escalate_recurring_errors — 阈值 + 幂等
# ─────────────────────────────────────────────────────────────


class TestEscalateRecurringErrors:
  def test_below_threshold_no_action(
    self, tmp_project: Path,
  ) -> None:
    """重复次数 < threshold → 不晋升。"""
    work_root = tmp_project / "workspace" / "work"
    learnings_root = tmp_project / ".learnings"
    for course in ("c1", "c2"):
      work = work_root / course
      work.mkdir(parents=True)
      try:
        raise ValueError("template not found")
      except ValueError as exc:
        write_runtime_error(work, "draft", exc)
    escalated = escalate_recurring_errors(
      work_root, learnings_root, threshold=3
    )
    assert escalated == []
    assert not (learnings_root / "ERRORS.md").exists()

  def test_at_threshold_promotes(
    self, tmp_project: Path,
  ) -> None:
    """重复 ≥ threshold → 晋升到 .learnings/ERRORS.md。"""
    work_root = tmp_project / "workspace" / "work"
    learnings_root = tmp_project / ".learnings"
    for course in ("c1", "c2", "c3"):
      work = work_root / course
      work.mkdir(parents=True)
      try:
        raise ConnectionError("Ollama 11434 unreachable")
      except ConnectionError as exc:
        write_runtime_error(work, "chapters", exc)
    escalated = escalate_recurring_errors(
      work_root, learnings_root, threshold=3
    )
    assert len(escalated) == 1
    assert "Connection:ollama" in escalated[0]
    errors_file = learnings_root / "ERRORS.md"
    assert errors_file.exists()
    content = errors_file.read_text(encoding="utf-8")
    assert "Connection:ollama" in content
    assert "Occurrences" in content

  def test_is_idempotent(
    self, tmp_project: Path,
  ) -> None:
    """重复调用 escalate → 已存在的 Pattern-Key 不重复写入。"""
    work_root = tmp_project / "workspace" / "work"
    learnings_root = tmp_project / ".learnings"
    for course in ("c1", "c2", "c3"):
      work = work_root / course
      work.mkdir(parents=True)
      try:
        raise ConnectionError("Ollama")
      except ConnectionError as exc:
        write_runtime_error(work, "chapters", exc)
    # 第一次晋升
    first = escalate_recurring_errors(work_root, learnings_root)
    assert len(first) == 1
    # 第二次相同数据应空(幂等)
    second = escalate_recurring_errors(work_root, learnings_root)
    assert second == []

  def test_skips_learnings_directory(
    self, tmp_project: Path,
  ) -> None:
    """``.learnings/`` 自身目录下的 ERRORS.md 不参与计数。"""
    work_root = tmp_project / "workspace" / "work"
    learnings_root = tmp_project / ".learnings"
    # 把 ERRORS.md 写到 .learnings/ 自身(应被忽略)
    (learnings_root / "ERRORS.md").write_text(
      "## [old entry]\n\n**Pattern-Key**: `Connection:ollama`\n",
      encoding="utf-8",
    )
    # 在 work_root 放 2 次相同错误(< threshold)
    for course in ("c1", "c2"):
      work = work_root / course
      work.mkdir(parents=True)
      try:
        raise ConnectionError("Ollama")
      except ConnectionError as exc:
        write_runtime_error(work, "chapters", exc)
    escalated = escalate_recurring_errors(
      work_root, learnings_root, threshold=3
    )
    assert escalated == []
    # .learnings/ERRORS.md 不被修改
    content = (learnings_root / "ERRORS.md").read_text(encoding="utf-8")
    assert "**Occurrences" not in content

  def test_threshold_configurable(
    self, tmp_project: Path,
  ) -> None:
    """threshold 可配置(threshold=2 → 2 次重复即晋升)。"""
    work_root = tmp_project / "workspace" / "work"
    learnings_root = tmp_project / ".learnings"
    for course in ("c1", "c2"):
      work = work_root / course
      work.mkdir(parents=True)
      try:
        raise ValueError("template missing")
      except ValueError as exc:
        write_runtime_error(work, "draft", exc)
    escalated = escalate_recurring_errors(
      work_root, learnings_root, threshold=2
    )
    assert len(escalated) == 1
    assert "Value:template" in escalated[0]


# ─────────────────────────────────────────────────────────────
# assess_llm_health — 跨 run 统计 + 推荐策略
# ─────────────────────────────────────────────────────────────


class TestAssessLLMHealth:
  def test_no_runs_returns_empty(
    self, tmp_project: Path,
  ) -> None:
    """无 pipeline_run.json → total_runs=0,recommendation=None。"""
    work_root = tmp_project / "workspace" / "work"
    health = assess_llm_health(work_root)
    assert health["total_runs"] == 0
    assert health["llm_failure_rate"] == 0.0
    assert health["recommendation"] is None

  def test_aggregates_across_runs(
    self, tmp_project: Path,
  ) -> None:
    """多 run 累积 calls/failures。"""
    work_root = tmp_project / "workspace" / "work"
    for course in ("c1", "c2"):
      work = work_root / course
      work.mkdir(parents=True)
      (work / "pipeline_run.json").write_text(
        json.dumps(
          {
            "llm_health": {
              "ollama": {"calls": 5, "failures": 1},
            }
          }
        ),
        encoding="utf-8",
      )
    health = assess_llm_health(work_root)
    assert health["total_runs"] == 2
    assert health["total_llm_calls"] == 10
    assert health["total_llm_failures"] == 2
    assert health["llm_failure_rate"] == pytest.approx(0.2)
    assert health["providers"]["ollama"]["calls"] == 10
    assert health["providers"]["ollama"]["failures"] == 2

  def test_high_failure_rate_recommends_switch(
    self, tmp_project: Path,
  ) -> None:
    """失败率 > 20% → recommendation='switch_provider'。"""
    work_root = tmp_project / "workspace" / "work"
    work = work_root / "c1"
    work.mkdir(parents=True)
    (work / "pipeline_run.json").write_text(
      json.dumps(
        {
          "llm_health": {
            "ollama": {"calls": 10, "failures": 3},
          }
        }
      ),
      encoding="utf-8",
    )
    health = assess_llm_health(work_root)
    assert health["llm_failure_rate"] == pytest.approx(0.3)
    assert health["recommendation"] == "switch_provider"

  def test_medium_failure_rate_recommends_reduce_chunk(
    self, tmp_project: Path,
  ) -> None:
    """失败率 10-20% → recommendation='reduce_chunk'(严格 > 0.10 触发)。"""
    work_root = tmp_project / "workspace" / "work"
    work = work_root / "c1"
    work.mkdir(parents=True)
    # 2/13 = 0.1538 → 严格大于 0.10 且小于 0.20
    (work / "pipeline_run.json").write_text(
      json.dumps(
        {
          "llm_health": {
            "ollama": {"calls": 13, "failures": 2},
          }
        }
      ),
      encoding="utf-8",
    )
    health = assess_llm_health(work_root)
    assert health["llm_failure_rate"] == pytest.approx(0.1538, abs=1e-3)
    assert health["recommendation"] == "reduce_chunk"

  def test_low_failure_rate_no_recommendation(
    self, tmp_project: Path,
  ) -> None:
    """失败率 < 10% → recommendation=None。"""
    work_root = tmp_project / "workspace" / "work"
    work = work_root / "c1"
    work.mkdir(parents=True)
    (work / "pipeline_run.json").write_text(
      json.dumps(
        {
          "llm_health": {
            "ollama": {"calls": 100, "failures": 5},
          }
        }
      ),
      encoding="utf-8",
    )
    health = assess_llm_health(work_root)
    assert health["llm_failure_rate"] == pytest.approx(0.05)
    assert health["recommendation"] is None

  def test_handles_malformed_run_files(
    self, tmp_project: Path,
  ) -> None:
    """run_file 不是有效 JSON → 跳过,不影响整体统计。"""
    work_root = tmp_project / "workspace" / "work"
    work = work_root / "c1"
    work.mkdir(parents=True)
    (work / "pipeline_run.json").write_text("not json", encoding="utf-8")
    # 另一个 run 含有效数据
    work2 = work_root / "c2"
    work2.mkdir(parents=True)
    (work2 / "pipeline_run.json").write_text(
      json.dumps({"llm_health": {"ollama": {"calls": 1, "failures": 0}}}),
      encoding="utf-8",
    )
    health = assess_llm_health(work_root)
    assert health["total_runs"] == 1  # 跳过了 c1
    assert health["total_llm_calls"] == 1


# ─────────────────────────────────────────────────────────────
# post_pipeline_hook — escalate + health 合并返回
# ─────────────────────────────────────────────────────────────


class TestPostPipelineHook:
  def test_returns_escalated_and_health(
    self, tmp_project: Path, work_dir: Path,
  ) -> None:
    """post_pipeline_hook 返回 escalated_pattern_keys + llm_health + timestamp。"""
    # 制造 3 次重复错误(应晋升)
    for course in ("c1", "c2", "c3"):
      w = tmp_project / "workspace" / "work" / course
      w.mkdir(parents=True)
      try:
        raise ValueError("test pattern")
      except ValueError as exc:
        write_runtime_error(w, "render", exc)
    result = post_pipeline_hook(
      work_dir, project_root=tmp_project,
    )
    assert "escalated_pattern_keys" in result
    assert "llm_health" in result
    assert "timestamp" in result
    assert len(result["escalated_pattern_keys"]) >= 1

  def test_default_project_root(
    self, work_dir: Path,
  ) -> None:
    """不传 project_root → 默认用 paths.project_root()(不抛错)。"""
    # 简单触发,看是否抛错(没数据时也 OK)
    result = post_pipeline_hook(work_dir)
    assert "escalated_pattern_keys" in result


# ─────────────────────────────────────────────────────────────
# find_known_pattern_keys
# ─────────────────────────────────────────────────────────────


class TestFindKnownPatternKeys:
  def test_no_learnings_file(
    self, tmp_project: Path,
  ) -> None:
    """learnings/ERRORS.md 不存在 → 返回空集合。"""
    keys = find_known_pattern_keys(tmp_project / ".learnings")
    assert keys == set()

  def test_extracts_keys(
    self, tmp_project: Path,
  ) -> None:
    """从 ``## [PatternKey]`` 形式提取已知 Pattern-Key。"""
    learnings_root = tmp_project / ".learnings"
    (learnings_root / "ERRORS.md").write_text(
      "## [OutOfMemory:whisper]\n\n"
      "Some content...\n\n"
      "## [Connection:ollama]\n\n"
      "More content...\n",
      encoding="utf-8",
    )
    keys = find_known_pattern_keys(learnings_root)
    assert keys == {"OutOfMemory:whisper", "Connection:ollama"}

  def test_default_root_uses_global(
    self, tmp_project: Path,
  ) -> None:
    """不传 root → 用全局 LEARNINGS_DIR(不抛错)。"""
    keys = find_known_pattern_keys()
    assert isinstance(keys, set)
