"""media_to_doc CLI 入口(Typer)。

W6 状态(2026-07-19):
- ``mtd run`` 完整 11 stage 入口已实装(基于 :func:`runner.run_pipeline`)
- ``mtd resume`` 续跑已实装(从 ``state.inbox_path`` 派生 inbox)
- ``mtd status`` 显示进度已实装
- ``mtd list`` 扫 inbox 列出课程已实装
- inbox 自动隔离(避免多视频误选),失败时 ``--no-isolate`` 关闭
"""

from __future__ import annotations

import contextlib
import json as _json
import sys
import time
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import WorkflowConfig
from .paths import INBOX_DIR, LEARNINGS_DIR, WORK_DIR, WORKSPACE_ROOT
from .pipeline.audio import SUPPORTED_EXTS, find_media
from .pipeline.runner import PipelineResult, run_pipeline
from .state import STAGE_ORDER, State

# ─────────────────────────────────────────────────────────────
# Typer app(全局单例)
# ─────────────────────────────────────────────────────────────

app = typer.Typer(
  name="mtd",
  help="把本地音视频一键转化为带 AI 配图、可独立分发的 Markdown + HTML 讲义。",
  no_args_is_help=True,
  add_completion=False,
  rich_markup_mode="rich",
)

console = Console()


def eprint(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401
  """错误输出快捷方式(走 stdout,便于 Typer CliRunner / UI / 管道一致捕获)。

  设计权衡:Typer 0.12+ 的 CliRunner 不支持 ``mix_stderr``,stderr 输出
  在测试里难以捕获。让 eprint 也走 stdout 可被 MCP / 管道 / 测试一致读取。
  生产 shell 仍可用 ``2>log.txt`` 重定向。
  """
  console.print(*args, **kwargs)


@app.callback(invoke_without_command=True)
def _root_callback(
  ctx: typer.Context,
  version_flag: bool = typer.Option(
    False,
    "--version",
    help="显示版本信息并退出(Unix 习惯)",
    is_eager=True,
  ),
) -> None:
  """顶层 callback:处理 ``--version`` 快捷选项与无子命令时的 help。"""
  if version_flag:
    console.print(f"media-to-doc [bold cyan]{__version__}[/bold cyan]")
    raise typer.Exit(code=0)


def version_callback() -> None:
  """显示版本并退出(供 main() / 测试复用)。"""
  console.print(f"media-to-doc [bold cyan]{__version__}[/bold cyan]")
  raise typer.Exit(code=0)


# ─────────────────────────────────────────────────────────────
# mtd version
# ─────────────────────────────────────────────────────────────


@app.command()
def version() -> None:
  """显示版本信息。"""
  console.print(f"media-to-doc [bold cyan]{__version__}[/bold cyan]")


# ─────────────────────────────────────────────────────────────
# mtd paths — 调试用,显示关键路径
# ─────────────────────────────────────────────────────────────


@app.command()
def paths() -> None:
  """显示默认 workspace / inbox / work / learnings 路径。"""
  console.print(f"[dim]workspace_root[/dim]  {WORKSPACE_ROOT}")
  console.print(f"[dim]inbox_dir[/dim]      {INBOX_DIR}")
  console.print(f"[dim]work_dir[/dim]       {WORK_DIR}")
  console.print(f"[dim]learnings_dir[/dim]  {LEARNINGS_DIR}")


# ─────────────────────────────────────────────────────────────
# inbox 隔离 helpers(W6:让 CLI 与 scripts/run_smoke.py 行为一致)
# ─────────────────────────────────────────────────────────────


def _isolate_inbox(
  inbox: Path,
  target_video: Path,
  staging_dir: Path,
  *,
  exclude_dirs: list[Path] | None = None,
) -> list[tuple[Path, Path]]:
  """把 inbox 中除目标视频外的所有媒体文件 mv 到 ``staging_dir``。

  Returns
  -------
  list[tuple[Path, Path]]
    ``[(original_path, staged_path), ...]`` 供 :func:`_restore_isolated` 反向恢复。
  """
  target_resolved = target_video.resolve()
  exclude_resolved: list[Path] = [
    d.resolve() for d in (exclude_dirs or [])
  ]
  moved: list[tuple[Path, Path]] = []
  staging_dir.mkdir(parents=True, exist_ok=True)
  exclude_resolved.append(staging_dir.resolve())
  for path in sorted(inbox.rglob("*")):
    if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTS:
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


def _restore_isolated(
  moved: list[tuple[Path, Path]], staging_dir: Path,
) -> None:
  """把隔离的文件移回原路径,然后清理空的 staging_dir 子目录。"""
  for original, staged in moved:
    if not staged.exists():
      continue
    original.parent.mkdir(parents=True, exist_ok=True)
    staged.rename(original)
  if not staging_dir.exists():
    return
  for dirpath in sorted(staging_dir.rglob("*"), reverse=True):
    if dirpath.is_dir():
      with contextlib.suppress(OSError):
        dirpath.rmdir()
  with contextlib.suppress(OSError):
    staging_dir.rmdir()


def _print_summary_table(result: PipelineResult) -> None:
  """打印 stage 状态表(供 status / run / resume 复用)。"""
  table = Table(title=f"流水线进度 — {result.state.course}", show_lines=False)
  table.add_column("Stage", style="bold")
  table.add_column("Status")
  table.add_column("Started")
  table.add_column("Finished")
  table.add_column("Error", overflow="fold")

  for stage in STAGE_ORDER:
    ss = result.state.stages[stage]
    status_style = {
      "completed": "[green]completed[/green]",
      "running": "[yellow]running[/yellow]",
      "failed": "[red]failed[/red]",
      "skipped": "[dim]skipped[/dim]",
      "pending": "[dim]pending[/dim]",
    }.get(ss.status, ss.status)
    table.add_row(
      stage,
      status_style,
      ss.started_at or "-",
      ss.finished_at or "-",
      ss.error or "",
    )
  console.print(table)


def _result_to_json(result: PipelineResult, work: Path) -> str:
  """把 PipelineResult 序列化为 JSON 字符串(供 --json / MCP 复用)。"""
  payload = {
    "course": result.state.course,
    "inbox_path": result.state.inbox_path,
    "work_dir": str(work),
    "is_success": result.is_success,
    "duration_seconds": round(result.duration_seconds, 2),
    "completed": result.completed,
    "failed": result.failed,
    "stages": {
      stage: {
        "status": ss.status,
        "started_at": ss.started_at,
        "finished_at": ss.finished_at,
        "error": ss.error,
      }
      for stage, ss in result.state.stages.items()
    },
  }
  return _json.dumps(payload, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────
# mtd run — 完整流水线(W6 实装)
# ─────────────────────────────────────────────────────────────


@app.command()
def run(
  inbox: Path = typer.Argument(
    ...,
    help="inbox 目录(含待处理视频,可多文件,自动隔离)",
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
  ),
  work_dir: Path | None = typer.Option(
    None,
    "--work-dir",
    "-w",
    help="work 目录(默认 <inbox>/output)",
  ),
  llm: str | None = typer.Option(
    None,
    "--llm",
    help="LLM provider 覆盖(ollama/anthropic/openai_compatible)",
  ),
  llm_model: str | None = typer.Option(
    None,
    "--llm-model",
    help="LLM 模型名覆盖(默认 qwen3:14b)",
  ),
  imagegen: str | None = typer.Option(
    None,
    "--imagegen",
    help="imagegen provider 覆盖(local_sdxl/skip)",
  ),
  longdoc_llm: str | None = typer.Option(
    None,
    "--longdoc-llm",
    help="longdoc LLM provider(默认 skip 只跑规则清理)",
  ),
  no_longdoc: bool = typer.Option(
    False,
    "--no-longdoc",
    help="跳过 longdoc 阶段",
  ),
  stop_after: str | None = typer.Option(
    None,
    "--stop-after",
    help="跑到该 stage 后停下(调试用)",
  ),
  force: bool = typer.Option(
    False,
    "--force",
    help="强制重跑所有 stage(默认跳过已完成)",
  ),
  no_isolate: bool = typer.Option(
    False,
    "--no-isolate",
    help="禁用 inbox 自动隔离(用户自行保证单视频)",
  ),
  json_output: bool = typer.Option(
    False,
    "--json",
    help="JSON 输出(供 UI / MCP 调用)",
  ),
) -> None:
  """完整流水线:audio → asr → ... → verify。"""
  cfg = WorkflowConfig()
  if llm:
    cfg.llm.provider = llm  # type: ignore[assignment]
  if llm_model:
    cfg.llm.model = llm_model
  if imagegen:
    cfg.imagegen.provider = imagegen  # type: ignore[assignment]
  if longdoc_llm:
    cfg.pipeline.longdoc_llm_provider = longdoc_llm
  if no_longdoc:
    cfg.pipeline.skip_longdoc = True

  inbox = inbox.resolve()
  work = (work_dir or inbox / "output").resolve()
  work.mkdir(parents=True, exist_ok=True)

  # inbox 自动隔离(避免多视频误选 + 避免扫到 work_dir 下的中间产物)
  moved: list[tuple[Path, Path]] = []
  staging_dir: Path | None = None
  if not no_isolate:
    try:
      target_video = find_media(inbox, exclude_dirs=[work])
    except FileNotFoundError as exc:
      eprint(f"[red]ERR:[/red] {exc}")
      raise typer.Exit(code=2) from None
    staging_dir = work / f".excluded-{int(time.time())}"
    moved = _isolate_inbox(
      inbox, target_video, staging_dir, exclude_dirs=[work],
    )
    if moved and not json_output:
      console.print(
        f"[dim]隔离 {len(moved)} 个非目标文件 → {staging_dir.name}[/dim]"
      )

  if not json_output:
    console.print(f"[bold]inbox[/bold]  {inbox}")
    console.print(f"[bold]work[/bold]   {work}")
    console.print(
      f"[bold]config[/bold] llm={cfg.llm.provider}/{cfg.llm.model} "
      f"imagegen={cfg.imagegen.provider} longdoc={cfg.pipeline.longdoc_llm_provider}"
    )

  try:
    result = run_pipeline(
      inbox=inbox,
      work=work,
      config=cfg,
      skip_completed=not force,
      stop_after=stop_after,
    )
  except Exception as exc:
    if json_output:
      err_payload = {
        "error": f"{type(exc).__name__}: {exc}",
        "work_dir": str(work),
      }
      # sys.stdout.write 绕开 Rich markup / 自动换行 / Windows ANSI 干扰
      sys.stdout.write(_json.dumps(err_payload, ensure_ascii=False, indent=2) + "\n")
    else:
      eprint(
        f"\n[red]FAIL[/red]: {type(exc).__name__}: {exc}",
      )
      state_path = work / "state.json"
      if state_path.exists():
        eprint(
          f"[dim]state.json: {state_path}[/dim]",
        )
        eprint(
          state_path.read_text(encoding="utf-8")[:2000],
        )
    raise typer.Exit(code=1) from None
  else:
    if json_output:
      # sys.stdout.write 绕开 Rich markup + 自动 wrap 干扰(JSON 不应被 Rich 二次渲染)
      sys.stdout.write(_result_to_json(result, work) + "\n")
    else:
      _print_summary_table(result)
      console.print(
        f"\n[green]OK[/green]: {len(result.completed)} stage 完成 / "
        f"{len(result.failed)} 失败,耗时 {result.duration_seconds:.1f}s"
      )
      console.print(f"[dim]state.json: {work / 'state.json'}[/dim]")
    if not result.is_success:
      raise typer.Exit(code=1) from None
  finally:
    if moved and staging_dir is not None:
      try:
        _restore_isolated(moved, staging_dir)
      except Exception as exc:
        eprint(
          f"[yellow]WARN[/yellow]: 恢复隔离文件失败: "
          f"{type(exc).__name__}: {exc}",
        )
        eprint(
          f"  隔离文件位于 {staging_dir},请手动检查",
        )


# ─────────────────────────────────────────────────────────────
# mtd resume — 续跑(W6 实装)
# ─────────────────────────────────────────────────────────────


@app.command()
def resume(
  work_dir: Path = typer.Argument(
    ...,
    help="work 目录(从 state.json 恢复)",
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
  ),
  inbox_dir: Path | None = typer.Option(
    None,
    "--inbox",
    help="覆盖 state.json 里记录的 inbox 路径(默认从 state.inbox_path 派生)",
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
  ),
  stop_after: str | None = typer.Option(
    None,
    "--stop-after",
    help="跑到该 stage 后停下(调试用)",
  ),
  force: bool = typer.Option(
    False,
    "--force",
    help="强制重跑所有 stage",
  ),
  json_output: bool = typer.Option(
    False,
    "--json",
    help="JSON 输出",
  ),
) -> None:
  """续跑中断的流水线(从 work/state.json 恢复)。"""
  work = work_dir.resolve()
  state_path = work / "state.json"
  if not state_path.exists():
    eprint(
      f"[red]ERR:[/red] state.json 不存在: {state_path}\n"
      f"首次跑请用 [bold]mtd run <inbox_dir>[/bold]",
    )
    raise typer.Exit(code=2) from None

  if inbox_dir is not None:
    inbox: Path | None = inbox_dir.resolve()
  else:
    inbox = None  # 让 run_pipeline 从 state.inbox_path 派生

  if not json_output:
    console.print(f"[bold]work[/bold]   {work}")
    if inbox is not None:
      console.print(f"[bold]inbox[/bold]  {inbox}  [dim](override)[/dim]")
    else:
      console.print("[bold]inbox[/bold]  [dim](auto from state.json)[/dim]")

  try:
    result = run_pipeline(
      inbox=inbox,
      work=work,
      skip_completed=not force,
      stop_after=stop_after,
    )
  except Exception as exc:
    if json_output:
      console.print_json(data={"error": f"{type(exc).__name__}: {exc}"})
    else:
      eprint(
        f"\n[red]FAIL[/red]: {type(exc).__name__}: {exc}",
      )
    raise typer.Exit(code=1) from None

  if json_output:
    sys.stdout.write(_result_to_json(result, work) + "\n")
  else:
    _print_summary_table(result)
    console.print(
      f"\n[green]OK[/green]: {len(result.completed)} stage 完成 / "
      f"{len(result.failed)} 失败,耗时 {result.duration_seconds:.1f}s"
    )
  if not result.is_success:
    raise typer.Exit(code=1) from None


# ─────────────────────────────────────────────────────────────
# mtd status — 进度查询(W6 实装)
# ─────────────────────────────────────────────────────────────


@app.command()
def status(
  work_dir: Path = typer.Argument(
    ...,
    help="work 目录",
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
  ),
  json_output: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
  """查询流水线进度(只读,不动 state)。"""
  work = work_dir.resolve()
  state_path = work / "state.json"
  if not state_path.exists():
    eprint(
      f"[red]ERR:[/red] state.json 不存在: {state_path}",
    )
    raise typer.Exit(code=2) from None

  state = State.load(state_path)

  if json_output:
    payload = {
      "course": state.course,
      "inbox_path": state.inbox_path,
      "current_stage": state.current_stage,
      "started_at": state.started_at,
      "updated_at": state.updated_at,
      "is_complete": state.is_complete(),
      "stages": {
        stage: {
          "status": ss.status,
          "started_at": ss.started_at,
          "finished_at": ss.finished_at,
          "error": ss.error,
        }
        for stage, ss in state.stages.items()
      },
    }
    console.print_json(data=payload)
    return

  # 文字表格
  table = Table(title=f"流水线进度 — {state.course}", show_lines=False)
  table.add_column("Stage", style="bold")
  table.add_column("Status")
  table.add_column("Started")
  table.add_column("Finished")
  table.add_column("Error", overflow="fold")

  for stage in STAGE_ORDER:
    ss = state.stages[stage]
    status_style = {
      "completed": "[green]completed[/green]",
      "running": "[yellow]running[/yellow]",
      "failed": "[red]failed[/red]",
      "skipped": "[dim]skipped[/dim]",
      "pending": "[dim]pending[/dim]",
    }.get(ss.status, ss.status)
    table.add_row(
      stage, status_style,
      ss.started_at or "-", ss.finished_at or "-",
      ss.error or "",
    )
  console.print(table)
  if state.inbox_path:
    console.print(f"[dim]inbox_path: {state.inbox_path}[/dim]")
  if state.is_complete():
    console.print("[green]全部 stage 已完成[/green]")
  else:
    next_s = state.next_stage()
    if next_s:
      console.print(f"[dim]下一个 stage: {next_s}[/dim]")


# ─────────────────────────────────────────────────────────────
# mtd list — 列出 inbox 课程(W6 实装)
# ─────────────────────────────────────────────────────────────


@app.command(name="list")  # noqa: A001
def list_(  # noqa: A001
  workspace: Path | None = typer.Option(
    None, "--workspace", "-w", help="workspace 根目录(默认 ./workspace)"
  ),
  json_output: bool = typer.Option(False, "--json", help="JSON 输出"),
) -> None:
  """列出 inbox 中的课程(每个子目录算一节课)。"""
  ws_root = (workspace or WORKSPACE_ROOT).resolve()
  inbox_root = ws_root / "inbox"

  if not inbox_root.exists():
    if json_output:
      console.print_json(data={"courses": []})
    else:
      console.print(f"[yellow]inbox 不存在[/yellow]: {inbox_root}")
      console.print("[dim]提示: 创建子目录并放入视频文件[/dim]")
    return

  courses: list[dict[str, object]] = []
  for entry in sorted(inbox_root.iterdir()):
    if not entry.is_dir():
      continue
    media = [
      p.name for p in sorted(entry.rglob("*"))
      if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
    ]
    courses.append({
      "name": entry.name,
      "path": str(entry),
      "media_files": media,
      "media_count": len(media),
    })

  if json_output:
    console.print_json(data={"workspace": str(ws_root), "courses": courses})
    return

  if not courses:
    console.print(f"[yellow]inbox 空[/yellow]: {inbox_root}")
    return

  table = Table(title=f"inbox 课程 — {inbox_root}", show_lines=False)
  table.add_column("Course", style="bold")
  table.add_column("Media")
  table.add_column("Count", justify="right")
  for c in courses:
    media_str = ", ".join(c["media_files"][:3])  # type: ignore[arg-type]
    if len(c["media_files"]) > 3:  # type: ignore[arg-type]
      media_str += f" ... (+{len(c['media_files']) - 3})"  # type: ignore[arg-type]
    table.add_row(
      str(c["name"]), media_str or "[dim](no media)[/dim]",
      str(c["media_count"]),
    )
  console.print(table)


# ─────────────────────────────────────────────────────────────
# mtd doctor — 系统诊断(Phase 2)
# ─────────────────────────────────────────────────────────────


@app.command()
def doctor() -> None:
  """系统诊断(GPU / 显存 / 磁盘 / ffmpeg / Ollama / Python)。"""
  console.print("[yellow]⚠[/yellow] mtd doctor 尚未实装(Phase 2)。")
  raise typer.Exit(code=1)


# ─────────────────────────────────────────────────────────────
# mtd config — 配置管理
# ─────────────────────────────────────────────────────────────


config_app = typer.Typer(help="配置管理(get / set / edit / path)。")
app.add_typer(config_app, name="config")


@config_app.command("path")
def config_path() -> None:
  """显示配置文件路径。"""
  from .paths import CONFIG_FILE
  console.print(str(CONFIG_FILE))


# ─────────────────────────────────────────────────────────────
# mtd model — 模型管理(Phase 2)
# ─────────────────────────────────────────────────────────────


@app.command()
def model(
  action: str = typer.Argument(..., help="list / download / delete / clean"),
  name: str | None = typer.Option(None, "--name", "-n"),
) -> None:
  """模型管理。"""
  console.print("[yellow]⚠[/yellow] mtd model 尚未实装(Phase 2)。")
  raise typer.Exit(code=1)


# ─────────────────────────────────────────────────────────────
# mtd mcp — 启动 MCP server(W7 实装)
# ─────────────────────────────────────────────────────────────


@app.command()
def mcp() -> None:
  """启动 MCP server(stdio JSON-RPC,供 Claude Desktop / Codex 调用)。"""
  console.print("[yellow]⚠[/yellow] mtd mcp 尚未实装(W7)。")
  raise typer.Exit(code=1)


# ─────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────


def main() -> None:
  """CLI 入口(``pyproject.toml [project.scripts]`` 注册)。"""
  try:
    app()
  except SystemExit:
    raise
  except Exception:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    sys.exit(1)


if __name__ == "__main__":
  main()
