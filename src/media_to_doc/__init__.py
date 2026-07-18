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

详细设计见:
- ``PRD.md`` §4 功能清单
- ``TDD.md`` §4 模块设计
- ``ROADMAP.md`` 执行规划
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Duanyi"
__license__ = "MIT"

# ─────────────────────────────────────────────────────────────
# 顶层 re-export(PEP 562 __getattr__ 实现 lazy import,
# 重依赖按需加载,启动 < 1 秒)
#
# Phase 1 实施后,以下接口将逐步实装:
# - from media_to_doc import WorkflowConfig, run_pipeline
# - from media_to_doc import STAGE_ORDER
# - from media_to_doc import PipelineLogger, gatekeeper_check
#
# Phase 0 阶段仅暴露版本与元信息。
# ─────────────────────────────────────────────────────────────

__all__ = [
    "__version__",
    "__author__",
    "__license__",
]
