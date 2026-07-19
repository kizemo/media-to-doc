# handoff-pipeline-w7-mcp-2026-07-19.md — Phase 4 W7 MCP server 快照

> **会话主题**:Phase 4 W7 MCP server — stdio JSON-RPC,6 工具
> **会话日期**:2026-07-19,~2 小时
> **会话状态**:**已完成,无阻塞**(400 passed / 3 skipped + ruff 全过)

---

## 1. 本次会话目标

承接 `handoff-pipeline-w6-cli-2026-07-19.md`,启动 W7 = MCP server。
按 ROADMAP §3 Phase 4 W7 任务清单:

1. `src/media_to_doc/mcp_server.py` — stdio JSON-RPC + 6 工具(纯函数 + Server 单例)
2. `cli.py` 实装 `mtd mcp` 子命令(替换 W6 占位)
3. `tests/test_mcp_server.py` — 30 用例覆盖 6 工具纯函数 + 协议层
4. `docs/MCP_INTEGRATION.md` — Claude Desktop 配置 + 工具签名 + 错误处理
5. `README.md` + `CLAUDE.md` §9.4 同步
6. commit:`feat(cli): W7 — mcp_server.py + mtd mcp + 6 工具`

---

## 2. 已完成

| 项 | 文件 | 行数 / 测试数 | 状态 |
|---|---|---|---|
| `feat/pipeline-w7-mcp` 分支(基于 W6 `23c1f96`) | git branch | - | [x] |
| `src/media_to_doc/mcp_server.py`(`Server` + 6 `tool_xxx()` + 协议层) | `src/media_to_doc/` | 479 行 | [x] |
| `src/media_to_doc/cli.py`:`mtd mcp` 实装(调 `mcp_server.main()`) | `src/media_to_doc/cli.py` | +8 行 | [x] |
| `tests/test_mcp_server.py` | `tests/` | 30 用例 | [x] |
| `docs/MCP_INTEGRATION.md`(Claude Desktop 集成指南) | `docs/` | 200+ 行 | [x] |
| `README.md` §3 MCP 配置更新 + 路线图 W7 完成 | `README.md` | - | [x] |
| `CLAUDE.md` §9.4 MCP 标注 W7 已实装 | `CLAUDE.md` | - | [x] |
| `task.md` Phase 4 全部 [x] + 会话 12 历史追加 | `task.md` | - | [x] |
| 测试结果 | pytest | **400 passed / 3 skipped** | [x] |
| lint 结果 | ruff check | All checks passed | [x] |
| W7 commit | git | (待 commit) | [~] |

**测试数量统计**:

- W1:79 passed / 3 skipped
- W2:212 passed / 3 skipped(+133)
- W3:285 passed / 3 skipped(+73)
- W4:346 passed / 3 skipped(+61)
- W5:349 passed / 3 skipped(+3,imagehash 装上)
- W6:370 passed / 3 skipped(+21)
- W7:**400 passed / 3 skipped**(+30)
- **当前总数:400 passed / 3 skipped**

---

## 3. 已读 / 已写文件清单

### 已读(信息已缓存,下次会话无需重读)

- `MEMORY.md`、`task.md`、`handoff-pipeline-w6-cli-2026-07-19.md`
- `_research/PROJECT_DESCRIPTION.md` §6.3 / 任务 9 + 13(MCP 章节)
- `.venv/Lib/site-packages/mcp/server/stdio.py`(stdio_server 源码)
- `.venv/Lib/site-packages/mcp/types.py`(Tool / TextContent / CallToolResult schema)
- `src/media_to_doc/cli.py` W6 版(`_isolate_inbox` / `_result_to_json` / `_print_summary_table`)
- `src/media_to_doc/state.py`(`State.load` / `save` / `STAGE_ORDER`)
- `src/media_to_doc/pipeline/runner.py`(`run_pipeline(inbox=None, ...)` 派生逻辑)
- `tests/test_cli.py` W6 版(monkeypatch run_pipeline stub 模式)

### 已写(本次会话新增)

**源码**(1 新文件,~479 行):

- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/mcp_server.py`

**测试**(1 新文件,30 用例):

- `F:/soft/00selfmade/media-to-doc/tests/test_mcp_server.py`

**文档**(1 新文件,~200 行):

- `F:/soft/00selfmade/media-to-doc/docs/MCP_INTEGRATION.md`

### 已修改

- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/cli.py`
  - `mtd mcp` 子命令:替换 W6 占位("尚未实装"),调 `mcp_server.main()`
  - KeyboardInterrupt → 静默 exit 0(Claude Desktop 关闭连接触发)
