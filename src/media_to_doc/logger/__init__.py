"""media_to_doc.logger — Loop Engineering 闭环(W8 实装)。

LE 五层:
- L1 执行层::func:`timed_stage`(上下文管理器)+ :class:`PipelineLogger`
- L2 审核层::func:`gatekeeper_check`(4 项机器可验证)
- L3 沉淀层::class:`PipelineLogger`(memory/YYYY-MM-DD.md + pipeline_run.json)
- L4 进化层::func:`post_pipeline_hook`(Pattern-Key 晋升 + LLM 健康度)

公开 API::
    from media_to_doc.logger import (
        PipelineLogger,
        PipelineRun,
        StageRecord,
        GatekeeperResult,
        timed_stage,
        gatekeeper_check,
        post_pipeline_hook,
        assess_llm_health,
        escalate_recurring_errors,
        find_known_pattern_keys,
        write_runtime_error,
    )

设计文档:
- ``_research/LE_DESIGN.md``(详细设计)
- ``_research/le_prototype/README.md``(原型 23 测试)
- ``PRD.md`` §4.1.G(LE 功能定位)
- ``TDD.md`` §4.5(模块接口)
"""

from __future__ import annotations

__version__ = "0.1.0-phase6-wired"

# ─────────────────────────────────────────────────────────────
# 公共 API(避免重依赖 eager import,允许 logger.__init__ 单独 import)
# ─────────────────────────────────────────────────────────────

# 纯数据 + 上下文管理器(无副作用,可立即暴露)
# L2 审核层(只读 work 目录,无副作用)
from .gatekeeper import gatekeeper_check

# L4 进化层(scan + write .learnings/,可能创建文件但幂等)
from .learnings import (
  assess_llm_health,
  escalate_recurring_errors,
  find_known_pattern_keys,
  post_pipeline_hook,
  write_runtime_error,
)
from .pipeline_logger import (
  GatekeeperResult,
  PipelineLogger,
  PipelineRun,
  StageRecord,
  timed_stage,
)

__all__ = [
  # 数据模型
  "StageRecord",
  "PipelineRun",
  "GatekeeperResult",
  # L1 执行 + L3 沉淀
  "PipelineLogger",
  "timed_stage",
  # L2 审核
  "gatekeeper_check",
  # L4 进化
  "post_pipeline_hook",
  "assess_llm_health",
  "escalate_recurring_errors",
  "find_known_pattern_keys",
  "write_runtime_error",
]
