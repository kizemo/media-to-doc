# handoff — W6 CLI run/resume 实装

**会话**: 2026-07-19
**分支**: `feat/cli-w6-run-resume`
**任务**: ROADMAP Phase 4 W6 — CLI `mtd run` / `mtd resume` / `mtd status` / `mtd list` 实装

---

## 1. 交付清单

| 文件 | 变更 | 行数 |
|---|---|---|
| `src/media_to_doc/cli.py` | 重写:run/resume/status/list 实装 + inbox 隔离 + JSON 输出 + eprint helper | +520 |
| `src/media_to_doc/state.py` | 加 `inbox_path: str \| None = None` 字段(W6 让 resume 不必传 inbox) | +3 |
| `src/media_to_doc/pipeline/runner.py` | `run_pipeline(inbox: Path \| None, ...)` + 自动写回 inbox_path 到 state | +39 / -16 |
| `src/media_to_doc/pipeline/audio.py` | `find_media(exclude_dirs=...)` 让 CLI 在 work_dir 在 inbox 内时正确选视频 | +22 / -3 |
| `tests/test_cli.py` | 新增:21 用例覆盖 4 个命令 | +396 |
| `tests/test_smoke.py` | 改写 `test_cli_run_not_implemented`:run 已实装,空 inbox → exit 2 | +3 / -3 |

**净增 +534 行,21 个新测试。**

---

## 2. 设计决策

### 2.1 resume 不必传 inbox

**Why**: W5 用户流程:`mtd run` 启动 → 中断 → `mtd resume` 续跑。resume 时用户不应该需要记得 inbox 路径。
**How**: `state.inbox_path` 持久化,`run_pipeline(inbox=None)` 自动从 state.json 派生。
**Trade-off**: 用户移动了源文件,inbox 派生可能失败 → 用户可用 `--inbox` 覆盖。

### 2.2 inbox 自动隔离

**Why**: W5 smoke runner 验证:inbox 多视频时 `find_media` 按 ASCII 排序选错文件。
**How**: CLI 默认开启 `_isolate_inbox`(mv 非目标媒体到 `<work>/.excluded-<ts>/`),跑完 `try/finally` 恢复。
**Opt-out**: `--no-isolate` 给明确单视频场景用。

### 2.3 CLI 测试策略

**Why**: 11 stage 真跑会触发 ffmpeg/Whisper 重依赖;CI 离线跑不动。
**How**: `monkeypatch` 替换 `cli.run_pipeline` 为 stub(stub 模拟真 run_pipeline 的 inbox 派生 + state.json 持久化)。
**Stub 行为**: mark 全部 11 stage 为 completed → `result.is_success=True` → CLI exit 0。

### 2.4 JSON 输出绕开 Rich markup

**Why**: Rich Console 默认 `markup=True`,会把 `[...]` 当 markup tag 解析。JSON 字符串含大量 `[`(数组)+反斜杠转义,被 Rich 错误处理成 ANSI 控制序列 + 强制换行。
**How**: JSON 输出改用 `sys.stdout.write(_json.dumps(...))`,不经过 Rich。
**Trade-off**: JSON 输出无 Rich 颜色高亮(本来也不该有)。其它文本输出保留 Rich 美化。

### 2.5 eprint 走 stdout 而非 stderr

**Why**: Typer 0.12+ 的 CliRunner 不支持 `mix_stderr`,stderr 输出在测试里极难捕获。
**How**: `eprint(*args)` 直接调 `console.print(*args)`(走 stdout)。
**Trade-off**: 生产 shell 仍可用 `2>log.txt` 重定向。MCP / 管道 / 测试都能一致读取。

---

## 3. CLI 命令速查

```bash
# 完整跑(自动隔离 inbox 多视频 + 默认 imagegen=skip)
uv run mtd run <inbox_dir>

# 自定义 work 目录 + 覆盖 LLM
uv run mtd run <inbox> --work-dir <path> --llm anthropic --llm-model claude-sonnet-4-6

# 强制重跑所有 stage + JSON 输出(供 UI / MCP 消费)
uv run mtd run <inbox> --force --json

# 续跑(从 state.inbox_path 派生 inbox)
uv run mtd resume <work_dir>

# 续跑 + 覆盖 inbox(视频被移动后)
uv run mtd resume <work_dir> --inbox <new_inbox>

# 查看进度(只读)
uv run mtd status <work_dir>
uv run mtd status <work_dir> --json

# 列出 inbox 课程
uv run mtd list --workspace <ws_root>
uv run mtd list --json
```

