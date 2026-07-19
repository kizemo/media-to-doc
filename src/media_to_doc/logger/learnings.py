"""LE L4 进化层 — Learnings Management(W8 落地)。

实现错误模式自动识别、晋升、LLM 健康度评估。
参考 ``_research/LE_DESIGN.md`` §3.3。

陷阱飞轮机制:重复 ≥ 3 自动晋升 → 下次同类错误命中规则。

W8 适配:
- 包内依赖:``from media_to_doc.paths import LEARNINGS_DIR``(项目根 ``.learnings/``)
- ``post_pipeline_hook`` 接 ``project_root`` 参数(默认用 ``LEARNINGS_DIR.parent``)
"""

from __future__ import annotations

import json
import re
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from ..paths import LEARNINGS_DIR
from ..paths import project_root as _project_root
from .pipeline_logger import _extract_pattern_key


def write_runtime_error(work: Path, stage: str, exc: BaseException) -> str:
  """运行时错误写盘 + 提取 Pattern-Key。

  Returns
  -------
  str
    Pattern-Key(供后续跨 run 聚合)
  """
  errors_file = work / "ERRORS.md"
  errors_file.parent.mkdir(parents=True, exist_ok=True)
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
  with errors_file.open("a", encoding="utf-8") as f:
    f.write(entry)
  return pattern_key


def escalate_recurring_errors(
  work_root: Path,
  learnings_root: Path,
  threshold: int = 3,
) -> list[str]:
  """LE L4 进化层:Pattern-Key ≥ threshold 自动晋升。

  扫描所有 ``<work_root>/**/ERRORS.md``,统计 Pattern-Key,
  重复 ≥ threshold 的写入 ``<learnings_root>/ERRORS.md``
  (幂等:已存在的 Pattern-Key 不会重复写入)。

  Returns
  -------
  list[str]
    新晋升的 Pattern-Key 列表
  """
  pattern_counter: Counter[str] = Counter()
  pattern_examples: dict[str, list[tuple[str, str]]] = {}

  for errors_file in work_root.rglob("ERRORS.md"):
    if ".learnings" in errors_file.parts:
      continue
    course = errors_file.parent.name
    content = errors_file.read_text(encoding="utf-8")
    keys = re.findall(r"\*\*Pattern-Key\*\*: `(.+?)`", content)
    for key in keys:
      pattern_counter[key] += 1
      pattern_examples.setdefault(key, []).append(
        (course, errors_file.name)
      )

  target = learnings_root / "ERRORS.md"
  target.parent.mkdir(parents=True, exist_ok=True)
  existing_content = (
    target.read_text(encoding="utf-8") if target.exists() else ""
  )

  new_entries: list[str] = []
  for key, count in pattern_counter.most_common():
    if count < threshold:
      continue
    # 幂等:已存在的 Pattern-Key 跳过(标题格式 `## [key]`)
    if f"## [{key}]" in existing_content:
      continue
    examples = pattern_examples[key][:5]
    example_str = "\n".join(
      f"- `{course}/{err_file}`" for course, err_file in examples
    )
    entry = (
      f"\n## [{key}]\n\n"
      f"**First promoted**: {datetime.now():%Y-%m-%d %H:%M:%S}\n"
      f"**Occurrences**: {count} (across {len(examples)} shown)\n"
      f"**Threshold**: {threshold}\n"
      f"**Auto-detected**: True\n"
      f"**Examples**:\n{example_str}\n\n"
      f"**Recommended action**: "
      f"review / write rule / patch code\n"
    )
    new_entries.append(entry)

  if new_entries:
    if existing_content and not existing_content.endswith("\n"):
      existing_content += "\n"
    target.write_text(
      existing_content + "\n".join(new_entries), encoding="utf-8"
    )

  return [
    e.split("\n")[1].strip().removeprefix("## ").strip()
    for e in new_entries
    if e
  ]  # return Pattern-Key titles (without `## ` prefix)


