# media-to-doc

> 把本地音视频(培训录像、讲座录音、运营课、电商课)一键转化为**带 AI 配图、可独立分发**的
> Markdown + HTML 讲义。

[![Status: v0.1.0-dev](https://img.shields.io/badge/status-v0.1.0--dev-yellow)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![Tests: 508 passed](https://img.shields.io/badge/tests-508%20passed-green)]()

---

## 这是什么

`media-to-doc` 是一款开源工具,把培训音视频自动转写、校对、配图、编排,
产出可分发、可独立阅读的讲座讲义(`.md` + `.html`)。

**核心特点**:

- **11 阶段流水线**:`audio → asr → frames → ocr → asr_correct → chapters → draft → imagegen → render → longdoc → verify`
- **本地优先**:默认完全离线,Ollama + Faster-Whisper + SDXL 全栈本地推理
- **可插拔 LLM**:支持 Ollama / Anthropic / OpenAI-compatible(MiniMax、DeepSeek、智谱、Moonshot、混元等)
- **跨项目可调用**:Python API + CLI(`mtd`)+ MCP server(供 Claude Desktop / Codex 原生集成)
- **Loop Engineering**:内置五层闭环(执行 / 审核 / 沉淀 / 进化 / 健康度),跑得越多、质量越好
- **可分发的产物**:图片一律相对路径,讲义目录可整盘复制 / 上传 / 丢知识库

---

## 5 分钟快速开始

### 1. 安装

```bash
# 前置:Python 3.11+ / uv 0.11+ / ffmpeg 4+
pip install uv
git clone https://github.com/media-to-doc/media-to-doc.git
cd media-to-doc

# 核心依赖(轻量,CLI + Python API + MCP server)
uv sync

# 全部功能(可选,重依赖约 5GB:faster-whisper / scenedetect / rapidocr / diffusers / anthropic / openai)
uv sync --all-extras
```

### 2. 验证安装

```bash
uv run mtd --version
# 期望:media-to-doc 0.1.0

uv run pytest
# 期望:508 passed / 0 skipped
```

### 3. 跑一条流水线

```bash
# 把视频放到 inbox
mkdir -p workspace/inbox/我的培训
cp "我的培训.mp4" workspace/inbox/我的培训/

# 跑完整 11 stage(需要 --all-extras 装的依赖)
uv run mtd run workspace/inbox/我的培训/

# 中断后续跑(默认从 state.json 派生 inbox)
uv run mtd resume workspace/output/我的培训/

# 状态查询
uv run mtd status workspace/output/我的培训/

# 跨 run 健康度查询(W8 LE)
uv run mtd list workspace/
```

> **默认输出位置**:跑完流水线后,讲义在 `<inbox 父目录>/output/我的培训/raw/` 下(详见 [§产物布局](#产物布局))。

---

## 三种调用方式

### 1. CLI(终端用户)

```bash
mtd run <INBOX>               # 完整流水线
mtd resume <WORK>             # 续跑
mtd status <WORK>             # 查 11 stage 进度
mtd list [--workspace <DIR>]  # 列出 inbox 课程 + 跨 run 健康度(W8)
mtd doctor                    # 系统诊断
mtd config get llm.model      # 配置查询
mtd mcp                       # 启动 MCP server(8 工具)
```

完整 CLI 文档见 `mtd <command> --help`。

### 2. Python API(开发者,W9 PEP 562 顶层 re-export)

```python
from media_to_doc import WorkflowConfig, run_pipeline, list_runs

# 配置
cfg = WorkflowConfig()  # 默认 ollama + skip imagegen

# 跑流水线
result = run_pipeline(
    inbox=Path("workspace/inbox/course1"),
    work=Path("workspace/output/course1"),
    config=cfg,
    stop_after="chapters",  # 可选:先看 LLM 章节质量再跑后续
)

print(f"完成 {len(result.completed)}/11 stage")
print(f"LE pipeline_run = {result.pipeline_run.course}")

# 跨 run 健康度查询(W8)
runs = list_runs(workspace_root="workspace", limit=10)
print(f"llm_health_global = {runs['llm_health_global']}")
```

**优势**:`import media_to_doc` 启动 < 100ms,faster-whisper / diffusers 等重依赖按需加载。
完整公开 API 列表(52 个符号)见 [`media_to_doc.__all__`](src/media_to_doc/__init__.py)。

最小可跑示例:[`examples/cross_project_demo.py`](examples/cross_project_demo.py)。

### 3. MCP Server(Claude Desktop / Codex / Cline,W7 + W8)

```json
// ~/Library/Application Support/Claude/claude_desktop_config.json (macOS)
// %APPDATA%\Claude\claude_desktop_config.json (Windows)
{
  "mcpServers": {
    "media-to-doc": {
      "command": "uv",
      "args": ["--project", "F:/soft/00selfmade/media-to-doc", "run", "mtd-mcp"]
    }
  }
}
```

**8 个工具**(W7=6 + W8=2):

| 工具 | 类型 | 用途 |
|---|---|---|
| `list_courses` | 只读 | 列出 inbox 课程 |
| `run_pipeline` | 副作用 | 跑流水线 |
| `resume_pipeline` | 副作用 | 续跑 |
| `check_status` | 只读 | 查 11 stage 进度 |
| `list_outputs` | 只读 | 列出产物 |
| `read_lecture` | 只读 | 读讲义(raw / cleaned / final) |
| `get_run_metrics` | 只读 | **W8** 单课程 LE 元数据 |
| `list_runs` | 只读 | **W8** 跨 run 健康度 |

完整用法见 **[docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md)**。

---

## 公开 API(W9 顶层 re-export)

所有公开符号通过 `from media_to_doc import <name>` 一行访问,
底层用 PEP 562 `__getattr__` 实现 lazy import。

| 类别 | 符号 |
|---|---|
| **配置** | `WorkflowConfig`, `LLMConfig`, `ImagegenConfig`, `PathsConfig`, `PipelineConfig` |
| **流水线状态** | `STAGE_ORDER`, `StageState`, `StageStatus`, `State` |
| **流水线入口** | `run_pipeline`, `run_stage`, `PipelineResult`, `STAGE_FUNCS` |
| **11 stage 函数** | `prepare_audio`, `transcribe`, `extract_keyframes`, `KeyFrame`, `run_ocr`, `correct_asr`, `split_chapters`, `generate_drafts`, `generate_images`, `render_outputs`, `render_html`, `process_long_doc`, `render_final_html`, `verify_pipeline`, `VerifyReport` |
| **LLM provider** | `BaseLLMProvider`, `ChatMessage`, `ChatResponse`, `HealthReport`, `HealthStatus`, `get_provider`, `PROVIDERS` |
| **LE 健康度查询(W8)** | `get_run_metrics`, `list_runs`, `get_escalated_errors` |
| **Loop Engineering(W8)** | `PipelineLogger`, `PipelineRun`, `StageRecord`, `GatekeeperResult`, `timed_stage`, `gatekeeper_check`, `post_pipeline_hook`, `assess_llm_health`, `escalate_recurring_errors`, `find_known_pattern_keys`, `write_runtime_error` |

---

## 环境变量

| 变量 | 默认 | 用途 |
|---|---|---|
| `MEDIA_TO_DOC_WORKSPACE` | `~/Documents/media-to-doc/workspace` | workspace 根(覆盖 `paths.py`) |
| `MEDIA_TO_DOC_INBOX` | `<workspace>/inbox` | inbox 根 |
| `MEDIA_TO_DOC_WORK` | `<workspace>/output` | work 根(默认输出) |
| `MEDIA_TO_DOC_CONFIG` | `<workspace>/config.yaml` | 配置文件路径 |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama 服务地址 |
| `ANTHROPIC_API_KEY` | (无) | Anthropic Claude API key |
| `OPENAI_API_KEY` | (无) | OpenAI / 兼容协议 key |
| `OPENAI_BASE_URL` | (无) | OpenAI 兼容端点(MiniMax / DeepSeek 等 preset 也可) |
| `HF_ENDPOINT` | `https://huggingface.co` | HuggingFace 镜像(中国大陆设 `https://hf-mirror.com`) |
| `HF_HUB_DISABLE_XET` | (无) | 设 `1` 禁用 xet 加速(国内网络需要) |
| `MEDIA_TO_DOC_LOG_LEVEL` | `INFO` | 日志级别:`DEBUG` / `INFO` / `WARNING` / `ERROR` |

---

## 产物布局(W3-W8 稳定版)

```
<inbox 父目录>/                     ← 与视频同盘(可整盘复制 / 上传 / 丢知识库)
├── inbox/<课程名>/                ← 输入(视频 + 用户素材)
│   ├── 培训.mp4
│   ├── img/                       ← 关键帧(W1 frames stage)
│   └── ocr/                       ← OCR 文本(W2 ocr stage)
│
└── output/<课程名>/                ← 流水线产物(work 目录)
    ├── state.json                 ← 11 stage 调度状态(scheduler 真相)
    ├── memory/YYYY-MM-DD.md       ← LE 每 stage 一行
    ├── pipeline_run.json          ← LE 完整元数据(W8)
    ├── ERRORS.md                  ← 运行时错误(若有)
    ├── verify/
    │   └── verify.json            ← 4 项机器可验证检查结果
    └── chapters/
        └── raw/<视频同名>/        ← 最终讲义产物
            ├── <视频同名>.md          ← render 阶段产物
            ├── <视频同名>.html        ← render HTML
            ├── <视频同名>_cleaned.md  ← longdoc 净化稿
            ├── <视频同名>_final.html  ← 推荐分发(TOC + 锚点 + 内嵌 CSS)
            ├── chapter_01.md ...      ← draft 章节稿
            └── images/gen_*.png       ← SDXL AI 配图(相对路径)
```

整盘复制 `output/<课程名>/` 到任何电脑,讲义 + 图片全部相对路径,**零依赖**。

> **输出目录约定**:默认输出到 `<inbox 父目录>/output/<课程名>/`,
> 与视频同盘(便于整盘分发)。自定义用 `--work-dir`(CLI)或 `run_pipeline(work=...)`(Python API)。

---

## Loop Engineering 五层闭环(W8)

| 层 | 组件 | 职责 |
|---|---|---|
| **L1 执行** | `timed_stage(logger, stage)` 上下文管理器 | 每次 stage 自动计时 + 错误捕获 + 写入 memory |
| **L2 审核** | `gatekeeper_check(work)` | 4 项机器可验证(outputs_exist / chapters_complete / image_refs / html_structure) |
| **L3 沉淀** | `PipelineLogger` | 写 `memory/YYYY-MM-DD.md` + `pipeline_run.json`(可跨 run 聚合) |
| **L4 进化** | `post_pipeline_hook(work)` | Pattern-Key 重复 ≥ 3 次自动晋升到 `.learnings/ERRORS.md` |
| **L5 健康度** | `assess_llm_health(work_root)` + `list_runs(workspace_root)` | 跨 run LLM 失败率 + 推荐策略(switch_provider / reduce_chunk) |

设计文档:`_research/LE_DESIGN.md`(已落地 W8,W9+ 仅维护)。

---

## 文档导航

| 文档 | 受众 |
|---|---|
| [PRD.md](PRD.md) | 产品需求(用户场景 / 功能清单 / 验收) |
| [TDD.md](TDD.md) | 技术设计(架构 / 模块 / 接口) |
| [ROADMAP.md](ROADMAP.md) | 执行规划(阶段 / 里程碑 / 估算) |
| [CLAUDE.md](CLAUDE.md) | Claude 协作规则(项目级指引) |
| [task.md](task.md) | 活跃 todo |
| [docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md) | MCP 8 工具详细文档(W7 + W8) |
| [examples/cross_project_demo.py](examples/cross_project_demo.py) | 跨项目调用示例(W9) |
| [.learnings/LEARNINGS.md](.learnings/LEARNINGS.md) | W1-W8 best_practice 沉淀(W9 首批条目) |

---

## 路线图

| 阶段 | 内容 | 状态 |
|---|---|---|
| **Phase 0** | 项目骨架 + uv init + 首 commit | ✅ 完成 |
| **Phase 1** | 11 阶段核心流水线 | ✅ W1-W4 完成 |
| **Phase 2** | 端到端冒烟 | ✅ W5 完成 |
| **Phase 3** | LLM provider 抽象(ollama/anthropic/openai_compat) | ✅ W2 完成 |
| **Phase 4** | 跨项目可调用:CLI + MCP server + Python API | ✅ W6-W7 + W9 完成 |
| **Phase 5** | Loop Engineering 闭环 | ✅ W8 完成(482 测试) |
| **Phase 6** | 文档与示例 | ✅ W9 完成(508 测试) |
| **Phase 7** | v1.0 发布准备 | ⏳ 未来 |

完整规划见 [ROADMAP.md](ROADMAP.md)。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 包管理 | [uv](https://github.com/astral-sh/uv) |
| 语音转写 | Faster-Whisper large-v3(CUDA fp16 / CPU 兜底) |
| 关键帧 | PySceneDetect ContentDetector + pHash 去重 |
| OCR | RapidOCR(ONNX 本地推理) |
| LLM 默认 | Ollama + Qwen3-14B(`num_ctx=65536`) |
| AI 配图 | SDXL Base + Refiner(diffusers,可跳过) |
| 文档渲染 | jinja2 + markdown 库 + jieba(TOC + 锚点 + 内嵌 CSS) |
| CLI | Typer + Rich(JSON 输出绕开 markup) |
| MCP Server | mcp stdio JSON-RPC(W7 + W8 共 8 工具) |
| LE | PipelineLogger + Gatekeeper + 进化层(W8) |
| 客户端 UI(规划) | Tauri 2.x + React 18 + TypeScript |
| 安装器(规划) | NSIS 3.x + SignPath.io |

---

## 开发

### 跑测试

```bash
uv run pytest                          # 全量(508 用例,~5s)
uv run pytest tests/test_init.py -v    # 单文件
uv run pytest -k "test_lazy_import"    # 按关键字过滤

uv run ruff check src/ tests/          # lint
uv run ruff format src/ tests/         # 格式化(可选)
```

### 项目结构

```
media-to-doc/
├── src/media_to_doc/                  ← 主包
│   ├── __init__.py                    ← PEP 562 顶层 re-export(W9)
│   ├── cli.py                         ← mtd CLI 入口
│   ├── mcp_server.py                  ← mtd-mcp stdio server
│   ├── config.py / state.py / paths.py
│   ├── llm/                           ← LLM providers + health
│   ├── pipeline/                      ← 11 stage + runner
│   └── logger/                        ← LE 五层(W8)
├── tests/                             ← pytest 508 用例
├── examples/cross_project_demo.py    ← 跨项目 demo(W9)
├── docs/MCP_INTEGRATION.md
├── .learnings/                        ← LE 学习库
├── workspace/                         ← 默认 inbox / output
└── pyproject.toml                     ← uv 包元数据
```

### 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat(pipeline): 新增 imagegen provider
fix(llm): Ollama num_ctx 默认 65536
docs(readme): W9 — 文档完善 + Python API re-export
test(logger): 11 用例覆盖 gatekeeper image_refs
```

scope 候选:`pipeline` / `cli` / `mcp` / `llm` / `longdoc` / `imagegen` / `asr` /
`frames` / `ocr` / `chapters` / `verify` / `logger` / `learnings` / `docs` / `tests`

---

## 许可证

MIT License — 见 [LICENSE](LICENSE)。

完整免责声明:用户需自行确保上传音视频的版权合规,本项目仅作为内容整理工具,不对侵权内容负责。