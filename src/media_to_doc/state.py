"""media_to_doc 流水线状态管理(STAGE_ORDER + State 持久化)。

Phase 0 占位:定义 11 阶段顺序常量与 State 数据类。
Phase 1 起逐步添加:从 state.json 加载/保存、stage 跳过逻辑、resume 命令支持。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

# ─────────────────────────────────────────────────────────────
# STAGE_ORDER — 11 阶段流水线顺序常量
# ─────────────────────────────────────────────────────────────

STAGE_ORDER: tuple[str, ...] = (
  "audio",          # ffmpeg 抽音
  "asr",            # Faster-Whisper 转写
  "frames",         # PySceneDetect + pHash
  "ocr",            # RapidOCR
  "asr_correct",    # OCR × ASR 8s 校对
  "chapters",       # LLM 章节切分
  "draft",          # LLM 草稿生成
  "imagegen",       # SDXL Base + Refiner(可选 skip)
  "render",         # Markdown + HTML 渲染
  "longdoc",        # 深度净化 + 最终 HTML
  "verify",         # gatekeeper + image_refs 校验
)

assert len(STAGE_ORDER) == 11, "STAGE_ORDER 必须包含 11 个阶段"


# ─────────────────────────────────────────────────────────────
# 类型别名
# ─────────────────────────────────────────────────────────────

StageStatus = Literal["pending", "running", "completed", "failed", "skipped"]


# ─────────────────────────────────────────────────────────────
# StageState — 单个 stage 的状态
# ─────────────────────────────────────────────────────────────


@dataclass
class StageState:
  """单个 stage 的执行状态。"""

  name: str
  status: StageStatus = "pending"
  started_at: str | None = None  # ISO 格式
  finished_at: str | None = None
  error: str | None = None
  output_paths: list[str] = field(default_factory=list)

  def to_dict(self) -> dict[str, object]:
    return asdict(self)

  @property
  def is_completed(self) -> bool:
    return self.status == "completed"


# ─────────────────────────────────────────────────────────────
# State — 单个课程的整体状态
# ─────────────────────────────────────────────────────────────


@dataclass
class State:
  """单个课程(``work/<course>/``)的完整流水线状态。

  持久化到 ``work/<course>/state.json``,支持 ``mtd resume`` 续跑。
  """

  course: str
  started_at: str  # ISO 格式
  updated_at: str  # ISO 格式
  current_stage: str | None = None
  stages: dict[str, StageState] = field(default_factory=dict)

  # ── 构造 ────────────────────────────────────────────────

  @classmethod
  def new(cls, course: str) -> State:
    """为新课程创建初始 state。"""
    now = datetime.now().isoformat(timespec="seconds")
    return cls(
      course=course,
      started_at=now,
      updated_at=now,
      stages={stage: StageState(name=stage) for stage in STAGE_ORDER},
    )

  # ── 状态查询 ────────────────────────────────────────────

  def completed_stages(self) -> list[str]:
    return [s.name for s in self.stages.values() if s.is_completed]

  def pending_stages(self) -> list[str]:
    return [s.name for s in self.stages.values() if s.status == "pending"]

  def next_stage(self) -> str | None:
    for stage in STAGE_ORDER:
      if self.stages[stage].status in ("pending", "failed"):
        return stage
    return None

  def is_complete(self) -> bool:
    """所有 stage 都已完成(无 failed / pending)。"""
    return all(s.status in ("completed", "skipped") for s in self.stages.values())

  # ── 状态修改 ────────────────────────────────────────────

  def mark(self, stage: str, status: StageStatus, error: str | None = None) -> None:
    """更新单个 stage 的状态。"""
    if stage not in self.stages:
      raise KeyError(f"未知 stage: {stage}")
    self.stages[stage].status = status
    self.updated_at = datetime.now().isoformat(timespec="seconds")
    if status == "running":
      self.stages[stage].started_at = self.updated_at
      self.current_stage = stage
    elif status in ("completed", "failed", "skipped"):
      self.stages[stage].finished_at = self.updated_at
      self.stages[stage].error = error
      if status == "completed":
        # 推进 current_stage 到下一个 pending
        next_stage = self.next_stage()
        self.current_stage = next_stage

  # ── 序列化 ──────────────────────────────────────────────

  def to_dict(self) -> dict[str, object]:
    return {
      "course": self.course,
      "started_at": self.started_at,
      "updated_at": self.updated_at,
      "current_stage": self.current_stage,
      "stages": {name: stage.to_dict() for name, stage in self.stages.items()},
    }

  def save(self, path: Path) -> None:
    """持久化到 JSON 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
      json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
      encoding="utf-8",
    )

  @classmethod
  def load(cls, path: Path) -> State:
    """从 JSON 文件加载。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    stages = {
      name: StageState(**stage_data)
      for name, stage_data in data.pop("stages", {}).items()
    }
    return cls(stages=stages, **data)


__all__ = [
  "STAGE_ORDER",
  "StageStatus",
  "StageState",
  "State",
]
