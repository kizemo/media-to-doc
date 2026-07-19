"""端到端 smoke runner — 把单个音视频跑成讲义。

默认行为(项目约定,W5 引入):
- ``inbox``  = 视频所在目录
- ``work``   = 视频同目录下的 ``output`` 子目录(便于整盘复制 / 上传 / 归档)
- ``config`` = :class:`WorkflowConfig` 默认 + Ollama ``qwen3:14b``
- ``imagegen`` 默认 ``skip``(生产可切 ``local_sdxl``)
- **inbox 隔离**:跑前自动把 inbox 中除目标视频外的所有媒体文件 mv 到
  ``<work>/.excluded-<timestamp>/``,跑完用 ``try/finally`` 恢复(避免
  ``find_media`` 选错文件,也避免污染原素材目录)

用法::

    # 默认(work = <视频目录>/output,imagegen=skip,inbox 自动隔离)
    uv run python scripts/run_smoke.py /path/to/lecture.mp4

    # 自定义 work_dir
    uv run python scripts/run_smoke.py /path/to/lecture.mp4 --work-dir D:/runs/001

    # 调试 — 只跑到某 stage
    uv run python scripts/run_smoke.py /path/to/lecture.mp4 --stop-after chapters

    # 生产 — 开 SDXL 配图 + longdoc LLM 净化
    uv run python scripts/run_smoke.py /path/to/lecture.mp4 \\
        --imagegen local_sdxl --longdoc-llm ollama

    # 禁用 inbox 隔离(用户手动保证 inbox 单视频)
    uv run python scripts/run_smoke.py /path/to/lecture.mp4 --no-isolate
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# 网络环境(W5 起默认):中国大陆访问 huggingface.co 走 hf-mirror.com
# + 禁用 xet(镜像不支持 xet 重构协议)
# 用户可在外部覆盖(如需直连 / 用代理)
# ─────────────────────────────────────────────────────────────
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
# 显式 unset 系统代理(避免 Claude Code 系统代理 502)
for _proxy in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "CC_HAHA_SYSTEM_PROXY_URL"):
  os.environ.pop(_proxy, None)

# 把 src/ 加进 sys.path(脚本独立运行不依赖 uv install)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from media_to_doc.config import WorkflowConfig  # noqa: E402
from media_to_doc.pipeline.runner import run_pipeline  # noqa: E402

# ─────────────────────────────────────────────────────────────
# inbox 隔离(inbox 里可能有多个媒体文件,find_media 按 ASCII 排序选错)
# ─────────────────────────────────────────────────────────────

# 与 pipeline.audio.SUPPORTED_EXTS 同步(若 audio.py 改了这里也要改)
MEDIA_EXTS: frozenset[str] = frozenset({
  ".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".flv",
  ".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg",
})


def _isolate_inbox(
  inbox: Path,
  target_video: Path,
  staging_dir: Path,
  *,
  exclude_dirs: list[Path] | None = None,
) -> list[tuple[Path, Path]]:
  """把 inbox 中除目标视频外的所有媒体文件 mv 到 ``staging_dir``。

  保持相对路径(同名文件不会冲突)。

  跳过 ``exclude_dirs`` 下的所有文件(典型用法:排除 ``work_dir`` 自身,
  否则 ``inbox.rglob("*")`` 会扫到 ``output/asr/audio.wav`` 等产物并误移)。

  Returns
  -------
  list[tuple[Path, Path]]
    ``[(original_path, staged_path), ...]`` 供 ``_restore_isolated`` 反向恢复。
  """
  target_resolved = target_video.resolve()
  exclude_resolved: list[Path] = [
    d.resolve() for d in (exclude_dirs or [])
  ]
  moved: list[tuple[Path, Path]] = []
  staging_dir.mkdir(parents=True, exist_ok=True)
  exclude_resolved.append(staging_dir.resolve())
  for path in sorted(inbox.rglob("*")):
    if not path.is_file() or path.suffix.lower() not in MEDIA_EXTS:
      continue
    resolved = path.resolve()
    if resolved == target_resolved:
      continue
    if any(resolved.is_relative_to(excl) for excl in exclude_resolved):
      continue
    rel = path.relative_to(inbox)
    dest = staging_dir / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    path.rename(dest)
    moved.append((path, dest))
  return moved


def _restore_isolated(moved: list[tuple[Path, Path]], staging_dir: Path) -> None:
  """把隔离的文件移回原路径,然后清理空的 staging_dir 子目录。"""
  for original, staged in moved:
    if not staged.exists():
      continue
    original.parent.mkdir(parents=True, exist_ok=True)
    staged.rename(original)
  # 清理空目录(从深到浅)
  if not staging_dir.exists():
    return
  import contextlib
  for dirpath in sorted(staging_dir.rglob("*"), reverse=True):
    if dirpath.is_dir():
      with contextlib.suppress(OSError):
        dirpath.rmdir()
  with contextlib.suppress(OSError):
    staging_dir.rmdir()


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
  p = argparse.ArgumentParser(description="media-to-doc 端到端 smoke runner")
  p.add_argument("video", type=Path, help="输入视频文件路径")
  p.add_argument(
    "--work-dir",
    type=Path,
    default=None,
    help="work_dir 路径(默认: <视频所在目录>/output)",
  )
  p.add_argument(
    "--stop-after",
    type=str,
    default=None,
    help="跑到该 stage 后停下(如 chapters / render / longdoc)",
  )
  p.add_argument(
    "--imagegen",
    type=str,
    default="skip",
    choices=["local_sdxl", "skip"],
    help="imagegen provider(默认 skip,生产可切 local_sdxl)",
  )
  p.add_argument(
    "--longdoc-llm",
    type=str,
    default="skip",
    help="longdoc LLM provider(默认 skip 只跑规则清理;可选 ollama/anthropic)",
  )
  p.add_argument(
    "--llm-provider",
    type=str,
    default="ollama",
    choices=["ollama", "anthropic", "openai_compatible"],
    help="chapters / draft 用 LLM provider(默认 ollama)",
  )
  p.add_argument("--llm-model", type=str, default="qwen3:14b", help="LLM 模型名")
  p.add_argument(
    "--no-skip-completed",
    action="store_true",
    help="强制重跑所有 stage(默认跳过已完成)",
  )
  p.add_argument(
    "--no-isolate",
    action="store_true",
    help="禁用 inbox 自动隔离(用户自行保证 inbox 单视频)",
  )
  return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
  args = parse_args(argv)
  video: Path = args.video.resolve()
  if not video.is_file():
    print(f"ERR: 视频文件不存在: {video}", file=sys.stderr)
    return 2

  inbox = video.parent
  work = (args.work_dir or inbox / "output").resolve()
  work.mkdir(parents=True, exist_ok=True)

  cfg = WorkflowConfig()
  cfg.imagegen.provider = args.imagegen  # type: ignore[assignment]
  cfg.pipeline.longdoc_llm_provider = args.longdoc_llm
  cfg.llm.provider = args.llm_provider  # type: ignore[assignment]
  cfg.llm.model = args.llm_model

  print(f"video  : {video}")
  print(f"inbox  : {inbox}")
  print(f"work   : {work}")
  print(
    f"config : llm={cfg.llm.provider}/{cfg.llm.model} "
    f"imagegen={cfg.imagegen.provider} longdoc={cfg.pipeline.longdoc_llm_provider}"
  )

  # inbox 隔离(默认开启)— 排除 work_dir 自身,避免移走流水线产物
  moved: list[tuple[Path, Path]] = []
  staging_dir: Path | None = None
  if not args.no_isolate:
    staging_dir = work / f".excluded-{int(time.time())}"
    moved = _isolate_inbox(inbox, video, staging_dir, exclude_dirs=[work])
    if moved:
      print(f"隔离 {len(moved)} 个非目标文件 → {staging_dir}")
    else:
      print("inbox 中仅 1 个媒体文件,无需隔离")
      staging_dir = None

  try:
    result = run_pipeline(
      inbox=inbox,
      work=work,
      config=cfg,
      skip_completed=not args.no_skip_completed,
      stop_after=args.stop_after,
    )
  except Exception as exc:
    print(f"\nFAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
    state_path = work / "state.json"
    if state_path.exists():
      print(f"\nstate.json: {state_path}", file=sys.stderr)
      print(state_path.read_text(encoding="utf-8")[:2000], file=sys.stderr)
    return 1
  finally:
    if moved and staging_dir is not None:
      print(f"恢复 {len(moved)} 个隔离文件...")
      try:
        _restore_isolated(moved, staging_dir)
      except Exception as exc:
        print(f"WARN: 恢复失败: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"  隔离文件位于 {staging_dir},请手动检查", file=sys.stderr)

  print(
    f"\nOK: {len(result.completed)} stage 完成 / "
    f"{len(result.failed)} 失败,耗时 {result.duration_seconds:.1f}s"
  )
  print(f"state.json: {work / 'state.json'}")
  return 0 if result.is_success else 1


if __name__ == "__main__":
  raise SystemExit(main())