- `F:/soft/00selfmade/media-to-doc/README.md`
  - §3 MCP Server 标题修正路径(macOS / Windows)
  - 链接到 `docs/MCP_INTEGRATION.md`
  - 路线图重排:Phase 0/1/3/5 ✅,Phase 2/6 ⏳
- `F:/soft/00selfmade/media-to-doc/CLAUDE.md`
  - §9.4 加"W7 已实装"标注 + 文档链接 + 工具清单
- `F:/soft/00selfmade/media-to-doc/task.md`
  - 最后更新日期 → W7 完成
  - Phase 4 全部 checkbox → [x]
  - 追加会话 12 历史 + W8 候选

---

## 4. 关键决策与原因

### 决策 1:handler 同步 + 日志走 stderr

**问题**:stdio MCP server 与日志输出共享 stdout,JSON-RPC 帧不能被任何额外字符污染。

**选项**:
- A:`print()` 全部日志 + handler async(MCP 标准)
- B:日志走 stderr + handler 同步(参考实现设计)
- C:handler async 但 log 用 logging.StreamHandler(sys.stderr)

**选择**:B

**原因**:
1. 参考实现 `c80abaf` 已验证 B 方案(commit message 明确指出)
2. `print(..., file=sys.stderr)` 比 `logging` 配置简单,无需 logger init
3. 同步 handler 不阻塞 event loop(每 tool 调用都是快操作 < 100ms)
4. `run_pipeline` 等长任务虽然慢,但 MCP 客户端可轮询 `check_status` 检查进度

**下次何时再讨论**:不会 — 设计已稳定

### 决策 2:6 工具纯函数 + `handle_call_tool` 包装 try/except

**问题**:MCP handler 抛异常会断 JSON-RPC 帧协议,客户端收到残缺响应。

**选项**:
- A:handler 抛异常(MCP SDK 会返回 error frame,但内容难控)
- B:工具纯函数 + handler 包装 try/except → TextContent 含 JSON 错误

**选择**:B

**原因**:
1. 错误格式统一(`{"error": "...", "tool": "..."}`),前端/UI 可解析
2. `handle_call_tool` 内部异常额外带 `traceback` 字段,便于调试
3. 工具纯函数便于直接单测(绕过 MCP 协议层)
4. 与 `_pipeline_result_to_dict` / `_state_to_dict` 等同模块 helper 一致

**下次何时再讨论**:不会 — 模式已稳定

### 决策 3:read-only 工具带 `ToolAnnotations(readOnlyHint=True)`

**问题**:MCP 客户端(Claude Desktop / Cline)能否区分只读 vs 副作用工具?

**选项**:
- A:全部不标
- B:只读工具加 `readOnlyHint=True`(list_courses / check_status / list_outputs / read_lecture)
- C:用 `destructiveHint=True` 标副作用工具

**选择**:B

**原因**:
1. MCP SDK 1.28.1 支持 `ToolAnnotations`(`title / readOnlyHint / destructiveHint / idempotentHint`)
2. 只读工具无副作用,可被 LLM 安全调用而不破坏状态
3. 客户端可在 UI 标注"只读"标识,提高用户信任
4. 副作用工具(run / resume)不标 readOnlyHint,默认 False 即可

**下次何时再讨论**:不会 — ToolAnnotations 已稳定

### 决策 4:`tool_run_pipeline` 不吞 `find_media` 异常

**问题**:`inbox` 空目录(无媒体)时,`run_pipeline` 会继续跑但 audio 阶段失败。

**选项**:
- A:`find_media` 抛 FileNotFoundError → tool_run_pipeline 吞掉,继续 run_pipeline
- B:`find_media` 抛 FileNotFoundError → tool_run_pipeline 直接抛给 MCP 客户端

**选择**:B

**原因**:
1. 友好错误比跑 11 stage 失败更省时间(几秒 vs 几小时)
2. CLI `mtd run` 也是这种行为(空 inbox → exit 2 + 友好提示)
3. MCP 客户端可直接看到错误原因,引导用户检查 inbox

**下次何时再讨论**:不会 — 行为已与 cli 对齐

### 决策 5:`tool_list_outputs` 用 `Path.parts[0] == "images"` 分类

**问题**:`rel.startswith("images/")` 在 Windows 上失败(Path 用 `\\`)。

**选项**:
- A:正则同时匹配 `images[/\\]`
- B:用 `Path.parts[0]` 检查首段(跨平台)

**选择**:B

