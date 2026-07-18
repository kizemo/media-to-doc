"""``media_to_doc.utils.ffmpeg_utils`` 单元测试。

策略:
- 不依赖真实 ffmpeg 二进制,通过 monkeypatch ``_resolve`` 注入探测结果
- ``run_ffmpeg`` 通过 monkeypatch ``subprocess.run`` 覆盖,验证参数与异常路径
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from media_to_doc.utils import ffmpeg_utils
from media_to_doc.utils.ffmpeg_utils import (
  FFmpegError,
  find_ffmpeg,
  find_ffprobe,
  is_ffmpeg_available,
  run_ffmpeg,
  run_ffprobe,
)

# ─────────────────────────────────────────────────────────────
# 路径探测
# ─────────────────────────────────────────────────────────────


def test_find_ffmpeg_via_which(monkeypatch: pytest.MonkeyPatch) -> None:
  """PATH 中找到 → 返回 Path。"""
  fake_path = Path("C:/ffmpeg/bin/ffmpeg.exe")
  monkeypatch.setattr(ffmpeg_utils.shutil, "which", lambda name: str(fake_path) if name == "ffmpeg" else None)
  monkeypatch.setattr(ffmpeg_utils.os, "name", "nt")
  monkeypatch.delenv("MEDIA_TO_DOC_FFMPEG", raising=False)

  result = find_ffmpeg()
  assert result == fake_path
  assert is_ffmpeg_available() is True


def test_find_ffmpeg_env_var_priority(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
  """环境变量优先级最高(即使 PATH 中也有其它)。"""
  fake = tmp_path / "my_ffmpeg.exe"
  fake.write_bytes(b"")
  monkeypatch.setenv("MEDIA_TO_DOC_FFMPEG", str(fake))
  # PATH 探测不存在
  monkeypatch.setattr(ffmpeg_utils.shutil, "which", lambda name: None)

  result = find_ffmpeg()
  assert result == fake


def test_find_ffmpeg_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
  """三处都未找到 → 返回 None。"""
  monkeypatch.delenv("MEDIA_TO_DOC_FFMPEG", raising=False)
  monkeypatch.setattr(ffmpeg_utils.shutil, "which", lambda name: None)
  # Windows 候选路径也不存在
  monkeypatch.setattr(
    ffmpeg_utils, "_WINDOWS_FFMPEG_CANDIDATES", tuple(p for p in ("/nonexistent/ffmpeg.exe",))
  )
  monkeypatch.setattr(ffmpeg_utils.os, "name", "nt")

  assert find_ffmpeg() is None
  assert is_ffmpeg_available() is False


def test_find_ffprobe_separate_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
  """ffprobe 与 ffmpeg 各自独立探测。"""
  ffprobe = tmp_path / "ffprobe.exe"
  ffprobe.write_bytes(b"")
  monkeypatch.setenv("MEDIA_TO_DOC_FFPROBE", str(ffprobe))
  monkeypatch.setattr(ffmpeg_utils.shutil, "which", lambda name: None)

  result = find_ffprobe()
  assert result == ffprobe
  assert result.is_file()


# ─────────────────────────────────────────────────────────────
# run_ffmpeg 异常路径
# ─────────────────────────────────────────────────────────────


def test_run_ffmpeg_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
  """找不到 ffmpeg → FileNotFoundError。"""
  monkeypatch.setattr(ffmpeg_utils, "find_ffmpeg", lambda: None)

  with pytest.raises(FileNotFoundError, match="ffmpeg 未找到"):
    run_ffmpeg(["-version"])


def test_run_ffmpeg_failure_raises(monkeypatch: pytest.MonkeyPatch) -> None:
  """非零退出 + check=True → FFmpegError,带 cmd 与 stderr。"""
  fake_bin = Path("/fake/ffmpeg.exe")
  monkeypatch.setattr(ffmpeg_utils, "find_ffmpeg", lambda: fake_bin)
  fake_proc = MagicMock(returncode=1, stdout="", stderr="bad codec")
  monkeypatch.setattr(ffmpeg_utils.subprocess, "run", lambda *a, **kw: fake_proc)

  with pytest.raises(FFmpegError) as exc_info:
    run_ffmpeg(["-i", "x.mp4"])

  assert exc_info.value.returncode == 1
  assert "bad codec" in exc_info.value.stderr
  assert exc_info.value.cmd[0] == str(fake_bin)


def test_run_ffmpeg_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
  """subprocess.TimeoutExpired → FFmpegError。"""
  import subprocess

  fake_bin = Path("/fake/ffmpeg.exe")
  monkeypatch.setattr(ffmpeg_utils, "find_ffmpeg", lambda: fake_bin)

  def raise_timeout(*args: object, **kwargs: object) -> None:
    raise subprocess.TimeoutExpired(cmd=["ffmpeg"], timeout=1.0)

  monkeypatch.setattr(ffmpeg_utils.subprocess, "run", raise_timeout)

  with pytest.raises(FFmpegError, match="timeout"):
    run_ffmpeg(["-i", "x.mp4"], timeout=1.0)


def test_run_ffmpeg_check_false_returns_result(monkeypatch: pytest.MonkeyPatch) -> None:
  """check=False 时返回 CompletedProcess,不抛。"""
  fake_bin = Path("/fake/ffmpeg.exe")
  monkeypatch.setattr(ffmpeg_utils, "find_ffmpeg", lambda: fake_bin)
  fake_proc = MagicMock(returncode=0, stdout="b'', b''")
  fake_proc.stdout = "ffmpeg version 6.0"
  fake_proc.stderr = ""
  monkeypatch.setattr(ffmpeg_utils.subprocess, "run", lambda *a, **kw: fake_proc)

  result = run_ffmpeg(["-version"], check=False)
  assert result.stdout == "ffmpeg version 6.0"


def test_run_ffprobe_uses_30s_default_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
  """ffprobe 默认 30s 超时(比 ffmpeg 短)。"""
  fake_bin = Path("/fake/ffprobe.exe")
  monkeypatch.setattr(ffmpeg_utils, "find_ffprobe", lambda: fake_bin)
  captured: dict[str, object] = {}

  def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
    captured["cmd"] = cmd
    captured["kwargs"] = kwargs
    return MagicMock(returncode=0, stdout="{}", stderr="")

  monkeypatch.setattr(ffmpeg_utils.subprocess, "run", fake_run)
  run_ffprobe(["-v", "quiet", "-print_format", "json", "-show_format", "x.mp4"])

  assert captured["kwargs"]["timeout"] == 30.0  # type: ignore[index]
