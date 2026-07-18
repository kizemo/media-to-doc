"""ffmpeg / ffprobe 路径探测 + subprocess 包装。

设计要点:
- Windows 上 ffmpeg 不一定在 PATH(用户从 gyan.dev / BtbN / winget 装都可能)
- 自动探测顺序:``shutil.which`` → 常见安装目录 → 用户自定义(MEDIA_TO_DOC_FFMPEG)
- ``run_ffmpeg()`` / ``run_ffprobe()`` 失败时抛 ``FFmpegError``(带 exit code + stderr)
- 测试可通过 ``monkeypatch`` 探测函数,无需真实二进制
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# 异常
# ─────────────────────────────────────────────────────────────


class FFmpegError(RuntimeError):
  """ffmpeg / ffprobe 执行失败。

  Attributes
  ----------
  cmd : list[str]
    实际执行的命令(便于排错)
  returncode : int
    进程退出码
  stderr : str
    进程 stderr 全文(可能很长)
  """

  def __init__(self, message: str, *, cmd: list[str], returncode: int, stderr: str) -> None:
    super().__init__(message)
    self.cmd = cmd
    self.returncode = returncode
    self.stderr = stderr

  def __repr__(self) -> str:
    return (
      f"FFmpegError({self.args[0]!r}, returncode={self.returncode}, "
      f"cmd={self.cmd!r})"
    )


# ─────────────────────────────────────────────────────────────
# 环境变量覆盖
# ─────────────────────────────────────────────────────────────

ENV_FFMPEG = "MEDIA_TO_DOC_FFMPEG"
ENV_FFPROBE = "MEDIA_TO_DOC_FFPROBE"


# ─────────────────────────────────────────────────────────────
# 路径探测
# ─────────────────────────────────────────────────────────────

# Windows 常见 ffmpeg 安装位置(可被环境变量覆盖)
_WINDOWS_FFMPEG_CANDIDATES: tuple[str, ...] = (
  r"C:\ffmpeg\bin\ffmpeg.exe",
  r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
  r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
  r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
)

_WINDOWS_FFPROBE_CANDIDATES: tuple[str, ...] = tuple(
  path.replace("ffmpeg.exe", "ffprobe.exe") for path in _WINDOWS_FFMPEG_CANDIDATES
)


def _resolve(env_var: str, windows_candidates: tuple[str, ...], binary: str) -> Path | None:
  """探测二进制路径,优先级:环境变量 → PATH → Windows 常见位置。

  返回 ``None`` 表示未找到(由调用者决定是否抛错)。
  """
  env_value = os.environ.get(env_var)
  if env_value:
    path = Path(env_value).expanduser()
    if path.is_file():
      return path

  which_path = shutil.which(binary)
  if which_path:
    return Path(which_path)

  if os.name == "nt":
    for candidate in windows_candidates:
      if Path(candidate).is_file():
        return Path(candidate)

  return None


def find_ffmpeg() -> Path | None:
  """探测 ffmpeg 路径,未找到返回 ``None``。"""
  return _resolve(ENV_FFMPEG, _WINDOWS_FFMPEG_CANDIDATES, "ffmpeg")


def find_ffprobe() -> Path | None:
  """探测 ffprobe 路径,未找到返回 ``None``。"""
  return _resolve(ENV_FFPROBE, _WINDOWS_FFPROBE_CANDIDATES, "ffprobe")


def is_ffmpeg_available() -> bool:
  """``find_ffmpeg() is not None`` 的便利方法。"""
  return find_ffmpeg() is not None


def is_ffprobe_available() -> bool:
  return find_ffprobe() is not None


# ─────────────────────────────────────────────────────────────
# subprocess 包装
# ─────────────────────────────────────────────────────────────


def _run(
  binary_label: str,
  binary_path: Path,
  args: list[str],
  *,
  timeout: float,
  check: bool,
) -> subprocess.CompletedProcess[str]:
  """执行二进制,捕获 stdout / stderr,失败时抛 :class:`FFmpegError`。"""
  cmd = [str(binary_path), *args]
  try:
    result = subprocess.run(
      cmd,
      capture_output=True,
      text=True,
      timeout=timeout,
      check=False,
    )
  except subprocess.TimeoutExpired as exc:
    raise FFmpegError(
      f"{binary_label} timeout after {timeout}s",
      cmd=cmd,
      returncode=-1,
      stderr=str(exc),
    ) from exc

  if check and result.returncode != 0:
    raise FFmpegError(
      f"{binary_label} failed (rc={result.returncode}): {result.stderr.strip()[:500]}",
      cmd=cmd,
      returncode=result.returncode,
      stderr=result.stderr,
    )

  return result


def run_ffmpeg(
  args: list[str],
  *,
  timeout: float = 600.0,
  check: bool = True,
) -> subprocess.CompletedProcess[str]:
  """运行 ffmpeg。

  Parameters
  ----------
  args : list[str]
    传给 ffmpeg 的参数(不含二进制本身)
  timeout : float
    超时秒数,默认 10 分钟
  check : bool
    失败是否抛 ``FFmpegError``,默认 True

  Raises
  ------
  FileNotFoundError
    ffmpeg 未找到
  FFmpegError
    超时或非零退出
  """
  binary = find_ffmpeg()
  if binary is None:
    raise FileNotFoundError(
      "ffmpeg 未找到。请安装 ffmpeg 或设置环境变量 MEDIA_TO_DOC_FFMPEG。"
    )
  return _run("ffmpeg", binary, args, timeout=timeout, check=check)


def run_ffprobe(
  args: list[str],
  *,
  timeout: float = 30.0,
  check: bool = True,
) -> subprocess.CompletedProcess[str]:
  """运行 ffprobe,默认 30s 超时(只查元数据)。"""
  binary = find_ffprobe()
  if binary is None:
    raise FileNotFoundError(
      "ffprobe 未找到。请安装 ffmpeg/ffprobe 或设置环境变量 MEDIA_TO_DOC_FFPROBE。"
    )
  return _run("ffprobe", binary, args, timeout=timeout, check=check)


__all__ = [
  "FFmpegError",
  "ENV_FFMPEG",
  "ENV_FFPROBE",
  "find_ffmpeg",
  "find_ffprobe",
  "is_ffmpeg_available",
  "is_ffprobe_available",
  "run_ffmpeg",
  "run_ffprobe",
]
