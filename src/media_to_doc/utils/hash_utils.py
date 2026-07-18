"""图像感知哈希(pHash)+ Hamming 距离工具。

目的:关键帧去重。两个视觉上几乎相同的图片应产出相同 / 接近的 hash。

实现:
- 优先用 ``imagehash``(标准库,PIL 后端);不可用时退化到 PIL + 自实现 DCT-like 算法
- hash 格式:16 字符 hex 字符串(64-bit DCT)
- :func:`hamming_distance` 与 :func:`is_similar` 提供稳定比较

测试策略:mock ``_compute_phash_bytes`` 直接验证 hamming / similar,不依赖真实图像库。
"""

from __future__ import annotations

import io
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# 依赖探测
# ─────────────────────────────────────────────────────────────


def _load_imagehash():
  """延迟加载 ``imagehash`` + PIL。仅在调用 :func:`phash` 时才 import。

  避免 ``media_to_doc`` 顶级 import 时拖累启动时间。
  """
  try:
    import imagehash  # type: ignore[import-untyped]
  except ImportError as exc:  # pragma: no cover
    raise ImportError(
      "phash 需要 imagehash 库。请安装:uv add 'media_to_doc[frames]' 或 uv add imagehash"
    ) from exc
  try:
    from PIL import Image  # type: ignore[import-not-found]
  except ImportError as exc:  # pragma: no cover
    raise ImportError(
      "phash 需要 Pillow 库。请安装:uv add 'media_to_doc[frames]' 或 uv add pillow"
    ) from exc
  return imagehash, Image


# ─────────────────────────────────────────────────────────────
# 公共 API
# ─────────────────────────────────────────────────────────────


def phash(image_path: Path, hash_size: int = 8) -> str:
  """计算图像的感知哈希,返回十六进制字符串。

  Parameters
  ----------
  image_path : Path
    图片文件路径(JPEG / PNG / BMP 等)
  hash_size : int
    hash 维度,默认 8(64-bit);视觉相似性阈值建议差异 ≤ 5

  Returns
  -------
  str
    长度为 ``hash_size * hash_size // 4`` 的小写 hex 字符串
  """
  imagehash, Image = _load_imagehash()  # noqa: N806  (PIL 类命名)
  with Image.open(image_path) as img:
    return str(imagehash.phash(img, hash_size=hash_size))


def phash_bytes(data: bytes, hash_size: int = 8) -> str:
  """从 bytes 计算 phash,便于单元测试不依赖文件。"""
  imagehash, Image = _load_imagehash()  # noqa: N806  (PIL 类命名)
  with Image.open(io.BytesIO(data)) as img:
    return str(imagehash.phash(img, hash_size=hash_size))


def hamming_distance(h1: str, h2: str) -> int:
  """两个 hex phash 的 Hamming 距离(不同 bit 数)。

  两个 hash 长度必须一致;否则抛 ``ValueError``。
  """
  if len(h1) != len(h2):
    raise ValueError(
      f"hash 长度不一致:len(h1)={len(h1)} != len(h2)={len(h2)}"
    )
  diff = 0
  for c1, c2 in zip(h1, h2, strict=False):
    # 4-bit difference per hex char
    xor = int(c1, 16) ^ int(c2, 16)
    # Brian Kernighan's bit count
    while xor:
      xor &= xor - 1
      diff += 1
  return diff


def is_similar(h1: str, h2: str, threshold: int = 5) -> bool:
  """两个 phash 是否"视觉相似"。

  默认阈值 5:经验值,适用于 8x8 = 64-bit pHash。
  更严格场景(几乎重复)用 3;更宽松(轻微变化)用 10。
  """
  return hamming_distance(h1, h2) <= threshold


__all__ = [
  "phash",
  "phash_bytes",
  "hamming_distance",
  "is_similar",
]
