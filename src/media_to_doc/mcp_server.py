"""media_to_doc MCP server(stdio JSON-RPC,供 Claude Desktop / Codex 调用)。

W7 状态(2026-07-19):
- 6 个工具暴露:list_courses / run_pipeline / resume_pipeline /
  check_status / list_outputs / read_lecture
- 全部 handler 同步 + 日志走 stderr(stdout 留给 JSON-RPC 帧)
- 错误路径返回 ``isError=True`` 的 :class:`CallToolResult`,不抛异常
- ``mtd-mcp`` 入口已在 ``pyproject.toml [project.scripts]`` 注册

设计参考:_research/PROJECT_DESCRIPTION.md §6.3 / 任务 9 + 13。
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

from . import __version__
from .config import WorkflowConfig
from .paths import WORKSPACE_ROOT
from .pipeline.audio import SUPPORTED_EXTS, find_media
from .pipeline.runner import PipelineResult, run_pipeline
from .state import STAGE_ORDER, State

# ─────────────────────────────────────────────────────────────
# 日志 helper —— 全部走 stderr,stdout 留给 JSON-RPC 帧
# ─────────────────────────────────────────────────────────────


def _log(msg: str) -> None:
  """调试日志走 stderr(参考实现的设计原则)。"""
  print(f"[mtd-mcp] {msg}", file=sys.stderr, flush=True)


# ─────────────────────────────────────────────────────────────
# Server 单例
# ─────────────────────────────────────────────────────────────

server: Server = Server("media-to-doc")

INSTRUCTIONS = (
  "media-to-doc:把本地培训音视频转为带 AI 配图、可独立分发的 Markdown + HTML 讲义。\n"
  "6 个工具:\n"
  "  - list_courses: 列出 inbox 课程\n"
  "  - run_pipeline: 跑完整流水线\n"
  "  - resume_pipeline: 续跑中断的流水线\n"
  "  - check_status: 查 state.json 进度\n"
  "  - list_outputs: 列出产物文件\n"
  "  - read_lecture: 读讲义 (raw/cleaned/final 三版本)"
)


# ─────────────────────────────────────────────────────────────
# JSON 序列化 helper
# ─────────────────────────────────────────────────────────────


def _json_dumps(payload: Any) -> str:
  """统一 JSON 序列化(ensure_ascii=False,indent=2)。"""
  return json.dumps(payload, ensure_ascii=False, indent=2)


def _pipeline_result_to_dict(result: PipelineResult, work: Path) -> dict[str, Any]:
  """把 PipelineResult 序列化为可 JSON 化的 dict(供 run/resume 复用)。"""
  return {
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


def _state_to_dict(state: State) -> dict[str, Any]:
  """把 State 序列化为可 JSON 化的 dict(供 check_status 复用)。"""
  return {
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


# ─────────────────────────────────────────────────────────────
# 路径 helper
# ─────────────────────────────────────────────────────────────


def _resolve_workspace(workspace_root: str | None) -> Path:
  """解析 workspace 根(优先入参,fallback 全局 WORKSPACE_ROOT)。"""
  if workspace_root:
    return Path(workspace_root).expanduser().resolve()
  return WORKSPACE_ROOT.resolve()


def _resolve_work_from_inbox(inbox: Path) -> Path:
  """``work_dir = <inbox>/output``(与 cli.run 默认值一致)。"""
  return (inbox / "output").resolve()


# ─────────────────────────────────────────────────────────────
# 6 个工具实现 —— 纯函数,失败抛 ValueError/FileNotFoundError
# ─────────────────────────────────────────────────────────────


def tool_list_courses(workspace_root: str | None = None) -> dict[str, Any]:
  """列出 inbox 下的课程。

  Parameters
  ----------
  workspace_root : str | None
    workspace 根目录;None 时用全局 WORKSPACE_ROOT

  Returns
  -------
  dict
    ``{"workspace": str, "courses": [{name, path, media_files, media_count}, ...]}``
  """
  ws_root = _resolve_workspace(workspace_root)
  inbox_root = ws_root / "inbox"

  if not inbox_root.exists():
    return {"workspace": str(ws_root), "inbox": str(inbox_root), "courses": []}

  courses: list[dict[str, Any]] = []
  for entry in sorted(inbox_root.iterdir()):
    if not entry.is_dir():
      continue
    media = [
      str(p.relative_to(entry)) for p in sorted(entry.rglob("*"))
      if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
    ]
    courses.append({
      "name": entry.name,
      "path": str(entry),
      "media_files": media,
      "media_count": len(media),
    })
  return {"workspace": str(ws_root), "inbox": str(inbox_root), "courses": courses}


def _build_config(
  llm: str | None,
  imagegen: str | None,
  longdoc_llm: str | None,
  no_longdoc: bool,
) -> WorkflowConfig:
  """从 MCP 入参派生 WorkflowConfig(参考 cli.run 的覆盖逻辑)。"""
  cfg = WorkflowConfig()
  if llm:
    cfg.llm.provider = llm  # type: ignore[assignment]
  if imagegen:
    cfg.imagegen.provider = imagegen  # type: ignore[assignment]
  if longdoc_llm:
    cfg.pipeline.longdoc_llm_provider = longdoc_llm
  if no_longdoc:
    cfg.pipeline.skip_longdoc = True
  return cfg


def tool_run_pipeline(
  inbox_dir: str,
  workspace_root: str | None = None,
  llm: str | None = None,
  imagegen: str | None = None,
  longdoc_llm: str | None = None,
  no_longdoc: bool = False,
  force: bool = False,
  stop_after: str | None = None,
) -> dict[str, Any]:
  """跑完整流水线。

  Parameters
  ----------
  inbox_dir : str
    源 inbox 目录(必填)
  workspace_root : str | None
    workspace 根(仅用于派生 inbox_path;work_dir 默认 = inbox/output)
  llm / imagegen / longdoc_llm : str | None
    provider 覆盖(同 cli.run)
  no_longdoc : bool
    是否跳过 longdoc 阶段
  force : bool
    强制重跑所有 stage
  stop_after : str | None
    跑到该 stage 后停下

  Returns
  -------
  dict
    PipelineResult JSON(``_pipeline_result_to_dict`` 格式)
  """
  inbox = Path(inbox_dir).expanduser().resolve()
  if not inbox.exists() or not inbox.is_dir():
    raise FileNotFoundError(f"inbox 目录不存在: {inbox}")

  work = _resolve_work_from_inbox(inbox)
  work.mkdir(parents=True, exist_ok=True)

  # 找目标视频(inbox 必须含至少一个媒体文件,否则抛错)
  target_video = find_media(inbox, exclude_dirs=[work])

  # inbox 自动隔离(避免多视频误选)—— 与 cli.run 默认行为一致
  moved: list[tuple[Path, Path]] = []
  staging_dir: Path | None = None
  media_count = sum(
    1 for p in inbox.rglob("*")
    if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
    and not p.resolve().is_relative_to(work.resolve())
  )
  if media_count > 1:
    staging_dir = work / f".excluded-{int(time.time())}"
    moved = _isolate_inbox(inbox, target_video, staging_dir, exclude_dirs=[work])
    if moved:
      _log(f"隔离 {len(moved)} 个非目标文件 → {staging_dir.name}")

  cfg = _build_config(llm, imagegen, longdoc_llm, no_longdoc)

  try:
    result = run_pipeline(
      inbox=inbox,
      work=work,
      config=cfg,
      skip_completed=not force,
      stop_after=stop_after,
    )
    return _pipeline_result_to_dict(result, work)
  finally:
    if moved and staging_dir is not None:
      try:
        _restore_isolated(moved, staging_dir)
      except Exception as exc:
        _log(f"WARN: 恢复隔离文件失败: {type(exc).__name__}: {exc}")


def tool_resume_pipeline(
  work_dir: str,
  inbox_dir: str | None = None,
  force: bool = False,
  stop_after: str | None = None,
) -> dict[str, Any]:
  """续跑中断的流水线。

  Parameters
  ----------
  work_dir : str
    work 目录(必填,含 state.json)
  inbox_dir : str | None
    覆盖 state.json 里的 inbox 路径
  force : bool
    强制重跑所有 stage
  stop_after : str | None
    跑到该 stage 后停下

  Returns
  -------
  dict
    PipelineResult JSON
  """
  work = Path(work_dir).expanduser().resolve()
  if not work.exists() or not work.is_dir():
    raise FileNotFoundError(f"work 目录不存在: {work}")
  state_path = work / "state.json"
  if not state_path.exists():
    raise FileNotFoundError(
      f"state.json 不存在: {state_path}\n"
      f"首次跑请用 run_pipeline(inbox_dir=...)"
    )

  inbox: Path | None = None
  if inbox_dir is not None:
    inbox = Path(inbox_dir).expanduser().resolve()

  result = run_pipeline(
    inbox=inbox,
    work=work,
    skip_completed=not force,
    stop_after=stop_after,
  )
  return _pipeline_result_to_dict(result, work)


def tool_check_status(work_dir: str) -> dict[str, Any]:
  """查 state.json 进度(只读)。

  Parameters
  ----------
  work_dir : str
    work 目录

  Returns
  -------
  dict
    State JSON(含 11 stage 状态)
  """
  work = Path(work_dir).expanduser().resolve()
  state_path = work / "state.json"
  if not state_path.exists():
    raise FileNotFoundError(f"state.json 不存在: {state_path}")
  state = State.load(state_path)
  return _state_to_dict(state)


def tool_list_outputs(inbox_dir: str) -> dict[str, Any]:
  """列出 inbox 跑完后 work/<course>/ 下的所有产物。

  Parameters
  ----------
  inbox_dir : str
    源 inbox 目录(work_dir 派生为 ``<inbox>/output``)

  Returns
  -------
  dict
    ``{"inbox": str, "work_dir": str, "outputs": {...}, "stages": {...}}``
    outputs 按类别分组:raw_md/raw_html/cleaned_md/final_html/images/manifests
  """
  inbox = Path(inbox_dir).expanduser().resolve()
  if not inbox.exists() or not inbox.is_dir():
    raise FileNotFoundError(f"inbox 目录不存在: {inbox}")
  work = _resolve_work_from_inbox(inbox)
  if not work.exists():
    raise FileNotFoundError(
      f"work 目录不存在: {work}\n"
      f"请先用 run_pipeline(inbox_dir=...) 跑完整流水线"
    )

  # 派生 stem(从 chapters/raw/ 的子目录名推断;若没有则用 "output")
  stem = "output"
  chapters_raw = work / "chapters" / "raw"
  if chapters_raw.exists():
    for entry in chapters_raw.iterdir():
      if entry.is_dir():
        stem = entry.name
        break

  raw_dir = chapters_raw / stem
  outputs: dict[str, list[str]] = {
    "raw_md": [],
    "raw_html": [],
    "cleaned_md": [],
    "final_html": [],
    "images": [],
    "manifests": [],
  }
  if raw_dir.exists():
    for p in sorted(raw_dir.rglob("*")):
      if not p.is_file():
        continue
      rel = str(p.relative_to(raw_dir))
      # 用 Path parts 检查 images/ 子目录(Windows 路径分隔符兼容)
      is_image = len(p.relative_to(raw_dir).parts) >= 2 and \
        p.relative_to(raw_dir).parts[0] == "images"
      if is_image:
        outputs["images"].append(rel)
      elif p.name == f"{stem}.md":
        outputs["raw_md"].append(rel)
      elif p.name == f"{stem}.html":
        outputs["raw_html"].append(rel)
      elif p.name == f"{stem}_cleaned.md":
        outputs["cleaned_md"].append(rel)
      elif p.name == f"{stem}_final.html":
        outputs["final_html"].append(rel)
      else:
        outputs["manifests"].append(rel)

  # verify.json 在 work 根目录
  verify_json = work / "verify.json"
  if verify_json.exists():
    outputs["manifests"].append("verify.json")

  # 推断每个 stage 是否完成(state.json 优先,否则看产物存在)
  state_path = work / "state.json"
  stage_status: dict[str, str] = {}
  if state_path.exists():
    state = State.load(state_path)
    for stage in STAGE_ORDER:
      stage_status[stage] = state.stages[stage].status
  else:
    # fallback:产物存在性推断
    raw_md = raw_dir / f"{stem}.md" if raw_dir.exists() else None
    final_html = raw_dir / f"{stem}_final.html" if raw_dir.exists() else None
    stage_status = {
      "audio": "completed" if (work / "asr" / "audio.wav").exists() else "pending",
      "asr": "completed" if (work / "asr" / "transcript.jsonl").exists() else "pending",
      "frames": "completed" if (work / "frames" / "keyframes.json").exists() else "pending",
      "ocr": "completed" if (work / "ocr" / "ocr_results.json").exists() else "pending",
      "asr_correct": "completed" if (work / "asr_correct" / "transcript_corrected.jsonl").exists() else "pending",
      "chapters": "completed" if (work / "chapters" / "chapters.json").exists() else "pending",
      "draft": "completed" if raw_dir.exists() and any(raw_dir.glob("chapter_*.md")) else "pending",
      "imagegen": "skipped",  # 默认 skip,无法从产物判断
      "render": "completed" if raw_md is not None and raw_md.exists() else "pending",
      "longdoc": "completed" if final_html is not None and final_html.exists() else "pending",
      "verify": "completed" if verify_json.exists() else "pending",
    }

  return {
    "inbox": str(inbox),
    "work_dir": str(work),
    "stem": stem,
    "outputs": outputs,
    "stages": stage_status,
  }


# read_lecture 的 version 取值
_VERSIONS: dict[str, dict[str, str]] = {
  "raw": {"md": "{stem}.md", "html": "{stem}.html"},
  "cleaned": {"md": "{stem}_cleaned.md", "html": "{stem}_cleaned.html"},
  "final": {"md": "{stem}_final.md", "html": "{stem}_final.html"},
}


def tool_read_lecture(
  inbox_dir: str,
  version: str,
  fmt: str = "md",
) -> dict[str, Any]:
  """读讲义(支持 raw / cleaned / final 三版本 + md / html 双格式)。

  Parameters
  ----------
  inbox_dir : str
    源 inbox 目录(work_dir 派生为 ``<inbox>/output``)
  version : str
    ``raw`` / ``cleaned`` / ``final``(必填)
  fmt : str
    ``md``(默认)/ ``html``

  Returns
  -------
  dict
    ``{"version", "fmt", "path", "content", "size_bytes"}``
  """
  if version not in _VERSIONS:
    raise ValueError(f"version 必须是 raw/cleaned/final,收到: {version!r}")
  if fmt not in ("md", "html"):
    raise ValueError(f"fmt 必须是 md/html,收到: {fmt!r}")

  inbox = Path(inbox_dir).expanduser().resolve()
  if not inbox.exists() or not inbox.is_dir():
    raise FileNotFoundError(f"inbox 目录不存在: {inbox}")
  work = _resolve_work_from_inbox(inbox)

  # 派生 stem
  stem = "output"
  chapters_raw = work / "chapters" / "raw"
  if chapters_raw.exists():
    for entry in chapters_raw.iterdir():
      if entry.is_dir():
        stem = entry.name
        break

  rel_name = _VERSIONS[version][fmt].format(stem=stem)
  target = chapters_raw / stem / rel_name

  # cleaned.md / cleaned.html / final.md 在某些路径下也直接放在 chapters/raw/
  # 兼容 <stem>_cleaned.md(没 html 版本,fallback 到 md 内容)
  if not target.exists() and fmt == "html":
    # fallback:html 不存在时返回说明
    alt = chapters_raw / stem / _VERSIONS[version]["md"].format(stem=stem)
    if alt.exists():
      return {
        "version": version,
        "fmt": fmt,
        "path": str(alt),
        "content": (
          f"# {stem} ({version} · {fmt})\n\n"
          f"(html 版本不存在,以下为 md 版本内容)\n\n"
          f"{alt.read_text(encoding='utf-8')}"
        ),
        "size_bytes": alt.stat().st_size,
        "note": "html 版本未生成,fallback 到 md",
      }
    raise FileNotFoundError(
      f"讲义文件不存在: {target}\n"
      f"可能是 longdoc 阶段未跑(version=cleaned/final) 或 "
      f"render 未生成(version=raw)"
    )

  if not target.exists():
    raise FileNotFoundError(
      f"讲义文件不存在: {target}\n"
      f"请先用 run_pipeline 跑完整流水线"
    )

  content = target.read_text(encoding="utf-8")
  return {
    "version": version,
    "fmt": fmt,
    "path": str(target),
    "content": content,
    "size_bytes": len(content.encode("utf-8")),
  }


# ─────────────────────────────────────────────────────────────
# inbox 隔离 helpers(从 cli.py 复用,避免循环 import)
# ─────────────────────────────────────────────────────────────


def _isolate_inbox(
  inbox: Path,
  target_video: Path,
  staging_dir: Path,
  *,
  exclude_dirs: list[Path] | None = None,
) -> list[tuple[Path, Path]]:
  """把 inbox 中除目标视频外的媒体文件 mv 到 ``staging_dir``。

  与 cli._isolate_inbox 同语义;放在本模块避免对 cli Typer 副作用的依赖。
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
  """把隔离的文件移回原路径(异常不抛,只 log)。"""
  import contextlib  # noqa: PLC0415 — 局部 import 避免 mcp_server 顶层依赖

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


