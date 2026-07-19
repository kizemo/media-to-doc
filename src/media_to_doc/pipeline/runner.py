"""流水线编排器(runner)— 串起 11 stage + LE 闭环。

W4 状态(2026-07-18):
- 11 stage 全部实装:``audio`` / ``asr`` / ``frames`` / ``ocr`` / ``asr_correct`` /
  ``chapters`` / ``draft`` / ``imagegen`` / ``render`` / ``longdoc`` / ``verify``
- longdoc / verify 由 :mod:`longdoc` / :mod:`verify` 提供真函数

W8 状态(2026-07-19):
- LE L1 执行层接入:``run_stage`` 用 ``timed_stage(logger, stage)`` 替换裸 try/except
- LE L2 审核层接入:``run_pipeline`` 末尾 ``gatekeeper_check(work)``
- LE L3 沉淀层接入:``PipelineLogger.finalize()`` 写 ``<work>/pipeline_run.json``
- LE L4 进化层接入:``post_pipeline_hook(work)`` 扫 Pattern-Key + LLM 健康度

双轨持久化:
- ``<work>/state.json`` = 调度状态(W4 已有,11 stage + 时间戳 + error)
- ``<work>/pipeline_run.json`` = LE 沉淀(W8 新增,quality + llm_health + gatekeeper_passed)

核心职责:
1. 状态机:加载/保存 state.json,跳过已完成 stage
2. 错误处理:stage 失败 → mark + 抛 + 不吞异常(LE 也会写 ERRORS.md)
3. 上下文分发:每 stage 拿到 (inbox, work, config) + 各自的 kwargs
4. LE 收尾:无论成败,finally 块跑 gatekeeper + finalize + post_pipeline_hook

参考:TDD §4.1.3 ``pipeline/runner.py`` 伪代码 +
     LE 原型 ``_research/le_prototype/runner.py`` 接口约定(已迁移)。
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import WorkflowConfig
from ..logger import (
  GatekeeperResult,
  PipelineLogger,
  PipelineRun,
  gatekeeper_check,
  post_pipeline_hook,
  timed_stage,
)
from ..state import STAGE_ORDER, StageState, State
from .asr import transcribe
from .asr_correct import correct_asr
from .audio import prepare_audio
from .chapters import split_chapters
from .draft import generate_drafts
from .frames import extract_keyframes
from .imagegen import generate_images
from .longdoc import process_long_doc
from .ocr import run_ocr
from .render import render_outputs
from .verify import verify_pipeline

# ─────────────────────────────────────────────────────────────
# STAGE_FUNCS — stage 名 → 函数映射(便于 runner 调度 + 测试覆盖)
# ─────────────────────────────────────────────────────────────


# 占位:未实现的 stage 抛清晰错误
def _not_implemented_stage(*args: Any, **kwargs: Any) -> None:
  raise NotImplementedError(
    f"Stage {kwargs.get('_stage_name', '?')} 尚未实装(Phase 1 W4+)",
  )


def _chapters_wrapper(work: Path, config: WorkflowConfig) -> Any:
  """chapters 阶段的实际包装:从 config 派生 LLM provider,再调 split_chapters。

  设计原因:runner 的 STAGE_FUNCS 想保持 ``func(work, config)`` 统一签名,
  但 :func:`split_chapters` 需要 provider 实例。包装层做工厂调用。
  """
  from ..llm import get_provider

  llm_cfg = config.llm
  provider = get_provider(
    llm_cfg.provider,
    model=llm_cfg.model,
    api_key=llm_cfg.api_key_ref,
    base_url=llm_cfg.base_url,
    temperature=llm_cfg.temperature,
    max_tokens=llm_cfg.max_tokens,
    timeout_seconds=llm_cfg.timeout_seconds,
    num_ctx=llm_cfg.num_ctx,
  )
  return split_chapters(work, provider, config)


def _draft_wrapper(work: Path, config: WorkflowConfig) -> Any:
  """draft 阶段的包装:从 config 派生 LLM provider,再调 generate_drafts。"""
  from ..llm import get_provider

  llm_cfg = config.llm
  provider = get_provider(
    llm_cfg.provider,
    model=llm_cfg.model,
    api_key=llm_cfg.api_key_ref,
    base_url=llm_cfg.base_url,
    temperature=llm_cfg.temperature,
    max_tokens=llm_cfg.max_tokens,
    timeout_seconds=llm_cfg.timeout_seconds,
    num_ctx=llm_cfg.num_ctx,
  )
  return generate_drafts(work, provider, config)


def _longdoc_wrapper(work: Path, config: WorkflowConfig) -> Any:
  """longdoc 阶段的包装:从 config 派生 LLM provider(provider='skip' 时短路)。

  ``config.pipeline.longdoc_llm_provider == "skip"`` → 不创建 provider,传 None;
  ``process_long_doc`` 内部检测到 ``provider is None`` 时只跑规则清理。
  """
  from ..llm import get_provider

  if config.pipeline.longdoc_llm_provider == "skip":
    return process_long_doc(work, None, config)

  llm_cfg = config.llm
  provider = get_provider(
    llm_cfg.provider,
    model=llm_cfg.model,
    api_key=llm_cfg.api_key_ref,
    base_url=llm_cfg.base_url,
    temperature=llm_cfg.temperature,
    max_tokens=llm_cfg.max_tokens,
    timeout_seconds=llm_cfg.timeout_seconds,
  )
  return process_long_doc(work, provider, config)


STAGE_FUNCS: dict[str, Callable[..., Any]] = {
  "audio": prepare_audio,           # audio(inbox, work, config)
  "asr": transcribe,                # asr(work, config, ...)
  "frames": extract_keyframes,      # frames(video, img_dir, work_dir, config, hint_timestamps)
  "ocr": run_ocr,                   # ocr(img_dir, config, output_dir=, manifest_path=)
  "asr_correct": correct_asr,       # asr_correct(work, config, ocr_dir=, transcript_path=, output_path=)
  "chapters": _chapters_wrapper,    # chapters(work, config) → 内部调 LLM
  "draft": _draft_wrapper,          # draft(work, config) → 内部调 LLM
  "imagegen": generate_images,      # imagegen(work, config)
  "render": render_outputs,         # render(work, config)
  "longdoc": _longdoc_wrapper,      # longdoc(work, config) → 内部调 LLM 或 skip
  "verify": verify_pipeline,        # verify(work, ...)
}


# ─────────────────────────────────────────────────────────────
# StageContext — 每 stage 运行时共享上下文
# ─────────────────────────────────────────────────────────────


@dataclass
class StageContext:
  """每 stage 共享的数据。

  Fields
  ------
  inbox : Path
    源 inbox 目录(音视频 + 产物)
  work : Path
    中间产物根目录(state.json 所在)
  video : Path | None
    inbox 内第一个媒体文件(由 :func:`audio.find_media` 派生)
  img_dir : Path | None
    关键帧目录(``<inbox>/img/``)
  config : WorkflowConfig
    运行时配置
  hint_timestamps : list[float]
    ASR 转写产生的段落起止时间戳(``frames`` stage 用,前置 ``asr`` 后才有)
  """

  inbox: Path
  work: Path
  config: WorkflowConfig
  video: Path | None = None
  img_dir: Path | None = None
  hint_timestamps: list[float] = field(default_factory=list)

  def resolve_video(self) -> Path:
    if self.video is None:
      from .audio import find_media
      self.video = find_media(self.inbox)
    return self.video


# ─────────────────────────────────────────────────────────────
# PipelineResult — run_pipeline 返回值
# ─────────────────────────────────────────────────────────────


@dataclass
class PipelineResult:
  """``run_pipeline()`` 的返回摘要。

  Fields
  ------
  state : State
    最终 State 对象(已落盘)
  completed : list[str]
    本次 run 中完成或跳过的 stage 名
  failed : list[str]
    本次 run 中失败的 stage 名(若有)
  duration_seconds : float
    整个 run 耗时
  pipeline_run : PipelineRun | None
    LE L3 沉淀层的 :class:`PipelineRun` 对象(``<work>/pipeline_run.json`` 内容),
    若 LE 写盘失败则为 ``None``
  """

  state: State
  completed: list[str]
  failed: list[str]
  duration_seconds: float
  pipeline_run: PipelineRun | None = None

  @property
  def is_success(self) -> bool:
    return not self.failed and self.state.is_complete()


# ─────────────────────────────────────────────────────────────
# 单 stage 调度
# ─────────────────────────────────────────────────────────────


def run_stage(
  stage: str,
  ctx: StageContext,
  state: State,
  logger: PipelineLogger | None = None,
) -> StageState:
  """执行单个 stage,返回更新后的 :class:`StageState`。

  行为:
  - 检查 ``state.is_completed`` → 直接跳过,返回当前 stage_state
  - ``mark(stage, 'running')`` → save
  - 调用 :data:`STAGE_FUNCS`[stage],按 stage 名 + ctx 字段分发参数
  - 用 LE ``timed_stage(logger, stage)`` 包裹 stage 执行 → 自动写 memory 行 + ERRORS.md(失败时)
  - 成功 → ``mark(stage, 'completed')`` + save
  - 失败 → ``mark(stage, 'failed', error=str)`` + save,异常上抛

  Parameters
  ----------
  stage : str
    stage 名,必须是 :data:`STAGE_ORDER` 之一
  ctx : StageContext
    运行时上下文(inbox / work / config / video / img_dir / hint_timestamps)
  state : State
    流水线状态机(已落盘或新建)
  logger : PipelineLogger | None
    LE L3 沉淀 logger;若 ``None`` → 创建一个临时 logger(向后兼容单独调用 ``run_stage`` 的测试)
  """
  if stage not in STAGE_FUNCS:
    raise KeyError(f"未知 stage: {stage!r}")
  if stage not in state.stages:
    raise KeyError(f"State 缺少 stage: {stage!r}")

  stage_state = state.stages[stage]
  if stage_state.is_completed:
    return stage_state

  state.mark(stage, "running")
  _save_state(state, ctx.work)

  func = STAGE_FUNCS[stage]

  # 临时 logger(向后兼容单独调用 ``run_stage`` 的测试,不传 logger 时也能跑 LE)
  if logger is None:
    logger = PipelineLogger(ctx.work, course=state.course)

  try:
    with timed_stage(logger, stage):
      _invoke_stage(stage, func, ctx)
  except Exception as exc:
    state.mark(stage, "failed", error=_format_error(exc))
    _save_state(state, ctx.work)
    raise

  state.mark(stage, "completed")
  _save_state(state, ctx.work)
  return stage_state


def _invoke_stage(stage: str, func: Callable[..., Any], ctx: StageContext) -> None:
  """按 stage 名字分发参数,真正调用 stage 函数。

  与 STAGE_FUNCS 解耦是为了让 runner 不需要为每个 stage 写分支。
  """
  if stage == "audio":
    func(ctx.inbox, ctx.work, ctx.config)
    return

  if stage == "asr":
    # 仅在 audio 完成后才能跑 asr;若 audio 失败 throw
    if ctx.work.joinpath("asr", "audio.wav").exists() is False:
      raise FileNotFoundError("asr stage 需要 audio.wav;请先跑 audio stage")
    func(ctx.work, ctx.config)
    # 提取 hint_timestamps 供 frames 使用
    if ctx.hint_timestamps == []:
      ctx.hint_timestamps = _read_segment_endpoints(ctx.work)
    return

  if stage == "frames":
    video = ctx.resolve_video()
    img_dir = ctx.img_dir or (ctx.inbox / "img")
    func(video, img_dir, ctx.work, ctx.config, ctx.hint_timestamps)
    return

  if stage == "ocr":
    # ocr 跑前需要 frames 完成(关键帧存在)
    img_dir = ctx.img_dir or (ctx.inbox / "img")
    if not img_dir.exists() or not any(img_dir.iterdir()):
      raise FileNotFoundError(
        f"ocr stage 需要关键帧目录 {img_dir} 非空;请先跑 frames stage"
      )
    # OCR 输出统一写到 work/ocr/ — asr_correct 默认从这里读
    output_dir = ctx.work / "ocr"
    manifest_path = output_dir / "ocr_results.json"
    func(img_dir, ctx.config, output_dir=output_dir, manifest_path=manifest_path)
    return

  if stage == "asr_correct":
    # asr_correct 依赖 asr 和 ocr 产物
    if not (ctx.work / "asr" / "transcript.jsonl").exists():
      raise FileNotFoundError(
        "asr_correct stage 需要 transcript.jsonl;请先跑 asr stage"
      )
    func(ctx.work, ctx.config, ocr_dir=ctx.work / "ocr")
    return

  if stage == "chapters":
    # chapters 依赖 asr + frames + (可选) asr_correct
    if not (ctx.work / "asr" / "transcript.jsonl").exists():
      raise FileNotFoundError(
        "chapters stage 需要 transcript.jsonl;请先跑 asr stage"
      )
    if not (ctx.work / "frames" / "keyframes.json").exists():
      raise FileNotFoundError(
        "chapters stage 需要 keyframes.json;请先跑 frames stage"
      )
    func(ctx.work, ctx.config)
    return

  if stage == "draft":
    # draft 依赖 chapters + asr
    if not (ctx.work / "chapters" / "chapters.json").exists():
      raise FileNotFoundError(
        "draft stage 需要 chapters.json;请先跑 chapters stage"
      )
    if not (ctx.work / "asr" / "transcript.jsonl").exists():
      raise FileNotFoundError(
        "draft stage 需要 transcript.jsonl;请先跑 asr stage"
      )
    func(ctx.work, ctx.config)
    return

  if stage == "imagegen":
    # imagegen 依赖 draft(产物 chapter_NN.md)
    drafts_dir = _resolve_drafts_dir(ctx.work)
    if drafts_dir is None:
      raise FileNotFoundError(
        "imagegen stage 需要 drafts 目录(含 chapter_NN.md);请先跑 draft stage"
      )
    func(ctx.work, ctx.config, drafts_dir=drafts_dir)
    return

  if stage == "render":
    # render 依赖 chapters + draft
    if not (ctx.work / "chapters" / "chapters.json").exists():
      raise FileNotFoundError(
        "render stage 需要 chapters.json;请先跑 chapters stage"
      )
    drafts_dir = _resolve_drafts_dir(ctx.work)
    if drafts_dir is None:
      raise FileNotFoundError(
        "render stage 需要 drafts 目录;请先跑 draft stage"
      )
    func(ctx.work, ctx.config)
    return

  if stage == "longdoc":
    # longdoc 依赖 render 阶段产物 ``<drafts_dir>/<stem>.md``
    drafts_dir = _resolve_drafts_dir(ctx.work)
    if drafts_dir is None:
      raise FileNotFoundError(
        "longdoc stage 需要 drafts 目录(含 <stem>.md);请先跑 render stage"
      )
    func(ctx.work, ctx.config)
    return

  if stage == "verify":
    # verify 是最终检查,几乎所有 stage 都已跑过
    if not (ctx.work / "chapters" / "chapters.json").exists():
      raise FileNotFoundError(
        "verify stage 需要 chapters.json;请先跑 chapters stage"
      )
    func(ctx.work)
    return

  # 占位 stage(目前 _not_implemented_stage)
  func(_stage_name=stage)


def _resolve_drafts_dir(work: Path) -> Path | None:
  """``<work>/chapters/raw/<video_stem>`` 派生(读 chapters.json 的 video)。"""
  chapters_json = work / "chapters" / "chapters.json"
  if not chapters_json.exists():
    return None
  import json as _json

  data = _json.loads(chapters_json.read_text(encoding="utf-8"))
  stem = (data.get("video") or "").strip() or "output"
  candidate = work / "chapters" / "raw" / stem
  return candidate if candidate.exists() else None


def _read_segment_endpoints(work: Path) -> list[float]:
  """从 transcript.jsonl 提取每个 segment 起止秒,作为 frames 补点 hint。"""
  from .asr import read_transcript_jsonl

  transcript = work / "asr" / "transcript.jsonl"
  if not transcript.exists():
    return []
  segments = read_transcript_jsonl(transcript)
  out: list[float] = []
  for seg in segments:
    out.append(float(seg.start))
    out.append(float(seg.end))
  return out


def _format_error(exc: BaseException) -> str:
  """把异常格式化为简短字符串(state.json 内保存)。"""
  return f"{type(exc).__name__}: {exc}"


def _save_state(state: State, work: Path) -> None:
  state.save(work / "state.json")


# ─────────────────────────────────────────────────────────────
# 编排主入口
# ─────────────────────────────────────────────────────────────


def run_pipeline(
  inbox: Path | None,
  work: Path,
  config: WorkflowConfig | None = None,
  *,
  skip_completed: bool = True,
  stop_after: str | None = None,
) -> PipelineResult:
  """完整流水线入口(W8:11 stage + LE 闭环)。

  Parameters
  ----------
  inbox : Path | None
    源 inbox 目录(含原始音视频)。``None`` 时从 ``work/state.json`` 的
    :attr:`State.inbox_path` 派生(W6 起,resume 默认行为)
  work : Path
    中间产物目录(将创建 ``state.json``,各 stage 输出目录)
  config : WorkflowConfig | None
    配置,默认使用 :class:`WorkflowConfig` 默认值
  skip_completed : bool
    是否跳过已完成 stage(``mtd resume --force`` 用 ``False`` 表示强制重跑)
  stop_after : str | None
    指定 stage 名 → 跑到该 stage 后停下(便于调试)

  Returns
  -------
  PipelineResult
    含最终 State + 完成/失败 stage 列表 + 耗时 + LE PipelineRun

  Raises
  ------
  ValueError
    ``inbox`` 缺且 state.json 没记录 inbox_path(从未 ``mtd run`` 启动过)
  Exception
    任何 stage 失败会上抛(已 mark & save state,LE 也会写 ERRORS.md +
    ``pipeline_run.json`` 末尾摘要)

  Notes
  -----
  LE 收尾顺序(finally 块,无论成败都会跑):

  1. L2 ``gatekeeper_check(work)`` → 检查产物完整性
  2. L3 ``logger.finalize(gatekeeper_result, llm_health={})`` → 写 ``pipeline_run.json``
  3. L4 ``post_pipeline_hook(work)`` → 扫 Pattern-Key 晋升 + LLM 健康度评估
  """
  cfg = config or WorkflowConfig()
  work = work.resolve()
  work.mkdir(parents=True, exist_ok=True)

  # 加载或初始化 state(必须在 inbox 派生前;state 可能含 inbox_path)
  state_path = work / "state.json"
  state: State
  if state_path.exists():
    state = State.load(state_path)
  else:
    state = State.new(course=_derive_course_name(inbox, work))

  # inbox 派生:inbox=None → 从 state.inbox_path 读
  if inbox is None:
    if state.inbox_path:
      inbox = Path(state.inbox_path)
    else:
      raise ValueError(
        "inbox 缺省且 state.json 未记录 inbox_path;"
        "首次跑请用 ``mtd run <inbox_dir>`` 而非 ``mtd resume``"
      )
  inbox = inbox.resolve()

  # 写回 inbox_path(W6 起 state 自带此字段,resume 不传 inbox 也能复用)
  if state.inbox_path != str(inbox):
    state.inbox_path = str(inbox)
    state.save(state_path)

  # LE L3 沉淀层:logger(W8 新增)
  logger = PipelineLogger(work, course=state.course)

  # 跳过已完成 stage(默认行为)
  started = time.monotonic()
  completed_now: list[str] = []
  failed_now: list[str] = []
  pipeline_run: PipelineRun | None = None

  try:
    for stage in STAGE_ORDER:
      if skip_completed and state.stages[stage].is_completed:
        completed_now.append(stage)
        if stop_after is not None and stage == stop_after:
          break
        continue
      if state.stages[stage].status == "skipped":
        if stop_after is not None and stage == stop_after:
          break
        continue

      ctx = StageContext(inbox=inbox, work=work, config=cfg)
      try:
        run_stage(stage, ctx, state, logger)
      except Exception:
        failed_now.append(stage)
        raise

      completed_now.append(stage)

      if stop_after is not None and stage == stop_after:
        break
  finally:
    # LE 收尾:L2 审核 + L3 沉淀 + L4 进化(无论成败都跑)
    gatekeeper: GatekeeperResult | None = None
    try:
      gatekeeper = gatekeeper_check(work)
    except Exception as exc:
      # gatekeeper 异常不破坏主流程,记录到 stderr
      print(f"[le] gatekeeper_check failed: {exc}", file=sys.stderr)

    try:
      pipeline_run = logger.finalize(
        gatekeeper_result=gatekeeper,
        llm_health={},  # TODO(W9+): 跨 stage 累积 LLM provider.health()
      )
    except Exception as exc:
      print(f"[le] logger.finalize failed: {exc}", file=sys.stderr)

    try:
      post_pipeline_hook(work)
    except Exception as exc:
      # post_pipeline_hook 失败不应破坏 run_pipeline 返回
      print(f"[le] post_pipeline_hook failed: {exc}", file=sys.stderr)

  return PipelineResult(
    state=state,
    completed=completed_now,
    failed=failed_now,
    duration_seconds=time.monotonic() - started,
    pipeline_run=pipeline_run,
  )


def _derive_course_name(inbox: Path, work: Path) -> str:
  """从 inbox / work 路径派生课程名(``state.course`` 用)。"""
  if work.name and work.name != "work":
    return work.name
  return inbox.name or "untitled-course"


__all__ = [
  "STAGE_FUNCS",
  "StageContext",
  "PipelineResult",
  "run_stage",
  "run_pipeline",
]  # noqa: F401
