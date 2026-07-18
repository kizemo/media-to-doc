"""media_to_doc pytest 测试包。

测试布局(Phase 1+ 扩展):
- tests/test_smoke.py         — Phase 0 占位,基础 import / CLI 调用
- tests/test_cli.py           — Phase 1+ CLI 参数解析与命令行为
- tests/test_config.py        — Phase 1+ WorkflowConfig 序列化 / 校验
- tests/test_paths.py         — Phase 1+ 路径解析与覆盖
- tests/test_state.py         — Phase 1+ State 持久化与 resume
- tests/test_pipeline/        — Phase 1+ 11 stage 单元测试
- tests/test_llm/             — Phase 1+ LLM provider 抽象测试
- tests/test_logger/          — Phase 5  LE 沉淀层测试
- tests/test_mcp_server.py    — Phase 4  MCP server 测试
"""
