"""``media_to_doc.utils.hash_utils`` 单元测试。

策略:
- ``hamming_distance`` / ``is_similar`` 是纯函数,直接覆盖
- ``phash_bytes`` 需要 imagehash + PIL,若未装直接 skip(CI 不强制)
"""

from __future__ import annotations

import io

import pytest

from media_to_doc.utils.hash_utils import (
  hamming_distance,
  is_similar,
  phash_bytes,
)

# ─────────────────────────────────────────────────────────────
# hamming_distance
# ─────────────────────────────────────────────────────────────


def test_hamming_distance_identical() -> None:
  """相同 hash → 距离 0。"""
  assert hamming_distance("abcdef1234567890", "abcdef1234567890") == 0


def test_hamming_distance_one_bit_diff() -> None:
  """1 bit 差异 → 距离 1。"""
  # '0' (0000) vs '1' (0001) → 1 bit
  assert hamming_distance("0", "1") == 1
  # 1 字符差 1 bit
  assert hamming_distance("0", "2") == 1  # 0000 vs 0010
  assert hamming_distance("0", "4") == 1  # 0000 vs 0100


def test_hamming_distance_full_nibble_diff() -> None:
  """整个 nibble 取反 → 距离 4。"""
  assert hamming_distance("0", "f") == 4


def test_hamming_distance_multi_character() -> None:
  """多个字符的差异累加。"""
  # 'a' = 1010, 'b' = 1011 → 1 bit
  # '0' = 0000, '1' = 0001 → 1 bit
  # 总计 2 bits
  assert hamming_distance("a0", "b1") == 2
  # 同字符差全 nibble → 4 bits
  assert hamming_distance("00", "ff") == 8


def test_hamming_distance_unequal_length() -> None:
  """长度不等 → ValueError。"""
  with pytest.raises(ValueError, match="hash 长度不一致"):
    hamming_distance("ab", "abc")


# ─────────────────────────────────────────────────────────────
# is_similar
# ─────────────────────────────────────────────────────────────


def test_is_similar_default_threshold() -> None:
  """阈值 5:差距 ≤ 5 视为相似。"""
  h1 = "0000000000000000"  # 全 0
  h2_close = "0100000000000000"  # 1 bit different
  h3_far = h1[:7] + "f" + h1[8:]  # 4 bits different

  assert is_similar(h1, h2_close) is True
  assert is_similar(h1, h3_far) is True  # 4 ≤ 5


def test_is_similar_strict_threshold() -> None:
  """阈值 3:同样差距视为不相似。"""
  h1 = "0000000000000000"
  h2 = h1[:7] + "f" + h1[8:]  # 4 bits different

  assert is_similar(h1, h2, threshold=3) is False
  assert is_similar(h1, h2, threshold=4) is True


# ─────────────────────────────────────────────────────────────
# phash_bytes(可选,依赖 imagehash + PIL)
# ─────────────────────────────────────────────────────────────


def test_phash_bytes_returns_hex_string() -> None:
  """phash_bytes 必须返回 hex 字符串(由真实图像计算)。"""
  imagehash = pytest.importorskip("imagehash")
  pil_image = pytest.importorskip("PIL.Image")
  _ = (imagehash, pil_image)

  # 构造 32x32 红色 RGB 图片
  img = pil_image.new("RGB", (32, 32), color=(255, 0, 0))
  buf = io.BytesIO()
  img.save(buf, format="PNG")
  data = buf.getvalue()

  h = phash_bytes(data)
  assert isinstance(h, str)
  # 默认 8x8 = 64-bit → 16 chars hex
  assert len(h) == 16
  int(h, 16)  # 必须是合法 hex 字符串


def test_phash_bytes_stable() -> None:
  """同一图像两次调用 → 相同 hash。"""
  pytest.importorskip("imagehash")
  pil_image = pytest.importorskip("PIL.Image")

  img = pil_image.new("RGB", (32, 32), color=(128, 128, 128))
  buf = io.BytesIO()
  img.save(buf, format="PNG")

  h1 = phash_bytes(buf.getvalue())
  h2 = phash_bytes(buf.getvalue())
  assert h1 == h2


def test_phash_bytes_similar_images_small_distance() -> None:
  """两张相似图像 → pHash hamming 距离小。"""
  pytest.importorskip("imagehash")
  pil_image = pytest.importorskip("PIL.Image")

  img_a = pil_image.new("RGB", (32, 32), color=(100, 100, 100))
  img_b = pil_image.new("RGB", (32, 32), color=(110, 110, 110))  # 微变

  buf_a, buf_b = io.BytesIO(), io.BytesIO()
  img_a.save(buf_a, format="PNG")
  img_b.save(buf_b, format="PNG")

  h_a = phash_bytes(buf_a.getvalue())
  h_b = phash_bytes(buf_b.getvalue())
  assert is_similar(h_a, h_b, threshold=10)
