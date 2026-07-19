# MCP Server 集成指南

> 适用版本:**media-to-doc v0.1.0+**(W7 + W8)
> 上游依赖:`mcp>=1.0.0`(已在 `[mcp]` extras / `all` extras 注册)

media-to-doc 提供 **8 个 MCP 工具**(W7=6 + W8=2),可在 Claude Desktop /
Codex / Cline 等 MCP 客户端中调用,把"启动流水线 / 读讲义 / 查 LE 健康度"
封装为对话式工具调用。

---

## 1. 快速配置

### 1.1 Claude Desktop

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS)/`%APPDATA%\Claude\claude_desktop_config.json`(Windows):

```json
{
  "mcpServers": {
    "media-to-doc": {
      "command": "uv",
      "args": [
        "--project", "F:/soft/00selfmade/media-to-doc",
        "run", "mtd-mcp"
      ]
    }
  }
}
```

> **关键**:`args` 必须用绝对路径,且 `--project` 后接 media-to-doc 项目根。

### 1.2 其它 MCP 客户端

`mtd-mcp` 命令注册在 `pyproject.toml [project.scripts]`,任何 MCP 客户端
只需配置 `command + args`。如果客户端不支持 `--project`,可写包装脚本:

```bash
#!/usr/bin/env bash
# /usr/local/bin/mtd-mcp
exec uv --project F:/soft/00selfmade/media-to-doc run mtd-mcp "$@"
```

---

## 2. 8 个工具

| 工具 | 类型 | 用途 |
|---|---|---|
| `list_courses` | 只读 | 列出 workspace/inbox 下所有课程 |
| `run_pipeline` | **副作用** | 跑完整流水线(可中断后续跑) |
| `resume_pipeline` | **副作用** | 从 `state.json` 续跑 |
| `check_status` | 只读 | 查 11 stage 进度 |
| `list_outputs` | 只读 | 列出产物(按类别分组) |
| `read_lecture` | 只读 | 读讲义(raw / cleaned / final × md / html) |
| `get_run_metrics` | 只读 | **W8** 读单个课程的 LE 元数据(state + pipeline_run + errors) |
| `list_runs` | 只读 | **W8** 扫 workspace 所有 run,带跨 run LLM 健康度 |

---

## 3. 工具签名

### 3.1 `list_courses`

```python
list_courses(workspace_root: str | None = None) -> dict
```

**Returns**: `{workspace, inbox, courses: [{name, path, media_files, media_count}]}`

**示例 Prompt**:
> "列出我 inbox 里的所有课程"

### 3.2 `run_pipeline`

```python
run_pipeline(
  inbox_dir: str,                       # 必填
  workspace_root: str | None = None,
  llm: Literal["ollama","anthropic","openai_compatible"] | None = None,
  imagegen: Literal["local_sdxl","skip"] | None = None,
  longdoc_llm: str | None = None,       # 默认 skip 只跑规则清理
  no_longdoc: bool = False,
  force: bool = False,                  # 强制重跑所有 stage
  stop_after: str | None = None,        # 11 stage 之一,跑到停下
) -> dict                                # PipelineResult JSON
```

**Returns**: `{course, inbox_path, work_dir, is_success, duration_seconds,
completed, failed, stages: {...}}`

**示例 Prompt**:
> "把 workspace/inbox/培训01/ 这目录的培训视频跑成讲义"

### 3.3 `resume_pipeline`

```python
resume_pipeline(
  work_dir: str,                        # 必填
  inbox_dir: str | None = None,         # 默认从 state.json 派生
  force: bool = False,
  stop_after: str | None = None,
) -> dict
```

### 3.4 `check_status`

```python
check_status(work_dir: str) -> dict
```

**Returns**: `{course, inbox_path, current_stage, started_at, updated_at,
is_complete, stages: {stage: {status, started_at, finished_at, error}}}`

### 3.5 `list_outputs`

```python
list_outputs(inbox_dir: str) -> dict
```

**Returns**:
```json
{
  "inbox": "...",
  "work_dir": "...",
  "stem": "<视频同名>",
  "outputs": {
    "raw_md": ["<stem>.md"],
    "raw_html": ["<stem>.html"],
    "cleaned_md": ["<stem>_cleaned.md"],
    "final_html": ["<stem>_final.html"],
    "images": ["images/gen_001.png", ...],
    "manifests": ["chapter_01.md", "verify.json", ...]
  },
  "stages": {"audio": "completed", ...}
}
```

### 3.6 `read_lecture`

```python
read_lecture(
  inbox_dir: str,                       # 必填
  version: Literal["raw","cleaned","final"],   # 必填
  fmt: Literal["md","html"] = "md",
) -> dict
```