def assess_llm_health(work_root: Path, last_n: int = 20) -> dict[str, Any]:
  """LE 健康度:抽最近 N run 统计 LLM 失败率。

  Returns
  -------
  dict
    含 ``total_runs`` / ``total_llm_calls`` / ``total_llm_failures`` /
    ``llm_failure_rate`` / ``providers`` / ``recommendation``
  """
  run_files = sorted(
    work_root.rglob("pipeline_run.json"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
  )[:last_n]

  if not run_files:
    return {
      "total_runs": 0,
      "total_llm_calls": 0,
      "total_llm_failures": 0,
      "llm_failure_rate": 0.0,
      "providers": {},
      "recommendation": None,
    }

  provider_stats: dict[str, dict[str, int]] = {}
  total_calls = 0
  total_failures = 0
  parsed_runs = 0  # 仅计成功解析的 run_file

  for run_file in run_files:
    try:
      data = json.loads(run_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
      continue
    parsed_runs += 1
    llm_health = data.get("llm_health", {})
    for provider, stats in llm_health.items():
      if not isinstance(stats, dict):
        continue
      provider_stats.setdefault(provider, {"calls": 0, "failures": 0})
      provider_stats[provider]["calls"] += stats.get("calls", 0)
      provider_stats[provider]["failures"] += stats.get("failures", 0)
      total_calls += stats.get("calls", 0)
      total_failures += stats.get("failures", 0)

  failure_rate = (total_failures / total_calls) if total_calls else 0.0

  for _provider, stats in provider_stats.items():
    stats["rate"] = (
      stats["failures"] / stats["calls"] if stats["calls"] else 0.0
    )

  recommendation: str | None = None
  if failure_rate > 0.20:
    recommendation = "switch_provider"
  elif failure_rate > 0.10:
    recommendation = "reduce_chunk"

  return {
    "total_runs": parsed_runs,
    "total_llm_calls": total_calls,
    "total_llm_failures": total_failures,
    "llm_failure_rate": failure_rate,
    "providers": provider_stats,
    "recommendation": recommendation,
  }


def post_pipeline_hook(
  work: Path,
  project_root: Path | None = None,
) -> dict[str, Any]:
  """LE L4 进化层入口:每次 run 完成后触发。

  步骤:
  1. 扫描 ERRORS.md 找 Pattern-Key 重复
  2. ≥ 3 次 → 晋升 ``<project_root>/.learnings/ERRORS.md``
  3. ``assess_llm_health()`` 给 LLM 切换建议
  """
  root = project_root or _project_root()
  work_root = work.parent  # workspace/work/
  learnings_root = root / ".learnings"

  escalated = escalate_recurring_errors(work_root, learnings_root)
  health = assess_llm_health(work_root)

  return {
    "escalated_pattern_keys": escalated,
    "llm_health": health,
    "timestamp": datetime.now().isoformat(timespec="seconds"),
  }


def find_known_pattern_keys(learnings_root: Path | None = None) -> set[str]:
  """读 ``<learnings_root>/ERRORS.md`` 提取所有已知 Pattern-Key。

  供 PipelineLogger 启动时检查,命中已知模式时:
  - 自动注入警告到 stage prompt
  - 或在 stage 启动前先校验依赖

  Returns
  -------
  set[str]
    已知 Pattern-Key 集合(空集合 = 无历史错误)
  """
  root = learnings_root if learnings_root is not None else LEARNINGS_DIR
  target = root / "ERRORS.md"
  if not target.exists():
    return set()
  content = target.read_text(encoding="utf-8")
  return set(re.findall(r"^## \[(.+)\]$", content, re.MULTILINE))


__all__ = [
  "write_runtime_error",
  "escalate_recurring_errors",
  "assess_llm_health",
  "post_pipeline_hook",
  "find_known_pattern_keys",
]
