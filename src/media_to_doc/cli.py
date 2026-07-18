"""media_to_doc CLI 入口(Typer)。

Phase 0 占位:仅暴露 ``mtd --version`` / ``mtd --help`` 与最简命令骨架。
Phase 1 起逐阶段实装各命令(``run`` / ``resume`` / ``status`` / ``list`` /
``doctor`` / ``config`` / ``model`` / ``mcp`` / ``update``)。
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from . import __version__
from .paths import INBOX_DIR, LEARNINGS_DIR, WORK_DIR, WORKSPACE_ROOT

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
# mtd paths — 调试用,显示关键路径(便于其它 Claude 项目引用)
# ─────────────────────────────────────────────────────────────


@app.command()
def paths() -> None:
  """显示默认 workspace / inbox / work / learnings 路径。"""
  console.print(f"[dim]workspace_root[/dim]  {WORKSPACE_ROOT}")
  console.print(f"[dim]inbox_dir[/dim]      {INBOX_DIR}")
  console.print(f"[dim]work_dir[/dim]       {WORK_DIR}")
  console.print(f"[dim]learnings_dir[/dim]  {LEARNINGS_DIR}")


# ─────────────────────────────────────────────────────────────
# mtd run — 完整流水线(Phase 1 实装)
# ─────────────────────────────────────────────────────────────


@app.command()
def run(
  inbox: Path = typer.Argument(
    ...,
    help="inbox 目录(包含待处理视频)",
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
  ),
  workspace: Path | None = typer.Option(
    None,
    "--workspace",
    "-w",
    help="workspace 根目录(默认 ./workspace)",
  ),
  llm: str | None = typer.Option(
    None,
    "--llm",
    help="LLM provider 覆盖(ollama/anthropic/openai_compatible)",
  ),
  imagegen: str | None = typer.Option(
    None,
    "--imagegen",
    help="imagegen provider 覆盖(local_sdxl/skip)",
  ),
  no_longdoc: bool = typer.Option(
    False,
    "--no-longdoc",
    help="跳过 longdoc 阶段(只产原版讲义,不做深度净化)",
  ),
  json_output: bool = typer.Option(
    False,
    "--json",
    help="JSON 输出(供 UI / MCP 调用)",
  ),
) -> None:
  """完整流水线:audio → asr → ... → verify。"""
  console.print(
    f"[yellow]⚠[/yellow] mtd run 尚未实装(Phase 1)。inbox={inbox}",
  )
  raise typer.Exit(code=1)


# ─────────────────────────────────────────────────────────────
# mtd resume — 续跑(Phase 1 实装)
# ─────────────────────────────────────────────────────────────


@app.command()
def resume(
  work: Path = typer.Argument(
    ...,
    help="work 目录(从 state.json 恢复)",
    exists=True,
    file_okay=False,
    dir_okay=True,
    readable=True,
  ),
) -> None:
  """续跑中断的流水线。"""
  console.print(f"[yellow]⚠[/yellow] mtd resume 尚未实装(Phase 1)。work={work}")
  raise typer.Exit(code=1)


# ─────────────────────────────────────────────────────────────
# mtd status — 进度查询(Phase 1 实装)
# ─────────────────────────────────────────────────────────────


@app.command()
def status(
  work: Path = typer.Argument(..., help="work 目录"),
) -> None:
  """查询流水线进度。"""
  console.print(f"[yellow]⚠[/yellow] mtd status 尚未实装(Phase 1)。work={work}")
  raise typer.Exit(code=1)


# ─────────────────────────────────────────────────────────────
# mtd list — 列出 inbox 课程(Phase 1 实装)
# ─────────────────────────────────────────────────────────────


@app.command(name="list")  # 避免与 Python list 关键字冲突
def list_(  # noqa: A001  # typer 命令名
  workspace: Path | None = typer.Option(None, "--workspace", "-w"),
) -> None:
  """列出 inbox 中的课程。"""
  console.print("[yellow]⚠[/yellow] mtd list 尚未实装(Phase 1)。")
  raise typer.Exit(code=1)


# ─────────────────────────────────────────────────────────────
# mtd doctor — 系统诊断(Phase 2 实装)
# ─────────────────────────────────────────────────────────────


@app.command()
def doctor() -> None:
  """系统诊断(GPU / 显存 / 磁盘 / ffmpeg / Ollama / Python)。"""
  console.print("[yellow]⚠[/yellow] mtd doctor 尚未实装(Phase 2)。")
  raise typer.Exit(code=1)


# ─────────────────────────────────────────────────────────────
# mtd config — 配置管理(Phase 1 实装)
# ─────────────────────────────────────────────────────────────


config_app = typer.Typer(help="配置管理(get / set / edit / path)。")
app.add_typer(config_app, name="config")


@config_app.command("path")
def config_path() -> None:
  """显示配置文件路径。"""
  from .paths import CONFIG_FILE
  console.print(str(CONFIG_FILE))


# ─────────────────────────────────────────────────────────────
# mtd model — 模型管理(Phase 2 实装)
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
# mtd mcp — 启动 MCP server(Phase 4 实装)
# ─────────────────────────────────────────────────────────────


@app.command()
def mcp() -> None:
  """启动 MCP server(stdio JSON-RPC,供 Claude Desktop / Codex 调用)。"""
  console.print("[yellow]⚠[/yellow] mtd mcp 尚未实装(Phase 4)。")
  raise typer.Exit(code=1)


# ─────────────────────────────────────────────────────────────
# 入口(支持 ``uv run mtd`` 和 ``python -m media_to_doc.cli``)
# ─────────────────────────────────────────────────────────────


def main() -> None:
  """CLI 入口(``pyproject.toml [project.scripts]`` 注册)。"""
  app()


if __name__ == "__main__":
  main()
