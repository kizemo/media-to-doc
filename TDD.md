# media-to-doc — Technical Design Document (TDD)

> 版本:v1.0 · 日期:2026-07-17 · 状态:待评审
>
> 本文档定义 `media-to-doc` 的**技术架构、模块划分、数据流、接口规范、关键技术决策**。
> 产品需求见 `PRD.md`,执行节奏见 `ROADMAP.md`。

---

## 0. 文档元信息

| 项 | 值 |
|---|---|
| 项目代号 | media-to-doc |
| 文档版本 | v1.0 |
| 创建日期 | 2026-07-17 |
| 状态 | Draft |
| 关联文档 | `PRD.md`、`ROADMAP.md`、`CLAUDE.md`、`_research/PROJECT_DESCRIPTION.md` |

---

## 1. 技术选型总览

| 层 | 技术 | 理由 |
|---|---|---|
| **后端核心** | Python 3.11+ / uv | 参考实现已验证,生态最丰富,GPU 库支持好 |
| **包管理** | uv | 比 pip/poetry 快 10-100x,锁文件可靠 |
| **语音转写** | Faster-Whisper large-v3 | CTranslate2 后端,RTF 0.1x,准确率业内领先 |
| **关键帧** | PySceneDetect(ContentDetector) | 开源镜头切换检测事实标准 |
| **图像去重** | ImageHash(pHash) | 感知哈希,O(n) 去重 |
| **OCR** | RapidOCR(ONNX) | 离线推理,中文支持好,速度快 |
| **LLM 默认** | Ollama + Qwen3-14B | 本地最强开源中文模型,RTX 3090 跑得动 |
| **LLM 云端** | Anthropic / OpenAI / MiniMax / DeepSeek / 智谱 / Moonshot / 混元 / OpenRouter | 覆盖国内外主流 |
| **AI 配图** | SDXL Base + Refiner(diffusers) | 开源文生图最强基线 |
| **文档渲染** | jinja2 + markdown 库 + TOC + 锚点 + 内嵌 CSS | 纯 Python,跨平台 |
| **CLI** | Typer + Rich | 现代 Python CLI,自动 help,彩色输出 |
| **MCP Server** | mcp 库 + stdio JSON-RPC | Anthropic 官方协议 |
| **客户端 UI** | **Tauri 2.x + React 18 + TypeScript** | 安装包小(~10-30MB),启动快 |
| **UI 状态管理** | Zustand + TanStack Query | 轻量,适合 Tauri |
| **UI 组件** | shadcn/ui + Tailwind CSS | 现代,无障碍,可定制 |
| **UI 图表** | Recharts | 任务进度、模型统计 |
| **安装器** | **NSIS 3.x** | 用户确认;轻量、高度可定制;支持中文向导、注册表项、卸载、文件关联 |
| **代码签名** | SignPath.io(开源免费) | 给安装器 + 可执行文件签名,消除 SmartScreen 警告 |
| **CI/CD** | GitHub Actions(Windows + macOS + Linux runners) | 免费且成熟 |
| **发布渠道** | PyPI + GitHub Releases + WinGet + Scoop + Chocolatey | 覆盖全平台安装方式 |
| **国际化** | react-i18next + pybabel | 中英文切换 |
| **遥测** | opt-in,本地聚合,可选上传 | 隐私优先 |
| **测试** | pytest + Playwright(E2E UI) | 后端 + UI 全覆盖 |

---

## 2. 系统架构

### 2.1 总体架构图

