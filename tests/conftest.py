"""pytest 全局 fixtures。

Phase 0 仅提供最简 fixtures;Phase 1 起按需添加:
- ``tmp_inbox`` — 临时 inbox 目录
- ``tmp_work`` — 临时 work 目录
- ``mock_ffmpeg`` — ffmpeg 调用 mock
- ``mock_llm`` — LLM provider mock
- ``sample_audio`` — 测试用 wav 文件
"""

from __future__ import annotations

import pytest


@pytest.fixture
def anyio_backend() -> str:
  """pytest-anyio 默认异步后端(Phase 4+ 用于 MCP server 测试)。"""
  return "asyncio"
