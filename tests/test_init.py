"""media_to_doc 顶层 ``__init__`` 的 lazy import 测试。

W9 B 部分:验证 PEP 562 ``__getattr__`` 的行为:

1. ``import media_to_doc`` 不应触发重依赖(faster-whisper / scenedetect /
   rapidocr / diffusers / anthropic / ollama / openai)
2. ``from media_to_doc import <name>`` 真正访问时才加载目标模块
3. ``media_to_doc.<name>`` 未知符号抛 ``AttributeError``(含可用符号提示)
4. ``dir(media_to_doc)`` 列出全部公开符号
5. ``__all__`` 与 ``_LAZY_EXPORTS`` 同步
"""

from __future__ import annotations

import importlib
import sys

import pytest

# ─────────────────────────────────────────────────────────────
# 基础元信息
# ─────────────────────────────────────────────────────────────


def test_version_is_string() -> None:
  """``__version__`` 是字符串(给 CLI / MCP 展示用)。"""
  import media_to_doc

  assert isinstance(media_to_doc.__version__, str)
  assert media_to_doc.__version__  # 非空


def test_author_and_license() -> None:
  """元信息字段:author / license。"""
  import media_to_doc

  assert media_to_doc.__author__
  assert media_to_doc.__license__ == "MIT"


def test_all_attribute_present() -> None:
  """``__all__`` 是 list 且非空。"""
  import media_to_doc

  assert isinstance(media_to_doc.__all__, list)
  assert len(media_to_doc.__all__) > 10


# ─────────────────────────────────────────────────────────────
# Lazy import 行为验证
# ─────────────────────────────────────────────────────────────


def test_lazy_import_workflow_config() -> None:
  """``WorkflowConfig`` 通过 ``__getattr__`` 正确加载。"""
  from media_to_doc import WorkflowConfig

  cfg = WorkflowConfig()
  assert cfg.llm.provider == "ollama"  # 默认值


def test_lazy_import_stage_order() -> None:
  """``STAGE_ORDER`` 来自 ``state`` 模块。"""
  from media_to_doc import STAGE_ORDER

  assert len(STAGE_ORDER) == 11
  assert STAGE_ORDER[0] == "audio"
  assert STAGE_ORDER[-1] == "verify"


def test_lazy_import_run_pipeline_callable() -> None:
  """``run_pipeline`` 是可调用的(签名导入,不真跑)。"""
  from media_to_doc import run_pipeline

  assert callable(run_pipeline)


def test_lazy_import_llm_provider_registry() -> None:
  """``get_provider`` + ``PROVIDERS`` 从 ``media_to_doc.llm`` 加载。"""
  from media_to_doc import PROVIDERS, get_provider

  assert "ollama" in PROVIDERS
  assert "anthropic" in PROVIDERS
  assert "openai_compatible" in PROVIDERS
  assert callable(get_provider)


def test_lazy_import_le_logger_classes() -> None:
  """LE W8 全部公开类通过 lazy import 加载。"""
  from media_to_doc import (
    GatekeeperResult,
    PipelineLogger,
    PipelineRun,
    StageRecord,
    gatekeeper_check,
    timed_stage,
  )

  assert PipelineLogger.__name__ == "PipelineLogger"
  assert PipelineRun.__name__ == "PipelineRun"
  assert StageRecord.__name__ == "StageRecord"
  assert GatekeeperResult.__name__ == "GatekeeperResult"
  assert callable(timed_stage)
  assert callable(gatekeeper_check)


def test_lazy_import_health_query_functions() -> None:
  """LE W8 健康度查询函数。"""
  from media_to_doc import (
    get_escalated_errors,
    get_run_metrics,
    list_runs,
  )

  assert callable(get_run_metrics)
  assert callable(list_runs)
  assert callable(get_escalated_errors)


# ─────────────────────────────────────────────────────────────
# 缓存行为:第二次访问不再触发 ``import_module``
# ─────────────────────────────────────────────────────────────


def test_lazy_import_caches_attribute(monkeypatch: pytest.MonkeyPatch) -> None:
  """首次访问后,符号被缓存到 ``globals()``,后续访问不再走 ``__getattr__``。"""
  import media_to_doc

  # 触发缓存
  _ = media_to_doc.WorkflowConfig
  assert "WorkflowConfig" in vars(media_to_doc)

  # 删除缓存 → 模拟"清空"场景
  del media_to_doc.WorkflowConfig
  assert "WorkflowConfig" not in vars(media_to_doc)

  # 再次访问 → 重新走 ``__getattr__`` 加载
  cfg = media_to_doc.WorkflowConfig()
  assert cfg.llm.provider == "ollama"


