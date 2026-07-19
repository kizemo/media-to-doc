"""W10-A progress poll helper: read state.json robustly (Windows path backslash fix)."""
import json
from pathlib import Path

WORK_STATE = Path(r"E:/resource/2026-01-27_年度复训/output/state.json")


def fix_paths(text: str) -> str:
    """Replace ``\\X`` with ``/X`` when X isn't a valid JSON escape character."""
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
    if not WORK_STATE.exists():
        print("state.json 不存在")
        return 1
    text = WORK_STATE.read_text(encoding="utf-8")
    d = json.loads(fix_paths(text))
    print(f"updated_at: {d['updated_at']}  current_stage: {d['current_stage']}")
    print("stages:")
    for n, s in d["stages"].items():
        print(
            f"  {n:14s} {s['status']:10s} "
            f"started={s.get('started_at')} finished={s.get('finished_at')}"
        )
    asr_transcript = WORK_STATE.parent / "asr" / "transcript.jsonl"
    if asr_transcript.exists():
        size = asr_transcript.stat().st_size
        lines = sum(1 for _ in asr_transcript.open(encoding="utf-8"))
        print(f"transcript.jsonl: {size} bytes / {lines} segments / "
              f"mtime={asr_transcript.stat().st_mtime}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
