"""W13-A polling loop: print state every 5 minutes, exit on asr completion or max iters.

Usage: uv run --project F:/soft/00selfmade/media-to-doc python scripts/_w13a_poll_loop.py
"""
import json
import sys
import time
from pathlib import Path

WORK_STATE = Path(r"E:/resource/2026-01-27_年度复训/_w13a_inbox/output/state.json")
EXPECTED_SECONDS = 6660.0  # 01.mp4 ~111min estimated
POLL_INTERVAL = 300  # 5 min


def fix_paths(text: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            if nxt in '"\\/bfnrtu':
                out.append(text[i : i + 2])
                i += 2
            else:
                out.append("/")
                i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def poll_once() -> dict:
    if not WORK_STATE.exists():
        return {"status": "no_state"}
    text = WORK_STATE.read_text(encoding="utf-8")
    return json.loads(fix_paths(text))


def asr_progress(d: dict) -> tuple[int, int, float]:
    """Return (segments, bytes, last_end_seconds)."""
    p = WORK_STATE.parent / "asr" / "transcript.jsonl"
    if not p.exists():
        return 0, 0, 0.0
    text = p.read_text(encoding="utf-8")
    lines = text.splitlines()
    segments = len(lines)
    bytes_ = p.stat().st_size
    last_end = 0.0
    for ln in lines[-30:]:
        try:
            seg = json.loads(ln)
            end = float(seg.get("end", 0))
            if end > last_end:
                last_end = end
        except Exception:
            pass
    return segments, bytes_, last_end


def fmt_duration(secs: float) -> str:
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    return f"{h}h{m}m{s}s"


def main() -> int:
    started = time.time()
    iter_count = 0
    last_logged_progress = ""
    while iter_count < 100:  # 100 * 5min = 8.3h cap
        iter_count += 1
        try:
            d = poll_once()
        except Exception as e:
            print(f"[{iter_count:03d}] poll error: {e}")
            time.sleep(POLL_INTERVAL)
            continue
        if d.get("status") == "no_state":
            print(f"[{iter_count:03d}] state.json missing; waiting...")
            time.sleep(POLL_INTERVAL)
            continue
        stages = d.get("stages", {})
        asr_stage = stages.get("asr", {})
        asr_status = asr_stage.get("status", "pending")
        segs, bts, last_end = asr_progress(d)
        pct_str = f"{last_end / EXPECTED_SECONDS * 100:.1f}%"
        progress_str = f"asr_segments={segs} asr_bytes={bts:,} last_end={last_end:.1f}s ({pct_str})"
        # 只在进度变化时打印
        if progress_str != last_logged_progress or asr_status != "running":
            print(
                f"[{iter_count:03d} {fmt_duration(time.time()-started)}] "
                f"{d.get('updated_at','')} current={d.get('current_stage','')} "
                f"asr_status={asr_status} {progress_str}"
            )
            last_logged_progress = progress_str
        if asr_status == "completed":
            print(f"ASR 完成 @ {fmt_duration(time.time()-started)}")
            return 0
        if asr_status == "failed":
            print(f"ASR 失败: {asr_stage.get('error')}")
            return 2
        time.sleep(POLL_INTERVAL)
    print(f"达到最大轮询次数 {iter_count},退出")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