def test_lazy_import_independent_per_symbol(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  """每个符号独立缓存:删一个不影响另一个。"""
  import media_to_doc

  _ = media_to_doc.WorkflowConfig
  _ = media_to_doc.STAGE_ORDER

  assert "WorkflowConfig" in vars(media_to_doc)
  assert "STAGE_ORDER" in vars(media_to_doc)

  del media_to_doc.WorkflowConfig

  assert "WorkflowConfig" not in vars(media_to_doc)
  assert "STAGE_ORDER" in vars(media_to_doc)  # 不受影响


# ─────────────────────────────────────────────────────────────
# 错误处理:未知符号
# ─────────────────────────────────────────────────────────────


def test_unknown_attribute_raises_with_hint() -> None:
  """未知符号抛 ``AttributeError``,消息含可用符号列表。"""
  import media_to_doc

  with pytest.raises(AttributeError) as excinfo:
    _ = media_to_doc.this_does_not_exist

  msg = str(excinfo.value)
  assert "this_does_not_exist" in msg
  assert "可用符号" in msg


def test_underscore_dunder_unknown_raises() -> None:
  """下划线开头的未知符号同样抛错(不沉默)。"""
  import media_to_doc

  with pytest.raises(AttributeError):
    _ = media_to_doc.__definitely_not_a_real_symbol__


# ─────────────────────────────────────────────────────────────
# ``dir()`` 自动补全
# ─────────────────────────────────────────────────────────────


def test_dir_includes_all_public_symbols() -> None:
  """``dir(media_to_doc)`` 包含所有 ``__all__`` 项。"""
  import media_to_doc

  listed = set(dir(media_to_doc))
  for name in media_to_doc.__all__:
    assert name in listed, f"dir() 缺 {name}"


def test_dir_includes_lazy_exports() -> None:
  """``dir()`` 包含 ``_LAZY_EXPORTS`` 中所有符号(尚未触发 ``__getattr__`` 也能补全)。"""
  import media_to_doc

  listed = set(dir(media_to_doc))
  for name in media_to_doc._LAZY_EXPORTS:
    assert name in listed, f"dir() 缺 lazy 符号 {name}"


# ─────────────────────────────────────────────────────────────
# ``__all__`` / ``_LAZY_EXPORTS`` 一致性
# ─────────────────────────────────────────────────────────────


def test_all_matches_lazy_exports() -> None:
  """``__all__`` 与 ``_LAZY_EXPORTS`` keys 完全一致(除去元字段)。"""
  import media_to_doc

  meta = {"__version__", "__author__", "__license__"}
  expected = set(media_to_doc._LAZY_EXPORTS.keys()) | meta
  assert set(media_to_doc.__all__) == expected


def test_lazy_exports_target_modules_importable() -> None:
  """``_LAZY_EXPORTS`` 中所有目标模块都能正常 import(无 typo)。"""
  import media_to_doc

  for name, target in media_to_doc._LAZY_EXPORTS.items():
    # 直接走 import_module 验证目标模块存在 + 符号存在
    module = importlib.import_module(target)
    assert hasattr(module, name), f"{target} 没有 {name}"


# ─────────────────────────────────────────────────────────────
# 启动性能(轻量):``import media_to_doc`` 不应触发重依赖
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
  "heavy_module",
  [
    "faster_whisper",
    "scenedetect",
    "rapidocr",
    "diffusers",
    "anthropic",
    "ollama",
    "openai",
  ],
)
def test_import_media_to_doc_does_not_load_heavy_modules(
  heavy_module: str,
) -> None:
  """``import media_to_doc`` 不应 eager-import 重依赖。

  注:``mcp`` 也不应被加载(MCP server 走独立 ``mcp_server`` 入口)。
  """
  # 确保 fresh import:从 sys.modules 移除再 reimport
  saved = sys.modules.pop("media_to_doc", None)
  try:
    import media_to_doc  # noqa: F401
    # 触发 lazy 符号解析才会真的 import 目标模块
    assert heavy_module not in sys.modules, (
      f"import media_to_doc 触发 {heavy_module} 被加载 → 失去 lazy import 意义"
    )
  finally:
    if saved is not None:
      sys.modules["media_to_doc"] = saved


# ─────────────────────────────────────────────────────────────
# 实际跨符号访问的端到端冒烟
# ─────────────────────────────────────────────────────────────


def test_full_pipeline_api_surface_smoke() -> None:
  """冒烟:一次性访问多个公开符号,确保全部可解析。"""
  from media_to_doc import (  # noqa: F401
    STAGE_FUNCS,
    STAGE_ORDER,
    BaseLLMProvider,
    HealthReport,
    PipelineConfig,
    PipelineLogger,
    PipelineResult,
    StageState,
    StageStatus,
    State,
    WorkflowConfig,
    assess_llm_health,
    correct_asr,
    escalate_recurring_errors,
    extract_keyframes,
    find_known_pattern_keys,
    gatekeeper_check,
    generate_drafts,
    generate_images,
    get_escalated_errors,
    get_provider,
    get_run_metrics,
    list_runs,
    post_pipeline_hook,
    prepare_audio,
    process_long_doc,
    render_final_html,
    render_html,
    render_outputs,
    run_ocr,
    run_pipeline,
    run_stage,
    split_chapters,
    timed_stage,
    transcribe,
    verify_pipeline,
    write_runtime_error,
  )


def test_pipeline_result_is_a_dataclass() -> None:
  """``PipelineResult`` 是 dataclass(有 ``__dataclass_fields__``)。"""
  from media_to_doc import PipelineResult

  assert hasattr(PipelineResult, "__dataclass_fields__")
  fields = set(PipelineResult.__dataclass_fields__.keys())
  # 既有字段(W4-W7)
  assert "state" in fields
  assert "completed" in fields
  assert "failed" in fields
  assert "duration_seconds" in fields
  # W8 新增:LE 沉淀层引用
  assert "pipeline_run" in fields