```
┌──────────────────────────────────────────────────────────────────┐
│  Windows Desktop(用户机器)                                       │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Tauri Client (React + TypeScript)                         │ │
│  │  ├─ Dashboard / 任务页 / 设置页 / 集成页 / 预览页          │ │
│  │  └─ IPC → Tauri Rust Backend                              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↕ IPC                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Python Backend (Rust spawned subprocess)                  │ │
│  │  ├─ CLI (Typer): mtd run / resume / status / list / ...  │ │
│  │  ├─ MCP Server (stdio): 6 tools                           │ │
│  │  ├─ Pipeline (11 stages)                                  │ │
│  │  └─ System Service: scheduler / model manager / doctor    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↕ spawn                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  External Processes                                        │ │
│  │  ├─ ffmpeg.exe(音视频处理)                                │ │
│  │  ├─ ollama serve(LLM 推理)                                │ │
│  │  ├─ faster-whisper / rapidocr / diffusers(库内调用)        │ │
│  │  └─ (可选)云端 LLM HTTP 调用                              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Storage:                                                        │
│  ├─ %APPDATA%\media-to-doc\config.yaml                          │
│  ├─ %LOCALAPPDATA%\media-to-doc\logs\                           │
│  ├─ %LOCALAPPDATA%\media-to-doc\models\(HF 缓存)               │
│  ├─ %USERPROFILE%\.ollama\(Ollama 模型)                        │
│  └─ workspace\inbox\ + workspace\work\(用户指定)                │
└──────────────────────────────────────────────────────────────────┘
                              ↕ stdio / HTTP
┌──────────────────────────────────────────────────────────────────┐
│  External AI Services(可选)                                     │
│  ├─ Anthropic API (Claude)                                      │
│  ├─ OpenAI API (GPT)                                            │
│  ├─ MiniMax / DeepSeek / 智谱 / Moonshot / OpenRouter / ...      │
│  └─ 自定义 OpenAI-compatible endpoint                            │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 进程模型

| 进程 | 启动方式 | 生命周期 |
|---|---|---|
| **Tauri 客户端** | 桌面快捷方式 | 用户启动到关闭 |
| **mtd 后端(单任务)** | Tauri 启动时 spawn,或用户命令行 | 单个 pipeline run |
| **Ollama serve** | 安装时注册 Windows Service,开机自启 | 系统级常驻 |
| **MCP Server** | Claude Desktop 启动时 spawn | Claude Desktop 生命周期 |
| **ffmpeg** | 后端 subprocess per stage | 短任务 |
| **System Tray** | Tauri 内 | 客户端生命周期 |

### 2.3 关键设计原则

1. **后端可独立运行**:即使没有 Tauri 客户端,Python 后端 + CLI + MCP server 全部可用
2. **客户端是装饰**:Tauri 只是 UI,所有逻辑在后端,UI 坏了 CLI 仍能用
3. **local-first**:所有数据本地存储,云端 API 仅按需调用,网络断开不影响
4. **lazy load**:重依赖(torch / diffusers / faster-whisper / rapidocr)按需 import,启动 < 1 秒
5. **可恢复**:每 stage 落盘 + state.json + resume 命令

---

## 3. 目录结构

```
F:\soft\00selfmade\media-to-doc\
├── CLAUDE.md
├── README.md                       # 用户文档
├── PRD.md                          # 产品需求
├── TDD.md                          # 本文件
├── ROADMAP.md                      # 项目执行规划
├── CONTRIBUTING.md                 # 贡献指南
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── LICENSE                         # MIT
├── CHANGELOG.md
├── pyproject.toml                  # Python 包元数据
├── uv.lock
├── .gitignore
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                  # pytest + ruff + mypy
│   │   ├── build-windows.yml       # NSIS 打包
│   │   ├── build-macos.yml
│   │   ├── build-linux.yml
│   │   └── release.yml             # 发布到 PyPI + GitHub Release
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── installer/
│   ├── media-to-doc.nsi            # NSIS 主脚本
│   ├── pages/                      # 自定义 UI 页面
│   ├── assets/                     # 图标、banners
│   └── build.ps1                   # NSIS 构建脚本
├── src/
│   └── media_to_doc/               # Python 包
│       ├── __init__.py             # 顶层 re-export + lazy import
│       ├── cli.py                  # Typer CLI
│       ├── mcp_server.py           # MCP stdio server
│       ├── config.py               # 配置管理
│       ├── paths.py                # 路径常量
│       ├── state.py                # STAGE_ORDER + State 持久化
│       ├── system/                 # 系统检测与管理
│       │   ├── __init__.py
│       │   ├── doctor.py           # 系统诊断
│       │   ├── gpu.py              # GPU / 显存检测
│       │   ├── models.py           # 模型下载 / 管理
│       │   ├── ollama.py           # Ollama 安装 / 启动
│       │   └── service.py          # Windows Service 注册
│       ├── pipeline/               # 11 阶段流水线
│       │   ├── __init__.py
│       │   ├── runner.py           # 编排器
│       │   ├── audio.py
│       │   ├── asr.py
│       │   ├── frames.py
│       │   ├── ocr.py
│       │   ├── asr_correct.py
│       │   ├── chapters.py
│       │   ├── draft.py
│       │   ├── imagegen.py
│       │   ├── render.py
│       │   ├── longdoc.py
│       │   └── verify.py
│       ├── llm/                    # LLM provider 抽象
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── ollama.py
│       │   ├── anthropic.py
│       │   ├── openai_compat.py
│       │   ├── models.py           # 模型列表自动发现
│       │   └── health.py           # LLM 健康度评估
│       ├── logger/                 # Loop Engineering 沉淀
│       │   ├── __init__.py
│       │   ├── pipeline_logger.py
│       │   ├── gatekeeper.py
│       │   └── learnings.py        # .learnings/ 管理
│       └── utils/
│           ├── __init__.py
│           ├── ffmpeg_utils.py
│           ├── hash_utils.py
│           └── progress.py
├── ui/                             # Tauri + React 客户端
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── src/                        # React 源码
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Tasks.tsx
│   │   │   ├── Settings.tsx
│   │   │   ├── Integration.tsx
│   │   │   ├── Preview.tsx
│   │   │   └── Learnings.tsx
│   │   ├── components/
│   │   ├── ipc/                    # Tauri IPC 绑定
│   │   ├── i18n/
│   │   └── stores/
│   ├── src-tauri/                  # Rust 后端
│   │   ├── Cargo.toml
│   │   ├── tauri.conf.json
│   │   ├── icons/
│   │   └── src/
│   │       ├── main.rs             # spawn mtd 后端
│   │       ├── tray.rs             # 系统托盘
│   │       └── ipc.rs              # IPC handlers
│   └── tests/                      # Playwright E2E
├── tests/                          # pytest
│   ├── conftest.py
│   ├── test_cli.py
│   ├── test_pipeline/
│   │   ├── test_audio.py
│   │   ├── test_asr.py
│   │   ├── test_frames.py
│   │   ├── test_ocr.py
│   │   ├── test_asr_correct.py
│   │   ├── test_chapters.py
│   │   ├── test_draft.py
│   │   ├── test_imagegen.py
│   │   ├── test_render.py
│   │   ├── test_longdoc.py
│   │   └── test_verify.py
│   ├── test_llm/
│   ├── test_logger/
│   ├── test_mcp_server.py
│   └── test_system/
├── docs/                           # 用户文档
│   ├── installation.md
│   ├── quickstart.md
│   ├── cli.md
│   ├── api.md
│   ├── providers.md
│   ├── mcp-integration.md
│   └── troubleshooting.md
├── examples/
│   ├── basic/
│   └── advanced/
├── .learnings/                     # 项目级学习库(git 追踪)
│   ├── LEARNINGS.md
│   └── ERRORS.md
├── workspace/                      # 运行时数据(gitignore)
│   ├── inbox/
│   └── work/
└── _research/                      # 研究材料(gitignore)
    └── PROJECT_DESCRIPTION.md
```

---

## 4. 模块设计

### 4.1 后端核心模块

#### 4.1.1 `cli.py` — Typer CLI 入口

```python
# 伪代码
app = typer.Typer()

