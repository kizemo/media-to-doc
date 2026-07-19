"""W10-A final: verify get_run_metrics (MCP-equivalent) returns real llm_health."""
import json
import sys
from pathlib import Path

OUTPUT = Path(r"E:/resource/2026-01-27_年度复训/output")


def main() -> int:
    # Use the public Python API (same as MCP tool calls from Claude Desktop)
    sys.path.insert(0, str(Path(r"F:/soft/00selfmade/media-to-doc/src")))
    from media_to_doc import get_run_metrics  # PEP 562 lazy import

    print("=== get_run_metrics (Python API, MCP tool equivalent) ===\n")
    metrics = get_run_metrics(OUTPUT)
    print("Top-level keys:", sorted(metrics.keys()))
    print()
    print("course:", metrics["course"])
    print("gatekeeper_passed:", metrics["pipeline_run"]["gatekeeper_passed"])
    print(
        "duration:",
        metrics["pipeline_run"]["duration_seconds"],
        "s =",
        round(metrics["pipeline_run"]["duration_seconds"] / 60, 1),
        "min",
    )
    print()
    print("=== llm_health (real data) ===")
    print(json.dumps(metrics["pipeline_run"]["llm_health"], indent=2, ensure_ascii=False))
    print()
    print("=== stages completed ===")
    stages = metrics["pipeline_run"]["stages"]
    print(f"total stages recorded: {len(stages)}")
    for s in stages:
        emoji = (
            "✓"
            if s["status"] == "completed"
            else "✗"
            if s["status"] == "failed"
            else "·"
        )
        print(
            f"  {emoji} {s['stage']:14s} {s['status']:10s} {s['duration_seconds']:>7.1f}s"
        )

    # Sanity assertions
    print()
    print("=== Sanity checks ===")
    assert metrics["pipeline_run"]["llm_health"], "llm_health 不能为空"
    expected_keys = {"chapters_ollama", "draft_ollama"}
    actual_keys = set(metrics["pipeline_run"]["llm_health"].keys())
    missing = expected_keys - actual_keys
    assert not missing, f"llm_health 缺: {missing}"
    for key, stats in metrics["pipeline_run"]["llm_health"].items():
        assert "calls" in stats, f"{key} 缺 calls"
        assert "failures" in stats, f"{key} 缺 failures"
        assert isinstance(stats["calls"], int)
        assert isinstance(stats["failures"], int)
        assert stats["calls"] >= 1, f"{key} calls={stats['calls']} 应 >=1"
        assert stats["failures"] == 0, f"{key} failures={stats['failures']} 应 0"
    print("✓ llm_health 含 chapters_ollama + draft_ollama")
    print("✓ calls >= 1, failures == 0")
    print("✓ W10-A 主目标达成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