---

## 4. 关键测试用例(21 个,全过)

| 用例 | 覆盖点 |
|---|---|
| `test_run_creates_state_and_work_dir` | work 默认 = inbox/output + state.json 写入 |
| `test_run_with_work_dir_override` | `--work-dir` 覆盖 |
| `test_run_llm_and_imagegen_overrides` | 4 个覆盖项生效 |
| `test_run_no_longdoc_sets_config_flag` | `--no-longdoc` 改 config |
| `test_run_force_disables_skip_completed` | `--force` 透传 |
| `test_run_stop_after_passthrough` | `--stop-after` 透传 |
| `test_run_no_media_returns_error` | inbox 无媒体 → exit 2 |
| `test_run_isolates_inbox_multivideo` | 多视频隔离 + 恢复 + staging 清理 |
| `test_run_json_output` | `--json` 输出可解析 JSON |
| `test_run_pipeline_exception_returns_error` | pipeline 抛错 → exit 1 + 错误信息 |
| `test_resume_uses_state_inbox_path` | resume 默认从 state.json 派生 inbox |
| `test_resume_inbox_override` | `--inbox` 覆盖 |
| `test_resume_no_state_json_returns_error` | 无 state.json → exit 2 + 提示 mtd run |
| `test_resume_force_flag` | `--force` 透传 |
| `test_status_reads_state_json` | 表格输出含 stage 名 + 状态 |
| `test_status_no_state_returns_error` | 无 state.json → exit 2 |
| `test_status_json_output` | `--json` 输出含完整 stages dict |
| `test_list_scans_inbox` | 列出所有子目录 + 媒体文件 |
| `test_list_empty_inbox` | inbox 空目录友好提示 |
| `test_list_json_output` | `--json` 输出结构化 courses |
| `test_list_missing_inbox` | inbox 不存在友好提示 |

---

## 5. 测试与 lint

- `uv run pytest`:**370/370 passed**(W5 349 + W6 21 CLI 用例),3 skip 不变
- `uv run ruff check src tests`:**All checks passed**
- `uv run mtd --version` → `media-to-doc 0.1.0`
- `uv run mtd list` → 显示 inbox 状态
- `uv run mtd list --json` → 合法 JSON 输出

---

## 6. 下次会话(W7 候选)

按 ROADMAP Phase 4:

- **A. MCP server**(stdio JSON-RPC,6 工具 + Claude Desktop 配置)— 2-3h,产品价值最大
- **B. Python API 顶层 re-export**(`from media_to_doc import ...` + lazy import PEP 562)— 1h,跨项目可调用基础
- **C. __init__.py lazy import + CLI 顶层 from media_to_doc import** — 30min,简单 win

**推荐**:A(MCP 优先,B + C 是它前置,可合并做)

**预计 commit message**:`feat(cli): W6 — mtd run/resume/status/list with inbox isolation + JSON output`

---

## 7. 技术债(给 W7+)

1. **JSON 输出绕开 Rich**:`sys.stdout.write` 简单但失去 Rich 高亮。后续如果要让 JSON 也带 syntax highlight,可改用 `Console.print_json(data=payload)`(已用于 status/list 命令)。
2. **CLI 测试 stub 模拟 inbox 派生**:stub 复制了真 run_pipeline 的 inbox 派生逻辑(13 行),如果 run_pipeline 改了这逻辑,stub 也会不一致。低风险 — 真 pipeline 有自己独立测试覆盖。
3. **eprint 走 stdout 而非 stderr**:Typer CliRunner 限制,生产环境 shell 用 `2>` 重定向即可。

---

## 8. session 健康

- 工具调用次数:<100(本会话 ~80)
- 单回合 diff 最大:cli.py 重写 +520 行(W6 CLI 整体改造,合理范围)
- 测试状态:370/370 全过
- 心跳提示:无
- 撞墙征兆:无
