"""Stage 5 — ``asr_correct``:OCR × ASR 8s 校对候选。

输入:
- ``work/asr/transcript.jsonl``:ASR 段落
- ``inbox/<课程>/ocr/frame_<ts_ms>.txt`` 或 ``work/ocr/ocr_results.json``:OCR 文字

输出:
- ``work/asr/asr_corrections.json``:每个 ASR segment 的"OCR 候选修正"列表

算法(W2 启发式,无 LLM):
1. 对每个 ASR segment,找到时间戳 ±4s 窗口内的所有 OCR 文本
2. 合并窗口内 OCR → ``ocr_window_text``
3. 提取 OCR 中长度 ≥ ``min_candidate_len`` 的"中文字符连续片段"(regex)
4. 过滤掉 ASR 文本已包含的子串 → 得到"候选修正"
5. 候选带频次(OCR 中出现次数)→ 排序输出

复杂度:O(N×M)(N=ASR 段数,M=OCR 帧数),单讲座 ~1000 段 ~ 200 帧,
实测 < 1 秒,不调 LLM 也能跑通。

W3+ 改进方向:
- 用 LLM 评估每个候选是否真的修正(避免 OCR 误识别成专有名词)
- 候选替换 ASR 后重生成 transcript.jsonl(目前 W2 只产候选,不直接改 ASR)

参考:TDD §5 数据流第 5 步 + PROJECT_DESCRIPTION §3.2 asr_correct 行。
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..config import PipelineConfig, WorkflowConfig
from .asr import read_transcript_jsonl

# ─────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────

DEFAULT_WINDOW_SECONDS = 8.0
# 半窗口:扩大窗口允许轻微错位
DEFAULT_HALF_WINDOW = DEFAULT_WINDOW_SECONDS / 2
# 候选片段最少连续字符数(过滤单字噪声)
DEFAULT_MIN_CANDIDATE_LEN = 3
# 单次最多保留的候选数
DEFAULT_TOP_K = 5

# 中文字符连续片段(2+ 字符,涵盖中日韩统一表意文字)
_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,}")
# 非 CJK 切分 regex(标点 / 数字 / 字母 / 空白)
_NON_CJK_PATTERN = re.compile(r"[^\u4e00-\u9fff]+")
# 候选子串长度上限(避免"整段"作为候选)
_MAX_CANDIDATE_LEN = 12


# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


@dataclass
class CorrectionCandidate:
  """单个候选修正片段。"""

  text: str  # 候选文字(如"达摩盘")
  frequency: int  # 在窗口 OCR 中出现次数
  score: float  # 归一化得分 = frequency × 长度系数


@dataclass
class AsrCorrection:
  """单个 ASR segment 的校对结果。"""

  segment_idx: int
  segment_start: float
  segment_end: float
  segment_text: str
  ocr_window_text: str  # 时间窗内合并的 OCR 文本
  candidates: list[CorrectionCandidate] = field(default_factory=list)

  def to_dict(self) -> dict[str, object]:
    return {
      "segment_idx": self.segment_idx,
      "segment_start": self.segment_start,
      "segment_end": self.segment_end,
      "segment_text": self.segment_text,
      "ocr_window_text": self.ocr_window_text,
      "candidates": [asdict(c) for c in self.candidates],
    }


@dataclass
class AsrCorrectionsReport:
  """整体校对结果(对应 ``asr_corrections.json``)。"""

  video: str = ""
  window_seconds: float = DEFAULT_WINDOW_SECONDS
  min_candidate_len: int = DEFAULT_MIN_CANDIDATE_LEN
  corrections: list[AsrCorrection] = field(default_factory=list)

  def to_dict(self) -> dict[str, object]:
    return {
      "video": self.video,
      "window_seconds": self.window_seconds,
      "min_candidate_len": self.min_candidate_len,
      "count": len(self.corrections),
      "corrections": [c.to_dict() for c in self.corrections],
    }

  def save(self, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
      json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
      encoding="utf-8",
    )


# ─────────────────────────────────────────────────────────────
# OCR 文本按时间戳索引
# ─────────────────────────────────────────────────────────────


@dataclass
class _OcrEntry:
  """单帧 OCR(时间戳 + 文本)。"""

  timestamp_ms: int
  text: str


def _load_ocr_entries(ocr_dir: Path) -> list[_OcrEntry]:
  """从 ``<ocr_dir>/frame_<ts_ms>.txt`` 加载所有 OCR 文本。

  文件名约定由 :mod:`ocr` 模块保证(``frame_<9位毫秒>.txt``)。
  """
  entries: list[_OcrEntry] = []
  if not ocr_dir.exists():
    return entries

  for txt_file in sorted(ocr_dir.iterdir()):
    if not txt_file.is_file() or not txt_file.name.startswith("frame_"):
      continue
    stem = txt_file.stem  # frame_<ts_ms>
    parts = stem.split("_")
    if len(parts) != 2 or not parts[1].isdigit():
      continue
    ts_ms = int(parts[1])
    text = txt_file.read_text(encoding="utf-8").strip()
    if text:
      entries.append(_OcrEntry(timestamp_ms=ts_ms, text=text))

  entries.sort(key=lambda e: e.timestamp_ms)
  return entries


def _collect_window_text(
  entries: list[_OcrEntry],
  start_seconds: float,
  end_seconds: float,
  half_window: float,
) -> str:
  """收集 [start - half, end + half] 窗口内所有 OCR 文本,合并返回。"""
  lo_ms = max(0, int((start_seconds - half_window) * 1000))
  hi_ms = int((end_seconds + half_window) * 1000)
  parts: list[str] = []
  for entry in entries:
    if entry.timestamp_ms < lo_ms:
      continue
    if entry.timestamp_ms > hi_ms:
      break
    parts.append(entry.text)
  return "\n".join(parts)


# ─────────────────────────────────────────────────────────────
# 候选提取
# ─────────────────────────────────────────────────────────────


def _extract_candidates(
  ocr_text: str,
  asr_text: str,
  min_len: int,
) -> list[CorrectionCandidate]:
  """从 OCR 文本里提取 ASR 中缺失的长连续片段作为候选。

  算法:
  1. 按非 CJK 字符切分 OCR 文本 → 多个 CJK 连续段
  2. 对每段做长度 ``[min_len, min(_MAX_CANDIDATE_LEN, len(segment))]`` 滑动窗口
  3. 累计每个 substring 在窗口内的出现频次
  4. 过滤掉 ASR 中已包含的子串
  5. 评分 ``frequency × (1 + 0.5 × (len - min_len))`` → 降序

  设计动机:
  - 单用 regex 提取 CJK chunks 会把"达摩盘选品技巧"当一整段 → 无法识别局部专有名词
  - 滑动窗口能让"达摩盘"作为独立候选被识别,即使它嵌在更长 CJK 段里
  - 不引入 jieba 等分词重依赖(W2 启发式)
  """
  if not ocr_text:
    return []

  # 1. 按非 CJK 切分
  chunks = [c for c in _NON_CJK_PATTERN.split(ocr_text) if c]
  if not chunks:
    return []

  # 2. 滑动窗口提取子串 + 累加频次
  counter: Counter[str] = Counter()
  for chunk in chunks:
    max_size = min(_MAX_CANDIDATE_LEN, len(chunk))
    if max_size < min_len:
      continue
    for size in range(min_len, max_size + 1):
      for i in range(len(chunk) - size + 1):
        counter[chunk[i : i + size]] += 1

  # 3. 过滤:ASR 中已包含的子串不算候选
  filtered = [(text, freq) for text, freq in counter.items() if text not in asr_text]
  if not filtered:
    return []

  # 4. 转候选 + 评分
  candidates: list[CorrectionCandidate] = []
  for text, freq in filtered:
    # 长度系数:稍微奖励长串,但避免其碾压短串
    score = float(freq) * (1.0 + 0.2 * (len(text) - min_len))
    candidates.append(CorrectionCandidate(text=text, frequency=freq, score=score))

  # 5. 按 score 降序
  candidates.sort(key=lambda c: (-c.score, -c.frequency, c.text))
  return candidates


# ─────────────────────────────────────────────────────────────
# 公开 API
# ─────────────────────────────────────────────────────────────


def correct_asr(
  work: Path,
  config: WorkflowConfig | None = None,
  *,
  ocr_dir: Path | None = None,
  transcript_path: Path | None = None,
  output_path: Path | None = None,
) -> AsrCorrectionsReport:
  """Stage 5:ASR × OCR 8s 校对候选。

  Parameters
  ----------
  work : Path
    work 根目录
  config : WorkflowConfig | None
    配置(用 ``pipeline.default_asr_window_seconds`` 调窗口大小)
  ocr_dir : Path | None
    OCR 文本目录,默认 ``<work>/ocr/``
  transcript_path : Path | None
    transcript.jsonl 路径,默认 ``<work>/asr/transcript.jsonl``
  output_path : Path | None
    输出 json 路径,默认 ``<work>/asr/asr_corrections.json``

  Returns
  -------
  AsrCorrectionsReport
    整体结果(已写盘)
  """
  pipeline_cfg: PipelineConfig = (config or WorkflowConfig()).pipeline
  window_seconds = float(pipeline_cfg.default_asr_window_seconds)
  half_window = window_seconds / 2.0

  ocr_dir = ocr_dir or (work / "ocr")
  transcript_path = transcript_path or (work / "asr" / "transcript.jsonl")
  output_path = output_path or (work / "asr" / "asr_corrections.json")

  if not transcript_path.exists():
    raise FileNotFoundError(
      f"找不到 {transcript_path};请先跑 transcribe() stage"
    )

  segments = read_transcript_jsonl(transcript_path)
  ocr_entries = _load_ocr_entries(ocr_dir)

  corrections: list[AsrCorrection] = []
  for idx, seg in enumerate(segments):
    window_text = _collect_window_text(ocr_entries, seg.start, seg.end, half_window)
    candidates = _extract_candidates(
      window_text,
      seg.text,
      DEFAULT_MIN_CANDIDATE_LEN,
    )
    # 取 top-K(避免 manifest 过大)
    candidates = candidates[:DEFAULT_TOP_K]
    corrections.append(AsrCorrection(
      segment_idx=idx,
      segment_start=float(seg.start),
      segment_end=float(seg.end),
      segment_text=seg.text,
      ocr_window_text=window_text,
      candidates=candidates,
    ))

  report = AsrCorrectionsReport(
    video=(transcript_path.parent.parent.name or ""),
    window_seconds=window_seconds,
    min_candidate_len=DEFAULT_MIN_CANDIDATE_LEN,
    corrections=corrections,
  )
  report.save(output_path)
  return report


# Re-export 给上层 import 用
__all__ = [
  "CorrectionCandidate",
  "AsrCorrection",
  "AsrCorrectionsReport",
  "DEFAULT_WINDOW_SECONDS",
  "DEFAULT_MIN_CANDIDATE_LEN",
  "correct_asr",
]
