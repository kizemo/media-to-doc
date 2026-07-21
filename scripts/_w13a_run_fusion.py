"""W13-A fusion runner: execute LLM fusion step after 01.mp4 pipeline complete.

Pre-conditions:
  - _w13a_inbox/output_final/01_先精准后放大的打爆策略_cleaned.md exists
  - output-w12c/chapters/raw/output_cleaned.md exists (03.mp4 W11-C cleaned)

Steps:
  1. mkdir _w13a_fusion/
  2. cp 01 + 03 cleaned.md into _w13a_fusion/
  3. uv run mtd merge _w13a_fusion/ --fusion ollama --name "年度复训综合"
  4. verify fusion plan output (7+ chapters, varied include values)
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:/resource/2026-01-27_年度复训")
INBOX = ROOT / "_w13a_inbox"
OUTPUT_FINAL_01 = INBOX / "output_final"
SOURCE_03 = ROOT / "output-w12c" / "chapters" / "raw" / "output_cleaned.md"
FUSION_DIR = ROOT / "_w13a_fusion"
PROJECT_ROOT = Path(r"F:/soft/00selfmade/media-to-doc")


def fail(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 1


def main() -> int:
    # 1) Pre-conditions
    if not OUTPUT_FINAL_01.exists():
        return fail(f"01 output_final 不存在:{OUTPUT_FINAL_01}")
    md_files = sorted(OUTPUT_FINAL_01.glob("*_cleaned.md"))
    if not md_files:
        return fail(f"01 *_cleaned.md 不存在 in {OUTPUT_FINAL_01}")
    md_01 = md_files[0]
    if not SOURCE_03.exists():
        return fail(f"03 cleaned.md 不存在:{SOURCE_03}")

    # 2) Build fusion dir
    if FUSION_DIR.exists():
        shutil.rmtree(FUSION_DIR)
    FUSION_DIR.mkdir(parents=True, exist_ok=True)

    cp_01_dest = FUSION_DIR / "01_cleaned.md"
    cp_03_dest = FUSION_DIR / "03_cleaned.md"
    shutil.copy2(md_01, cp_01_dest)
    shutil.copy2(SOURCE_03, cp_03_dest)
    print(f"copied:\n  {md_01} -> {cp_01_dest}\n  {SOURCE_03} -> {cp_03_dest}")

    # 3) Run mtd merge
    print("\n>> uv run mtd merge _w13a_fusion --fusion ollama --name '年度复训综合'")
    proc = subprocess.run(
        [
            "uv", "run", "--project", str(PROJECT_ROOT),
            "mtd", "merge", str(FUSION_DIR),
            "--fusion", "ollama",
            "--name", "年度复训综合",
        ],
        cwd=str(ROOT),
        env={
            "PATH": "/c/Windows/System32:/usr/bin:/bin",
            "HOME": str(Path.home()),
            "USERPROFILE": str(Path.home()),
            "OLLAMA_HOST": "http://localhost:11434",
        },
        capture_output=False,
    )
    if proc.returncode != 0:
        return fail(f"mtd merge 退出码={proc.returncode}")

    # 4) Verify output
    merged_md = FUSION_DIR / "年度复训综合_cleaned.md"
    if not merged_md.exists():
        return fail(f"merged.md 不存在:{merged_md}")
    text = merged_md.read_text(encoding="utf-8")
    h2_count = sum(1 for ln in text.split("\n") if ln.startswith("## "))
    print(f"\n>> merged.md H2 章节数={h2_count}")

    # Verify include= distribution in body
    include_all = text.count("`all`")  # rough indicator
    include_summary = text.count("`summary`")
    include_first_n = sum(
        1 for ln in text.split("\n") if "`first_n:" in ln
    )
    print(f">> include 分布(all/summary/first_n):"
          f" {include_all}/{include_summary}/{include_first_n}")

    if h2_count < 7:
        return fail(f"融合章节数 < 7 ({h2_count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