@app.command()
def run(inbox: Path, workspace: Path = None, llm: str = None, imagegen: str = None):
    """完整流水线"""
    ...

@app.command()
def resume(work: Path):
    """续跑中断的流水线"""
    ...

@app.command()
def status(work: Path):
    """进度"""
    ...

@app.command()
def list_(workspace: Path):
    """列出 inbox 课程"""
    ...

@app.command()
def doctor():
    """系统诊断"""
    ...

@app.command()
def config(action: str, key: str = None, value: str = None):
    """配置管理"""
    ...

@app.command()
def model(action: str, name: str = None):
    """模型管理"""
    ...

@app.command()
def mcp():
    """启动 MCP server(stdio)"""
    ...
```

设计要点:
- 所有命令支持 `--json` 输出,供 UI 调用
- 进度通过 stdout JSON 行输出(`{"stage": "asr", "progress": 0.4}`)
- 错误返回非零退出码 + 结构化 error JSON

#### 4.1.2 `mcp_server.py` — MCP stdio server

```python
# 伪代码
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("media-to-doc")

@app.list_tools()
async def list_tools():
    return [
        Tool(name="list_courses", description="...", inputSchema={...}),
        Tool(name="run_pipeline", ...),
        ...
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    # 调用 Python 后端
    ...
```

6 个工具:`list_courses` / `run_pipeline` / `resume_pipeline` / `check_status` / `list_outputs` / `read_lecture`

#### 4.1.3 `pipeline/runner.py` — 流水线编排器

```python
# 伪代码
STAGE_ORDER = [
    "audio", "asr", "frames", "ocr", "asr_correct",
    "chapters", "draft", "imagegen", "render", "longdoc", "verify"
]

async def run_pipeline(inbox: Path, work: Path, cfg: WorkflowConfig) -> PipelineResult:
    state = State.load(work / "state.json")
    logger = PipelineLogger(work)

    for stage in STAGE_ORDER:
        if state.completed(stage):
            continue  # 跳过已完成
        with timed_stage(logger, stage) as ctx:
            try:
                func = STAGE_FUNCS[stage]
                await func(inbox, work, cfg, ctx)
                state.mark(stage, "completed")
            except Exception as e:
                state.mark(stage, "failed", error=str(e))
                logger.error(e, stage)
                raise

    gatekeeper_result = gatekeeper_check(inbox, work)
    pipeline_run = logger.finalize()
    post_pipeline_hook(work, project_root)
    return PipelineResult(state, gatekeeper_result, pipeline_run)
```

设计要点:
- 同步 stage(`audio`/`asr`/`frames`/`ocr`/`asr_correct`/`chapters`/`draft`/`imagegen`/`render`/`longdoc`/`verify`)用 `asyncio.to_thread` 包装
- 每个 stage 可独立 timeout,默认 30 分钟
- 失败自动写 `ERRORS.md`,不中断整个 process

#### 4.1.4 `system/doctor.py` — 系统诊断

```python
# 伪代码
@dataclass
class SystemReport:
    os: OSInfo
    cpu: CPUInfo
    gpu: GPUInfo | None
    ram_gb: float
    disk_free_gb: float
    python: PythonInfo
    ffmpeg: bool
    ollama: OllamaStatus
    models: list[ModelInfo]

    def recommended_profile(self) -> Literal["full", "standard", "lightweight"]:
        """根据配置推荐部署级别"""
        if self.gpu and self.gpu.vram_gb >= 12 and self.disk_free_gb >= 30:
            return "full"
        elif self.gpu and self.gpu.vram_gb >= 6:
            return "standard"
        else:
            return "lightweight"
```

#### 4.1.5 `system/ollama.py` — Ollama 管理

```python
# 伪代码
class OllamaManager:
    def is_installed(self) -> bool: ...
    def install(self) -> bool: ...        # winget / 直接下载
    def is_running(self) -> bool: ...     # check 127.0.0.1:11434
    def start(self, port: int = 11434) -> bool: ...
    def register_service(self) -> bool: ...  # Windows Service,开机自启
    def pull_model(self, name: str, progress_cb) -> bool: ...
    def list_models(self) -> list[str]: ...
```

#### 4.1.6 `system/models.py` — 模型管理

```python
# 伪代码
class ModelManager:
    def list_available(self, category: Literal["asr", "ocr", "llm", "imagegen"]) -> list[ModelInfo]: ...
    def download(self, model_id: str, progress_cb) -> Path: ...  # 断点续传 + sha256 校验
    def is_cached(self, model_id: str) -> bool: ...
    def delete(self, model_id: str) -> bool: ...
    def get_path(self, model_id: str) -> Path: ...  # 跨平台:HuggingFace / Ollama / 自定义
```

### 4.2 LLM Provider 抽象

#### 4.2.1 接口定义

```python
# llm/base.py
from abc import ABC, abstractmethod
from typing import Iterator

class BaseLLMProvider(ABC):
    @abstractmethod
    def name(self) -> str: ...
    
    @abstractmethod
    def list_models(self) -> list[ModelInfo]: ...
    
    @abstractmethod
    def chat(self, prompt: str, *, model: str | None = None, 
             temperature: float = 0.3, max_tokens: int = 4096,
             stream: bool = False) -> str | Iterator[str]: ...
    
    @abstractmethod
    def health(self) -> HealthStatus:
        """最近 20 次调用成功率"""
        ...
```

#### 4.2.2 Provider 注册表

```python
# llm/__init__.py
PROVIDERS: dict[str, type[BaseLLMProvider]] = {
    "ollama": OllamaProvider,
    "anthropic": AnthropicProvider,
    "openai_compatible": OpenAICompatProvider,
}

def get_provider(name: str, config: dict) -> BaseLLMProvider:
    cls = PROVIDERS[name]
    return cls(**config)
```

#### 4.2.3 Anthropic Provider

```python
# llm/anthropic.py
class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.environ["ANTHROPIC_API_KEY"]
        self.client = anthropic.Anthropic(api_key=self.api_key, base_url=base_url)
    
    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(id="claude-opus-4-7", display_name="Claude Opus 4.7", tier="premium"),
            ModelInfo(id="claude-sonnet-4-6", display_name="Claude Sonnet 4.6", tier="standard"),
            ModelInfo(id="claude-haiku-4-5", display_name="Claude Haiku 4.5", tier="fast"),
        ]