# ─────────────────────────────────────────────────────────────
# 工具注册 —— inputSchema(JSON Schema) + handler
# ─────────────────────────────────────────────────────────────


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
  """注册 6 个 MCP 工具。"""
  return [
    types.Tool(
      name="list_courses",
      description="列出 workspace/inbox 下所有课程(每个子目录 + 媒体文件清单)",
      inputSchema={
        "type": "object",
        "properties": {
          "workspace_root": {
            "type": "string",
            "description": "workspace 根目录;省略时用全局默认",
          },
        },
        "additionalProperties": False,
      },
      annotations=types.ToolAnnotations(readOnlyHint=True),
    ),
    types.Tool(
      name="run_pipeline",
      description="跑完整流水线(audio → asr → ... → verify)。同步阻塞,长任务建议用 resume",
      inputSchema={
        "type": "object",
        "properties": {
          "inbox_dir": {
            "type": "string",
            "description": "源 inbox 目录(必填)",
          },
          "workspace_root": {
            "type": "string",
            "description": "workspace 根目录(可选)",
          },
          "llm": {
            "type": "string",
            "enum": ["ollama", "anthropic", "openai_compatible"],
            "description": "LLM provider 覆盖",
          },
          "imagegen": {
            "type": "string",
            "enum": ["local_sdxl", "skip"],
            "description": "imagegen provider 覆盖",
          },
          "longdoc_llm": {
            "type": "string",
            "description": "longdoc LLM provider(默认 skip 只跑规则清理)",
          },
          "no_longdoc": {
            "type": "boolean",
            "default": False,
            "description": "跳过 longdoc 阶段",
          },
          "force": {
            "type": "boolean",
            "default": False,
            "description": "强制重跑所有 stage",
          },
          "stop_after": {
            "type": "string",
            "enum": list(STAGE_ORDER),
            "description": "跑到该 stage 后停下(调试用)",
          },
        },
        "required": ["inbox_dir"],
        "additionalProperties": False,
      },
      annotations=types.ToolAnnotations(destructiveHint=False),
    ),
    types.Tool(
      name="resume_pipeline",
      description="续跑中断的流水线(从 work/state.json 恢复 inbox)",
      inputSchema={
        "type": "object",
        "properties": {
          "work_dir": {
            "type": "string",
            "description": "work 目录(必填,含 state.json)",
          },
          "inbox_dir": {
            "type": "string",
            "description": "覆盖 state.json 里的 inbox 路径",
          },
          "force": {
            "type": "boolean",
            "default": False,
            "description": "强制重跑所有 stage",
          },
          "stop_after": {
            "type": "string",
            "enum": list(STAGE_ORDER),
          },
        },
        "required": ["work_dir"],
        "additionalProperties": False,
      },
      annotations=types.ToolAnnotations(destructiveHint=False),
    ),
    types.Tool(
      name="check_status",
      description="查 state.json 进度(只读,11 stage 状态)",
      inputSchema={
        "type": "object",
        "properties": {
          "work_dir": {
            "type": "string",
            "description": "work 目录(必填)",
          },
        },
        "required": ["work_dir"],
        "additionalProperties": False,
      },
      annotations=types.ToolAnnotations(readOnlyHint=True),
    ),
    types.Tool(
      name="list_outputs",
      description="列出 work/<course>/ 下所有产物(raw/cleaned/final md+html+images)",
      inputSchema={
        "type": "object",
        "properties": {
          "inbox_dir": {
            "type": "string",
            "description": "源 inbox 目录(必填)",
          },
        },
        "required": ["inbox_dir"],
        "additionalProperties": False,
      },
      annotations=types.ToolAnnotations(readOnlyHint=True),
    ),
    types.Tool(
      name="read_lecture",
      description=(
        "读讲义内容(version: raw/cleaned/final 三版本 × md/html 双格式)"
      ),
      inputSchema={
        "type": "object",
        "properties": {
          "inbox_dir": {
            "type": "string",
            "description": "源 inbox 目录(必填)",
          },
          "version": {
            "type": "string",
            "enum": ["raw", "cleaned", "final"],
            "description": "讲义版本(raw=render 产物 / cleaned=longdoc md / final=longdoc html)",
          },
          "fmt": {
            "type": "string",
            "enum": ["md", "html"],
            "default": "md",
            "description": "输出格式(md 纯文本,html 含 CSS)",
          },
        },
        "required": ["inbox_dir", "version"],
        "additionalProperties": False,
      },
      annotations=types.ToolAnnotations(readOnlyHint=True),
    ),
  ]


