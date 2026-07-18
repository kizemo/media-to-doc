"""media_to_doc 流水线包。

Phase 1 W1 提供前 3 个 stage:
- :func:`prepare_audio` — ffmpeg 抽音 → work/asr/audio.wav
- :func:`transcribe` — Faster-Whisper 转写 → work/asr/transcript.jsonl
- :func:`extract_keyframes` — PySceneDetect + pHash → img/frame_*.jpg + keyframes.json

由 :mod:`media_to_doc.pipeline.runner` 串起所有 stage(含 W2+ 后续 stage 占位)。

各 stage 函数签名约定:
- 接受 :class:`pathlib.Path` 输入 + 可选 ``config``
- 中间产物写到 ``work_dir``,最终产物写到 ``inbox_dir/raw/``
- 失败抛清晰异常(便于 runner 捕获 + LE 沉淀)
"""

from __future__ import annotations

from . import asr, audio, frames, runner
from .asr import transcribe
from .audio import prepare_audio
from .frames import KeyFrame, extract_keyframes
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
  "run_stage",
  "run_pipeline",
  "STAGE_FUNCS",
  "PipelineResult",
  "audio",
  "asr",
  "frames",
  "runner",
]
