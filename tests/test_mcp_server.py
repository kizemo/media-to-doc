"""``media_to_doc.mcp_server`` 单元测试(W7)。

策略:
- 6 个 tool 纯函数直接调(走 Path/str 入参,绕开 MCP 协议层)
- MCP 协议层用 ``asyncio.run`` + ``handle_call_tool`` 包装,验证:
  - list_tools 返回 6 个 Tool + annotations
  - call_tool 包装 try/except,失败返回 isError 不抛
- 不真跑 11 stage(monkeypatch run_pipeline)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from media_to_doc import mcp_server
from media_to_doc.pipeline.runner import PipelineResult
from media_to_doc.state import STAGE_ORDER, State

# ─────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────


def _make_work_with_state(work: Path, course: str = "demo") -> State:
  """在 work/ 下写一份最小 state.json(11 stage 都 completed),返回 State。"""
  work.mkdir(parents=True, exist_ok=True)
  state = State.new(course=course)
  for stage in STAGE_ORDER:
    state.mark(stage, "completed")
  state.save(work / "state.json")
  return state


def _make_work_with_outputs(work: Path, stem: str = "lesson1") -> Path:
  """在 work/ 下造一份最小产物链(供 list_outputs / read_lecture 读取)。

  返回 raw_dir。
  """
  work.mkdir(parents=True, exist_ok=True)
  raw_dir = work / "chapters" / "raw" / stem
  raw_dir.mkdir(parents=True, exist_ok=True)
  # render 产物
  (raw_dir / f"{stem}.md").write_text(f"# {stem} raw md\n", encoding="utf-8")
  (raw_dir / f"{stem}.html").write_text(f"<h1>{stem} raw html</h1>", encoding="utf-8")
  # draft 产物
  (raw_dir / "chapter_01.md").write_text("# ch1", encoding="utf-8")
  # longdoc 产物
  (raw_dir / f"{stem}_cleaned.md").write_text(f"# {stem} cleaned md\n", encoding="utf-8")
  (raw_dir / f"{stem}_final.html").write_text(f"<h1>{stem} final html</h1>", encoding="utf-8")
  # imagegen 产物
  (raw_dir / "images").mkdir(exist_ok=True)
  (raw_dir / "images" / "gen_001.png").write_bytes(b"\x89PNG" + b"\x00" * 50)
  # verify.json
  (work / "verify.json").write_text('{"overall_passed": true}', encoding="utf-8")
  # 其它中间产物(供 stage 推断)
  (work / "asr" / "audio.wav").parent.mkdir(parents=True, exist_ok=True)
  (work / "asr" / "audio.wav").write_bytes(b"x" * 100)
  (work / "asr" / "transcript.jsonl").write_text("{}", encoding="utf-8")
  (work / "frames" / "keyframes.json").parent.mkdir(parents=True, exist_ok=True)
  (work / "frames" / "keyframes.json").write_text("[]", encoding="utf-8")
  (work / "ocr" / "ocr_results.json").parent.mkdir(parents=True, exist_ok=True)
  (work / "ocr" / "ocr_results.json").write_text("{}", encoding="utf-8")
  (work / "asr_correct" / "transcript_corrected.jsonl").parent.mkdir(parents=True, exist_ok=True)
  (work / "asr_correct" / "transcript_corrected.jsonl").write_text("{}", encoding="utf-8")
  (work / "chapters" / "chapters.json").parent.mkdir(parents=True, exist_ok=True)
  (work / "chapters" / "chapters.json").write_text(
    json.dumps({"video": stem, "chapters": []}), encoding="utf-8"
  )
  return raw_dir


def _fake_run_pipeline(
  inbox: Path | None,
  work: Path,
  config: Any = None,
  *,
  skip_completed: bool = True,
  stop_after: str | None = None,
) -> PipelineResult:
  """run_pipeline stub:模拟 inbox 派生 + state 写入。"""
  state_path = work / "state.json"
  state = State.load(state_path) if state_path.exists() else State.new(course=work.name)

  if inbox is None:
    if state.inbox_path:
      inbox = Path(state.inbox_path)
    else:
      raise ValueError("inbox 缺省且 state.json 未记录 inbox_path")
  inbox = inbox.resolve()

  if state.inbox_path != str(inbox):
    state.inbox_path = str(inbox)
  for stage_name in STAGE_ORDER:
    state.mark(stage_name, "completed")
  state.save(state_path)

  return PipelineResult(
    state=state,
    completed=list(STAGE_ORDER),
    failed=[],
    duration_seconds=0.1,
  )


# ─────────────────────────────────────────────────────────────
# tool_list_courses
# ─────────────────────────────────────────────────────────────


def test_list_courses_empty_inbox(tmp_path: Path) -> None:
  """空 inbox → 返回空 courses 列表。"""
  inbox_root = tmp_path / "inbox"
  inbox_root.mkdir()
  result = mcp_server.tool_list_courses(workspace_root=str(tmp_path))
  assert result["courses"] == []
  assert result["inbox"] == str(inbox_root.resolve())


def test_list_courses_multiple(tmp_path: Path) -> None:
  """多课程 + 含媒体文件。"""
  inbox_root = tmp_path / "inbox"
  inbox_root.mkdir()
  (inbox_root / "course_a").mkdir()
  (inbox_root / "course_a" / "video.mp4").write_bytes(b"x" * 10)
  (inbox_root / "course_a" / "extra.mkv").write_bytes(b"y" * 10)
  (inbox_root / "course_b").mkdir()
  (inbox_root / "course_b" / "audio.m4a").write_bytes(b"y" * 20)
  # 非媒体文件不算
  (inbox_root / "course_b" / "notes.txt").write_text("notes", encoding="utf-8")
  # 顶层文件不算课程
  (inbox_root / "orphan.mp4").write_bytes(b"z" * 5)

  result = mcp_server.tool_list_courses(workspace_root=str(tmp_path))
  courses = result["courses"]
  assert len(courses) == 2
  by_name = {c["name"]: c for c in courses}
  assert by_name["course_a"]["media_count"] == 2  # .mp4 + .mkv
  assert by_name["course_b"]["media_count"] == 1  # .m4a only


def test_list_courses_nonexistent_workspace(tmp_path: Path) -> None:
  """workspace 不存在 → courses=[](友好提示)。"""
  result = mcp_server.tool_list_courses(workspace_root=str(tmp_path / "nope"))
  assert result["courses"] == []


# ─────────────────────────────────────────────────────────────
# tool_run_pipeline
# ─────────────────────────────────────────────────────────────


def test_run_pipeline_creates_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
  """run_pipeline 写入 state.json 并返回完整 PipelineResult 摘要。"""
  inbox = tmp_path / "inbox" / "lesson"
  inbox.mkdir(parents=True)
  (inbox / "video.mp4").write_bytes(b"x" * 10)
  captured: list[dict[str, Any]] = []

  def fake(inbox, work, config=None, *, skip_completed=True, stop_after=None):
    captured.append({"inbox": inbox, "work": work, "skip_completed": skip_completed})
    return _fake_run_pipeline(inbox, work, config,
                              skip_completed=skip_completed, stop_after=stop_after)

  monkeypatch.setattr(mcp_server, "run_pipeline", fake)

  result = mcp_server.tool_run_pipeline(inbox_dir=str(inbox))
  assert result["is_success"] is True
  assert result["course"] == "output"  # default stem from inbox/output
  assert len(result["completed"]) == 11
  assert result["work_dir"] == str((inbox / "output").resolve())
  assert captured[0]["inbox"] == inbox.resolve()


def test_run_pipeline_inbox_not_found(tmp_path: Path) -> None:
  """inbox 不存在 → FileNotFoundError。"""
  with pytest.raises(FileNotFoundError, match="inbox 目录不存在"):
    mcp_server.tool_run_pipeline(inbox_dir=str(tmp_path / "nope"))


def test_run_pipeline_no_media_in_inbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
  """inbox 空目录 → find_media 抛 FileNotFoundError,run_pipeline 透传。"""
  inbox = tmp_path / "empty"
  inbox.mkdir()
  monkeypatch.setattr(mcp_server, "run_pipeline", _fake_run_pipeline)
  with pytest.raises(FileNotFoundError):
    mcp_server.tool_run_pipeline(inbox_dir=str(inbox))


def test_run_pipeline_passes_config_overrides(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """llm / imagegen / longdoc_llm / no_longdoc 覆盖项生效。"""
  inbox = tmp_path / "lesson"
  inbox.mkdir()
  (inbox / "video.mp4").write_bytes(b"x" * 10)
  captured_configs: list[Any] = []

  def fake(inbox, work, config=None, *, skip_completed=True, stop_after=None):
    captured_configs.append(config)
    return _fake_run_pipeline(inbox, work, config,
                              skip_completed=skip_completed, stop_after=stop_after)

  monkeypatch.setattr(mcp_server, "run_pipeline", fake)
  mcp_server.tool_run_pipeline(
    inbox_dir=str(inbox),
    llm="anthropic",
    imagegen="skip",
    longdoc_llm="ollama",
    no_longdoc=True,
  )
  cfg = captured_configs[0]
  assert cfg is not None
  assert cfg.llm.provider == "anthropic"
  assert cfg.imagegen.provider == "skip"
  assert cfg.pipeline.longdoc_llm_provider == "ollama"
  assert cfg.pipeline.skip_longdoc is True


def test_run_pipeline_force_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
  """force=True → skip_completed=False 透传。"""
  inbox = tmp_path / "lesson"
  inbox.mkdir()
  (inbox / "video.mp4").write_bytes(b"x" * 10)
  captured: list[bool] = []

  def fake(inbox, work, config=None, *, skip_completed=True, stop_after=None):
    captured.append(skip_completed)
    return _fake_run_pipeline(inbox, work, config,
                              skip_completed=skip_completed, stop_after=stop_after)

  monkeypatch.setattr(mcp_server, "run_pipeline", fake)
  mcp_server.tool_run_pipeline(inbox_dir=str(inbox), force=True)
  assert captured[0] is False


def test_run_pipeline_isolates_inbox_multivideo(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """inbox 多视频 → 自动隔离,跑完恢复。"""
  inbox = tmp_path / "lesson"
  inbox.mkdir()
  (inbox / "video1.mp4").write_bytes(b"x" * 10)
  (inbox / "video2.mp4").write_bytes(b"y" * 20)  # 多视频,ASCII 排序选 video1
  # 让 work 在 inbox 外(避免 rglob 误移 work 内的文件)
  monkeypatch.setattr(mcp_server, "run_pipeline", _fake_run_pipeline)
  mcp_server.tool_run_pipeline(inbox_dir=str(inbox))
  # 跑完后,被隔离的视频应该已经恢复回 inbox
  assert (inbox / "video2.mp4").exists()
  # work 下的 .excluded-* staging 目录应该被清理
  work = inbox / "output"
  excluded = list(work.glob(".excluded-*"))
  assert excluded == [], f"staging 目录应已清理,残留: {excluded}"


# ─────────────────────────────────────────────────────────────
# tool_resume_pipeline
# ─────────────────────────────────────────────────────────────


def test_resume_pipeline_uses_state_inbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
  """resume 不传 inbox_dir → 从 state.inbox_path 派生。"""
  work = tmp_path / "work"
  original_inbox = tmp_path / "original_inbox"
  original_inbox.mkdir()
  _make_work_with_state(work)
  state = State.load(work / "state.json")
  state.inbox_path = str(original_inbox)
  state.save(work / "state.json")

  captured: list[dict[str, Any]] = []

  def fake(inbox, work, config=None, *, skip_completed=True, stop_after=None):
    # 模拟 run_pipeline 派生:inbox=None → 从 state.inbox_path 读
    if inbox is None:
      inbox = Path(State.load(work / "state.json").inbox_path or "")
    inbox = inbox.resolve()
    captured.append({"inbox": inbox, "work": work})
    return _fake_run_pipeline(inbox, work, config,
                              skip_completed=skip_completed, stop_after=stop_after)

  monkeypatch.setattr(mcp_server, "run_pipeline", fake)
  mcp_server.tool_resume_pipeline(work_dir=str(work))
  assert captured[0]["inbox"] == original_inbox.resolve()


def test_resume_pipeline_inbox_override(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """resume 传 inbox_dir → 覆盖 state 里的 inbox。"""
  work = tmp_path / "work"
  _make_work_with_state(work)
  new_inbox = tmp_path / "new_inbox"
  new_inbox.mkdir()

  captured: list[Path | None] = []

  def fake(inbox, work, config=None, *, skip_completed=True, stop_after=None):
    captured.append(inbox)
    return _fake_run_pipeline(inbox, work, config,
                              skip_completed=skip_completed, stop_after=stop_after)

  monkeypatch.setattr(mcp_server, "run_pipeline", fake)
  mcp_server.tool_resume_pipeline(work_dir=str(work), inbox_dir=str(new_inbox))
  assert captured[0] == new_inbox.resolve()


def test_resume_pipeline_no_state_json(tmp_path: Path) -> None:
  """resume 找不到 state.json → FileNotFoundError。"""
  work = tmp_path / "empty_work"
  work.mkdir()
  with pytest.raises(FileNotFoundError, match="state.json 不存在"):
    mcp_server.tool_resume_pipeline(work_dir=str(work))


def test_resume_pipeline_work_not_found(tmp_path: Path) -> None:
  """work 目录不存在 → FileNotFoundError。"""
  with pytest.raises(FileNotFoundError, match="work 目录不存在"):
    mcp_server.tool_resume_pipeline(work_dir=str(tmp_path / "nope"))


# ─────────────────────────────────────────────────────────────
# tool_check_status
# ─────────────────────────────────────────────────────────────


def test_check_status_returns_state_dict(tmp_path: Path) -> None:
  """check_status 返回 11 stage 状态。"""
  work = tmp_path / "work"
  _make_work_with_state(work)
  result = mcp_server.tool_check_status(work_dir=str(work))
  assert result["is_complete"] is True
  assert all(
    result["stages"][stage]["status"] == "completed"
    for stage in STAGE_ORDER
  )


def test_check_status_no_state_json(tmp_path: Path) -> None:
  """check_status 找不到 state.json → FileNotFoundError。"""
  work = tmp_path / "no_state"
  work.mkdir()
  with pytest.raises(FileNotFoundError, match="state.json 不存在"):
    mcp_server.tool_check_status(work_dir=str(work))


# ─────────────────────────────────────────────────────────────
# tool_list_outputs
# ─────────────────────────────────────────────────────────────


def test_list_outputs_groups_by_category(tmp_path: Path) -> None:
  """list_outputs 把产物按类别分组。"""
  inbox = tmp_path / "lesson"
  inbox.mkdir()
  work = inbox / "output"
  _make_work_with_outputs(work, stem="lesson1")
  result = mcp_server.tool_list_outputs(inbox_dir=str(inbox))
  assert result["stem"] == "lesson1"
  outputs = result["outputs"]
  assert "chapter_01.md" not in outputs["raw_md"]  # draft 产物不在 raw_md
  assert any("lesson1.md" in p for p in outputs["raw_md"])
  assert any("lesson1.html" in p for p in outputs["raw_html"])
  assert any("lesson1_cleaned.md" in p for p in outputs["cleaned_md"])
  assert any("lesson1_final.html" in p for p in outputs["final_html"])
  assert any("gen_001.png" in p for p in outputs["images"])
  assert "verify.json" in outputs["manifests"]


def test_list_outputs_infer_stage_status(tmp_path: Path) -> None:
  """没有 state.json → 推断 stage 状态。"""
  inbox = tmp_path / "lesson"
  inbox.mkdir()
  work = inbox / "output"
  _make_work_with_outputs(work)
  result = mcp_server.tool_list_outputs(inbox_dir=str(inbox))
  stages = result["stages"]
  assert stages["audio"] == "completed"
  assert stages["asr"] == "completed"
  assert stages["render"] == "completed"
  assert stages["longdoc"] == "completed"
  assert stages["verify"] == "completed"


def test_list_outputs_no_work(tmp_path: Path) -> None:
  """work 目录不存在 → FileNotFoundError。"""
  inbox = tmp_path / "no_work"
  inbox.mkdir()
  with pytest.raises(FileNotFoundError, match="work 目录不存在"):
    mcp_server.tool_list_outputs(inbox_dir=str(inbox))


# ─────────────────────────────────────────────────────────────
# tool_read_lecture
# ─────────────────────────────────────────────────────────────


def test_read_lecture_raw_md(tmp_path: Path) -> None:
  """read_lecture(raw, md) → 读 <stem>.md。"""
  inbox = tmp_path / "lesson"
  inbox.mkdir()
  work = inbox / "output"
  _make_work_with_outputs(work, stem="L1")
  result = mcp_server.tool_read_lecture(inbox_dir=str(inbox), version="raw", fmt="md")
  assert result["version"] == "raw"
  assert result["fmt"] == "md"
  assert "L1 raw md" in result["content"]
  assert result["path"].endswith("L1.md")


def test_read_lecture_final_html(tmp_path: Path) -> None:
  """read_lecture(final, html) → 读 <stem>_final.html。"""
  inbox = tmp_path / "lesson"
  inbox.mkdir()
  work = inbox / "output"
  _make_work_with_outputs(work, stem="L2")
  result = mcp_server.tool_read_lecture(inbox_dir=str(inbox), version="final", fmt="html")
  assert result["version"] == "final"
  assert "<h1>L2 final html</h1>" in result["content"]


def test_read_lecture_cleaned_md(tmp_path: Path) -> None:
  """read_lecture(cleaned, md) → 读 <stem>_cleaned.md。"""
  inbox = tmp_path / "lesson"
  inbox.mkdir()
  work = inbox / "output"
  _make_work_with_outputs(work, stem="L3")
  result = mcp_server.tool_read_lecture(inbox_dir=str(inbox), version="cleaned", fmt="md")
  assert "L3 cleaned md" in result["content"]


def test_read_lecture_invalid_version(tmp_path: Path) -> None:
  """version 非法 → ValueError。"""
  inbox = tmp_path / "lesson"
  inbox.mkdir()
  with pytest.raises(ValueError, match="version 必须是 raw/cleaned/final"):
    mcp_server.tool_read_lecture(inbox_dir=str(inbox), version="bogus")


def test_read_lecture_invalid_fmt(tmp_path: Path) -> None:
  """fmt 非法 → ValueError。"""
  inbox = tmp_path / "lesson"
  inbox.mkdir()
  with pytest.raises(ValueError, match="fmt 必须是 md/html"):
    mcp_server.tool_read_lecture(inbox_dir=str(inbox), version="raw", fmt="pdf")


def test_read_lecture_file_missing(tmp_path: Path) -> None:
  """讲义文件不存在 → FileNotFoundError。"""
  inbox = tmp_path / "no_output"
  inbox.mkdir()
  with pytest.raises(FileNotFoundError, match="请先用 run_pipeline"):
    mcp_server.tool_read_lecture(inbox_dir=str(inbox), version="final")


# ─────────────────────────────────────────────────────────────
# MCP 协议层 —— handle_list_tools / handle_call_tool
# ─────────────────────────────────────────────────────────────


def test_list_tools_returns_six() -> None:
  """handle_list_tools 返回 6 个 Tool,带 readOnlyHint 标注。"""
  tools = asyncio.run(mcp_server.handle_list_tools())
  names = {t.name for t in tools}
  assert names == {
    "list_courses", "run_pipeline", "resume_pipeline",
    "check_status", "list_outputs", "read_lecture",
  }
  # 4 个 read-only 工具
  read_only = {t.name for t in tools if t.annotations and t.annotations.readOnlyHint}
  assert read_only == {"list_courses", "check_status", "list_outputs", "read_lecture"}
  # 全部有 inputSchema
  assert all(t.inputSchema.get("type") == "object" for t in tools)


def test_call_tool_wraps_file_not_found(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """call_tool 包装 FileNotFoundError → 返回 TextContent 含错误信息(不抛)。"""
  monkeypatch.setattr(mcp_server, "run_pipeline", _fake_run_pipeline)
  result = asyncio.run(mcp_server.handle_call_tool(
    "read_lecture",
    {"inbox_dir": str(tmp_path / "nope"), "version": "raw"},
  ))
  assert len(result) == 1
  text_block = result[0]
  assert text_block.text  # 包含 JSON 错误信息
  parsed = json.loads(text_block.text)
  assert "error" in parsed
  assert "FileNotFoundError" in parsed["error"]


def test_call_tool_wraps_value_error() -> None:
  """call_tool 包装 ValueError(未知工具名) → 返回错误信息。"""
  result = asyncio.run(mcp_server.handle_call_tool("bogus_tool", {}))
  parsed = json.loads(result[0].text)
  assert "未知工具" in parsed["error"]


def test_call_tool_success_returns_json(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """call_tool 成功 → 返回 JSON 字符串。"""
  work = tmp_path / "work"
  _make_work_with_state(work)
  result = asyncio.run(mcp_server.handle_call_tool(
    "check_status", {"work_dir": str(work)},
  ))
  parsed = json.loads(result[0].text)
  assert parsed["is_complete"] is True
  assert len(parsed["stages"]) == 11


def test_call_tool_internal_exception_returns_traceback(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """call_tool 内部未捕获异常 → 返回 traceback(便于调试)。"""

  def boom(*args, **kwargs):
    raise RuntimeError("boom")

  monkeypatch.setattr(mcp_server, "tool_check_status", boom)
  result = asyncio.run(mcp_server.handle_call_tool(
    "check_status", {"work_dir": str(tmp_path)},
  ))
  parsed = json.loads(result[0].text)
  assert "RuntimeError" in parsed["error"]
  assert "traceback" in parsed


# ─────────────────────────────────────────────────────────────
# mtd mcp 子命令 + main 入口
# ─────────────────────────────────────────────────────────────


def test_mtd_mcp_command_invokes_server(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
  """mtd mcp 命令调 mcp_server.main()(不再抛 NotImplementedError)。"""
  from typer.testing import CliRunner

  from media_to_doc.cli import app

  called = {"ok": False}

  def fake_main() -> None:
    called["ok"] = True

  monkeypatch.setattr("media_to_doc.mcp_server.main", fake_main)
  CliRunner().invoke(app, ["mcp"])
  assert called["ok"] is True
