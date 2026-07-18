"""media_to_doc 流水线包。

Phase 1 W3 提供 11 stage 中的前 9 个:
- :func:`prepare_audio` — ffmpeg 抽音 → work/asr/audio.wav
- :func:`transcribe` — Faster-Whisper 转写 → work/asr/transcript.jsonl
- :func:`extract_keyframes` — PySceneDetect + pHash → img/frame_*.jpg + keyframes.json
- :func:`run_ocr` — RapidOCR 对关键帧 → inbox/ocr/frame_*.txt
- :func:`correct_asr` — OCR × ASR 8s 校对候选 → work/asr/asr_corrections.json
- :func:`split_chapters` — LLM 章节切分 → work/chapters/chapter_*.md + chapters.json
- :func:`generate_drafts` — LLM 章节草稿 → raw/<stem>/chapter_NN.md
- :func:`generate_images` — SDXL Base+Refiner / skip → raw/<stem>/images/gen_*.png
- :func:`render_outputs` — 拼装 md + html(含 TOC + 内嵌 CSS)→ raw/<stem>.md/.html

由 :mod:`media_to_doc.pipeline.runner` 串起所有 stage(含 W4+ 后续 stage 占位)。

各 stage 函数签名约定:
- 接受 :class:`pathlib.Path` 输入 + 可选 ``config``
- 中间产物写到 ``work_dir``,最终产物写到 ``inbox_dir/raw/<stem>/``
- 失败抛清晰异常(便于 runner 捕获 + LE 沉淀)
"""

from __future__ import annotations

from . import (
  asr,
  asr_correct,
  audio,
  chapters,
  draft,
  frames,
  imagegen,
  ocr,
  render,
  runner,
)
from .asr import transcribe
from .asr_correct import correct_asr
from .audio import prepare_audio
from .chapters import split_chapters
from .draft import generate_drafts
from .frames import KeyFrame, extract_keyframes
from .imagegen import generate_images
from .ocr import run_ocr
from .render import render_html, render_outputs
from .runner import (
  STAGE_FUNCS,
  PipelineResult,
  run_pipeline,
  run_stage,
)

__all__ = [
  "prepare_audio",
  "transcribe",
  "extract_keyframes",
  "KeyFrame",
  "run_ocr",
  "correct_asr",
  "split_chapters",
  "generate_drafts",
  "generate_images",
  "render_outputs",
  "render_html",
  "run_stage",
  "run_pipeline",
  "STAGE_FUNCS",
  "PipelineResult",
  "asr",
  "asr_correct",
  "audio",
  "chapters",
  "draft",
  "frames",
  "imagegen",
  "ocr",
  "render",
  "runner",
]