```

#### 4.2.4 OpenAI Compatible Provider

```python
# llm/openai_compat.py
class OpenAICompatProvider(BaseLLMProvider):
    PRESETS = {
        "minimax": ("https://api.minimaxi.com/v1", ["MiniMax-Text-01", "abab6.5s-chat"]),
        "deepseek": ("https://api.deepseek.com/v1", ["deepseek-chat", "deepseek-coder"]),
        "zhipu": ("https://open.bigmodel.cn/api/paas/v4", ["glm-4", "glm-4-flash"]),
        "moonshot": ("https://api.moonshot.cn/v1", ["moonshot-v1-8k", "moonshot-v1-32k"]),
        "openrouter": ("https://openrouter.ai/api/v1", []),  # 自动拉取
        "dashscope": ("https://dashscope.aliyuncs.com/compatible-mode/v1", ["qwen-plus", "qwen-turbo"]),
        "hunyuan": ("https://hunyuan.tencent.com/v1", ["hunyuan-pro"]),
    }
    
    def __init__(self, base_url: str, api_key: str, model: str | None = None):
        self.client = openai.OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        # 自动探测模型列表(若 endpoint 支持)
        try:
            self._models = self.client.models.list()
        except:
            self._models = []
```

设计要点:
- 自动模型发现:输入 URL + Key 后,自动 GET `/v1/models` 拉取可选模型
- 预设厂商一键切换
- 用户自定义 URL 也能跑

### 4.3 Tauri 客户端

#### 4.3.1 IPC 接口(Rust ↔ Python)

```rust
// src-tauri/src/main.rs
#[tauri::command]
async fn run_pipeline(inbox: String, options: PipelineOptions) -> Result<String, String> {
    // spawn mtd run <inbox> --json
    // parse stdout JSON
}

#[tauri::command]
async fn list_courses(workspace: String) -> Result<Vec<Course>, String> { ... }

#[tauri::command]
async fn doctor() -> Result<SystemReport, String> { ... }

#[tauri::command]
async fn install_profile(profile: String) -> Result<InstallProgress, String> { ... }

#[tauri::command]
async fn set_llm_config(provider: String, config: Value) -> Result<Value, String> { ... }
```

#### 4.3.2 React 路由

```tsx
// ui/src/App.tsx
<Router>
  <Route path="/" element={<Dashboard />} />
  <Route path="/tasks" element={<Tasks />} />
  <Route path="/settings" element={<Settings />} />
  <Route path="/integration" element={<Integration />} />
  <Route path="/preview/:courseId" element={<Preview />} />
  <Route path="/learnings" element={<Learnings />} />
</Router>
```

#### 4.3.3 关键 UI 组件

| 组件 | 功能 | 依赖 |
|---|---|---|
| `<SystemDoctor>` | GPU/显存/磁盘/网络展示 + 推荐部署级别 | doctor() IPC |
| `<InstallProfile>` | 完整/标准/轻量 三选一 + 模型下载进度 | install_profile() IPC |
| `<TaskList>` | 任务列表 + 状态 + 进度 + 操作 | list_courses() + check_status() |
| `<TaskNew>` | 拖拽视频 / 选文件夹 / 选已有 | run_pipeline() |
| `<LlmConfig>` | Provider 选择 + Key 输入 + 模型自动拉取 | set_llm_config() |
| `<IntegrationPage>` | Claude Desktop JSON + Codex JSON 一键复制 + 教程 | static |
| `<LecturePreview>` | 嵌入 HTML 预览 + 编辑 | 静态资源 |
| `<LearningsView>` | LEARNINGS.md / ERRORS.md 可视化 | 读 workspace |

### 4.4 NSIS 安装器

#### 4.4.1 安装器脚本要点(`installer/media-to-doc.nsi`)

```nsi
; 安装器主要步骤:
; 1. 欢迎页(品牌 + License)
; 2. 许可协议(MIT)
; 3. 安装路径(默认 C:\Program Files\media-to-doc)
; 4. 系统检测(doctor):
;    - 检测 GPU/显存/磁盘
;    - 显示推荐部署级别
;    - 用户选择 full/standard/lightweight
; 5. 组件选择:
;    [x] Core (mtd + CLI + MCP, 必需)
;    [x] Ollama(default on)
;    [ ] qwen3:14b(default off, 需 9GB)
;    [ ] SDXL Base(default off, 需 6GB)
;    [ ] SDXL Refiner(default off, 需 6GB)
;    [x] Desktop shortcut
;    [x] Add to PATH
;    [x] Register file association(.mp4 .mp3 → mtd)
;    [x] System tray
; 6. 下载进度页(显示模型下载)
; 7. 安装中页
; 8. 完成页(打开客户端 / 启动 Ollama / 跳到 README)

; 卸载步骤:
; - 关闭 mtd / ollama
; - 移除注册表项
; - 移除 PATH
; - 移除文件关联
; - 询问是否保留 workspace/(默认保留)
; - 询问是否保留模型(默认保留,可减少下次安装时间)
```

#### 4.4.2 文件结构

```
C:\Program Files\media-to-doc\
├── mtd.exe                    # PyInstaller 打包的 CLI 入口
├── mtd-mcp.exe                # MCP server
├── media-to-doc.exe           # Tauri 客户端
├── python311.dll              # 嵌入式 Python
├── _internal\                 # Python 依赖
├── bin\ffmpeg.exe             # ffmpeg 可执行
├── LICENSE
├── README.md
└── uninstall.exe              # NSIS 卸载器