**Returns**: `{version, fmt, path, content, size_bytes}`

**版本说明**:
- `raw`:render 阶段产物(`<stem>.md` / `<stem>.html`)
- `cleaned`:longdoc 净化稿(`<stem>_cleaned.md`)
- `final`:longdoc 最终 HTML(`<stem>_final.html`,带 TOC + 锚点 + 内嵌 CSS)

### 3.7 `get_run_metrics` (W8)

```python
get_run_metrics(work_dir: str) -> dict
```

**Returns**: 一次性返回

- `course` / `inbox_path` / `work_dir`:课程元信息
- `state`:11 stage 调度状态(scheduler 真相源)
- `pipeline_run`:LE 沉淀层元数据(`memory/YYYY-MM-DD.md` + LE 质量分数 + `llm_health`)
- `gatekeeper_passed`:L2 审核层通过标记
- `errors`:Pattern-Key 列表(L4 进化层自动晋升候选)

**示例 Prompt**:
> "查 work/培训01/ 的 LE 健康度,如果有 gatekeeper 失败就告诉我"

### 3.8 `list_runs` (W8)

```python
list_runs(
  workspace_root: str | None = None,
  limit: int = 20,
) -> dict
```

**Returns**:

- `workspace` / `work_root`:扫描根
- `total_runs`:扫到的 run 总数
- `runs`:每个 run 的摘要(course / mtime / pipeline_run 部分字段)
- `llm_health_global`:跨 run 的 LLM 健康度聚合(失败率 + 推荐策略)

**示例 Prompt**:
> "列出我最近 10 个跑过的课程,看整体 LLM 失败率高不高"

---

## 4. 推荐工作流

### 4.1 一句话跑流水线

> "处理 workspace/inbox/培训01/ 这个目录的培训视频,完成后告诉我讲义前 3 个关键要点"

Claude Desktop 会自动:
1. 调 `run_pipeline(inbox_dir="...")` 启动流水线
2. (可选)轮询 `check_status` 直到完成
3. 调 `read_lecture(version="final", fmt="html")` 读讲义
4. 总结前 3 个关键要点

### 4.2 中断续跑

> "我的流水线在 asr 阶段中断了,从 work/培训01/ 续跑"

→ `resume_pipeline(work_dir="work/培训01/")`

### 4.3 列出产物 + 读讲义

> "列出 workspace/inbox/培训01/ 的产物,然后告诉我 _final.html 的章节列表"

Claude Desktop:
1. `list_outputs(inbox_dir="...")`
2. `read_lecture(version="final", fmt="html")`
3. 解析 HTML 提取章节(用 markdown 库或简单 regex)

---

## 5. 错误处理

所有工具的失败返回 `TextContent` 含 `{"error": "...", "tool": "..."}`,
**不会** 抛异常打断 MCP session。常见错误:

| 错误 | 原因 | 解决 |
|---|---|---|
| `FileNotFoundError: inbox 目录不存在` | `inbox_dir` 路径错误 | 用 `list_courses` 找正确路径 |
| `FileNotFoundError: state.json 不存在` | resume 时 work_dir 没跑过 | 先用 `run_pipeline` |
| `ValueError: inbox 缺省且 state.json 未记录` | resume 时 inbox=None 且 state.json 没记录 | 用 `run_pipeline(inbox_dir=...)` 启动 |
| `ValueError: version 必须是 raw/cleaned/final` | `read_lecture` 的 version 非法 | 用合法版本名 |

---

## 6. 调试

### 6.1 启动 server 看 stderr 日志

```bash
uv run mtd-mcp
# 或等价 uv run --project <path> mtd-mcp
```

所有日志走 stderr,stdout 留给 JSON-RPC 帧。Claude Desktop 启动失败时
可手动运行看错误信息。

### 6.2 测试 JSON-RPC 协议

```bash
# 启动 server 后,用 echo 发 initialize + tools/list:
(echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'
 sleep 1
 echo '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}') | uv run mtd-mcp
```

应看到 8 个工具的 JSON 描述。

### 6.3 已知限制

- `run_pipeline` 同步阻塞:长任务会卡住 MCP session 几小时,建议用
  `stop_after="chapters"` 先看 LLM 章节质量,再 resume 跑后半段
- `read_lecture` 一次性读全文:大讲义(>1MB)可能撑爆上下文,后续可加分页
- `list_outputs` 不递归查 `<work>/asr/` 等中间产物:只在 `chapters/raw/`
  下扫 md/html/images;中间产物查 state.json 的 stage 状态