@server.call_tool()
async def handle_call_tool(
  name: str, arguments: dict[str, Any] | None,
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
  """统一 MCP handler —— 包装 try/except,失败返回 isError=True。"""
  args = arguments or {}
  try:
    if name == "list_courses":
      payload = tool_list_courses(**args)
    elif name == "run_pipeline":
      payload = tool_run_pipeline(**args)
    elif name == "resume_pipeline":
      payload = tool_resume_pipeline(**args)
    elif name == "check_status":
      payload = tool_check_status(**args)
    elif name == "list_outputs":
      payload = tool_list_outputs(**args)
    elif name == "read_lecture":
      payload = tool_read_lecture(**args)
    else:
      raise ValueError(f"未知工具: {name!r}")
    return [types.TextContent(type="text", text=_json_dumps(payload))]
  except (ValueError, FileNotFoundError) as exc:
    _log(f"{name} 调用失败: {type(exc).__name__}: {exc}")
    err_payload = {"error": f"{type(exc).__name__}: {exc}", "tool": name}
    return [types.TextContent(type="text", text=_json_dumps(err_payload))]
  except Exception as exc:  # noqa: BLE001
    _log(f"{name} 内部错误: {type(exc).__name__}: {exc}")
    _log(traceback.format_exc())
    err_payload = {
      "error": f"{type(exc).__name__}: {exc}",
      "tool": name,
      "traceback": traceback.format_exc(),
    }
    return [types.TextContent(type="text", text=_json_dumps(err_payload))]


# ─────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────


async def _run() -> None:
  """stdio MCP server 主循环。"""
  _log(f"启动 media-to-doc MCP server v{__version__}")
  async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
    await server.run(
      read_stream,
      write_stream,
      server.create_initialization_options(
        server_name="media-to-doc",
        server_version=__version__,
        instructions=INSTRUCTIONS,
      ),
    )


def main() -> None:
  """``mtd-mcp`` 入口(``pyproject.toml [project.scripts]`` 注册)。"""
  import asyncio

  asyncio.run(_run())


if __name__ == "__main__":
  main()


__all__ = [
  "server",
  "tool_list_courses",
  "tool_run_pipeline",
  "tool_resume_pipeline",
  "tool_check_status",
  "tool_list_outputs",
  "tool_read_lecture",
  "main",
]
