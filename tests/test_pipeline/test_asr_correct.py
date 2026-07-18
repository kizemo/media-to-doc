"""ASR 校对 stage 测试。

覆盖:
- _load_ocr_entries 文件名解析
- _collect_window_text 时间窗收集
- _extract_candidates 候选提取(含 ASR 子串过滤)
- correct_asr 端到端(monkeypatch _load_ocr_entries)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from media_to_doc.pipeline import asr_correct as ac_mod
from media_to_doc.pipeline.asr import TranscriptSegment, write_transcript_jsonl
from media_to_doc.pipeline.asr_correct import (
  DEFAULT_MIN_CANDIDATE_LEN,
  DEFAULT_WINDOW_SECONDS,
  AsrCorrection,
  AsrCorrectionsReport,
  CorrectionCandidate,
  correct_asr,
)

# ─────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────


def _write_ocr_file(ocr_dir: Path, ts_ms: int, text: str) -> None:
  ocr_dir.mkdir(parents=True, exist_ok=True)
  (ocr_dir / f"frame_{ts_ms:09d}.txt").write_text(text, encoding="utf-8")


def _write_transcript(work: Path, segments: list[TranscriptSegment]) -> None:
  asr_dir = work / "asr"
  asr_dir.mkdir(parents=True, exist_ok=True)
  write_transcript_jsonl(iter(segments), asr_dir / "transcript.jsonl")


# ─────────────────────────────────────────────────────────────
# _load_ocr_entries
# ─────────────────────────────────────────────────────────────


def test_load_ocr_entries_parses_timestamp(tmp_path: Path) -> None:
  ocr_dir = tmp_path / "ocr"
  _write_ocr_file(ocr_dir, 1_000, "第一帧")
  _write_ocr_file(ocr_dir, 5_000, "第五秒")

  entries = ac_mod._load_ocr_entries(ocr_dir)
  assert len(entries) == 2
  assert entries[0].timestamp_ms == 1_000
  assert entries[0].text == "第一帧"
  assert entries[1].timestamp_ms == 5_000
  # 按时间戳排序
  assert entries[0].timestamp_ms < entries[1].timestamp_ms


def test_load_ocr_entries_skips_empty_files(tmp_path: Path) -> None:
  ocr_dir = tmp_path / "ocr"
  _write_ocr_file(ocr_dir, 1_000, "kept")
  _write_ocr_file(ocr_dir, 2_000, "")
  _write_ocr_file(ocr_dir, 3_000, "  \n  ")  # 空白也跳过

  entries = ac_mod._load_ocr_entries(ocr_dir)
  assert len(entries) == 1
  assert entries[0].text == "kept"


def test_load_ocr_entries_skips_non_frame_files(tmp_path: Path) -> None:
  ocr_dir = tmp_path / "ocr"
  _write_ocr_file(ocr_dir, 1_000, "kept")
  (ocr_dir / "README.txt").write_text("not a frame", encoding="utf-8")

  entries = ac_mod._load_ocr_entries(ocr_dir)
  assert len(entries) == 1


def test_load_ocr_entries_missing_dir(tmp_path: Path) -> None:
  assert ac_mod._load_ocr_entries(tmp_path / "nope") == []


# ─────────────────────────────────────────────────────────────
# _collect_window_text
# ─────────────────────────────────────────────────────────────


def test_collect_window_text_includes_overlapping_frames() -> None:
  entries = [
    ac_mod._OcrEntry(timestamp_ms=0, text="A"),
    ac_mod._OcrEntry(timestamp_ms=2_000, text="B"),
    ac_mod._OcrEntry(timestamp_ms=5_000, text="C"),
    ac_mod._OcrEntry(timestamp_ms=20_000, text="D"),
  ]
  # ASR segment [4.0s - 6.0s], half_window=4s → 覆盖 [0s, 10s]
  text = ac_mod._collect_window_text(entries, 4.0, 6.0, half_window=4.0)
  assert "A" in text and "B" in text and "C" in text
  assert "D" not in text


def test_collect_window_text_clamps_negative_lo() -> None:
  """start < half_window 时 lo 不应为负数。"""
  entries = [ac_mod._OcrEntry(timestamp_ms=500, text="early")]
  text = ac_mod._collect_window_text(entries, 0.5, 1.0, half_window=4.0)
  assert "early" in text


def test_collect_window_text_empty_when_no_overlap() -> None:
  entries = [ac_mod._OcrEntry(timestamp_ms=0, text="A")]
  text = ac_mod._collect_window_text(entries, 100.0, 110.0, half_window=4.0)
  assert text == ""


# ─────────────────────────────────────────────────────────────
# _extract_candidates
# ─────────────────────────────────────────────────────────────


def test_extract_candidates_picks_ocr_specific_phrases() -> None:
  ocr_text = "本节介绍达摩盘的使用方法和选品技巧"
  asr_text = "本节介绍打魔盘的使用方法和选品技巧"  # ASR 同音字错

  candidates = ac_mod._extract_candidates(ocr_text, asr_text, min_len=3)
  texts = [c.text for c in candidates]

  # "达摩盘" 在 ASR 里没有(ASR 是"打魔盘"),应作为候选
  assert "达摩盘" in texts
  # "使用方法和选品技巧" ASR 里有,不应入选
  assert "使用方法和选品技巧" not in texts


def test_extract_candidates_filters_short_chunks() -> None:
  """min_len=3 → 单字/双字片段不应入选。"""
  # 切分后每段都 < min_len → 无候选
  ocr_text = "A本B节C介D绍"  # 单个 CJK 散落,每段长度 1
  candidates = ac_mod._extract_candidates(ocr_text, "", min_len=3)
  assert candidates == []


def test_extract_candidates_window_from_continuous_cjk() -> None:
  """连续 CJK 段应该产生滑动窗口候选。"""
  # "达摩盘选品" 是连续 CJK,应提取多个候选
  ocr_text = "达摩盘选品"
  candidates = ac_mod._extract_candidates(ocr_text, "", min_len=2)
  texts = {c.text for c in candidates}
  # 至少应该有:达摩、摩盘、盘选、选品、达摩盘、摩盘选、盘选品、达摩盘选品
  assert "达摩盘" in texts
  assert "选品" in texts
  # 短窗口也保留
  assert "达摩" in texts


def test_extract_candidates_includes_repeated_candidates() -> None:
  """OCR 中多次出现的专有名词应该 frequency > 1。"""
  # 跨段(空白切分)出现两次
  ocr_text = "达摩盘选品 达摩盘方法"
  asr_text = "打魔盘"
  candidates = ac_mod._extract_candidates(ocr_text, asr_text, min_len=3)
  damo = [c for c in candidates if c.text == "达摩盘"]
  assert len(damo) == 1
  assert damo[0].frequency == 2  # 出现 2 次


def test_extract_candidates_skips_asr_substrings() -> None:
  ocr_text = "本节介绍"
  asr_text = "本节介绍"
  candidates = ac_mod._extract_candidates(ocr_text, asr_text, min_len=3)
  assert candidates == []


def test_extract_candidates_returns_empty_when_no_cjk() -> None:
  candidates = ac_mod._extract_candidates("hello world", "hi", min_len=3)
  assert candidates == []


def test_extract_candidates_sorted_by_score_desc() -> None:
  ocr_text = "达摩盘方法达摩盘方法达摩盘方法达摩盘方法达摩盘方法选品技巧方法选品技巧方法选品技巧方法"
  asr_text = ""
  candidates = ac_mod._extract_candidates(ocr_text, asr_text, min_len=3)
  # "达摩盘" 频次 >= "选品技巧",前者在 score 中应该 >= 后者
  damo_idx = next((i for i, c in enumerate(candidates) if c.text == "达摩盘"), -1)
  xuan_idx = next((i for i, c in enumerate(candidates) if c.text == "选品技巧"), -1)
  assert damo_idx != -1 and xuan_idx != -1
  assert damo_idx < xuan_idx  # 达摩盘 排序在选品技巧 之前


# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


def test_correction_candidate_dataclass() -> None:
  c = CorrectionCandidate(text="达摩盘", frequency=3, score=5.0)
  assert c.text == "达摩盘"
  assert c.frequency == 3
  assert c.score == 5.0


def test_asr_correction_to_dict() -> None:
  corr = AsrCorrection(
    segment_idx=0,
    segment_start=0.0,
    segment_end=5.0,
    segment_text="本节介绍打魔盘",
    ocr_window_text="本节介绍达摩盘",
    candidates=[CorrectionCandidate(text="达摩盘", frequency=1, score=1.0)],
  )
  payload = corr.to_dict()
  assert payload["segment_idx"] == 0
  assert payload["candidates"][0]["text"] == "达摩盘"


def test_corrections_report_save(tmp_path: Path) -> None:
  report = AsrCorrectionsReport(
    video="c1",
    window_seconds=8.0,
    min_candidate_len=3,
    corrections=[
      AsrCorrection(
        segment_idx=0, segment_start=0.0, segment_end=5.0,
        segment_text="x", ocr_window_text="y", candidates=[],
      ),
    ],
  )
  out = tmp_path / "asr_corrections.json"
  report.save(out)

  import json
  data = json.loads(out.read_text(encoding="utf-8"))
  assert data["video"] == "c1"
  assert data["count"] == 1
  assert data["window_seconds"] == 8.0


# ─────────────────────────────────────────────────────────────
# correct_asr 端到端
# ─────────────────────────────────────────────────────────────


def test_correct_asr_end_to_end(tmp_path: Path) -> None:
  work = tmp_path / "work"
  asr_dir = work / "asr"
  asr_dir.mkdir(parents=True)
  ocr_dir = tmp_path / "ocr"
  ocr_dir.mkdir()

  # ASR 段落:两段
  _write_transcript(work, [
    TranscriptSegment(start=0.0, end=5.0, text="本节介绍打魔盘选品"),
    TranscriptSegment(start=10.0, end=15.0, text="下一段"),
  ])
  # OCR:第 1 段时间窗内出现"达摩盘";第 2 段 OCR 文字仅包含 ASR 子串 → 无候选
  _write_ocr_file(ocr_dir, 1_500, "达摩盘")
  _write_ocr_file(ocr_dir, 3_000, "达摩盘")
  _write_ocr_file(ocr_dir, 11_000, "下一段")  # 等于 ASR 文字 → 滑动窗口后 substring 全在 ASR 中

  report = correct_asr(work, ocr_dir=ocr_dir)

  assert len(report.corrections) == 2
  # 第 1 段有候选
  first = report.corrections[0]
  assert first.candidates != []
  assert any(c.text == "达摩盘" for c in first.candidates)
  # 第 2 段无中文候选
  second = report.corrections[1]
  assert second.candidates == []


def test_correct_asr_raises_when_no_transcript(tmp_path: Path) -> None:
  work = tmp_path / "empty_work"
  work.mkdir()
  with pytest.raises(FileNotFoundError, match="transcript.jsonl"):
    correct_asr(work)


def test_correct_asr_handles_no_ocr_files(tmp_path: Path) -> None:
  """OCR 目录不存在或为空 → 每段 ocr_window_text 为空,候选为空。"""
  work = tmp_path / "work"
  _write_transcript(work, [
    TranscriptSegment(start=0.0, end=5.0, text="hello"),
  ])
  report = correct_asr(work, ocr_dir=tmp_path / "nonexistent_ocr")
  assert report.corrections[0].ocr_window_text == ""
  assert report.corrections[0].candidates == []


def test_correct_asr_top_k_limit(tmp_path: Path) -> None:
  """候选超 DEFAULT_TOP_K 时只保留 top-K(score 排序)。"""
  work = tmp_path / "work"
  _write_transcript(work, [
    TranscriptSegment(start=0.0, end=5.0, text="ASR 内容"),
  ])
  ocr_dir = tmp_path / "ocr"
  # 制造 10 个不同候选(频次 1)
  candidates_text = " ".join(f"候选{i:02d}" for i in range(10))
  _write_ocr_file(ocr_dir, 2_000, candidates_text)

  report = correct_asr(work, ocr_dir=ocr_dir)
  # DEFAULT_TOP_K = 5
  assert len(report.corrections[0].candidates) <= ac_mod.DEFAULT_TOP_K


def test_correct_asr_uses_custom_window_via_config(tmp_path: Path) -> None:
  """config.pipeline.default_asr_window_seconds 调窗口大小。"""
  work = tmp_path / "work"
  _write_transcript(work, [
    TranscriptSegment(start=0.0, end=2.0, text="x"),
  ])
  ocr_dir = tmp_path / "ocr"
  # OCR 在 t=20s,默认窗口 8s 收不到,但窗口 = 50s 时能收到
  _write_ocr_file(ocr_dir, 20_000, "达摩盘测试")

  from media_to_doc.config import PipelineConfig, WorkflowConfig

  cfg = WorkflowConfig(pipeline=PipelineConfig(default_asr_window_seconds=50.0))
  report = correct_asr(work, ocr_dir=ocr_dir, config=cfg)
  assert any(c.text == "达摩盘测试" for c in report.corrections[0].candidates)


def test_correct_asr_writes_json(tmp_path: Path) -> None:
  work = tmp_path / "work"
  _write_transcript(work, [
    TranscriptSegment(start=0.0, end=5.0, text="x"),
  ])
  correct_asr(work, ocr_dir=tmp_path / "ocr")
  assert (work / "asr" / "asr_corrections.json").exists()


def test_default_constants() -> None:
  assert DEFAULT_WINDOW_SECONDS == 8.0
  assert DEFAULT_MIN_CANDIDATE_LEN == 3
