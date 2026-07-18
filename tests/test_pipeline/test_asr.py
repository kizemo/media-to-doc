"""``media_to_doc.pipeline.asr`` 单元测试。

策略:
- 真 faster-whisper 不可用 → mock _transcribe_with_whisper 返回假 segments
- TranscriptSegment / jsonl 往返纯函数测试
- 不依赖真实 GPU / Whisper 模型
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from media_to_doc.pipeline.asr import (
  TranscriptSegment,
  read_transcript_jsonl,
  transcribe,
  write_transcript_jsonl,
)

# ─────────────────────────────────────────────────────────────
# TranscriptSegment 序列化
# ─────────────────────────────────────────────────────────────


def test_segment_to_jsonl_omits_none_words() -> None:
  """words=None 时不写 ``words`` 字段(jsonl 行更紧凑)。"""
  seg = TranscriptSegment(start=0.0, end=1.5, text="hello", words=None)
  line = seg.to_jsonl()
  payload = json.loads(line)
  assert payload == {"start": 0.0, "end": 1.5, "text": "hello", "speaker": None}


def test_segment_to_jsonl_includes_words_when_present() -> None:
  """words 有值时正常序列化。"""
  seg = TranscriptSegment(
    start=2.0,
    end=3.0,
    text="你好",
    words=[{"start": 2.0, "end": 2.5, "word": "你"}, {"start": 2.5, "end": 3.0, "word": "好"}],
  )
  payload = json.loads(seg.to_jsonl())
  assert payload["text"] == "你好"
  assert len(payload["words"]) == 2


def test_segment_jsonl_chinese_safe() -> None:
  """中文 ensure_ascii=False,直接存原始字符。"""
  seg = TranscriptSegment(start=0.0, end=2.0, text="培训课程讲义生成")
  line = seg.to_jsonl()
  assert "培训课程讲义生成" in line
  assert "\\u" not in line  # 没有 escape


# ─────────────────────────────────────────────────────────────
# write_transcript_jsonl / read_transcript_jsonl 往返
# ─────────────────────────────────────────────────────────────


def test_write_then_read_transcript_roundtrip(tmp_path: Path) -> None:
  """写读一致。"""
  segments = [
    TranscriptSegment(start=0.0, end=2.0, text="第一段"),
    TranscriptSegment(start=2.0, end=4.5, text="second segment"),
    TranscriptSegment(start=4.5, end=6.0, text="第三段", speaker="S1"),
  ]
  output = tmp_path / "transcript.jsonl"
  count = write_transcript_jsonl(iter(segments), output)

  assert count == 3
  assert output.exists()

  loaded = read_transcript_jsonl(output)
  assert len(loaded) == 3
  assert loaded[0].text == "第一段"
  assert loaded[2].speaker == "S1"


def test_write_creates_parent_dir(tmp_path: Path) -> None:
  """父目录不存在时自动创建。"""
  output = tmp_path / "deep" / "nested" / "transcript.jsonl"
  write_transcript_jsonl(iter([TranscriptSegment(start=0.0, end=1.0, text="x")]), output)
  assert output.exists()


def test_read_skips_empty_lines(tmp_path: Path) -> None:
  """读取时跳过空行。"""
  output = tmp_path / "transcript.jsonl"
  output.write_text(
    '{"start": 0.0, "end": 1.0, "text": "a"}\n'
    '\n'
    '{"start": 1.0, "end": 2.0, "text": "b"}\n',
    encoding="utf-8",
  )
  loaded = read_transcript_jsonl(output)
  assert len(loaded) == 2


# ─────────────────────────────────────────────────────────────
# transcribe(主入口,mock faster-whisper)
# ─────────────────────────────────────────────────────────────


def _patch_whisper(monkeypatch: pytest.MonkeyPatch, fake_segments: list[TranscriptSegment]) -> None:
  """替换 _transcribe_with_whisper,返回固定 segments。"""
  import media_to_doc.pipeline.asr as asr_mod

  def fake_transcribe(audio_path: Path, **kwargs: object) -> Iterator[TranscriptSegment]:
    assert audio_path.exists(), "audio.wav 必须存在"
    return iter(fake_segments)

  monkeypatch.setattr(asr_mod, "_transcribe_with_whisper", fake_transcribe)


def test_transcribe_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
  """完整流程:audio.wav → mock whisper → transcript.jsonl。"""
  asr_dir = tmp_path / "asr"
  asr_dir.mkdir()
  (asr_dir / "audio.wav").write_bytes(b"fake wav")

  fake_segments = [
    TranscriptSegment(start=0.0, end=2.0, text="你好"),
    TranscriptSegment(start=2.0, end=4.5, text="世界"),
  ]
  _patch_whisper(monkeypatch, fake_segments)

  output = transcribe(tmp_path)

  assert output == tmp_path / "asr" / "transcript.jsonl"
  loaded = read_transcript_jsonl(output)
  assert [s.text for s in loaded] == ["你好", "世界"]


def test_transcribe_requires_audio_wav(tmp_path: Path) -> None:
  """audio.wav 缺失 → FileNotFoundError。"""
  with pytest.raises(FileNotFoundError, match="audio.wav"):
    transcribe(tmp_path)


def test_transcribe_propagates_whisper_errors(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """whisper 抛异常 → transcribe 不吞。"""
  asr_dir = tmp_path / "asr"
  asr_dir.mkdir()
  (asr_dir / "audio.wav").write_bytes(b"")

  import media_to_doc.pipeline.asr as asr_mod

  def boom(*args: object, **kwargs: object) -> Iterator[TranscriptSegment]:
    raise RuntimeError("cuda OOM")

  monkeypatch.setattr(asr_mod, "_transcribe_with_whisper", boom)

  with pytest.raises(RuntimeError, match="cuda OOM"):
    transcribe(tmp_path)


def test_transcribe_passes_kwargs_to_whisper(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """transcribe 的 model/device kwargs 透传到下层。"""
  asr_dir = tmp_path / "asr"
  asr_dir.mkdir()
  (asr_dir / "audio.wav").write_bytes(b"")

  captured_kwargs: dict[str, object] = {}

  def fake_transcribe(audio_path: Path, **kwargs: object) -> Iterator[TranscriptSegment]:
    captured_kwargs.update(kwargs)
    return iter([TranscriptSegment(start=0.0, end=1.0, text="x")])

  import media_to_doc.pipeline.asr as asr_mod
  monkeypatch.setattr(asr_mod, "_transcribe_with_whisper", fake_transcribe)

  transcribe(tmp_path, model="small", device="cpu", compute_type="int8")

  assert captured_kwargs["model"] == "small"
  assert captured_kwargs["device"] == "cpu"
  assert captured_kwargs["compute_type"] == "int8"


def test_transcribe_returns_output_path(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """返回值必须是 transcript.jsonl 路径(便于 runner 串联)。"""
  asr_dir = tmp_path / "asr"
  asr_dir.mkdir()
  (asr_dir / "audio.wav").write_bytes(b"")

  _patch_whisper(monkeypatch, [TranscriptSegment(start=0.0, end=1.0, text="hi")])

  result = transcribe(tmp_path)
  assert result.name == "transcript.jsonl"
  assert result.parent == asr_dir
