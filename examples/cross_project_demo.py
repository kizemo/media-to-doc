"""examples/cross_project_demo.py — 最小跨项目调用示例

本示例演示其它 Python 项目里如何以**纯 import** 的方式调用 media_to_doc
的全部公开 API,无需走 CLI / MCP / 启动子进程。

W9 实装:PEP 562 `__getattr__` 顶层 re-export,
`import media_to_doc` 启动 < 100ms,faster-whisper / diffusers 等
重依赖按需加载(只在访问 `transcribe` / `generate_images` 等符号时才真 import)。

跑法(在 media-to-doc 项目根目录):
    uv run python examples/cross_project_demo.py --help
    uv run python examples/cross_project_demo.py demo-lazy
    uv run python examples/cross_project_demo.py demo-metrics
    uv run python examples/cross_project_demo.py demo-pipeline --work-dir ./workspace/work/demo
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# 顶层 re-export(W9) — 一行 import 拿到全部公开 API
# ─────────────────────────────────────────────────────────────


def demo_lazy_import() -> None:
  """演示 1:`import media_to_doc` 不触发重依赖。

  验证 ``faster_whisper`` / ``diffusers`` / ``anthropic`` 等模块
  在 ``import media_to_doc`` 之后**不在** ``sys.modules`` 里。
  """
  print("=" * 60)
  print("Demo 1: lazy import — import media_to_doc 不加载重依赖")
  print("=" * 60)

  import media_to_doc  # noqa: F401

  heavy_modules = [
    "faster_whisper",
    "scenedetect",
    "rapidocr",
    "diffusers",
    "anthropic",
    "ollama",
    "openai",
  ]
  import sys

  print(f"\n__version__ = {media_to_doc.__version__}")
  print(f"__all__ 长度 = {len(media_to_doc.__all__)}")
  print("\n重依赖模块加载状态(应该全 False):")
  for name in heavy_modules:
    loaded = name in sys.modules
    status = "[LOADED]" if loaded else "[lazy OK]"
    print(f"  {status:10s} {name}")


def demo_metrics_query() -> None:
  """演示 2:跨 run 健康度查询(W8)。

  调用 ``list_runs(workspace_root)`` 获取跨 run LLM 健康度聚合。
  """
  print("=" * 60)
  print("Demo 2: list_runs — 跨 run LLM 健康度查询")
  print("=" * 60)

  from media_to_doc import list_runs

  workspace = Path(__file__).resolve().parent.parent / "workspace"
  if not workspace.exists():
    print(f"workspace 不存在({workspace}),跳过")
    return

  print(f"\n扫 workspace = {workspace}")
  result = list_runs(workspace_root=str(workspace), limit=5)

  print(f"\ntotal_runs = {result.get('total_runs', 0)}")
  print("runs(前 5):")
  for run in result.get("runs", [])[:5]:
    course = run.get("course", "?")
    mtime = run.get("mtime_iso", "?")
    print(f"  - {course} (mtime={mtime})")

  llm = result.get("llm_health_global", {})
  if llm:
    print("\nllm_health_global:")
    print(f"  failure_rate = {llm.get('failure_rate', 'n/a')}")
    print(f"  recommendation = {llm.get('recommendation', 'n/a')}")
  else:
    print("\nllm_health_global: <空>(还没跑过 pipeline)")


def demo_pipeline_run(work_dir: Path) -> None:
  """演示 3:`run_pipeline` 真实跑全流程(需要 GPU + 已装 all-extras)。

  默认 ``stop_after="chapters"``,只跑到 LLM 章节切分就停(避免 imagegen 烧 GPU)。
  """
  print("=" * 60)
  print("Demo 3: run_pipeline — 跑到 chapters 停下(不调 imagegen)")
  print("=" * 60)

  from media_to_doc import WorkflowConfig, run_pipeline

  cfg = WorkflowConfig()
  cfg.pipeline.longdoc_llm_provider = "skip"  # 跳过 longdoc LLM 调用

  inbox = work_dir.parent / "inbox" / work_dir.name
  print(f"\ninbox = {inbox}")
  print(f"work  = {work_dir}")
  print(f"config: llm={cfg.llm.provider}, imagegen={cfg.imagegen.provider}")

  if not inbox.exists():
    print("\ninbox 不存在,跳过(本 demo 不会自动创建样本视频)")
    print(f"提示:把 mp4 放到 {inbox}/ 后重跑")
    return

  start = time.time()
  result = run_pipeline(
    inbox=inbox,
    work=work_dir,
    config=cfg,
    stop_after="chapters",
  )
  elapsed = time.time() - start

  print("\n=== 结果 ===")
  print(f"completed stages = {result.completed}")
  print(f"failed stages    = {result.failed}")
  print(f"duration         = {result.duration_seconds:.1f}s (实测 {elapsed:.1f}s)")
  print(f"is_complete      = {result.is_completed}")
  if result.pipeline_run is not None:
    print(f"LE pipeline_run  = {result.pipeline_run.course} "
          f"(quality={result.pipeline_run.quality})")
  else:
    print("LE pipeline_run  = None(finalize 失败,state.json 已先 save)")


def demo_workflow_config() -> None:
  """演示 4:WorkflowConfig 数据类 + YAML 序列化。"""
  print("=" * 60)
  print("Demo 4: WorkflowConfig — 配置数据类")
  print("=" * 60)

  from media_to_doc import (
    ImagegenConfig,
    LLMConfig,
    PathsConfig,
    PipelineConfig,
    WorkflowConfig,
  )

  cfg = WorkflowConfig(
    llm=LLMConfig(provider="ollama", model="qwen3:14b", num_ctx=65536),
    imagegen=ImagegenConfig(provider="skip"),  # 跳过 SDXL 烧 GPU
    paths=PathsConfig(workspace="D:/my_workspace"),
    pipeline=PipelineConfig(skip_longdoc=True, longdoc_llm_provider="skip"),
  )

  print(f"\nllm.provider          = {cfg.llm.provider}")
  print(f"llm.model             = {cfg.llm.model}")
  print(f"llm.num_ctx           = {cfg.llm.num_ctx}")
  print(f"imagegen.provider     = {cfg.imagegen.provider}")
  print(f"pipeline.skip_longdoc = {cfg.pipeline.skip_longdoc}")
  print("\nYAML 序列化(前 20 行):")
  yaml_str = cfg.to_yaml()
  for line in yaml_str.splitlines()[:20]:
    print(f"  {line}")


def main() -> int:
  parser = argparse.ArgumentParser(
    description="media_to_doc 跨项目调用 demo(W9 PEP 562 re-export)",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
可用 demo:
  demo-lazy        演示 lazy import(不需要任何 work_dir)
  demo-metrics     演示 list_runs 跨 run 健康度查询
  demo-pipeline    演示 run_pipeline 真实跑(需要 inbox)
  demo-config      演示 WorkflowConfig 数据类
""",
  )
  parser.add_argument(
    "demo",
    choices=["demo-lazy", "demo-metrics", "demo-pipeline", "demo-config"],
    help="要跑的 demo",
  )
  parser.add_argument(
    "--work-dir",
    type=Path,
    default=Path("./workspace/work/demo"),
    help="demo-pipeline 用的 work 目录",
  )
  args = parser.parse_args()

  print(f"media_to_doc v{__import__('media_to_doc').__version__}\n")

  if args.demo == "demo-lazy":
    demo_lazy_import()
  elif args.demo == "demo-metrics":
    demo_metrics_query()
  elif args.demo == "demo-pipeline":
    demo_pipeline_run(args.work_dir)
  elif args.demo == "demo-config":
    demo_workflow_config()

  print()
  return 0


if __name__ == "__main__":
  sys.exit(main())
