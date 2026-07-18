"""media_to_doc utils 子包。

Phase 1 W1 提供:
- ``ffmpeg_utils`` — ffmpeg / ffprobe 路径探测 + subprocess wrapper
- ``hash_utils`` — pHash + hamming distance(关键帧去重用)
- ``progress`` — rich.progress 统一接口(可全局静默)

Phase 4 + 视情况扩展:audio utils / OCR utils 等。
"""

from __future__ import annotations

from . import ffmpeg_utils, hash_utils, progress

__all__ = [
  "ffmpeg_utils",
  "hash_utils",
  "progress",
]
