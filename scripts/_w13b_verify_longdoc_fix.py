"""W13-B:验证 longdoc.py W12-D 兼容修复在 01.mp4 真产物上工作。

策略:
1. 复制 _w13a_inbox/output → _w13b_inbox/output(保留 output_final 不变)
2. 移除 workaround 拼装文件 chapters/raw/<video>.md
3. 调用 process_long_doc(work, provider=None, ...) 验证:
   - 读 output_final/<video>.md(W12-D 真相位置)而不是 chapters/raw/<video>/chapter_NN.md
   - cleaned_md 输出含真讲义的 TOC/摘要等结构(而不仅是 chapter 正文)
4. 对照 workaround 输出(retention_rate、chars_input 等)

用法:
    uv run python scripts/_w13b_verify_longdoc_fix.py

前置:需要 ``_w13a_inbox/`` 还在(W13-A 真跑产物)。
W13-A session 末 cleanup 后本脚本会 FileNotFoundError,届时需重新跑 W13-A。
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path("E:/resource/2026-01-27_年度复训")
SRC = ROOT / "_w13a_inbox"
DST = ROOT / "_w13b_inbox"
VIDEO = "01_先精准后放大的打爆策略"


def banner(msg: str) -> None:
  print(f"\n{'=' * 60}\n{msg}\n{'=' * 60}", flush=True)


def main() -> int:
  if DST.exists():
    shutil.rmtree(DST)
  banner(f"复制 {SRC} → {DST}")
  shutil.copytree(SRC / "output", DST / "output")
  if (SRC / "output_final").exists():
    shutil.copytree(SRC / "output_final", DST / "output_final")

  work = DST / "output"
  raw_md = work / "chapters" / "raw" / f"{VIDEO}.md"
  final_md = work.parent / "output_final" / f"{VIDEO}.md"
  chapter_dir = work / "chapters" / "raw" / VIDEO
  backup_cleaned = DST / "output_final" / f"{VIDEO}_cleaned.md.bak"

  banner("0. 验证布局")
  print(f"  work: {work}")
  print(f"  final_md (W12-D 真相位置): {final_md} exists={final_md.is_file()}")
  print(f"  raw_md (workaround): {raw_md} exists={raw_md.is_file()}")
  print(f"  chapter_dir (W12-D 中间产物): {chapter_dir} exists={chapter_dir.is_dir()}")
  assert final_md.is_file(), "W12-D 真讲义不存在,无法验证"

  banner("1. 备份 workaround 拼装的 raw_md + 现有 cleaned_md")
  if raw_md.exists():
    shutil.copy2(raw_md, raw_md.with_suffix(".md.bak"))
    raw_md.unlink()
    print("  workaround raw_md 已备份 + 删除")
  cleaned_path = DST / "output_final" / f"{VIDEO}_cleaned.md"
  if cleaned_path.exists():
    shutil.copy2(cleaned_path, backup_cleaned)
    print(f"  现有 cleaned_md 已备份 → {backup_cleaned.name}")

  banner("2. 调用 process_long_doc(skip LLM)")
  from media_to_doc.pipeline.longdoc import process_long_doc

  result = process_long_doc(work, None)
  print(f"  source_md: {result.source_md}")
  print(f"  cleaned_md: {result.cleaned_md}")
  print(f"  final_html: {result.final_html}")
  print(f"  provider: {result.provider}")
  print(f"  chars_input={result.stats.chars_input}, "
        f"chars_output={result.stats.chars_output}, "
        f"retention={result.stats.retention_rate:.4f}")

  banner("3. 验证:source 应是 W12-D final_md(不是 chapter 拼装)")
  assert result.source_md == final_md, (
    f"FAIL: source 应是 {final_md},实际是 {result.source_md}"
  )
  print("  [OK] source_md = final_dir/<video>.md (W12-D truth location)")

  banner("4. 验证:cleaned_md 应含真讲义结构(标题 + TOC + 摘要块)")
  cleaned_text = result.cleaned_md.read_text(encoding="utf-8")
  assert "## 目录" in cleaned_text, "cleaned_md 应含 TOC(W12-D 拼装讲义标志)"
  assert "**摘要**" in cleaned_text, "cleaned_md 应含摘要块(W12-D 拼装讲义标志)"
  assert "**关键要点**" in cleaned_text, "cleaned_md 应含关键要点块"
  assert "**引用关键帧**" in cleaned_text, "cleaned_md 应含关键帧引用块"
  print("  [OK] TOC + 摘要 + 要点 + 关键帧引用 — 真讲义结构齐全")

  banner("5. 验证:与 workaround 输出对比 retention_rate")
  if backup_cleaned.exists():
    bak_text = backup_cleaned.read_text(encoding="utf-8")
    bak_chars = len(bak_text)
    new_chars = len(cleaned_text)
    print(f"  workaround 输出: {bak_chars} chars")
    print(f"  W12-D 真讲义输出: {new_chars} chars")
    print(f"  差异: {new_chars - bak_chars} chars ({(new_chars - bak_chars) / max(bak_chars, 1):+.1%})")
    # W12-D 真讲义更长(含 TOC/摘要/要点/关键帧),workaround 是纯 chapter 正文
    assert new_chars > bak_chars, "W12-D 真讲义应比 workaround 输出更长(含结构化字段)"
    print("  [OK] W12-D 真讲义更长 = 含完整结构(预期)")
  else:
    print("  [SKIP] 无 backup,跳过对比")

  banner("6. 清理 _w13b_inbox")
  shutil.rmtree(DST)
  print(f"  [OK] {DST} 已删")

  banner("[ALL CHECKS PASSED]")
  return 0


if __name__ == "__main__":
  sys.exit(main())
