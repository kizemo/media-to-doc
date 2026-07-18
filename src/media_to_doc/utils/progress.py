"""rich.progress 轻量包装。

设计要点:
- 单一全局开关(env var ``MEDIA_TO_DOC_PROGRESS=0`` 关掉,CI / MCP 友好)
- 提供 ``progress(description, total)`` 上下文管理器,自动 enter/exit
- 提供 ``track(items, description)`` 包装 rich.progress.track,关掉时直接 yield
- 关闭时返回 no-op 实现,不污染调用方代码

W1 仅提供最简接口;Phase 2/3 视需要扩展为 TaskList + 子任务层级。
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

ENV_PROGRESS = "MEDIA_TO_DOC_PROGRESS"


def is_progress_enabled() -> bool:
  """是否启用进度条。默认 True;env ``MEDIA_TO_DOC_PROGRESS=0`` 关闭。"""
  flag = os.environ.get(ENV_PROGRESS, "1")
  return flag.lower() not in ("0", "false", "no", "off", "")


@contextmanager
def progress(description: str, total: float | None = None) -> Iterator[Any]:
  """进度条上下文管理器。

  启用时返回 :class:`rich.progress.Progress` 适配器;关闭时返回 no-op。
  两者都暴露 ``add_task`` / ``update`` / ``advance``。
  """
  if not is_progress_enabled():
    yield _NullProgress()
    return

  from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
  )

  with Progress(
    SpinnerColumn(),
    TextColumn("[bold blue]{task.description}"),
    BarColumn(),
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    TimeElapsedColumn(),
    transient=True,
  ) as prog:
    task_id = prog.add_task(description, total=total)
    yield _RichAdapter(prog, task_id)


def track(items: Sequence[Any], description: str = "处理中") -> Iterator[Any]:
  """rich.progress.track 的轻量包装,关闭时直接 yield 原序列。"""
  if not is_progress_enabled():
    yield from items
    return

  from rich.progress import track as rich_track

  yield from rich_track(items, description=description)


# ─────────────────────────────────────────────────────────────
# 内部 no-op / adapter
# ─────────────────────────────────────────────────────────────


class _NullProgress:
  """静默进度,占位 API。"""

  def add_task(self, _description: str, total: float | None = None) -> int:
    return 0

  def update(self, _task_id: int, **_kwargs: Any) -> None:
    return None

  def advance(self, _task_id: int, advance: float = 1.0) -> None:
    return None


class _RichAdapter:
  """把 ``rich.progress.Progress`` 适配成最小 ``add_task`` / ``update`` / ``advance``。"""

  def __init__(self, prog: Any, task_id: Any) -> None:
    self._prog = prog
    self._task_id = task_id

  def add_task(self, description: str, total: float | None = None) -> Any:
    return self._prog.add_task(description, total=total)

  def update(self, task_id: Any | None = None, **kwargs: Any) -> None:
    self._prog.update(task_id if task_id is not None else self._task_id, **kwargs)

  def advance(self, task_id: Any | None = None, advance: float = 1.0) -> None:
    self._prog.advance(task_id if task_id is not None else self._task_id, advance=advance)


__all__ = [
  "ENV_PROGRESS",
  "is_progress_enabled",
  "progress",
  "track",
]
