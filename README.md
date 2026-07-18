# media-to-doc

> 把本地音视频(培训录像、讲座录音、运营课、电商课)一键转化为**带 AI 配图、可独立分发**的
> Markdown + HTML 讲义。

[![Status: WIP](https://img.shields.io/badge/status-WIP-yellow)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)]()

---

## 这是什么

`media-to-doc` 是一款 Windows 开源桌面工具,内置 LLM/SDXL 推理栈,把培训音视频自动转写、
校对、配图、编排,产出可分发、可独立阅读的讲座讲义(`.md` + `.html`)。

**核心特点**:

- **11 阶段流水线**:audio → asr → frames → ocr → asr_correct → chapters → draft → imagegen → render → longdoc → verify
- **本地优先**:默认完全离线,Ollama + Faster-Whisper + SDXL 全栈本地推理
- **可插拔 LLM**:支持 Ollama / Anthropic / OpenAI-compatible(MiniMax、DeepSeek、智谱、Moonshot、混元等)
- **跨项目可调用**:Python API + CLI(`mtd`)+ MCP server(供 Claude Desktop / Codex 原生集成)
- **自我进化**:内置 Loop Engineering 闭环,跑得越多、质量越好

---

## 5 分钟快速开始

> ⚠️ **当前状态:Phase 0 项目骨架已落地,核心流水线开发中(v0.1.0-dev)**
> 完整跑通示例视频需到 v1.0(预计 8 周)。当前可在干净 Python 3.11+ 环境跑通 CLI smoke test。

### 安装

```bash
# 前置依赖:Python 3.11+ / uv 0.11+ / ffmpeg 4+
pip install uv   # 如未安装
git clone https://github.com/media-to-doc/media-to-doc.git
cd media-to-doc
uv sync
```

### 验证安装

```bash
uv run mtd --version
# 期望输出: media-to-doc 0.1.0

uv run mtd --help
# 期望输出: mtd 命令帮助信息

uv run pytest
# 期望输出: smoke test 全过
```

### 跑一条流水线(v1.0 后可用)

```bash
# 把视频放到 inbox
cp "我的培训.mp4" workspace/inbox/我的培训/

# 跑完整 11 阶段
uv run mtd run workspace/inbox/我的培训/

# 中断后续跑
uv run mtd resume workspace/work/我的培训/

# 状态查询
uv run mtd status workspace/work/我的培训/
```

---

## 三种调用方式

### 1. CLI(终端用户)

```bash
mtd run <INBOX>           # 完整流水线
mtd resume <WORK>         # 续跑
mtd status <WORK>         # 进度
mtd list                  # 列出 inbox 课程
mtd doctor                # 系统诊断
mtd config get llm.model  # 配置查询
mtd mcp                   # 启动 MCP server
```

### 2. Python API(开发者)

```python
from media_to_doc import WorkflowConfig, run_pipeline

cfg = WorkflowConfig(llm_provider="ollama", imagegen_provider="skip")
result = run_pipeline(
    inbox=Path("workspace/inbox/course1"),
    work=Path("workspace/work/course1"),
    config=cfg,
)
print(f"Gatekeeper: {result.gatekeeper_passed}")
print(f"Stages: {result.quality['completed']}/{result.quality['total_stages']}")
```

### 3. MCP Server(Claude Desktop / Codex)

```json
// ~/.config/claude_desktop_config.json(Linux/Mac)
// %APPDATA%\Claude\claude_desktop_config.json(Windows)
{
  "mcpServers": {
    "media-to-doc": {
      "command": "uv",
      "args": ["--project", "F:/soft/00selfmade/media-to-doc", "run", "mtd-mcp"]
    }
  }
}
```

可用工具:`list_courses` / `run_pipeline` / `resume_pipeline` / `check_status` / `list_outputs` / `read_lecture`

---

## 产物布局

```
inbox/<课程>/
├── raw/
│   ├── <视频同名>.md              ← 原版讲义
│   ├── <视频同名>.html
│   ├── <视频同名>_cleaned.md      ← longdoc 净化稿
│   ├── <视频同名>_final.html      ← 推荐分发(带 TOC / 锚点 / 内嵌 CSS)
│   └── images/gen_*.png           ← SDXL AI 配图(相对路径)
├── img/                            ← 关键帧
└── ocr/                            ← 截图 OCR

work/<课程>/                        ← 中间产物(可断点续跑)
├── state.json
├── memory/YYYY-MM-DD.md            ← LE 每 stage 一行
├── pipeline_run.json               ← LE 完整元数据
└── ERRORS.md                       ← 运行时错误(若有)
```

整盘复制 `inbox/<课程>/` 到任何电脑,讲义 + 图片全部相对路径,**零依赖**。

---

## 文档导航

| 文档 | 受众 |
|---|---|
| [PRD.md](PRD.md) | 产品需求(用户场景 / 功能清单 / 验收) |
| [TDD.md](TDD.md) | 技术设计(架构 / 模块 / 接口) |
| [ROADMAP.md](ROADMAP.md) | 执行规划(阶段 / 里程碑 / 估算) |
| [CLAUDE.md](CLAUDE.md) | Claude 协作规则(项目级指引) |
| [task.md](task.md) | 活跃 todo |
| `docs/installation.md` | 用户:各 OS 安装步骤(v1.0 后) |
| `docs/mcp-integration.md` | 用户:Claude Desktop 集成(v1.0 后) |

---

## 路线图

| 阶段 | 内容 | 状态 |
|---|---|---|
| **Phase 0** | 项目骨架 + uv init + 首 commit | ✅ 当前 |
| **Phase 1** | 11 阶段核心流水线 | ⏳ W1-W4 |
| **Phase 2** | Tauri 客户端 UI | ⏳ W5-W8 |
| **Phase 3** | NSIS 安装器 + 配置向导 | ⏳ W6-W7 |
| **Phase 4** | MCP server + 集成文档 | ⏳ W7 |
| **Phase 5** | Loop Engineering 闭环 | ⏳ W7.5-W8 |
| **Phase 6** | v1.0 发布(5 渠道全发) | ⏳ W8 |

完整规划见 [ROADMAP.md](ROADMAP.md)。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 包管理 | [uv](https://github.com/astral-sh/uv) |
| 语音转写 | Faster-Whisper large-v3(CUDA fp16) |
| 关键帧 | PySceneDetect ContentDetector + pHash 去重 |
| OCR | RapidOCR(ONNX 本地推理) |
| LLM 默认 | Ollama + Qwen3-14B |
| AI 配图 | SDXL Base + Refiner(diffusers) |
| 文档渲染 | jinja2 + markdown 库 |
| CLI | Typer + Rich |
| MCP Server | mcp stdio JSON-RPC |
| 客户端 UI(规划) | Tauri 2.x + React 18 + TypeScript |
| 安装器(规划) | NSIS 3.x + SignPath.io |

---

## 许可证

MIT License — 见 [LICENSE](LICENSE)。

完整免责声明:用户需自行确保上传音视频的版权合规,本项目仅作为内容整理工具,不对侵权内容负责。
