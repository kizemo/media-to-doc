"""W13-A watch-verify loop: poll state.json, exit once verify stage is completed/failed.

Exits with sentinel at /tmp/w13a_verify_done.flag containing timestamp and final status.
"""
import json
import time
from datetime import datetime
from pathlib import Path

WORK_STATE = Path(r"E:/resource/2026-01-27_年度复训/_w13a_inbox/output/state.json")
POLL_INTERVAL = 90  # seconds — tighter than 5min since post-ASR stages are faster
SENTINEL = Path("/tmp/w13a_verify_done.flag")


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


def main() -> int:
    started = time.time()
    iter_count = 0
    while iter_count < 200:  # 200 * 90s = 5h cap
        iter_count += 1
        try:
            if not WORK_STATE.exists():
                print(f"[{iter_count:03d}] state.json missing")
                time.sleep(POLL_INTERVAL)
                continue
            d = json.loads(fix_paths(WORK_STATE.read_text(encoding="utf-8")))
            stages = d.get("stages", {})
            current = d.get("current_stage", "?")
            verify = stages.get("verify", {})
            v_status = verify.get("status", "pending")
            summary = " ".join(
                f"{n}={s.get('status','?')}"
                for n, s in stages.items()
            )
            print(
                f"[{iter_count:03d} {int(time.time()-started)}s] "
                f"{d.get('updated_at','')} current={current} verify={v_status}"
            )
            print(f"  stages: {summary}")
            if v_status in ("completed", "failed"):
                SENTINEL.write_text(
                    f"{datetime.now().isoformat()} verify_status={v_status} "
                    f"error={verify.get('error')}\n",
                    encoding="utf-8",
                )
                print(f"verify stage final={v_status}; sentinel written")
                return 0 if v_status == "completed" else 2
        except Exception as e:
            print(f"[{iter_count:03d}] poll error: {e}")
        time.sleep(POLL_INTERVAL)
    print(f"max iters {iter_count} hit; bailing")
    SENTINEL.write_text(f"TIMEOUT at {datetime.now().isoformat()}\n", encoding="utf-8")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