C:\ProgramData\media-to-doc\   # 共享数据(只读)
├── models\                    # 共享模型缓存(可选)
└── ollama\                    # Ollama 安装

%APPDATA%\media-to-doc\
├── config.yaml                # 用户配置
├── state.json                 # 全局状态
└── workspace\                 # 用户数据(可改路径)
    ├── inbox\
    └── work\

%LOCALAPPDATA%\media-to-doc\
├── logs\                      # 日志
├── cache\                     # HF 模型缓存
└── .learnings\                # 项目级学习库
```

#### 4.4.3 代码签名

- 用 SignPath.io(开源免费)给 NSIS 安装器签名
- `installer/sign.sh` 调用 signpath-cli 上传 → 等待签名 → 下载 → 集成到 release

### 4.5 Loop Engineering 沉淀层

> **设计依据**:`_research/LE_KEYPOINTS.md`(基于 aiec.fun 两篇文章)
> **详细设计**:`_research/LE_DESIGN.md`
> **L1+L2 原型**:`_research/le_prototype/`(23 测试全过)

#### 4.5.1 LE 五层模型实现

| 层 | 模块 | 接口 | 文件 |
|---|---|---|---|
| **L1 执行层** | `timed_stage()` | 上下文管理器,自动捕获耗时/异常/输出 | `logger/pipeline_logger.py` |
| **L2 审核层** | `gatekeeper_check()` | 返回 `GatekeeperResult(ok, issues)`,4 项检查 | `logger/gatekeeper.py` |
| **L3 沉淀层** | `PipelineLogger` | 写 `memory/YYYY-MM-DD.md` + `pipeline_run.json` | `logger/pipeline_logger.py` |
| **L4 进化层** | `post_pipeline_hook()` + `escalate_recurring_errors()` + `assess_llm_health()` | Pattern-Key 聚合 + 晋升 + 健康度 | `logger/learnings.py` |
| **L5 编排层** | `run_pipeline()` + CLI + MCP | 串起 L1-L4 | `pipeline/runner.py` + `cli.py` + `mcp_server.py` |

#### 4.5.2 Memory 三层

| 层 | 实现 | 路径 |
|---|---|---|
| **即时记忆** | `PipelineLogger.append_stage()` | `workspace/work/<course>/memory/YYYY-MM-DD.md` |
| **短期记忆** | `pipeline_run.json` + `ERRORS.md` | `workspace/work/<course>/` |
| **长期记忆** | `.learnings/LEARNINGS.md` + `.learnings/ERRORS.md` | `<project_root>/.learnings/` |

#### 4.5.3 关键接口(已原型验证)

```python
# pipeline_logger.py
@dataclass
class StageRecord:
    stage: str
    started_at: str  # ISO
    finished_at: str | None
    duration_seconds: float
    status: str  # "running" | "completed" | "failed" | "skipped"
    error: str | None = None
    output_paths: list[str]
    metrics: dict[str, Any]

@dataclass
class PipelineRun:
    course: str
    started_at: str
    finished_at: str | None
    duration_seconds: float
    stages: list[StageRecord]
    quality: dict[str, Any]  # total_stages, completed, failed, completion_rate
    llm_health: dict[str, Any]
    gatekeeper_passed: bool

class PipelineLogger:
    def __init__(self, work_dir: Path, course: str): ...
    def append_stage(self, record: StageRecord) -> None: ...
    def write_error(self, stage: str, exc: BaseException) -> str: ...  # returns Pattern-Key
    def finalize(self, gatekeeper_result, llm_health) -> PipelineRun: ...

@contextmanager
def timed_stage(logger: PipelineLogger, stage: str) -> Iterator[StageRecord]: ...

# gatekeeper.py
@dataclass
class GatekeeperResult:
    ok: bool
    issues: list[str]
    checks_passed: list[str]
    checks_failed: list[str]

def gatekeeper_check(inbox: Path, work: Path) -> GatekeeperResult:
    """4 项机器可验证检查:
    1. lecture.md 存在 + 非空(>= 100 bytes)
    2. H1 >= 1, H2 >= 3
    3. lecture_final.html 存在 + >= 1000 bytes
    4. image_refs 全部存在
    """

# learnings.py
def write_runtime_error(work: Path, stage: str, exc: BaseException) -> str: ...
def escalate_recurring_errors(work_root: Path, learnings_root: Path, threshold: int = 3) -> list[str]:
    """幂等:已存在的 Pattern-Key 不会重复写入"""
def assess_llm_health(work_root: Path, last_n: int = 20) -> dict:
    """返回 LLM 失败率 + 推荐策略"""
def post_pipeline_hook(work: Path, project_root: Path) -> dict: ...
def find_known_pattern_keys(learnings_root: Path) -> set[str]: ...
```

#### 4.5.4 Pattern-Key 设计

**格式**:`ShortType:keyword`(例:`Connection:ollama` / `OutOfMemory:whisper`)

- `ShortType` = 异常类型去掉 "Error" 后缀
- `keyword` = 异常消息的第一个 token(转小写)
- 同根因异常产生相同 key(消息差异不影响)

#### 4.5.5 原型验证

`_research/le_prototype/` 23 测试全过:

- `TestPipelineLogger`:5 测试(初始化/append/error/finalize/Pattern-Key)
- `TestTimedStage`:3 测试(成功/失败/异常传递)
- `TestGatekeeper`:5 测试(全部通过/缺 md/章节少/缺 html/缺图片)
- `TestLearnings`:8 测试(写错误/低于阈值/晋升/幂等/查找/健康度/钩子)
- `TestRunPipelineEnd2End`:2 测试(成功路径/失败路径)

#### 4.5.6 Phase 5 迁移清单

1. 复制 `pipeline_logger.py` / `gatekeeper.py` / `learnings.py` 到 `src/media_to_doc/logger/`
2. 替换 mock stage 为真实 11 stage 函数
3. 接入 `cli.py` (`mtd run` 触发 `run_pipeline`)
4. Tauri UI 显示 `pipeline_run.json`
5. MCP 暴露 `get_run_metrics()` + `list_runs()`
6. 补 LEARNINGS.md L0/L1/L2 规范条目

---

## 5. 数据流

### 5.1 端到端数据流

```
用户输入:mp4 文件
    ↓