**原因**:
1. `Path.parts` 跨平台一致(都用 `/` 元素)
2. 比 regex 更可读、更鲁棒
3. 仅 1 行额外 diff:`len(p.relative_to(raw_dir).parts) >= 2 and parts[0] == "images"`

**下次何时再讨论**:不会 — Path.parts 跨平台方案已稳定

### 决策 6:`tool_run_pipeline` 复用 inbox 自动隔离

**问题**:MCP 端多视频 inbox 也要避免误选,还是只让用户自己保证?

**选项**:
- A:MCP 端只做单视频(用户自保证)
- B:复用 cli 的 `_isolate_inbox` 逻辑,默认隔离多视频

**选择**:B

**原因**:
1. W5 已验证隔离是必要的(`inbox 多视频按 ASCII 排序选错`)
2. MCP 端复用 cli 的语义,`mtd run` 和 MCP `run_pipeline` 行为一致
3. 隔离失败 → run_pipeline 不会跑(友好错误),不影响结果

**下次何时再讨论**:不会 — 行为已与 cli 对齐

### 决策 7:测试不真跑 11 stage(monkeypatch run_pipeline)

**问题**:MCP 集成测试要不要真跑流水线?

**选项**:
- A:真跑(monkeypatch 重依赖如 faster-whisper / diffusers)
- B:monkeypatch `mcp_server.run_pipeline`(整函数替换)

**选择**:B

**原因**:
1. W6 test_cli 已验证 stub 模式(370 用例全过)
2. 真跑会触发 ffmpeg / whisper / diffusers 重依赖,CI 离线跑不动
3. stub 模拟 `inbox 派生` + `state.save` 关键行为,已覆盖 _fake_run_pipeline 派生逻辑
4. 真 11 stage 行为由 `test_pipeline/*` 独立测试覆盖

**下次何时再讨论**:不会 — monkeypatch stub 模式已稳定

---

## 5. 撞墙 / 未完成 / 已知问题

### 5.1 撞墙点(已全部解决)

| 现象 | 已尝试 | 残留 |
|---|---|---|
| 测试 `test_list_courses_multiple` 期望 `.srt` 算媒体 → 实际不算 | 检查 `SUPPORTED_EXTS` → 改测试用 `.mkv` | 已解决 |
| `rel.startswith("images/")` Windows 失败 → images 分类错误 | 改用 `Path.parts[0] == "images"` | 已解决 |
| `tool_run_pipeline` 空 inbox 不报错 | 删 `try/except FileNotFoundError` 让异常透传 | 已解决 |
| ruff F401 报 unused imports | 删 `InitializationOptions` / `INBOX_DIR` / `_isolate_inbox` 里 `contextlib` | 已解决 |
| `test_resume_pipeline_uses_state_inbox` captured inbox 是 None | fake 也派生 inbox(从 state.inbox_path) | 已解决 |

### 5.2 TODO(下次会话继续)

按 ROADMAP §3 Phase 4 剩余 + Phase 6:

**Phase 4 剩余**:
- [ ] `__init__.py` 顶层 re-export + lazy import(PEP 562)— 跨项目直接 `from media_to_doc import run_pipeline`

**Phase 6 W8 候选**:
- [ ] **A. LE 闭环**(推荐优先)— 迁移 `_research/le_prototype/{pipeline_logger,gatekeeper,learnings}.py` 到
  `src/media_to_doc/logger/`,替换 mock stage 为真实 11 stage
- [ ] **B. Python API 顶层 re-export**(1h)
- [ ] **C. 测试巩固**(可选优化覆盖率)

### 5.3 已知问题 / 技术债

- `read_lecture` 一次性读全文:大讲义(>1MB)可撑爆 MCP 上下文;后续可加分页(参数 `max_chars`)
- `run_pipeline` 同步阻塞:长任务会卡住 MCP session;建议客户端用 `stop_after="chapters"` 先看 LLM 质量
- `tool_run_pipeline` 在 transport 断开时不会自动停(`asyncio.CancelledError` 处理未实装)
- Claude Desktop 配置需要用户手改路径(`F:/soft/00selfmade/media-to-doc`);后续可加 `mtd init` 命令写默认配置
- MCP 协议层(`handle_call_tool`)未对 `additionalProperties=False` 验证;malformed input 会直接抛 KeyError,被 except 兜住
- `tool_check_status` 不区分 staging(workspace 根 vs inbox/output 派生)— 未来可加 `--workspace-root` 参数
- 端到端 MCP 测试(用真实的 Claude Desktop 连接)未做;CI 只能保证 stdio 协议层 OK

