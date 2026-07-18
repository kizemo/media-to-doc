"""Stage 2 — ``asr``:Faster-Whisper 转写为 transcript.jsonl。

输入:``work/asr/audio.wav``(由 :mod:`audio` 抽出)
输出:``work/asr/transcript.jsonl``(每行一个 segment:``start``,``end``,``text``)

依赖:
- faster-whisper(lazy import,只装 ``media_to_doc[asr]`` extras 才可用)
- W1 测试通过 monkeypatch 注入假模型,不依赖真实 faster-whisper

参考:TDD §5 数据流第 2 步 + PROJECT_DESCRIPTION §3.2 asr 行 + §8 LE L1 stage 协议。
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..config import WorkflowConfig

# ─────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────

# Faster-Whisper 默认/推荐设置(可在 config 中覆盖)
DEFAULT_MODEL = "large-v3"
DEFAULT_DEVICE = "cuda"      # 自动降级 cpu
DEFAULT_COMPUTE_TYPE = "float16"
DEFAULT_BEAM_SIZE = 5
DEFAULT_VAD_FILTER = True


# ─────────────────────────────────────────────────────────────
# Segment 数据类
# ─────────────────────────────────────────────────────────────


@dataclass
class TranscriptSegment:
  """单个 ASR segment。

  Attributes
  ----------
  start : float
    段开始时间(秒)
  end : float
    段结束时间(秒)
  text : str
    文本内容
  speaker : str | None
    说话人标签(当前阶段未实现,留作 Phase 3 + 接入 pyannote.audio)
  words : list[dict] | None
    词级对齐(可选,Faster-Whisper word_timestamps=True 时填充)
  """

  start: float
  end: float
  text: str
  speaker: str | None = None
  words: list[dict[str, Any]] | None = None

  def to_jsonl(self) -> str:
    payload = asdict(self)
    if payload["words"] is None:
      payload.pop("words")
    return json.dumps(payload, ensure_ascii=False)


def write_transcript_jsonl(
  segments: Iterator[TranscriptSegment],
  output_path: Path,
) -> int:
  """把 segments 写入 jsonl 文件,返回写入条数。

  测试与真实 Faster-Whisper 共用这条路径(后者传入生成器)。
  """
  output_path.parent.mkdir(parents=True, exist_ok=True)
  count = 0
  with output_path.open("w", encoding="utf-8") as fh:
    for seg in segments:
      fh.write(seg.to_jsonl() + "\n")
      count += 1
  return count


def read_transcript_jsonl(path: Path) -> list[TranscriptSegment]:
  """读 transcript.jsonl 返回 segments 列表(下游 chapter / asr_correct 用)。"""
  segments: list[TranscriptSegment] = []
  with path.open(encoding="utf-8") as fh:
    for line in fh:
      line = line.strip()
      if not line:
        continue
      data = json.loads(line)
      segments.append(TranscriptSegment(**data))
  return segments


# ─────────────────────────────────────────────────────────────
# Faster-Whisper 懒加载
# ─────────────────────────────────────────────────────────────


def _try_load_whisper():
  """尝试加载 faster-whisper,失败抛 ``ImportError``(信息明确)。"""
  try:
    from faster_whisper import WhisperModel  # type: ignore[import-untyped]
  except ImportError as exc:
    raise ImportError(
      "transcribe() 需要 faster-whisper。安装方式:"
      "uv add 'media_to_doc[asr]' 或 uv add faster-whisper ctranslate2"
    ) from exc
  return WhisperModel


# ─────────────────────────────────────────────────────────────
# 真实实现(需要 faster-whisper 库)
# ─────────────────────────────────────────────────────────────


def _transcribe_with_whisper(
  audio_path: Path,
  *,
  model: str,
  device: str,
  compute_type: str,
  beam_size: int,
  vad_filter: bool,
  language: str | None,
) -> Iterator[TranscriptSegment]:
  """用 faster-whisper 跑转写,返回 generator(避免一次加载全部 segments)。"""
  WhisperModel = _try_load_whisper()  # noqa: N806  (3rd-party class)

  # 自动降级:无 CUDA 时切 CPU
  if device == "cuda" and not _has_cuda():
    device = "cpu"
    compute_type = "int8"

  whisper = WhisperModel(
    model,
    device=device,
    compute_type=compute_type,
  )
  segments_iter, _info = whisper.transcribe(
    str(audio_path),
    beam_size=beam_size,
    vad_filter=vad_filter,
    language=language,
    word_timestamps=False,
  )
  for seg in segments_iter:
    yield TranscriptSegment(
      start=float(seg.start),
      end=float(seg.end),
      text=str(seg.text).strip(),
    )


def _has_cuda() -> bool:
  """轻量 CUDA 可用性探测(无需 import torch 完整)。"""
  try:
    import torch  # type: ignore[import-not-found]

    return bool(torch.cuda.is_available())
  except ImportError:
    return os.environ.get("MEDIA_TO_DOC_FORCE_CUDA") == "1"


# ─────────────────────────────────────────────────────────────
# 公开 API
# ─────────────────────────────────────────────────────────────


def transcribe(
  work: Path,
  config: WorkflowConfig | None = None,
  *,
  model: str | None = None,
  device: str | None = None,
  compute_type: str | None = None,
  beam_size: int | None = None,
  vad_filter: bool | None = None,
  language: str | None = None,
) -> Path:
  """Stage 2:Faster-Whisper 转写。

  Parameters
  ----------
  work : Path
    work 根目录,需要含 ``asr/audio.wav``
  config : WorkflowConfig | None
    配置(覆盖默认设置)
  model / device / compute_type / beam_size / vad_filter / language
    单次覆盖参数(高级用)

  Returns
  -------
  Path
    transcript.jsonl 路径
  """
  audio_path = work / "asr" / "audio.wav"
  if not audio_path.exists():
    raise FileNotFoundError(
      f"找不到 {audio_path};请先跑 prepare_audio() stage"
    )

  # config 当前未用,asr kwargs 由函数参数控制;后续 W2 在 PipelineConfig 加 asr_* 字段
  _ = config  # silence F841 until W2
  kwargs: dict[str, Any] = {
    "model": model or DEFAULT_MODEL,
    "device": device or DEFAULT_DEVICE,
    "compute_type": compute_type or DEFAULT_COMPUTE_TYPE,
    "beam_size": beam_size if beam_size is not None else DEFAULT_BEAM_SIZE,
    "vad_filter": vad_filter if vad_filter is not None else DEFAULT_VAD_FILTER,
    "language": language,
  }

  output = work / "asr" / "transcript.jsonl"
  segments = _transcribe_with_whisper(audio_path, **kwargs)
  write_transcript_jsonl(segments, output)
  return output


__all__ = [
  "TranscriptSegment",
  "DEFAULT_MODEL",
  "DEFAULT_DEVICE",
  "DEFAULT_COMPUTE_TYPE",
  "DEFAULT_BEAM_SIZE",
  "DEFAULT_VAD_FILTER",
  "write_transcript_jsonl",
  "read_transcript_jsonl",
  "transcribe",
]
