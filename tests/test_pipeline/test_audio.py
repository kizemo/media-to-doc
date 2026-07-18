"""``media_to_doc.pipeline.audio`` 单元测试。

策略:
- ffmpeg 调用通过 monkeypatch ``media_to_doc.utils.ffmpeg_utils.run_ffmpeg`` 替换
- ``find_media`` 用真实文件创建验证
- 不依赖真实 ffmpeg 或视频
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from media_to_doc.pipeline import audio
from media_to_doc.pipeline.audio import (
  SUPPORTED_AUDIO_EXTS,
  SUPPORTED_VIDEO_EXTS,
  find_media,
  prepare_audio,
)

# ─────────────────────────────────────────────────────────────
# find_media
# ─────────────────────────────────────────────────────────────


def test_find_media_returns_first_video(tmp_path: Path) -> None:
  """找到首个视频文件(按字典序排序后首个)。"""
  (tmp_path / "b.mp4").write_bytes(b"")
  (tmp_path / "a.mov").write_bytes(b"")
  (tmp_path / "ignore.txt").write_text("ignored")

  result = find_media(tmp_path)
  # 排序后首个 = a.mov
  assert result.name == "a.mov"


def test_find_media_recursive(tmp_path: Path) -> None:
  """递归查找子目录。"""
  (tmp_path / "sub").mkdir()
  (tmp_path / "sub" / "course.mp4").write_bytes(b"")

  result = find_media(tmp_path)
  assert result.name == "course.mp4"


def test_find_media_no_match(tmp_path: Path) -> None:
  """无候选文件 → FileNotFoundError。"""
  (tmp_path / "readme.md").write_text("nothing here")

  with pytest.raises(FileNotFoundError, match="未找到支持的媒体文件"):
    find_media(tmp_path)


def test_find_media_inbox_not_exists(tmp_path: Path) -> None:
  """inbox 不存在 → FileNotFoundError。"""
  missing = tmp_path / "no-such-inbox"
  with pytest.raises(FileNotFoundError):
    find_media(missing)


def test_find_media_supports_audio_input(tmp_path: Path) -> None:
  """音频文件也能被识别。"""
  for ext in (".mp3", ".wav", ".m4a"):
    (tmp_path / f"audio{ext}").write_bytes(b"")

  result = find_media(tmp_path)
  assert result.suffix in SUPPORTED_AUDIO_EXTS


# ─────────────────────────────────────────────────────────────
# prepare_audio(视频转 wav)
# ─────────────────────────────────────────────────────────────


def test_prepare_audio_calls_ffmpeg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
  """视频文件 → 调 ffmpeg 转 wav。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "course.mp4").write_bytes(b"fake video content")
  work = tmp_path / "work"

  captured: dict[str, object] = {}

  def fake_run_ffmpeg(args: list[str], **kwargs: object) -> MagicMock:
    captured["args"] = args
    captured["kwargs"] = kwargs
    # 模拟 ffmpeg 写出 wav
    output = Path(args[-1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"RIFF....WAVE")
    return MagicMock(returncode=0)

  monkeypatch.setattr(
    "media_to_doc.pipeline.audio.run_ffmpeg", fake_run_ffmpeg,
  )

  output = prepare_audio(inbox, work)

  assert output == work / "asr" / "audio.wav"
  assert output.exists()
  # 关键参数必须出现
  args = captured["args"]
  assert "-i" in args
  assert "-acodec" in args
  assert "pcm_s16le" in args
  assert "16" in str(args[args.index("-ar") + 1])  # -ar 16000


def test_prepare_audio_skips_ffmpeg_for_audio_input(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """音频输入 → 直接复制,不调 ffmpeg。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  audio_src = inbox / "podcast.mp3"
  audio_src.write_bytes(b"original mp3 bytes")
  work = tmp_path / "work"

  called = {"n": 0}

  def fake_run_ffmpeg(args: list[str], **kwargs: object) -> None:
    called["n"] += 1

  monkeypatch.setattr(
    "media_to_doc.pipeline.audio.run_ffmpeg", fake_run_ffmpeg,
  )

  output = prepare_audio(inbox, work)
  assert called["n"] == 0  # 关键:未调 ffmpeg
  assert output == work / "asr" / "audio.wav"
  assert output.read_bytes() == b"original mp3 bytes"


def test_prepare_audio_overwrites_existing(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """已存在的 output.wav 先删除再抽(幂等)。"""
  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "course.mp4").write_bytes(b"")
  work = tmp_path / "work"
  asr_dir = work / "asr"
  asr_dir.mkdir(parents=True)
  existing = asr_dir / "audio.wav"
  existing.write_bytes(b"OLD CONTENT")

  def fake_run_ffmpeg(args: list[str], **kwargs: object) -> None:
    Path(args[-1]).write_bytes(b"NEW CONTENT")

  monkeypatch.setattr(
    "media_to_doc.pipeline.audio.run_ffmpeg", fake_run_ffmpeg,
  )

  output = prepare_audio(inbox, work)
  assert output.read_bytes() == b"NEW CONTENT"
  assert existing == output  # 文件名一致


def test_prepare_audio_propagates_ffmpeg_errors(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """ffmpeg 失败 → 异常上抛(由 runner 捕获 mark failed)。"""
  from media_to_doc.utils.ffmpeg_utils import FFmpegError

  inbox = tmp_path / "inbox"
  inbox.mkdir()
  (inbox / "bad.mp4").write_bytes(b"")
  work = tmp_path / "work"

  def fake_run_ffmpeg(args: list[str], **kwargs: object) -> None:
    raise FFmpegError(
      "Invalid data found when processing input",
      cmd=["ffmpeg"],
      returncode=1,
      stderr="Invalid data found",
    )

  monkeypatch.setattr(
    "media_to_doc.pipeline.audio.run_ffmpeg", fake_run_ffmpeg,
  )

  with pytest.raises(FFmpegError, match="Invalid data"):
    prepare_audio(inbox, work)


# ─────────────────────────────────────────────────────────────
# 常量 sanity
# ─────────────────────────────────────────────────────────────


def test_supported_exts_combine_video_and_audio() -> None:
  """SUPPORTED_EXTS = video + audio。"""
  assert set(SUPPORTED_VIDEO_EXTS).union(SUPPORTED_AUDIO_EXTS) == set(audio.SUPPORTED_EXTS)


def test_wav_is_in_audio_extensions() -> None:
  """.wav 必须出现在 SUPPORTED_AUDIO_EXTS(注意:就地复用,不要 double-suffix)。"""
  assert ".wav" in SUPPORTED_AUDIO_EXTS
