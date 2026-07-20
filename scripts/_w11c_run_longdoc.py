"""W11-C 工具 — 真跑 longdoc active 净化(qwen3:14b)。

承接 ``handoff-pipeline-w11-release-2026-07-20.md`` §9 W11-C:
用 ollama qwen3:14b 真跑 longdoc 净化 W11-C work_dir 的 render 产物,
跳过 ASR/frames/OCR/chapters/drafts(已 W10-A 跑过),只跑 longdoc + verify。

用法
----

::

    uv run python scripts/_w11c_run_longdoc.py <work_dir> [--model qwen3:14b]

    # 例:验 W11-C 真跑产物
    uv run python scripts/_w11c_run_longdoc.py \\
        "E:/resource/2026-01-27_年度复训/output-w11c"

设计
----

- 复用 W10-A 中间产物(asr/frames/ocr/chapters/render),只重跑 longdoc 真净化
- 不动 state.json(只在文件层覆盖 output_cleaned.md + output_final.html)
- 长任务估计 ~30-60 分钟,进度日志写到 stderr
- 跑完写 ``_W11C_DONE.txt`` 标记,便于 polling
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# 确保 src/ 在 path(无需 uv 装包)
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
  sys.path.insert(0, str(_SRC))


def run_longdoc_active(
  work: Path,
  model: str = "qwen3:14b",
  num_ctx: int = 32768,
) -> dict[str, object]:
  """真跑 longdoc 净化,返回摘要 dict。

  Parameters
  ----------
  work : Path
    work_dir(必须含 chapters/raw/output.md,来自 render)
  model : str
    ollama 模型名
  num_ctx : int
    Ollama context size(qwen3:14b 原生 40960,RoPE 可扩展)

  Returns
  -------
  dict
    ``provider / model / cleaned_md / final_html / chunks / duration_seconds /
    llm_health``
  """
  from media_to_doc.config import WorkflowConfig
  from media_to_doc.llm import get_provider
  from media_to_doc.pipeline.longdoc import process_long_doc

  # 默认 config,但 longdoc_llm_provider 改 ollama(W10-A 默认 "skip")
  cfg = WorkflowConfig()
  cfg.pipeline.longdoc_llm_provider = "ollama"

  provider = get_provider("ollama", model=model, num_ctx=num_ctx)

  started = time.monotonic()

  # 加 progress log(分块时 print)
  print(f"[w11c] starting longdoc active on {work}", file=sys.stderr)
  print(f"[w11c] provider={provider.name} model={model} num_ctx={num_ctx}", file=sys.stderr)
  print(
    "[w11c] source md: work/chapters/raw/output.md (must exist)",
    file=sys.stderr,
  )

  result = process_long_doc(work, provider, cfg)

  duration = time.monotonic() - started

  summary = {
    "work": str(work),
    "provider": result.provider,
    "model": result.model,
    "cleaned_md": str(result.cleaned_md) if result.cleaned_md else "",
    "cleaned_md_size": result.cleaned_md.stat().st_size if result.cleaned_md else 0,
    "final_html": str(result.final_html) if result.final_html else "",
    "final_html_size": result.final_html.stat().st_size if result.final_html else 0,
    "stats": result.stats.to_dict(),
    "duration_seconds": round(duration, 2),
  }
  if hasattr(provider, "health"):
    try:
      h = provider.health()
      summary["llm_health"] = {
        "calls": h.total_calls,
        "failures": h.total_failures,
      }
    except Exception:
      summary["llm_health"] = None

  return summary


def write_done_marker(work: Path, summary: dict[str, object]) -> None:
  """写 _W11C_DONE.txt 标记(便于 polling + 复盘)。"""
  marker = work / "_W11C_DONE.txt"
  marker.write_text(
    json.dumps(summary, ensure_ascii=False, indent=2),
    encoding="utf-8",
  )
  print(f"[w11c] done marker: {marker}", file=sys.stderr)


def main(argv: list[str]) -> int:
  parser = argparse.ArgumentParser(
    description="W11-C 真跑 longdoc active 净化",
  )
  parser.add_argument(
    "work_dir",
    help="work_dir 含 chapters/raw/output.md",
  )
  parser.add_argument(
    "--model",
    default="qwen3:14b",
    help="ollama 模型名(默认 qwen3:14b)",
  )
  parser.add_argument(
    "--num-ctx",
    type=int,
    default=32768,
    help="Ollama context size(默认 32768,在 qwen3:14b 原生 40960 内)",
  )
  args = parser.parse_args(argv[1:])

  work = Path(args.work_dir)
  if not (work / "chapters" / "raw" / "output.md").exists():
    print(
      f"[w11c] ERROR: missing {work / 'chapters' / 'raw' / 'output.md'};"
      "需要先跑 render stage",
      file=sys.stderr,
    )
    return 2

  summary = run_longdoc_active(work, model=args.model, num_ctx=args.num_ctx)
  write_done_marker(work, summary)

  # stdout 输出结构化 JSON,管道友好
  print(json.dumps(summary, ensure_ascii=False, indent=2))
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
