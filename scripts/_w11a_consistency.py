"""W11-A 工具 — gatekeeper 与 verify 一致性手动验收(W10-A 发现 bug 模式)。

承接 ``handoff-pipeline-w10-real-LE-verify-2026-07-19.md`` §5:Gatekeeper vs Verify
曾对同一份数据给出相反结论。本脚本调两边并断言一致,防回归。

用法
----

::

    uv run python scripts/_w11a_consistency.py <work_dir>

    # 例:验 W10-A 真跑产物
    uv run python scripts/_w11a_consistency.py \\
        "E:/resource/2026-01-27_年度复训/output"

退出码
------

- 0: gatekeeper 与 verify 一致
- 1: 一致但都 FAIL(产物不完整,需关注)
- 2: 不一致(BUG 回归,W11-A 修的就是这种)

设计
----

- 只读不写:不动 state.json / pipeline_run.json / verify.json
- 直接调 ``media_to_doc.logger.gatekeeper_check`` 与
  ``media_to_doc.pipeline.verify.verify_pipeline(write_report=False)``
- stdout 输出结构化判断结果,便于管道捕获
- 无关 longdoc skip / active — 任何产物布局都适用
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def check_consistency(work: Path) -> tuple[int, dict[str, object]]:
  """跑两边检查并断言一致,返回 (exit_code, summary_dict)。"""
  # Lazy import:重依赖避免路径脚本触发 sys.modules 装载
  from media_to_doc.logger import gatekeeper_check
  from media_to_doc.pipeline.verify import verify_pipeline

  if not work.exists():
    return 2, {
      "work": str(work),
      "error": f"work_dir 不存在:{work}",
    }

  # gatekeeper(只读,不动盘)
  gk = gatekeeper_check(work)
  # verify(write_report=False 避免覆盖 verify.json)
  vr = verify_pipeline(work, write_report=False)

  consistent = gk.ok == vr.overall_passed
  if consistent and gk.ok:
    exit_code = 0  # 都 PASS
  elif consistent and not gk.ok:
    exit_code = 1  # 都 FAIL(产物不完整)
  else:
    exit_code = 2  # 不一致(BUG)

  summary: dict[str, object] = {
    "work": str(work),
    "consistent": consistent,
    "gatekeeper": {
      "ok": gk.ok,
      "passed": list(gk.checks_passed),
      "failed": list(gk.checks_failed),
      "issues": list(gk.issues),
    },
    "verify": {
      "overall_passed": vr.overall_passed,
      "failures": list(vr.failures),
      "warnings": list(vr.warnings),
    },
  }
  return exit_code, summary


def main(argv: list[str]) -> int:
  if len(argv) != 2:
    print(
      f"用法:{argv[0]} <work_dir>\n"
      "例:uv run python scripts/_w11a_consistency.py "
      '"E:/resource/2026-01-27_年度复训/output"',
      file=sys.stderr,
    )
    return 2

  work = Path(argv[1])
  exit_code, summary = check_consistency(work)

  # 结构化 JSON 输出(stdout,管道友好)
  print(json.dumps(summary, ensure_ascii=False, indent=2))

  # 人类可读摘要(stderr,不影响 JSON 管道)
  if exit_code == 0:
    print(
      f"\n[OK] gatekeeper 与 verify 一致 PASS(work={work})",
      file=sys.stderr,
    )
  elif exit_code == 1:
    print(
      f"\n[INCOMPLETE] 一致但都 FAIL,产物不完整(work={work})",
      file=sys.stderr,
    )
  else:
    print(
      f"\n[INCONSISTENT] gatekeeper 与 verify 结论相反 — "
      f"W11-A bug 回归!(work={work})",
      file=sys.stderr,
    )
  return exit_code


if __name__ == "__main__":
  sys.exit(main(sys.argv))
