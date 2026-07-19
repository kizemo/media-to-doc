"""W10-A verify the gatekeeper fail cause + run get_run_metrics MCP-equivalent."""
import json
from pathlib import Path

OUTPUT = Path(r"E:/resource/2026-01-27_年度复训/output")


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
    verify_path = OUTPUT / "verify" / "verify.json"
    if verify_path.exists():
        text = verify_path.read_text(encoding="utf-8")
        v = json.loads(fix_paths(text))
        print("=== verify.json ===")
        print(json.dumps(v, indent=2, ensure_ascii=False)[:2000])
    else:
        print("verify.json NOT FOUND at expected path")

    img_path = OUTPUT / "imagegen" / "imagegen.json"
    if img_path.exists():
        t = img_path.read_text(encoding="utf-8")
        print()
        print("=== imagegen.json ===")
        print(json.dumps(json.loads(fix_paths(t)), indent=2, ensure_ascii=False)[:500])

    # Final lecture output
    chapters_dir = OUTPUT / "chapters"
    raw_dir = chapters_dir / "raw"
    if (raw_dir).exists():
        print()
        print("=== chapters/raw subdirs ===")
        for p in raw_dir.iterdir():
            print(f"  {p.name}")
            for f in p.iterdir():
                print(f"    {f.name} ({f.stat().st_size} bytes)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
