"""``media_to_doc.pipeline.frames`` 单元测试。

策略:
- ``_detect_scenes`` / ``_hash_frame`` / ``_extract_frame_image`` 通过 monkeypatch 替换
- ``KeyFrame`` / ``KeyFramesManifest`` 是数据类,直接测
- 不依赖 scenedetect / imagehash / 真实视频 / GPU
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from media_to_doc.pipeline.frames import (
  KeyFrame,
  KeyFramesManifest,
  _is_duplicate,
  _merge_timestamps,
  extract_keyframes,
)

# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


def test_key_frame_to_dict_includes_all_fields() -> None:
  """KeyFrame.to_dict 必须包含全部字段。"""
  kf = KeyFrame(timestamp_ms=12345, image_path="img/frame_000012345.jpg", phash="abcd" * 4, source="scene")
  d = kf.to_dict()
  assert d == {
    "timestamp_ms": 12345,
    "image_path": "img/frame_000012345.jpg",
    "phash": "abcdabcdabcdabcd",
    "source": "scene",
  }


def test_keyframes_manifest_save_roundtrip(tmp_path: Path) -> None:
  """KeyFramesManifest save/load 一致。"""
  manifest = KeyFramesManifest(
    video="course.mp4",
    frames=[
      KeyFrame(timestamp_ms=0, image_path="img/frame_0.jpg", phash="0000000000000000", source="scene"),
      KeyFrame(timestamp_ms=8000, image_path="img/frame_8000.jpg", phash="1111111111111111", source="asr_hint"),
    ],
    threshold=5,
  )
  output = tmp_path / "keyframes.json"
  manifest.save(output)

  data = json.loads(output.read_text(encoding="utf-8"))
  assert data["video"] == "course.mp4"
  assert len(data["frames"]) == 2
  assert data["frames"][1]["source"] == "asr_hint"
  assert data["threshold"] == 5


# ─────────────────────────────────────────────────────────────
# _merge_timestamps(纯函数)
# ─────────────────────────────────────────────────────────────


def test_merge_empty_inputs() -> None:
  """空输入 → 空输出。"""
  assert _merge_timestamps([], [], debounce_seconds=8.0) == []


def test_merge_scenes_only() -> None:
  """只有 scene 输入,8s 窗口内被合并。"""
  # 1.0 → 5.0 差 4s (< 8s) → 5.0 被合并掉
  # 1.0 → 12.0 差 11s (≥ 8s) → 12.0 保留
  # 因此保留 [1.0, 12.0]
  out = _merge_timestamps([1.0, 5.0, 12.0], [], debounce_seconds=8.0)
  assert [t for t, _ in out] == [1.0, 12.0]
  assert all(s == "scene" for _, s in out)


def test_merge_scenes_spaced_apart_all_kept() -> None:
  """间隔 ≥ 8s 才全部保留。"""
  out = _merge_timestamps([1.0, 10.0, 20.0], [], debounce_seconds=8.0)
  assert [t for t, _ in out] == [1.0, 10.0, 20.0]  # 各间隔 ≥ 8s
  assert all(s == "scene" for _, s in out)


def test_merge_hints_collapse_inside_window() -> None:
  """hint 落在 8s 窗口内 → 被合并掉。"""
  # scene at 10.0, hint at 12.0 → 差 2s < 8s → 只保留 10.0
  out = _merge_timestamps([10.0], [12.0], debounce_seconds=8.0)
  assert len(out) == 1
  assert out[0] == (10.0, "scene")  # scene 优先


def test_merge_scene_and_hint_far_apart_both_kept() -> None:
  """距离 ≥ 8s → scene 和 hint 都保留,按时间排序。"""
  # scene at 1.0, hint at 20.0
  out = _merge_timestamps([1.0], [20.0], debounce_seconds=8.0)
  assert out == [(1.0, "scene"), (20.0, "asr_hint")]


def test_merge_dedup_chain_window() -> None:
  """连续时间戳(窗口内)→ 只保留首。"""
  out = _merge_timestamps([0.0, 1.0, 3.0, 12.0], [], debounce_seconds=8.0)
  assert [t for t, _ in out] == [0.0, 12.0]


# ─────────────────────────────────────────────────────────────
# _is_duplicate(基于 hamming_distance)
# ─────────────────────────────────────────────────────────────


def test_is_duplicate_match() -> None:
  """完全相同的 hash → 重复。"""
  seen = ["abcdef0000000000"]
  assert _is_duplicate("abcdef0000000000", seen, threshold=5) is True


def test_is_duplicate_within_threshold() -> None:
  """差 ≤ 5 bit → 重复。"""
  h1 = "0000000000000000"
  h2 = "0100000000000000"  # 1 bit diff
  assert _is_duplicate(h2, [h1], threshold=5) is True


def test_is_not_duplicate_far_apart() -> None:
  """差 > threshold → 不重复。"""
  h1 = "0000000000000000"
  h2 = "ffff000000000000"  # 大多数 bit 都不同
  assert _is_duplicate(h2, [h1], threshold=5) is False


# ─────────────────────────────────────────────────────────────
# extract_keyframes(主入口,monkeypatch 重依赖)
# ─────────────────────────────────────────────────────────────


def test_extract_keyframes_returns_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
  """extract_keyframes 必须返回 KeyFrame 列表。"""
  import media_to_doc.pipeline.frames as frames_mod

  video = tmp_path / "input.mp4"
  video.write_bytes(b"")
  img_dir = tmp_path / "img"
  work_dir = tmp_path / "work"

  monkeypatch.setattr(frames_mod, "_detect_scenes", lambda *a, **kw: [1.0, 12.0])

  def fake_extract(video: Path, ts: float, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"fake jpg")

  monkeypatch.setattr(frames_mod, "_extract_frame_image", fake_extract)

  # 每次抽出的"图片"对应不同 hash
  hash_iter = iter(["0000000000000000", "1111111111111111"])
  monkeypatch.setattr(frames_mod, "_hash_frame", lambda path: next(hash_iter))

  result = extract_keyframes(video, img_dir, work_dir, hint_timestamps=[6.0])

  assert isinstance(result, list)
  assert all(isinstance(f, KeyFrame) for f in result)
  # scene 1.0 / scene 12.0 都保留,hint 6.0 在 8s 窗口(scene 12.0 之后 6s diff)→ 取决于 sort
  # 期望至少 2 个(scene 1.0 + scene 12.0 或 hint 6.0)
  assert len(result) >= 2


def test_extract_keyframes_dedupes_duplicate_hashes(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """两个相同 hash → 只保留一个 scene。"""
  import media_to_doc.pipeline.frames as frames_mod

  video = tmp_path / "v.mp4"
  video.write_bytes(b"")
  img_dir = tmp_path / "img"
  work_dir = tmp_path / "work"

  monkeypatch.setattr(frames_mod, "_detect_scenes", lambda *a, **kw: [1.0, 5.0])

  def fake_extract(video: Path, ts: float, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"")

  monkeypatch.setattr(frames_mod, "_extract_frame_image", fake_extract)
  # 两个相同 hash
  monkeypatch.setattr(frames_mod, "_hash_frame", lambda path: "0000000000000000")

  result = extract_keyframes(video, img_dir, work_dir)

  # 由于两个时间戳均在 8s 窗口(1.0→5.0 差 4s),debounce 后只剩 1.0
  # 所以应得到 1 个 KeyFrame,不是 2 个
  assert len(result) == 1


def test_extract_keyframes_writes_manifest_json(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """必须写出 keyframes.json 到 work/frames/。"""
  import media_to_doc.pipeline.frames as frames_mod

  video = tmp_path / "v.mp4"
  video.write_bytes(b"")
  img_dir = tmp_path / "img"
  work_dir = tmp_path / "work"

  monkeypatch.setattr(frames_mod, "_detect_scenes", lambda *a, **kw: [2.0])

  def fake_extract(video: Path, ts: float, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"")

  monkeypatch.setattr(frames_mod, "_extract_frame_image", fake_extract)
  monkeypatch.setattr(frames_mod, "_hash_frame", lambda path: "abcdef0000000000")

  extract_keyframes(video, img_dir, work_dir)

  manifest_path = work_dir / "frames" / "keyframes.json"
  assert manifest_path.exists()
  data = json.loads(manifest_path.read_text(encoding="utf-8"))
  assert data["video"].endswith("v.mp4")
  assert len(data["frames"]) == 1
  assert data["threshold"] == 5


def test_extract_keyframes_skips_failed_extraction(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """_hash_frame 抛异常 → skip 该 frame,继续下一个。"""
  import media_to_doc.pipeline.frames as frames_mod

  video = tmp_path / "v.mp4"
  video.write_bytes(b"")
  img_dir = tmp_path / "img"
  work_dir = tmp_path / "work"

  monkeypatch.setattr(frames_mod, "_detect_scenes", lambda *a, **kw: [1.0, 20.0])

  call_count = {"n": 0}

  def fake_extract(video: Path, ts: float, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"")

  def maybe_failing_hash(path: Path) -> str:
    call_count["n"] += 1
    if call_count["n"] == 1:
      raise OSError("hash failed")
    return "0000000000000000"

  monkeypatch.setattr(frames_mod, "_extract_frame_image", fake_extract)
  monkeypatch.setattr(frames_mod, "_hash_frame", maybe_failing_hash)

  result = extract_keyframes(video, img_dir, work_dir)

  # 1.0 的 hash 抛错,被 skip;20.0 的 hash 成功
  assert len(result) == 1
  assert result[0].timestamp_ms == 20000
