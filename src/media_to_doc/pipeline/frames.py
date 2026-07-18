"""Stage 3 — ``frames``:关键帧检测 + pHash 去重。

输入:视频文件 + (可选) ASR 时间戳提示
输出:``img/frame_<ts_ms>.jpg`` + ``work/frames/keyframes.json``

算法:
1. PySceneDetect ContentDetector 检测镜头切换
2. 合并 ASR 提示时间戳(去重)
3. 按画面变化率排序,8s 去抖动窗口内只保留首帧
4. pHash 去重,差异 ≤ 5 视为重复
5. 全帧列表写入 keyframes.json(下游 asr_correct 用)

测试:
- monkeypatch _detect_scenes 与 _hash_frame 注入假数据,
  不依赖 scenedetect / imagehash / 真实视频。

参考:TDD §5 数据流第 3 步 + PROJECT_DESCRIPTION §3.2 frames 行。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..config import PipelineConfig, WorkflowConfig

# ─────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────

DEFAULT_DEBOUNCE_SECONDS = 8.0
DEFAULT_PHASH_THRESHOLD = 5


# ─────────────────────────────────────────────────────────────
# KeyFrame 数据类
# ─────────────────────────────────────────────────────────────


@dataclass
class KeyFrame:
  """提取出的单个关键帧。

  Attributes
  ----------
  timestamp_ms : int
    视频内时间戳(毫秒)
  image_path : str
    关键帧文件相对路径(相对 ``img_dir``)
  phash : str
    感知哈希(pHash),长度 16 的 hex
  source : str
    来源类型:``"scene"``(镜头切换) / ``"asr_hint"``(ASR 提示)
  """

  timestamp_ms: int
  image_path: str
  phash: str
  source: str = "scene"

  def to_dict(self) -> dict[str, Any]:
    return asdict(self)


# ─────────────────────────────────────────────────────────────
# 关键帧元数据(整段输出)
# ─────────────────────────────────────────────────────────────


@dataclass
class KeyFramesManifest:
  """``keyframes.json`` 数据模型。"""

  video: str
  frames: list[KeyFrame] = field(default_factory=list)
  threshold: int = DEFAULT_PHASH_THRESHOLD

  def to_dict(self) -> dict[str, Any]:
    return {
      "video": self.video,
      "frames": [f.to_dict() for f in self.frames],
      "threshold": self.threshold,
    }

  def save(self, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
      json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
      encoding="utf-8",
    )


# ─────────────────────────────────────────────────────────────
# 镜头检测(可 mock)
# ─────────────────────────────────────────────────────────────


def _detect_scenes(video: Path, threshold: float = 27.0) -> list[float]:
  """PySceneDetect ContentDetector 检测镜头切换,返回秒级时间戳列表。

  慢速路径:真正调 scenedetect。测试通过 monkeypatch 替换。
  """
  try:
    from scenedetect import (  # type: ignore[import-untyped]
      ContentDetector,
      SceneManager,
      open_video,
    )
  except ImportError as exc:
    raise ImportError(
      "extract_keyframes() 需要 scenedetect。安装方式:"
      "uv add 'media_to_doc[frames]' 或 uv add scenedetect"
    ) from exc

  video_stream = open_video(str(video))
  scene_manager = SceneManager()
  scene_manager.add_detector(ContentDetector(threshold=threshold))
  scene_manager.detect_scenes(video_stream)
  # detect_scenes yields (start, end) Timecode tuples
  timestamps = [t[0].get_seconds() for t in scene_manager.get_scene_list()]
  return timestamps


# ─────────────────────────────────────────────────────────────
# 后处理:合并 hints / 去抖 / pHash 去重
# ─────────────────────────────────────────────────────────────


def _merge_timestamps(
  scene_times: list[float],
  hint_times: list[float],
  debounce_seconds: float,
) -> list[tuple[float, str]]:
  """合并 scene + hint 时间戳,8s 窗口内只保留首个 + 标注 source。"""
  indexed: list[tuple[float, str]] = (
    [(t, "scene") for t in scene_times] +
    [(t, "asr_hint") for t in hint_times]
  )
  indexed.sort(key=lambda pair: (pair[0], 0 if pair[1] == "scene" else 1))

  if not indexed:
    return []

  deduped: list[tuple[float, str]] = [indexed[0]]
  for ts, source in indexed[1:]:
    if ts - deduped[-1][0] >= debounce_seconds:
      deduped.append((ts, source))
    # 窗口内 hint 不挤掉 scene(scene 优先)
  return deduped


def _hash_frame(image_path: Path) -> str:
  """计算 frame pHash(lazy load imagehash + PIL)。"""
  from ..utils.hash_utils import phash

  return phash(image_path)


def _is_duplicate(new_hash: str, seen: list[str], threshold: int) -> bool:
  """基于 pHash Hamming 距离判定是否重复。"""
  from ..utils.hash_utils import hamming_distance

  return any(hamming_distance(new_hash, h) <= threshold for h in seen)


def _extract_frame_image(
  video: Path,
  timestamp_seconds: float,
  output: Path,
) -> None:
  """ffmpeg 抽单帧 → output 文件。

  测试通过 monkeypatch 替换为写 stub 文件。
  """
  from ..utils.ffmpeg_utils import run_ffmpeg

  output.parent.mkdir(parents=True, exist_ok=True)
  run_ffmpeg(
    [
      "-y",
      "-ss", f"{timestamp_seconds:.3f}",
      "-i", str(video),
      "-frames:v", "1",
      "-q:v", "2",
      str(output),
    ],
    timeout=120.0,
  )


# ─────────────────────────────────────────────────────────────
# 公开 API
# ─────────────────────────────────────────────────────────────


def extract_keyframes(
  video: Path,
  img_dir: Path,
  work_dir: Path,
  config: WorkflowConfig | None = None,
  hint_timestamps: list[float] | None = None,
) -> list[KeyFrame]:
  """Stage 3:提取关键帧 + pHash 去重。

  Parameters
  ----------
  video : Path
    视频文件路径
  img_dir : Path
    关键帧输出目录(``inbox/<课程>/img/``)
  work_dir : Path
    中间产物目录,``keyframes.json`` 写到 ``<work_dir>/frames/keyframes.json``
  config : WorkflowConfig | None
    配置(用 ``pipeline.default_asr_window_seconds`` 等字段做 tuning)
  hint_timestamps : list[float] | None
    ASR 转写产生的段落起止时间戳(秒),作为补点提示

  Returns
  -------
  list[KeyFrame]
    最终保留的关键帧列表(已按时间排序)
  """
  pipeline_cfg: PipelineConfig = (config or WorkflowConfig()).pipeline
  debounce_seconds = float(pipeline_cfg.default_asr_window_seconds)
  threshold = DEFAULT_PHASH_THRESHOLD

  img_dir.mkdir(parents=True, exist_ok=True)
  work_frames_dir = work_dir / "frames"
  work_frames_dir.mkdir(parents=True, exist_ok=True)

  # 检测镜头切换
  scene_times = _detect_scenes(video)
  hint_times = hint_timestamps or []

  # 合并 + 去抖
  merged = _merge_timestamps(scene_times, hint_times, debounce_seconds)

  # 抽帧 + pHash + 去重
  frames: list[KeyFrame] = []
  seen_hashes: list[str] = []
  for ts, source in merged:
    ts_ms = int(round(ts * 1000))
    img_path = img_dir / f"frame_{ts_ms:09d}.jpg"
    _extract_frame_image(video, ts, img_path)

    try:
      h = _hash_frame(img_path)
    except Exception:
      # 抽帧失败(如 0 字节文件)→ 跳过
      continue

    if _is_duplicate(h, seen_hashes, threshold):
      # 重复但保留 hint(给下游 OCR / 配图更多候选)
      if source == "asr_hint":
        frames.append(KeyFrame(
          timestamp_ms=ts_ms,
          image_path=str(img_path.relative_to(img_dir.parent)),
          phash=h,
          source=source,
        ))
      continue

    seen_hashes.append(h)
    frames.append(KeyFrame(
      timestamp_ms=ts_ms,
      image_path=str(img_path.relative_to(img_dir.parent)),
      phash=h,
      source=source,
    ))

  # 写 keyframes.json 到 work/frames/
  manifest = KeyFramesManifest(video=str(video), frames=frames, threshold=threshold)
  manifest.save(work_frames_dir / "keyframes.json")

  return frames


__all__ = [
  "KeyFrame",
  "KeyFramesManifest",
  "DEFAULT_DEBOUNCE_SECONDS",
  "DEFAULT_PHASH_THRESHOLD",
  "extract_keyframes",
]
