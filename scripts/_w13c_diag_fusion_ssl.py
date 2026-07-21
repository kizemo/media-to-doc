"""W13-C:诊断 W12-E fusion SSL 错误。

策略:
1. 用 ollama Python SDK 直接调 chat(与 merge_lectures 走同代码路径)
2. 试 3 种 prompt 大小:
   - small (200 chars) — 应能成功
   - medium (~5000 chars,模拟单视频 fusion 大小)
   - large (~20000 chars,模拟多视频 fusion 大小)— 可能触发
3. SSL 错误如果仍复现,记录详细 traceback 给下个会话

环境:必须先 unset HTTP_PROXY / HTTPS_PROXY(走 ollama 本地 11434)

诊断结论(W13-C):SSL 错误根因不是 ollama 服务 / prompt 大小,而是
``_w13a_run_fusion.py`` 子进程 ``env=`` 替换时未过滤掉 ``HTTP_PROXY`` 等
公司 VPN 代理变量,导致 ollama SDK 的 httpx 走代理后报 SSL。
修复:见 ``_w13a_run_fusion.py`` 的 W13-C 改动 — 子进程 env 显式剔除
8 个 proxy vars。
"""

from __future__ import annotations

import os
import sys
import time
import traceback


def banner(msg: str) -> None:
  print(f"\n--- {msg} ---", flush=True)


def main() -> int:
  # 0. 强制 unset 任何 proxy env(诊断脚本必须干净)
  for v in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
            "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy"):
    os.environ.pop(v, None)

  banner("1. 检查 ollama 服务是否运行")
  import urllib.request
  try:
    with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as r:
      print(f"  OK ollama /api/tags status={r.status}")
  except Exception as exc:
    print(f"  FAIL: ollama 服务不可达:{type(exc).__name__}: {exc}")
    return 2

  banner("2. import ollama SDK + OllamaProvider")
  try:
    from media_to_doc.llm import get_provider
  except Exception as exc:
    print(f"  FAIL import: {exc}")
    traceback.print_exc()
    return 2

  banner("3. 创建 ollama provider(num_ctx=65536,匹配 chapters/draft)")
  try:
    provider = get_provider("ollama", num_ctx=65536, timeout_seconds=60)
    print(f"  provider={provider.name}, model={provider.model}")
  except Exception as exc:
    print(f"  FAIL get_provider: {exc}")
    traceback.print_exc()
    return 2

  prompt_sizes = [
    ("small (200 chars)", "x" * 200),
    ("medium (5000 chars)", "x" * 5000),
    ("large (20000 chars)", "x" * 20000),
  ]

  for label, prompt in prompt_sizes:
    banner(f"4. 测试 {label}")
    t0 = time.time()
    try:
      resp = provider.chat(prompt)
      elapsed = time.time() - t0
      print(f"  OK elapsed={elapsed:.2f}s, text_len={len(resp.text)},"
            f" model={resp.model}, provider={resp.provider}")
    except Exception as exc:
      elapsed = time.time() - t0
      print(f"  FAIL elapsed={elapsed:.2f}s: {type(exc).__name__}: {exc}")
      traceback.print_exc()

  banner("5. 测试 fusion-sized prompt(中文 + 模拟真实场景)")
  # 模拟 _build_fusion_prompt 输出大小
  fake_summaries = "\n\n".join(
    [f"### 视频:{i}\n\n- **章节 {j}:模拟标题**\n  {'内容' * 100}\n"
     for i in range(1, 3) for j in range(1, 11)]
  )
  fusion_prompt = (
    "你是资深讲义编辑,擅长把多段独立讲义融合为一份连贯的全局讲义。"
    "任务:把下列多个视频的章节列表融合为统一的全局章节结构。\n\n"
    f"## 视频与章节列表\n\n{fake_summaries}\n\n"
    "## 输出格式\n\n严格的 JSON 对象,无 markdown 代码块标记:\n\n"
    '{"chapters": [{"title": "...", "sources": [{"video": "...",'
    '"chapter": "...", "include": "all"}]}]}\n'
  )
  print(f"  fusion_prompt 长度 = {len(fusion_prompt)} chars")
  t0 = time.time()
  try:
    resp = provider.chat(fusion_prompt)
    elapsed = time.time() - t0
    print(f"  OK elapsed={elapsed:.2f}s, text_len={len(resp.text)}")
    print(f"  resp head: {resp.text[:200]}")
  except Exception as exc:
    elapsed = time.time() - t0
    print(f"  FAIL elapsed={elapsed:.2f}s: {type(exc).__name__}: {exc}")
    traceback.print_exc()

  banner("DONE")
  return 0


if __name__ == "__main__":
  sys.exit(main())
