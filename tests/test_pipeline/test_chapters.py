"""chapters stage 测试。

要点:
- mock LLM provider,验证 prompt 构造 / JSON 解析 / 文件写入
- 覆盖 _parse_chapters_json(各种 LLM 输出格式)
- _coerce_chapter 类型容错
- _render_chapter_markdown 格式
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from media_to_doc.pipeline import chapters as ch_mod
from media_to_doc.pipeline.asr import TranscriptSegment, write_transcript_jsonl
from media_to_doc.pipeline.chapters import (
  Chapter,
  ChaptersReport,
  split_chapters,
)

# ─────────────────────────────────────────────────────────────
# 假 LLM provider
# ─────────────────────────────────────────────────────────────


class _FakeChatResponse:
  def __init__(self, text: str, provider: str = "fake", model: str = "fake-model") -> None:
    self.text = text
    self.provider = provider
    self.model = model
    self.duration_seconds = 0.1


class _FakeProvider:
  """最小 LLM provider mock(满足 duck-typing)。"""

  def __init__(self, replies: list[str] | str) -> None:
    self._replies = [replies] if isinstance(replies, str) else list(replies)
    self._call_count = 0
    self.last_prompt = ""
    self._calls: list[str] = []

  @property
  def name(self) -> str:
    return "fake"

  def list_models(self) -> list[str]:
    return ["fake-model"]

  def chat(self, prompt: str, **_kwargs: object) -> _FakeChatResponse:
    self._call_count += 1
    self.last_prompt = prompt
    self._calls.append(prompt)
    if not self._replies:
      raise RuntimeError("no more fake replies")
    text = self._replies.pop(0)
    return _FakeChatResponse(text=text)


def _write_transcript(work: Path, segments: list[TranscriptSegment]) -> None:
  asr_dir = work / "asr"
  asr_dir.mkdir(parents=True, exist_ok=True)
  write_transcript_jsonl(iter(segments), asr_dir / "transcript.jsonl")


def _write_keyframes(work: Path, timestamps_ms: list[int]) -> None:
  frames_dir = work / "frames"
  frames_dir.mkdir(parents=True, exist_ok=True)
  manifest = {
    "video": "x",
    "frames": [
      {"timestamp_ms": t, "image_path": f"frame_{t:09d}.jpg", "phash": "0" * 16, "source": "scene"}
      for t in timestamps_ms
    ],
    "threshold": 5,
  }
  (frames_dir / "keyframes.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
  )


# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


def test_chapter_duration_seconds() -> None:
  c = Chapter(idx=1, title="t", summary="s", start_seconds=10.0, end_seconds=42.5)
  assert c.duration_seconds == pytest.approx(32.5)


def test_chapter_to_dict_includes_all_fields() -> None:
  c = Chapter(
    idx=2,
    title="第 2 章",
    summary="摘要",
    start_seconds=60.0,
    end_seconds=120.0,
    key_points=["A", "B"],
    image_refs=[60.5, 90.0],
    illustrations=[["GEN: 配图"], "描述 B"],
  )
  payload = c.to_dict()
  assert payload["idx"] == 2
  assert payload["duration_seconds"] == 60.0
  assert payload["key_points"] == ["A", "B"]
  assert payload["image_refs"] == [60.5, 90.0]


def test_chapters_report_save(tmp_path: Path) -> None:
  r = ChaptersReport(
    video="c1",
    provider="fake",
    model="fake-model",
    chapters=[
      Chapter(idx=1, title="t", summary="s", start_seconds=0.0, end_seconds=10.0),
    ],
  )
  out = tmp_path / "chapters.json"
  r.save(out)
  data = json.loads(out.read_text(encoding="utf-8"))
  assert data["count"] == 1
  assert data["provider"] == "fake"


# ─────────────────────────────────────────────────────────────
# _parse_chapters_json(各种 LLM 输出格式)
# ─────────────────────────────────────────────────────────────


def test_parse_plain_json_array() -> None:
  raw = json.dumps([
    {"title": "A", "summary": "s", "start_seconds": 0.0, "end_seconds": 10.0},
  ], ensure_ascii=False)
  out = ch_mod._parse_chapters_json(raw)
  assert len(out) == 1
  assert out[0]["title"] == "A"


def test_parse_json_fenced_block() -> None:
  raw = "```json\n" + json.dumps([
    {"title": "A", "summary": "s", "start_seconds": 0.0, "end_seconds": 10.0},
  ]) + "\n```"
  out = ch_mod._parse_chapters_json(raw)
  assert len(out) == 1


def test_parse_json_with_surrounding_text() -> None:
  """LLM 偶尔会包一段说明文字 → 找第一个 [ 到最后一个 ]。"""
  raw = "以下是结果:\n" + json.dumps([
    {"title": "A", "summary": "s", "start_seconds": 0.0, "end_seconds": 10.0},
  ]) + "\n希望对您有帮助。"
  out = ch_mod._parse_chapters_json(raw)
  assert len(out) == 1


def test_parse_json_invalid_raises() -> None:
  with pytest.raises(ValueError, match="无法从 LLM 输出解析 JSON"):
    ch_mod._parse_chapters_json("this is not JSON")


def test_parse_json_non_array_raises() -> None:
  with pytest.raises(ValueError, match="无法从 LLM 输出解析 JSON"):
    ch_mod._parse_chapters_json(json.dumps({"not": "array"}))


# ─────────────────────────────────────────────────────────────
# _coerce_chapter
# ─────────────────────────────────────────────────────────────


def test_coerce_chapter_fills_missing_fields() -> None:
  raw = {"title": "x"}  # 缺 summary / start / end / key_points / image_refs / illustrations
  c = ch_mod._coerce_chapter(1, raw)
  assert c.idx == 1
  assert c.title == "x"
  assert c.summary == ""
  assert c.end_seconds > c.start_seconds
  assert c.key_points == []


def test_coerce_chapter_uses_default_title_when_empty() -> None:
  c = ch_mod._coerce_chapter(3, {"title": ""})
  assert c.title == "章节 3"


def test_coerce_chapter_invalid_types_become_defaults() -> None:
  raw = {
    "title": "ok",
    "start_seconds": "not a number",
    "end_seconds": ["x"],
    "key_points": "not a list",
    "image_refs": [10.5, "bad", None],
    "illustrations": [123, "valid"],
  }
  c = ch_mod._coerce_chapter(1, raw)
  assert c.start_seconds == 0.0
  assert c.end_seconds > c.start_seconds  # 自动修正 end > start
  assert c.key_points == []
  # image_refs:10.5 是数字,后两个无效
  assert c.image_refs == [10.5]
  # illustrations:123 不是字符串,会变成 "123";`valid` 保留
  assert "valid" in c.illustrations


def test_coerce_chapter_end_less_than_start_corrected() -> None:
  raw = {"title": "x", "start_seconds": 100.0, "end_seconds": 50.0}
  c = ch_mod._coerce_chapter(1, raw)
  assert c.end_seconds > c.start_seconds


# ─────────────────────────────────────────────────────────────
# _render_chapter_markdown
# ─────────────────────────────────────────────────────────────


def test_render_chapter_markdown_basic() -> None:
  c = Chapter(
    idx=1, title="第 1 章", summary="介绍",
    start_seconds=0.0, end_seconds=60.0,
  )
  md = ch_mod._render_chapter_markdown(c)
  assert "## 第 1 章" in md
  assert "**摘要**:介绍" in md


def test_render_chapter_markdown_includes_key_points() -> None:
  c = Chapter(
    idx=1, title="t", summary="s",
    start_seconds=0.0, end_seconds=10.0,
    key_points=["要点 A", "要点 B"],
  )
  md = ch_mod._render_chapter_markdown(c)
  assert "- 要点 A" in md
  assert "- 要点 B" in md


def test_render_chapter_markdown_includes_image_refs_with_frame_path() -> None:
  c = Chapter(
    idx=1, title="t", summary="s",
    start_seconds=0.0, end_seconds=10.0,
    image_refs=[12.345, 60.0],
  )
  md = ch_mod._render_chapter_markdown(c)
  assert "12.35s" in md or "12.34s" in md
  assert "frame_000012345.jpg" in md
  assert "frame_000060000.jpg" in md


def test_render_chapter_markdown_includes_illustrations() -> None:
  c = Chapter(
    idx=1, title="t", summary="s",
    start_seconds=0.0, end_seconds=10.0,
    illustrations=["绘制产品架构图", "绘制流程图"],
  )
  md = ch_mod._render_chapter_markdown(c)
  assert "[[GEN: 绘制产品架构图]]" in md
  assert "[[GEN: 绘制流程图]]" in md


# ─────────────────────────────────────────────────────────────
# _load_keyframe_timestamps
# ─────────────────────────────────────────────────────────────


def test_load_keyframe_timestamps_returns_sorted_seconds(tmp_path: Path) -> None:
  work = tmp_path / "work"
  _write_keyframes(work, [1000, 500, 3000, 2000])
  ts = ch_mod._load_keyframe_timestamps(work, top=10)
  assert ts == [0.5, 1.0, 2.0, 3.0]


def test_load_keyframe_timestamps_limits_to_top(tmp_path: Path) -> None:
  work = tmp_path / "work"
  _write_keyframes(work, [i * 1000 for i in range(20)])
  ts = ch_mod._load_keyframe_timestamps(work, top=5)
  assert len(ts) == 5


def test_load_keyframe_timestamps_returns_empty_when_no_manifest(tmp_path: Path) -> None:
  work = tmp_path / "work"
  work.mkdir()
  assert ch_mod._load_keyframe_timestamps(work, top=10) == []


# ─────────────────────────────────────────────────────────────
# _load_corrections
# ─────────────────────────────────────────────────────────────


def test_load_corrections_extracts_unique_candidates(tmp_path: Path) -> None:
  work = tmp_path / "work"
  work.mkdir()
  corrections = {
    "corrections": [
      {"candidates": [{"text": "达摩盘"}, {"text": "选品技巧"}]},
      {"candidates": [{"text": "达摩盘"}, {"text": "流量"}]},  # 达摩盘 重复
    ],
  }
  (work / "asr").mkdir()
  (work / "asr" / "asr_corrections.json").write_text(
    json.dumps(corrections, ensure_ascii=False), encoding="utf-8"
  )
  text = ch_mod._load_corrections(work)
  assert "- 达摩盘" in text
  assert "- 选品技巧" in text
  assert "- 流量" in text
  # 达摩盘 应该只出现一次
  assert text.count("达摩盘") == 1


def test_load_corrections_returns_empty_when_no_file(tmp_path: Path) -> None:
  work = tmp_path / "work"
  work.mkdir()
  assert ch_mod._load_corrections(work) == ""


# ─────────────────────────────────────────────────────────────
# split_chapters 端到端
# ─────────────────────────────────────────────────────────────


def test_split_chapters_end_to_end(tmp_path: Path) -> None:
  work = tmp_path / "work"
  _write_transcript(work, [
    TranscriptSegment(start=0.0, end=60.0, text="本节介绍达摩盘"),
    TranscriptSegment(start=60.0, end=120.0, text="选品策略"),
  ])
  _write_keyframes(work, [10_000, 30_000, 70_000])

  fake = _FakeProvider(replies=json.dumps([
    {
      "title": "第 1 章 入门",
      "summary": "介绍达摩盘",
      "start_seconds": 0.0,
      "end_seconds": 60.0,
      "key_points":["要点 1","要点 2"],
      "image_refs":[10.0, 30.0],
      "illustrations":["绘制架构图"],
    },
    {
      "title": "第 2 章 进阶",
      "summary": "选品策略",
      "start_seconds": 60.0,
      "end_seconds": 120.0,
      "key_points":["选品 A"],
      "image_refs":[70.0],
      "illustrations":[],
    },
  ], ensure_ascii=False))

  report = split_chapters(work, fake)  # type: ignore[arg-type]
  assert len(report.chapters) == 2
  assert report.chapters[0].title == "第 1 章 入门"
  assert report.chapters[1].key_points == ["选品 A"]

  # 文件输出
  out_dir = work / "chapters"
  assert (out_dir / "chapters.json").exists()
  assert (out_dir / "chapter_01.md").exists()
  assert (out_dir / "chapter_02.md").exists()

  # 验证 markdown 内容
  md1 = (out_dir / "chapter_01.md").read_text(encoding="utf-8")
  assert "## 第 1 章 入门" in md1
  assert "要点 1" in md1


def test_split_chapters_prompt_includes_transcript(tmp_path: Path) -> None:
  """验证 prompt 包含逐字稿内容(防止 prompt 构造错误)。"""
  work = tmp_path / "work"
  _write_transcript(work, [
    TranscriptSegment(start=0.0, end=60.0, text="特殊文本关键词 XYZ"),
  ])
  _write_keyframes(work, [10_000])

  fake = _FakeProvider(replies="[]")
  split_chapters(work, fake)  # type: ignore[arg-type]

  assert "特殊文本关键词 XYZ" in fake.last_prompt
  assert "10.00" in fake.last_prompt


def test_split_chapters_raises_when_no_transcript(tmp_path: Path) -> None:
  work = tmp_path / "empty_work"
  work.mkdir()
  fake = _FakeProvider("[]")
  with pytest.raises(FileNotFoundError, match="transcript.jsonl"):
    split_chapters(work, fake)  # type: ignore[arg-type]


def test_split_chapters_uses_custom_output_dir(tmp_path: Path) -> None:
  work = tmp_path / "work"
  _write_transcript(work, [
    TranscriptSegment(start=0.0, end=10.0, text="x"),
  ])
  _write_keyframes(work, [1_000])

  fake = _FakeProvider(replies=json.dumps([
    {"title": "A", "summary": "s", "start_seconds": 0.0, "end_seconds": 10.0,
     "key_points": [], "image_refs": [], "illustrations": []},
  ], ensure_ascii=False))

  custom = tmp_path / "my_chapters"
  report = split_chapters(work, fake, output_dir=custom)  # type: ignore[arg-type]
  assert (custom / "chapters.json").exists()
  assert (custom / "chapter_01.md").exists()
  assert report.provider == "fake"


def test_split_chapters_records_provider_and_model_in_report(tmp_path: Path) -> None:
  work = tmp_path / "work"
  _write_transcript(work, [TranscriptSegment(start=0.0, end=10.0, text="x")])
  _write_keyframes(work, [1_000])

  fake = _FakeProvider(replies="[]")
  report = split_chapters(work, fake)  # type: ignore[arg-type]
  assert report.provider == "fake"
  assert report.model == "fake-model"


def test_split_chapters_propagates_llm_exception(tmp_path: Path) -> None:
  """LLM 抛异常应上抛,不静默。"""
  work = tmp_path / "work"
  _write_transcript(work, [TranscriptSegment(start=0.0, end=10.0, text="x")])
  _write_keyframes(work, [1_000])

  fake = _FakeProvider(replies=[])  # 第一次调用即抛
  with pytest.raises(RuntimeError, match="no more fake replies"):
    split_chapters(work, fake)  # type: ignore[arg-type]