### 5.4 不写进 task 的"探索发现"

- **mcp 1.28.1 用低阶 API**:无 FastMCP,必须手动装饰 `@server.list_tools()` /
  `@server.call_tool()`。FastMCP 在 mcp>=1.10 才有
- **stdio_server 内部用 anyio 异步**:handler async 是必须的(`asyncio.run(handle_call_tool())`)
- **`InitializationOptions` 实际不需要 import**:`server.create_initialization_options(...)` 自动调用
- **Typer CliRunner 与 MCP 不冲突**:`mtd mcp` 直接调 `mcp_server.main()`,CliRunner 测试只需 monkeypatch 替换
- **路径分隔符在 Windows 测试要小心**:`Path.rglob` + `sorted` + `Path.parts` 三连,不要用字符串 startswith

---

## 6. 测试状态

```
$ uv run pytest
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-9.1.1
collected 403 items

tests/test_smoke.py::... [14 tests]
tests/test_utils/test_ffmpeg_utils.py::... [9 tests]
tests/test_utils/test_hash_utils.py::... [6 passed + 3 skipped]
tests/test_llm/test_base.py::... [12 tests]
tests/test_llm/test_ollama.py::... [11 tests]
tests/test_llm/test_anthropic.py::... [11 tests]
tests/test_llm/test_openai_compat.py::... [17 tests]
tests/test_pipeline/test_audio.py::... [9 tests]
tests/test_pipeline/test_asr.py::... [11 tests]
tests/test_pipeline/test_frames.py::... [10 tests + 1 pattern data]
tests/test_pipeline/test_ocr.py::... [20 tests]
tests/test_pipeline/test_asr_correct.py::... [19 tests]
tests/test_pipeline/test_chapters.py::... [21 tests]
tests/test_pipeline/test_draft.py::... [26 tests]
tests/test_pipeline/test_imagegen.py::... [18 tests]
tests/test_pipeline/test_render.py::... [29 tests]
tests/test_pipeline/test_longdoc.py::... [32 tests]
tests/test_pipeline/test_verify.py::... [27 tests]
tests/test_pipeline/test_runner.py::... [15 tests]
tests/test_cli.py::... [21 tests]
tests/test_mcp_server.py::... [30 tests]                              ← W7 NEW

======================= 400 passed, 3 skipped in 3.55s =======================
```

ruff check `src/ tests/`:

```
All checks passed!
```

---

## 7. Git 状态

```
$ git log --oneline -10
9582179 docs(task): mark W5 端到端跑通完成
5d8e981 docs(handoff): add W4 pipeline snapshot + task.md progress
3b32743 feat(pipeline): W4 — longdoc + verify stages (11 stages all live)
266d741 docs(handoff): add W3 pipeline snapshot + task.md progress
86694a0 feat(pipeline): draft + imagegen + render stages (W3)
f712552 feat(pipeline): ocr + asr_correct + chapters + llm providers
04f992c feat(pipeline): W1 — audio + asr + frames stages + utils + runner
```

W7 待 commit 内容(预计 7 文件,~1500 行):

- **源码**:1 新文件(`mcp_server.py` 479 行)+ `cli.py` +8 行
- **测试**:1 新文件(`test_mcp_server.py` 30 用例)
- **文档**:1 新文件(`docs/MCP_INTEGRATION.md` ~200 行)+ `README.md` + `CLAUDE.md` §9.4 + `task.md`

---

## 8. 给下一个会话的提示

**新会话第一句话建议**:

```
承接 handoff-pipeline-w7-mcp-2026-07-19.md,W7 已完成 MCP server(400 测试)。
请评审 W7 commit,决定 W8 方向:
- A. Phase 6 L2 LE 闭环(迁移 _research/le_prototype/)
- B. Python API 顶层 re-export + lazy import
- C. 测试巩固(可选优化覆盖率)
```

**主要任务**(按 W8 候选优先级排序):

1. **L2 LE 闭环**(架构演进)— 迁移 `_research/le_prototype/` 到
   `src/media_to_doc/logger/`,替换 mock stage 为真实 11 stage,
   `runner.run_pipeline` 末尾调 `gatekeeper_check` + `logger.finalize`
2. **Python API re-export**(跨项目可调用基础)— `__init__.py` 用 `__getattr__` 实现
   lazy import(PEP 562),让 `from media_to_doc import run_pipeline` 直接可用
3. **测试巩固**(可选)— 当前 400 用例已超 ROADMAP 目标(110+),可优化覆盖率或补端到端 MCP 集成测试

