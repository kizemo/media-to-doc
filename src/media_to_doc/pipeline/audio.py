"""Stage 1 — ``audio``:ffmpeg 抽音。

目标:把 ``inbox/<video>.mp4`` 转为 ``work/asr/audio.wav``(16 kHz 单声道 PCM),
供下游 :mod:`media_to_doc.pipeline.asr` 消费。

特性:
- 自动探测第一个视频(``mp4`` / ``mov`` / ``mkv`` / ``webm`` / ``m4v``)或音频(``mp3`` / ``wav`` / ``m4a``)
- 输出恒为 wav / 16 kHz / mono / pcm_s16le(Faster-Whisper 推荐)
- 重复运行幂等(覆盖前先 delete)
- ffmpeg 不在 PATH 时抛 :class:`FFmpegError` + ``FileNotFoundError``

参考:TDD §5 端到端数据流第 1 步 + PROJECT_DESCRIPTION §3.2 audio 行。
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ..config import WorkflowConfig
from ..utils.ffmpeg_utils import run_ffmpeg

# ─────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────

# Faster-Whisper / Faster-Whisper 推荐输入:16 kHz 单声道 PCM s16le
SAMPLE_RATE = 16000
CHANNELS = 1

SUPPORTED_VIDEO_EXTS: tuple[str, ...] = (
  ".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".flv",
)
SUPPORTED_AUDIO_EXTS: tuple[str, ...] = (
  ".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg",
)
SUPPORTED_EXTS: tuple[str, ...] = SUPPORTED_VIDEO_EXTS + SUPPORTED_AUDIO_EXTS


# ─────────────────────────────────────────────────────────────
# 公开 API
# ─────────────────────────────────────────────────────────────


def find_media(inbox: Path, *, exclude_dirs: list[Path] | None = None) -> Path:
  """在 inbox 下找到第一个支持的媒体文件。

  找不到抛 ``FileNotFoundError``(给 runner 清晰的退出信息)。

  Parameters
  ----------
  exclude_dirs : list[Path] | None
    排除这些目录下的文件(典型用法:work_dir 自身在 inbox 内时排除流水线产物)
  """
  candidates = _collect_media_files(inbox, exclude_dirs=exclude_dirs)
  if not candidates:
    raise FileNotFoundError(
      f"在 {inbox} 下未找到支持的媒体文件"
      f"(支持:{', '.join(SUPPORTED_EXTS)})"
    )
  return candidates[0]


def _collect_media_files(
  inbox: Path,
  *,
  exclude_dirs: list[Path] | None = None,
) -> list[Path]:
  """深度遍历 inbox 收集候选文件,按路径排序(稳定顺序便于测试)。"""
  if not inbox.exists():
    return []
  exclude_resolved: list[Path] = [
    d.resolve() for d in (exclude_dirs or [])
  ]
  candidates: list[Path] = []
  for path in sorted(inbox.rglob("*")):
    if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS:
      if exclude_resolved and any(
        path.resolve().is_relative_to(excl) for excl in exclude_resolved
      ):
        continue
      candidates.append(path)
  return candidates


def prepare_audio(
  inbox: Path,
  work: Path,
  config: WorkflowConfig | None = None,
) -> Path:
  """Stage 1:ffmpeg 抽音。

  Parameters
  ----------
  inbox : Path
    包含原始音视频的目录
  work : Path
    流水线中间产物根目录(将在其下创建 ``asr/`` 子目录)
  config : WorkflowConfig | None
    配置(当前未用,留作后续 silence padding / VAD 选项)

  Returns
  -------
  Path
    抽出的 wav 文件路径(``work/asr/audio.wav``)
  """
  source = find_media(inbox)
  asr_dir = work / "asr"
  asr_dir.mkdir(parents=True, exist_ok=True)
  output = asr_dir / "audio.wav"

  if output.exists():
    output.unlink()

  # 复制原文件而非重新抽音(音频格式省一步)
  if source.suffix.lower() in SUPPORTED_AUDIO_EXTS and source != output:
    shutil.copy2(source, output)
    return output

  run_ffmpeg(
    [
      "-y",                  # 覆盖输出
      "-i", str(source),     # 输入
      "-vn",                 # 不处理视频流
      "-ac", str(CHANNELS),  # 单声道
      "-ar", str(SAMPLE_RATE),  # 16 kHz
      "-acodec", "pcm_s16le",   # Faster-Whisper 推荐
      "-f", "wav",
      str(output),
    ],
    timeout=1800.0,  # 长视频留宽限
  )
  return output


__all__ = [
  "SAMPLE_RATE",
  "CHANNELS",
  "SUPPORTED_EXTS",
  "SUPPORTED_VIDEO_EXTS",
  "SUPPORTED_AUDIO_EXTS",
  "find_media",
  "prepare_audio",
]  # noqa: F401
