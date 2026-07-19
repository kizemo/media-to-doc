"""media_to_doc — 把本地音视频转化为带 AI 配图的 Markdown / HTML 讲义。

三层调用方式:
- Python API(开发者):``from media_to_doc import ...``
- CLI(终端用户):``mtd run <inbox>``
- MCP Server(AI 助手):``mtd-mcp`` stdio 协议

设计原则:
- 本地优先:默认 Ollama + Faster-Whisper + SDXL 全栈本地推理
- 可恢复:每阶段落盘 + state.json + resume 命令
- 跨平台产物:图片相对路径,产物目录可整盘复制
- Loop Engineering:自我驱动 / 审核 / 沉淀 / 进化 闭环

顶层 API 全部走 PEP 562 ``__getattr__`` 实现 lazy import,
重依赖(faster-whisper / scenedetect / rapidocr / diffusers / anthropic / openai)
只在用户实际访问时才加载,``import media_to_doc`` 启动 < 100ms。

公开 API 列表::

    # 配置
    WorkflowConfig, LLMConfig, ImagegenConfig, PathsConfig, PipelineConfig

    # 流水线状态
    STAGE_ORDER, StageState, StageStatus, State

    # 流水线入口
    run_pipeline, run_stage, PipelineResult, STAGE_FUNCS

    # 11 stage 函数
    prepare_audio, transcribe, extract_keyframes, run_ocr, correct_asr,
    split_chapters, generate_drafts, generate_images, render_outputs,
    process_long_doc, verify_pipeline

    # LLM provider
    BaseLLMProvider, ChatMessage, ChatResponse, HealthReport, HealthStatus,
    get_provider, PROVIDERS

    # LE 健康度查询(W8)
    get_run_metrics, list_runs, get_escalated_errors

    # Loop Engineering(W8)
    PipelineLogger, PipelineRun, StageRecord, GatekeeperResult, timed_stage,
    gatekeeper_check, post_pipeline_hook, assess_llm_health,
    escalate_recurring_errors, find_known_pattern_keys, write_runtime_error

详细设计见:
- ``PRD.md`` §4 功能清单
- ``TDD.md`` §4 模块设计
- ``ROADMAP.md`` 执行规划
- ``docs/MCP_INTEGRATION.md`` MCP 集成(W7 + W8)
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Duanyi"
__license__ = "MIT"

# ─────────────────────────────────────────────────────────────
# 顶层 re-export(PEP 562 ``__getattr__``)
#
# 所有公开符号在 :data:`_LAZY_EXPORTS` 中以 ``name -> "module.path"`` 形式注册。
# 用户 ``from media_to_doc import run_pipeline`` 时,
# ``__getattr__("run_pipeline")`` 才真正 ``import`` 目标模块,
# 重依赖(faster-whisper / rapidocr / diffusers / ollama / anthropic / openai)
# 按需加载,``import media_to_doc`` 启动 < 100ms。
#
# 添加新公开符号:追加 ``_LAZY_EXPORTS`` 一行 + ``__all__`` 一行即可,
# 无需修改任何其它代码。
# ─────────────────────────────────────────────────────────────

_LAZY_EXPORTS: dict[str, str] = {
  # ── 配置(轻量,数据类)───────────────────────────
  "WorkflowConfig": "media_to_doc.config",
  "LLMConfig": "media_to_doc.config",
  "ImagegenConfig": "media_to_doc.config",
  "PathsConfig": "media_to_doc.config",
  "PipelineConfig": "media_to_doc.config",
  # ── 流水线状态(轻量,dataclass + json)───────────────
  "STAGE_ORDER": "media_to_doc.state",
  "StageState": "media_to_doc.state",
  "StageStatus": "media_to_doc.state",
  "State": "media_to_doc.state",
  # ── 流水线入口(轻量,仅签名导入)──────────────────
  "run_pipeline": "media_to_doc.pipeline.runner",
  "run_stage": "media_to_doc.pipeline.runner",
  "PipelineResult": "media_to_doc.pipeline.runner",
  "STAGE_FUNCS": "media_to_doc.pipeline.runner",
  # ── 11 stage 函数(各自触发重依赖)──────────────────
  "prepare_audio": "media_to_doc.pipeline.audio",
  "transcribe": "media_to_doc.pipeline.asr",
  "extract_keyframes": "media_to_doc.pipeline.frames",
  "KeyFrame": "media_to_doc.pipeline.frames",
  "run_ocr": "media_to_doc.pipeline.ocr",
  "correct_asr": "media_to_doc.pipeline.asr_correct",
  "split_chapters": "media_to_doc.pipeline.chapters",
  "generate_drafts": "media_to_doc.pipeline.draft",
  "generate_images": "media_to_doc.pipeline.imagegen",
  "render_outputs": "media_to_doc.pipeline.render",
  "render_html": "media_to_doc.pipeline.render",
  "process_long_doc": "media_to_doc.pipeline.longdoc",
  "render_final_html": "media_to_doc.pipeline.longdoc",
  "verify_pipeline": "media_to_doc.pipeline.verify",
  "VerifyReport": "media_to_doc.pipeline.verify",
  # ── LLM provider 抽象(轻量)────────────────────
  "BaseLLMProvider": "media_to_doc.llm.base",
  "ChatMessage": "media_to_doc.llm.base",
  "ChatResponse": "media_to_doc.llm.base",
  "HealthReport": "media_to_doc.llm.base",
  "HealthStatus": "media_to_doc.llm.base",
  "PROVIDERS": "media_to_doc.llm",
  "get_provider": "media_to_doc.llm",
  # ── LE 健康度查询(W8)───────────────────────
  "get_run_metrics": "media_to_doc.llm.health",
  "list_runs": "media_to_doc.llm.health",
  "get_escalated_errors": "media_to_doc.llm.health",
  # ── Loop Engineering(W8)──────────────────────
  "PipelineLogger": "media_to_doc.logger.pipeline_logger",
  "PipelineRun": "media_to_doc.logger.pipeline_logger",
  "StageRecord": "media_to_doc.logger.pipeline_logger",
  "GatekeeperResult": "media_to_doc.logger.pipeline_logger",
  "timed_stage": "media_to_doc.logger.pipeline_logger",
  "gatekeeper_check": "media_to_doc.logger.gatekeeper",
  "post_pipeline_hook": "media_to_doc.logger.learnings",
  "assess_llm_health": "media_to_doc.logger.learnings",
  "escalate_recurring_errors": "media_to_doc.logger.learnings",
  "find_known_pattern_keys": "media_to_doc.logger.learnings",
  "write_runtime_error": "media_to_doc.logger.learnings",
}


def __getattr__(name: str) -> object:
  """PEP 562 lazy import:仅在访问符号时加载目标模块。"""
  target = _LAZY_EXPORTS.get(name)
  if target is None:
    raise AttributeError(
      f"module 'media_to_doc' has no attribute {name!r}. "
      f"可用符号: {sorted(_LAZY_EXPORTS.keys())}"
    )
  # importlib 导入并缓存到 sys.modules[target],然后取出符号
  import importlib

  module = importlib.import_module(target)
  value = getattr(module, name)
  # 缓存到本模块属性,避免下次重复 import_module
  globals()[name] = value
  return value


def __dir__() -> list[str]:
  """IDE 自动补全支持:列出所有公开符号。"""
  return sorted(list(globals().keys()) + list(_LAZY_EXPORTS.keys()))


__all__ = [
  "__version__",
  "__author__",
  "__license__",
  # 配置
  "WorkflowConfig",
  "LLMConfig",
  "ImagegenConfig",
  "PathsConfig",
  "PipelineConfig",
  # 流水线状态
  "STAGE_ORDER",
  "StageState",
  "StageStatus",
  "State",
  # 流水线入口
  "run_pipeline",
  "run_stage",
  "PipelineResult",
  "STAGE_FUNCS",
  # 11 stage 函数
  "prepare_audio",
  "transcribe",
  "extract_keyframes",
  "KeyFrame",
  "run_ocr",
  "correct_asr",
  "split_chapters",
  "generate_drafts",
  "generate_images",
  "render_outputs",
  "render_html",
  "process_long_doc",
  "render_final_html",
  "verify_pipeline",
  "VerifyReport",
  # LLM provider
  "BaseLLMProvider",
  "ChatMessage",
  "ChatResponse",
  "HealthReport",
  "HealthStatus",
  "PROVIDERS",
  "get_provider",
  # LE 健康度查询(W8)
  "get_run_metrics",
  "list_runs",
  "get_escalated_errors",
  # Loop Engineering(W8)
  "PipelineLogger",
  "PipelineRun",
  "StageRecord",
  "GatekeeperResult",
  "timed_stage",
  "gatekeeper_check",
  "post_pipeline_hook",
  "assess_llm_health",
  "escalate_recurring_errors",
  "find_known_pattern_keys",
  "write_runtime_error",
]