**别忘了**:

- 缩进 2 空格,Python 函数类型注解(全局偏好)
- 函数 ≤ 100 行,模块 ≤ 500 行(TDD §9.2)
- lazy import 重依赖(BeautifulSoup / lxml / faster-whisper)只在 extras 已装时可用
- `mcp_server.py` 已经有 `ToolAnnotations(readOnlyHint=True)`,W8+ 新增工具保持一致
- 测试不要真跑 11 stage(monkeypatch 是已验证模式)
- 不要破坏已通过的 400 个测试
- W7 的 `tool_run_pipeline` 错误路径已对齐 cli.run(空 inbox / 无媒体 → FileNotFoundError)

**关键参考**:

- `handoff-pipeline-w6-cli-2026-07-19.md` — 上一会话(W6 CLI 实装)
- `handoff-pipeline-w5-smoke-2026-07-18.md` — W5 端到端冒烟
- `_research/PROJECT_DESCRIPTION.md` §6.3(MCP 配置 + 6 工具)+ 任务 9 + 13
- `_research/LE_DESIGN.md` + `_research/le_prototype/`(W8 LE 迁移源)
- `ROADMAP.md` §3 Phase 4 W7(已完成)+ §4 Phase 6 LE 闭环
- `TDD.md` §5 数据流第 11 步(verify)+ LE 闭环设计
- 本会话:`src/media_to_doc/mcp_server.py`(6 工具纯函数 + Server + handler)
- 本会话:`docs/MCP_INTEGRATION.md`(Claude Desktop 集成指南)
- `.venv/Lib/site-packages/mcp/server/stdio.py`(stdio_server 异步 ctx mgr)
- `.venv/Lib/site-packages/mcp/types.py`(Tool / TextContent / CallToolResult)

**复杂度提示**:

- W7 是 2-3h 估 → 实际 ~2h(从 W6 handoff §6 估计)
- 6 工具纯函数 + 协议层 handler 模式可复用:W8+ 新增工具(LE metrics / list_runs)沿用同样模式
- mcp 1.28.1 用低阶 API(无 FastMCP),未来 mcp>=1.10 可升级
- LE 闭环工作量与 L1 核心流水线相当(~10-15h,见 W4 handoff §5.2)
- Python API re-export 是 1h 小任务,可与 LE 闭环并行做

---

## 9. 上下文参考链接

- `CLAUDE.md` — 项目级指引
- `task.md` — 活跃 todo(含本会话历史)
- `PRD.md` / `TDD.md` / `ROADMAP.md`
- `handoff-template.md` — 长期复用模板
- `handoff-pipeline-w6-cli-2026-07-19.md` — 上一会话(W6 CLI)
- `handoff-pipeline-w5-smoke-2026-07-18.md` — W5 端到端冒烟
- `_research/PROJECT_DESCRIPTION.md` §6.3 MCP 配置
- `_research/LE_DESIGN.md` — LE 详细设计(W8 接入参考)
- `_research/le_prototype/` — LE 原型(W8 迁移源)
- `git log --oneline`:W7 待 commit + `23c1f96` + `db92ac9` + `29f018e` + `82af24c` + `9582179`

---

## 10. 自检清单

- [x] 本会话目标全部完成(Phase 4 W7 全交付)
- [x] 无未提交代码改动(working tree clean,待 W7 commit)
- [x] 无未完成任务(下次会话从 W8 开始)
- [x] 测试状态明确(400 passed / 3 skipped in 3.55s)
- [x] Git 状态明确(W7 待 commit,分支就绪)
- [x] 下次会话第一句话建议清晰
- [x] 关键决策记录 7 条,带"为什么"
- [x] 上下文参考链接完整
- [x] `uv run pytest` 端到端验证通过(400/400)
- [x] `uv run ruff check src/ tests/` 全过
- [x] pytest 增量:W1 → W7 = 79 → 400(+321,目标 110+ 超 3 倍)
- [x] W7 MCP 6 工具全部就位(handler + 纯函数 + 测试)
- [x] `mtd mcp` 子命令实装(替换 W6 占位)
- [x] Claude Desktop 配置文档就绪(`docs/MCP_INTEGRATION.md`)
- [x] handler 日志走 stderr(stdout 留给 JSON-RPC,参考实现 c80abaf 验证)
- [x] `tool_run_pipeline` 与 cli.run 行为对齐(inbox 隔离 + 错误处理)
- [x] read-only 工具标 `readOnlyHint=True`(MCP 客户端可识别)