[1. audio] ffmpeg 抽音 → wav(work/asr/audio.wav)
    ↓
[2. asr] Faster-Whisper → transcript.jsonl(带时间戳)
    ↓
[3. frames] PySceneDetect + pHash → frame_*.jpg(inbox/img/)
    ↓
[4. ocr] RapidOCR → frame_*.txt(inbox/ocr/)
    ↓
[5. asr_correct] OCR×ASR 对齐 → corrections.json
    ↓
[6. chapters] LLM → chapters.json + chapter_NN.md
    ↓
[7. draft] LLM 模板 → 完整 draft.md
    ↓
[8. imagegen] SDXL Base+Refiner → gen_*.png(raw/<stem>/images/)
    ↓
[9. render] jinja2 拼装 → raw/<stem>.md + raw/<stem>.html
    ↓
[10. longdoc] 借鉴 long-doc-processor → raw/<stem>_cleaned.md + raw/<stem>_final.html
    ↓
[11. verify] gatekeeper → verify.json
    ↓
[LE] logger 沉淀 + learnings 晋升
    ↓
产物交付:用户可在浏览器打开 raw/<stem>_final.html,产物目录可整盘复制
```

### 5.2 配置数据流

```
%APPDATA%\media-to-doc\config.yaml
├── llm:
│   ├── provider: ollama  # ollama | anthropic | openai_compatible
│   ├── model: qwen3:14b
│   ├── fallback_providers: [anthropic]  # 主 provider 失败时降级
│   └── providers:
│       ├── ollama: { base_url: http://127.0.0.1:11434 }
│       ├── anthropic: { api_key: sk-ant-... }  # 加密存储
│       └── minimax: { base_url: https://api.minimaxi.com/v1, api_key: ... }
├── imagegen:
│   ├── provider: local_sdxl  # local_sdxl | skip
│   ├── base_model: stabilityai/stable-diffusion-xl-base-1.0
│   ├── refiner_model: stabilityai/stable-diffusion-xl-refiner-1.0
│   └── steps: 30
├── paths:
│   ├── workspace: %USERPROFILE%\media-to-doc-workspace
│   └── models_cache: %LOCALAPPDATA%\media-to-doc\cache
├── pipeline:
│   ├── default_chunk_size: 15000  # CJK chars
│   ├── default_ocr_threshold: 0.5
│   ├── default_asr_window_seconds: 8
│   └── longdoc:
│       ├── max_chunk_size: 15000
│       └── provider: ollama  # 可独立于主 LLM
├── system:
│   ├── install_profile: full  # full | standard | lightweight
│   ├── ollama_service: true
│   └── telemetry: false  # opt-in
└── ui:
    ├── language: zh-CN
    └── theme: auto  # auto | light | dark
```

API Key 加密存储:
- Windows DPAPI(user-scoped)
- 不上传,仅本地解密

### 5.3 状态数据流

```
work/<course>/state.json
{
  "course": "达摩盘人货场自检优化-2026-07-15",
  "stages": {
    "audio": {"status": "completed", "ts": "2026-07-15T10:30:00"},
    "asr": {"status": "completed", "ts": "..."},
    "frames": {"status": "in_progress", "ts": "..."},
    ...
  },
  "current_stage": "frames",
  "started_at": "...",
  "updated_at": "..."
}
```

---

## 6. 接口规范

### 6.1 CLI 接口

```
mtd <command> [options]

Commands:
  mtd run <INBOX>         完整流水线
    --workspace PATH       workspace 根目录
    --llm PROVIDER         LLM provider 覆盖
    --imagegen PROVIDER    imagegen provider 覆盖
    --no-longdoc           跳过 longdoc 阶段
    --json                 JSON 输出(供 UI)

  mtd resume <WORK>        续跑
  mtd status <WORK>        进度
  mtd list                 列出 inbox 课程
    --workspace PATH

  mtd doctor               系统诊断
  mtd config               配置
    get KEY
    set KEY VALUE
    edit                   打开编辑器
    path                   配置文件路径

  mtd model                模型管理
    list                   列出已下载
    download MODEL         下载
    delete MODEL           删除
    clean                  清理未用模型

  mtd mcp                  启动 MCP server(stdio)

  mtd version              版本
  mtd update               自更新
  mtd --help
```

### 6.2 Python API

```python
from media_to_doc import (
    WorkflowConfig, WorkspacePaths, State, STAGE_ORDER,
    prepare_audio, transcribe, extract_keyframes, run_ocr,
    correct_asr, split_chapters, generate_drafts,
    generate_images, render_outputs, render_html,
    process_long_doc, render_final_html, verify,
    PipelineLogger, gatekeeper_check, post_pipeline_hook,
    assess_llm_health, list_providers, get_provider,
    SystemReport, doctor,
)
```

### 6.3 MCP 工具

| 工具 | 输入 | 输出 |
|---|---|---|
| `list_courses(workspace_root)` | workspace_root: string | `[{name, video_count, status}]` |
| `run_pipeline(inbox_dir, workspace_root?)` | inbox_dir, workspace_root? | `{ok, completed, current_stage, last_error?}` |
| `resume_pipeline(work_dir)` | work_dir | `{ok, completed, current_stage}` |
| `check_status(work_dir)` | work_dir | `{stage, progress, started_at, updated_at}` |
| `list_outputs(inbox_dir)` | inbox_dir | `[{path, type, size}]` |
| `read_lecture(inbox_dir, version, fmt)` | inbox_dir, version, fmt | `{content}` |

---

## 7. 关键技术决策

### 7.1 决策记录(ADR 摘要)

| 决策 ID | 决策 | 选项 | 选择 | 原因 |
|---|---|---|---|---|
| ADR-001 | UI 技术栈 | Tauri / Electron / PyQt / Web | **Tauri** | 安装包小,启动快,跨平台潜力 |
| ADR-002 | 开源协议 | MIT / Apache 2.0 / AGPL / BSL | **MIT** | 最宽松,生态最广 |
| ADR-003 | Windows 安装器 | Inno Setup / MSI / NSIS / PyInstaller 自解压 | **NSIS** | 用户选择;轻量、高度可定制、支持中文向导 |
| ADR-004 | 包格式 | wheel / exe / MSI | **exe(NSIS) + wheel(PyPI)** | 双渠道覆盖 |
| ADR-005 | 默认 LLM | Ollama Qwen3-14B | 同左 | 本地最强中文模型 |
| ADR-006 | 默认 imagegen | SDXL Base + Refiner | 同左 | 业界基线 |
| ADR-007 | LLM 云端协议 | OpenAI compatible | **是** | 覆盖国内外所有主流 |
| ADR-008 | MCP 通信 | stdio / HTTP | **stdio** | Anthropic 官方推荐 |
| ADR-009 | 持久化 | SQLite / YAML / JSON | **YAML(配置) + JSON(状态)** | 用户可手编 |
| ADR-010 | API Key 存储 | 明文 / DPAPI / keyring | **DPAPI(Windows) + keyring** | 平台原生 |
| ADR-011 | 后端进程模型 | 单进程多 stage / 多进程 | **单进程 + async** | 简单,IPC 易 |
| ADR-012 | 升级策略 | 手动 / 自动 | **手动 + 提示** | 用户可控 |
| ADR-013 | 遥测 | opt-in / opt-out / 无 | **opt-in,默认关闭** | 隐私优先 |
| ADR-014 | 国际化 | 单语 / 多语 | **中英双语(i18n)** | 用户群决定 |
| ADR-015 | 文件命名 | snake_case / kebab-case | **snake_case(Python)/ kebab-case(UI)** | 语言习惯 |
| ADR-016 | 包名 | `media_to_doc`(Python) / `media-to-doc`(UI/PyPI) | 双名 | 平台习惯 |

### 7.2 关键技术挑战与缓解

#### 挑战 1:NSIS + Python 嵌入的体积控制

- 嵌入式 Python 311 含 stdlib ≈ 15MB
- PyTorch(SDXL 必需)≈ 800MB
- diffusers + transformers + accelerate + safetensors ≈ 2GB
- **解决**:模型不进安装包,安装后按 profile 按需下载;core 安装包目标 < 80MB

#### 挑战 2:Tauri Rust 工具链 Windows 编译

- 首次冷编译 5-10 分钟,CI 上 windows-latest 缓存可能失效
- **解决**:GitHub Actions windows-latest + `swatinem/rust-cache@v2`

#### 挑战 3:SDXL 在不同 GPU 上的兼容性

- RTX 3090 / 4090:✅ 全功能
- RTX 3060(8GB):⚠️ 需启用 attention slicing
- AMD GPU:⚠️ diffusers 支持 ROCm 但 Ollama 不支持
- 无 GPU:❌ 必须云端或 skip
- **解决**:doctor 报告给推荐 profile,自动选最佳实现

#### 挑战 4:长视频(>3 小时)的内存压力

- Faster-Whisper 大视频可能 OOM
- **解决**:自动切片 + 流式处理;视频 > 30 分钟时分片

#### 挑战 5:Claude Desktop MCP 协议版本演进

- 当前 2024-2025 协议迭代频繁
- **解决**:锁版本 + 关注 Anthropic 公告 + 半年一次协议升级 PR

---

## 8. 安全与隐私

### 8.1 数据本地化

- 所有用户数据(`workspace/`、`config.yaml`、模型缓存)默认本地
- 云端 API 调用**必须**用户显式配置 API key
- API key 用 Windows DPAPI 加密
- 遥测**完全 opt-in**,默认关闭

### 8.2 网络访问清单

| 行为 | 出站 | 入站 | 用户可关闭 |
|---|---|---|---|
| Ollama 本地推理 | - | 127.0.0.1:11434 | - |
| Faster-Whisper 模型下载 | huggingface.co | - | ✅ |
| SDXL 模型下载 | huggingface.co | - | ✅ |
| LLM 云端调用(若启用) | API endpoint | - | ✅(per provider) |
| 遥测(opt-in) | telemetry.media-to-doc.org | - | ✅ |
| 更新检查 | github.com/api | - | ✅ |

### 8.3 沙箱

- Python 子进程只读 `workspace/`
- Tauri 后端对文件系统访问限制在 `workspace/` + 配置目录
- WebView 禁用 `nodeIntegration`,启用 `contextIsolation`
- CSP 头严格限制

### 8.4 凭据处理

- API key **绝不**写入日志
- 配置文件不含明文 key,只引用加密 blob
- 卸载时不删除用户的 `workspace/`,但加密 blob 销毁(用户需重新配置)

---

## 9. 性能与可靠性

### 9.1 性能目标

| 场景 | 目标 |
|---|---|
| 应用冷启动 | < 3 秒 |
| 应用热启动 | < 1 秒 |
| `mtd doctor` | < 5 秒 |
| `mtd run` 1.5 小时视频 | < 30 分钟(完整流水线,RTX 3090) |
| ASR(Faster-Whisper large-v3) | RTF ≤ 0.1(10 分钟出 1.5 小时稿) |
| LLM 章节切分(qwen3:14b) | 90-300 秒/课程(取决于章节数) |
| SDXL Base+Refiner | 30-60 秒/张 |
| Longdoc 净化 | 60-180 秒/万字 |

### 9.2 可靠性设计

- **幂等**:每个 stage 多次执行结果一致(state.json 跟踪)
- **断点续跑**:每个 stage 完成后立即落盘
- **失败重试**:网络错误 / OOM 自动重试 2 次
- **健康检查**:`mtd doctor` 检查所有依赖
- **优雅降级**:重依赖失败时跳过并标注

### 9.3 可观测性

- 每个 stage 实时进度(`memory/YYYY-MM-DD.md`)
- 每个 pipeline run 完整元数据(`pipeline_run.json`)
- LLM 调用 token 计数 + 延迟 + 失败率
- 错误日志结构化,含 stage / traceback / 配置快照

---

## 10. 测试策略

### 10.1 测试金字塔

```
        ┌─────────┐
        │  E2E    │  5-10 用例(Playwright + Tauri)
        ├─────────┤
        │ 集成测试 │  30-50 用例(mock 外部依赖)
        ├─────────┤
        │ 单元测试 │  100+ 用例(纯函数)
        └─────────┘
```

### 10.2 关键测试点

| 模块 | 测试类型 | 关键场景 |
|---|---|---|
| `cli.py` | 单元 + 集成 | 命令参数解析、JSON 输出、退出码 |
| `pipeline/runner.py` | 集成 | 11 stage 完整跑通、resume、跳过已完成 |
| `pipeline/asr.py` | 单元 | Faster-Whisper mock,验证输出格式 |
| `pipeline/frames.py` | 单元 | PySceneDetect mock,pHash 去重 |
| `llm/*` | 单元 | 各 provider 接口 mock,健康度计算 |
| `mcp_server.py` | 单元 + 集成 | 6 个工具的 handler,stdio 通信 |
| `system/doctor.py` | 单元 | mock 系统调用,验证推荐 profile |
| `logger/*` | 单元 | memory 日志格式、ERRORS.md 晋升逻辑 |
| UI Dashboard | E2E | 启动 → 显示 doctor 结果 |
| UI InstallProfile | E2E | 选择 standard → 显示下载进度 |
| NSIS 安装器 | 手动 + 自动 | 全新机器安装 + 卸载 + 重装 |

### 10.3 CI/CD

```yaml
# .github/workflows/ci.yml
- ruff check src/
- mypy src/
- uv run pytest
- cargo test --manifest-path ui/src-tauri/Cargo.toml
- npm run lint (ui/src/)
- npm run test (ui/src/)
- npm run build (ui/src/)

# .github/workflows/build-windows.yml
- windows-latest runner
- NSIS 打包
- 签名(可选)
- 上传 artifact

# .github/workflows/release.yml
- 创建 GitHub Release
- 上传 .exe / wheel
- 提交到 WinGet / Scoop / Chocolatey
```

---

## 11. 部署与发布

### 11.1 发布渠道

| 渠道 | 格式 | 触发 | 自动化 |
|---|---|---|---|
| GitHub Releases | .exe + .whl | tag 推送 | ✅ |
| PyPI | wheel + sdist | tag 推送 | ✅ |
| WinGet | manifest | tag 推送后 | ✅(PR 自动) |
| Scoop | manifest | tag 推送后 | ✅(PR 自动) |
| Chocolatey | .nupkg | tag 推送后 | ✅(PR 自动) |
| Docker(可选) | image | tag 推送后 | P2 |

### 11.2 版本策略

- **语义化版本**:MAJOR.MINOR.PATCH
- 主版本:重大架构变化(L1→L2)
- 次版本:新功能(新 stage、新 provider)
- 修订版:bug fix

### 11.3 CHANGELOG

- 遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/)
- 每个 PR 标题用 Conventional Commits,自动生成 CHANGELOG

---

## 12. 文档清单

| 文件 | 受众 | 内容 |
|---|---|---|
| `README.md` | 用户 | 项目简介、快速开始、截图、链接 |
| `docs/installation.md` | 用户 | 系统要求、各 OS 安装步骤 |
| `docs/quickstart.md` | 用户 | 5 分钟跑通第一条流水线 |
| `docs/cli.md` | 用户 | CLI 完整命令参考 |
| `docs/api.md` | 开发者 | Python API 完整参考 |
| `docs/providers.md` | 用户 | LLM provider 配置详解 |
| `docs/mcp-integration.md` | 用户 | Claude Desktop / Codex 集成 |
| `docs/troubleshooting.md` | 用户 | 常见问题 + 解决方案 |
| `CONTRIBUTING.md` | 贡献者 | 开发流程、PR 规范、代码风格 |
| `CODE_OF_CONDUCT.md` | 社区 | 行为准则 |
| `SECURITY.md` | 用户 | 漏洞报告流程 |
| `ARCHITECTURE.md` | 开发者 | 高级架构图(本文件精简版) |

---

## 13. TDD 评审清单

- [ ] 技术选型有理由(ADR)
- [ ] 模块划分清晰(单一职责)
- [ ] 接口规范完整(CLI / Python API / MCP)
- [ ] 数据流图覆盖完整流水线
- [ ] 安全与隐私设计覆盖
- [ ] 性能与可靠性目标可度量
- [ ] 测试策略覆盖 P0
- [ ] 部署与发布流程明确
- [ ] 文档清单完整
- [ ] 与 PRD / ROADMAP 链接完整
