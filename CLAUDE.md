# media-to-doc — 项目指引

> 本文件是 Claude 在 `F:\soft\00selfmade\media-to-doc` 项目中工作时必须遵守的指引。
> 全局偏好见 `C:\Users\Duanyi\.claude\CLAUDE.md`,本文件优先于全局默认但不冲突。

---

## 1. 项目定位

**media-to-doc**:把本地音视频(培训录像、讲座录音、运营课、电商课等)和图片
转化为**带 AI 配图、可独立分发**的讲座 Markdown + HTML。

项目当前处于**启动阶段**:已完成对参考实现( `E:\办公文件\01学习资料\local-ai-workflow`)
的逆向研究,正在将研究成果落地为本项目的设计基础。

---

## 2. 与参考项目的关系

| 项 | 参考实现 | 本项目 |
|---|---|---|
| 路径 | `E:\办公文件\01学习资料` | `F:\soft\00selfmade\media-to-doc`(本目录) |
| Python 包 | `local_ai_workflow` | 待定(建议 `media_to_doc`) |
| CLI 命令 | `law` / `law-mcp` | 待定 |
| 部署形态 | 工作目录 + uv + PyPI 可装 | 同参考实现 + 在本项目根目录建完整代码 |
| 关系 | 父项目 | **参考实现 + 复刻/移植/再设计** |

**为什么另起项目**:参考实现的项目根目录是中文路径(`E:\办公文件\01学习资料`),
存在两类长期困扰:

- 跨平台 / 网络分发时中文路径在不同系统上编码不一致
- 整盘复制到其它电脑或上传到网盘时,绝对路径在最终文档里失效

本项目的设计目标之一是把这些历史包袱清掉,用更干净的英文路径和相对路径重建。

**复用而非重写**:参考实现的 11 阶段流水线、LLM provider 抽象、Loop Engineering 闭环设计
均经过 8 次 commit 验证(110 测试全过),值得直接复刻;具体模块(SDXL/Faster-Whisper/RapidOCR)
的依赖不变。

---

## 3. 核心架构(目标态)

### 3.1 流水线(11 阶段,与参考实现一致)

```
audio → asr → frames → ocr → asr_correct → chapters
     → draft → imagegen → render → longdoc → verify
```

每阶段功能详见 `_research/PROJECT_DESCRIPTION.md` §3.2。

### 3.2 设计约束(项目级)

- **可分发的产物**:图片一律相对路径,产物目录可整盘复制到任何电脑/上传网盘/丢知识库
- **可恢复**:每阶段落盘 + state.json + resume 命令,长任务中断可续跑
- **可在其它 Claude 项目中调用**:Python API / CLI / MCP server 三种暴露
- **可插拔 LLM**:`ollama` / `anthropic` / `openai_compatible` / 第三方兼容协议
- **可跳过重模块**:`imagegen_provider=skip` 让 Claude 自己做配图
- **Loop Engineering 五层闭环**:执行 / 审核 / 沉淀 / 进化 / 健康度

### 3.3 技术栈(目标态)

| 层 | 技术 |
|---|---|
| 包管理 | uv(参考实现已验证) |
| Python | 3.11+ |
| 语音转写 | Faster-Whisper large-v3,CUDA fp16 |
| 关键帧 | PySceneDetect ContentDetector + pHash 去重 |
| OCR | RapidOCR(ONNX 本地推理) |
| LLM 默认 | Ollama Qwen3-14B |
| AI 配图 | SDXL Base + Refiner(可跳过) |
| 文档渲染 | jinja2 + markdown 库 + TOC + 锚点 + 内嵌 CSS |
| MCP | `mcp.server.stdio` stdio JSON-RPC |
| 测试 | pytest |
| 学习库 | `.learnings/LEARNINGS.md`(best_practice)+ `ERRORS.md`(重复错误) |

---

## 4. 项目目录约定

```
F:\soft\00selfmade\media-to-doc\
├── CLAUDE.md                          ← 本文件
├── README.md                          ← 项目对外文档(用户视角)
├── task.md                            ← 活跃 todo(每会话开始时更新)
├── handoff-template.md                ← 会话交接模板(长期复用)
├── handoff-<topic>-<date>.md          ← 每次会话结束/撞墙前的快照
├── pyproject.toml                     ← 包元数据 + 入口
├── uv.lock                            ← 锁定依赖
├── config.yaml                        ← 运行时默认配置
├── .gitignore
├── .learnings/                        ← 项目级学习库
│   ├── LEARNINGS.md
│   └── ERRORS.md
├── src/
│   └── media_to_doc/                  ← 主包(待落地)
│       ├── __init__.py
│       ├── cli.py
│       └── ... 各阶段模块
├── tests/                             ← pytest
├── scripts/                           ← 一次性脚本(smoke runner 等)
├── workspace/                         ← 默认 inbox/work 目录(可由 env 覆盖)
│   ├── inbox/                         ← 音视频输入
│   └── work/                          ← 中间产物(可断点续跑)
└── _research/                         ← 研究/参考资料(不进 git)
    └── PROJECT_DESCRIPTION.md         ← 参考实现的完整逆向报告
```

`_research/` 目录**不进 git**,只在项目启动/调研阶段保留;当代码落地后可以归档或删除。

### 4.1 输出目录约定(W5+ 用户确认,2026-07-18;W12-D 拆分最终产物,2026-07-21)

流水线产物默认输出到 **视频所在目录**(与视频同盘,便于整盘复制 / 上传 /
知识库归档)。**这是项目级约定**,所有调用入口(`scripts/run_smoke.py`、
`mtd run` / `mtd resume` / `mtd merge`、MCP server)默认都遵循。

#### 4.1.1 拆分(2026-07-21,W12-D)

中间产物(11 stage 调度的 state / 中间文件)与最终产物(md / html 讲义)**分离**:

- `inbox_dir  = <video>.parent`(放视频的目录)
- `work_dir   = <video>.parent / "output"`(中间产物根,state.json 在此)
- `final_dir  = <video>.parent / "output_final"`(**最终 md/html**,自包含可分发)
- 自定义:`--work-dir` / `--final-dir`(支持任意路径,常用于 CI / 共享盘)

最终产物布局(`<final_dir>/`):

```
output_final/
├── <真视频名>.md          ← 拼装讲义 markdown(去后缀、去末尾空格)
├── <真视频名>.html        ← 渲染 HTML(含 v1.0.1 mermaid + tasklist 修复)
└── <真视频名>/
    └── images/            ← AI 配图(从 drafts_dir/images/ 复制,自包含)
```

**多视频合并**(`mtd merge`):

```
output_final/
├── 01_先精准后放大_cleaned.md    ← 单视频讲义(讲师版)
├── 01_先精准后放大/
│   └── images/
├── 02_拉新成交_cleaned.md
├── 02_拉新成交/
│   └── images/
├── 先精准后放大_cleaned.md       ← 合并产物(文件名 = 第一个 stem 去序号)
├── 先精准后放大_cleaned.html
└── 先精准后放大/
    └── images/                  ← 合并后的图片,命名 <video>_<file>.png
```

#### 4.1.2 兼容性策略

W12-D 默认新规 + **旧产物只读兼容**:
- gatekeeper / verify 优先查 `output_final/<stem>.md`,回退旧布局
  `output/chapters/raw/<stem>.md`
- `<stem>` 真视频名(从 chapters.json video 字段读,W12-D 起 = `derive_video_name(inbox)`)
- 旧产物不会自动迁移(用户需要时可用 `mtp` 一键复制)

#### 4.1.3 已有产物保护

跑前确认 `output/` 与 `output_final/` 无冲突;若有旧产物,先备份到
`output-backup-YYYY-MM-DD/`(参见 W5 端到端冒烟会话
`handoff-pipeline-w5-smoke-2026-07-18.md`)。

为什么这样设计:

- **可分发**:`output_final/` 自包含,整盘复制 / 网盘上传 / 知识库归档时
  `images/` 在讲义同目录,路径不会断裂
- **相对路径**:render 产物用 `<stem>/images/<file>` 等相对路径,跨机器鲁棒
- **零全局污染**:不在 `~/Documents` / 全局 `workspace/` 等散落产物
- **可覆盖**:`--work-dir` / `--final-dir` 满足 CI / 多输出场景
- **中间 vs 最终分离**:用户找讲义只看 `output_final/`,不需要扫 `output/chapters/raw/` 等嵌套

---

## 5. 工作流偏好(项目级)

### 5.1 修改前先简述计划

任何对代码的非平凡改动前,在用户消息前先列:

- 改动的文件清单
- 预计的测试影响
- 风险点

### 5.2 每次改动后跑测试

```bash
uv run pytest
```

测试失败 → 立即修;测试通过 → 报告"X passed"再继续。

### 5.3 Commit 规范

遵循 Conventional Commits:

```
feat(<scope>): <description>
fix(<scope>): <description>
refactor(<scope>): <description>
chore(<scope>): <description>
docs(<scope>): <description>
test(<scope>): <description>
```

示例 scope:`pipeline` / `mcp` / `llm` / `longdoc` / `cli` / `imagegen` / `asr` / `frames` / `ocr` / `chapters` / `verify` / `logger` / `learnings`

### 5.4 分支策略

- `master` — 稳定分支,只接受经过验证的 feat/fix commit
- `feat/<name>` — 新功能开发分支(参考实现就一直在 `feat/long-doc-skill-progressive-disclosure`)
- `fix/<name>` — 修复分支

非 trivial 工作必须在 feature 分支上,合并前确认测试全过。

### 5.5 会话健康(继承全局)

- 单个 session jsonl >10MB → 立即开新会话
- 单回合 diff >500 行 → 拆成多回合
- Bash 调用 >100 → 拆任务或新开会话
- 撞墙征兆出现 → 立即写 `handoff-<topic>-<date>.md`,再决定是否继续

### 5.6 Session-level pre-authorize

本会话及后续会话的自动合并/审核规则(W14-C 用户确认,2026-07-22):

| 触发条件 | 行为 |
|---|---|
| commit 含 `fix:` + 测试通过 + reviewer 通过 | **自动 merge master**,无需 ask |
| commit 含 `feat:` + 测试通过 + reviewer 通过 | **写 handoff,等用户拍板**,不自动 merge |
| commit 含 `wip` / `draft` | **永不 merge**,只写 handoff |
| 修改 `commands.rs` / `runner.rs`(Rust) | **必须 review 2 轮**(本会话 + 上一会话 reviewer),不能单轮 |
| 修改 `index.html`(frontend) | **单轮 review OK** |

**为什么这样设计**:fix 类改动风险低,自动合入减少排队;feat 类需用户确认方向;
Rust 后端改影响面大,双轮 review 防回归。

---

## 6. 文档维护

| 文件 | 何时更新 | 更新者 |
|---|---|---|
| `CLAUDE.md` | 项目目标/架构/约束变更时 | Claude 在每个 milestone commit 时同步 |
| `task.md` | 每个里程碑完成时勾选,新增 todo 时追加 | 每会话开头 |
| `handoff-<topic>-<date>.md` | 会话结束/撞墙前必写 | 会话主人 |
| `_research/PROJECT_DESCRIPTION.md` | 完成新会话的逆向研究时 | 研究会话 |
| `README.md` | 用户视角的功能/调用说明变更时 | 文档 commit |
| `.learnings/LEARNINGS.md` | 出现可复用 best_practice 时 | 任何会话 |
| `.learnings/ERRORS.md` | 同一 Pattern-Key 重复 ≥ 3 次自动晋升 | 进化层钩子 |

---

## 7. 禁止的反模式

- ❌ 不要把 handoff/task 文档放进 `~/.claude/projects/<proj>/memory/` 文件夹
- ❌ 不要把整个对话上下文塞进 memory(那是语义化记忆,不是会话上下文)
- ❌ 不要 `--resume` / `--continue` 任何 >5MB 的 session
- ❌ 不要在长流水线上启用 thinking 模型(易撞 600s)
- ❌ 不要硬编码用户路径(`C:\Users\Duanyi\...`),一律环境变量 + `~/.cache/...` 默认
- ❌ 不要在最终讲义里用绝对路径(`file:///C:/...`),一律相对路径
- ❌ 不要往 stdout 输出调试信息(MCP server 会破坏 JSON-RPC 协议)
- ❌ 不要跳过 `verify` / `gatekeeper` 阶段 — 它们是 Loop Engineering 审核层的兜底
- ❌ 不要在没有 L1 沉淀的情况下贸然上 L3(LE 进阶路线是渐进的)
- ❌ 不要直接修改 master 分支

---

## 8. 与全局 CLAUDE.md 的关系

全局指引在 `C:\Users\Duanyi\.claude\CLAUDE.md`,本文件是其在 `media-to-doc`
项目内的特化。任何本文件未提及的偏好,继承全局默认值:

- 简体中文回复,术语保留英文
- 缩进 2 空格,函数类型注解,camelCase(JS/TS)/ snake_case(Python)
- 包管理器优先 pnpm(Python 优先 uv)
- 安全红线:不硬编码密钥、不直接修改 main/master、删除文件前二次确认

---

## 9. 快速参考

### 9.1 启动一个新会话必做

1. 读 `C:\Users\Duanyi\.claude\projects\F--soft-00selfmade-media-to-doc\memory\MEMORY.md`(如有)
2. 读本文件 `CLAUDE.md`
3. 读 `task.md` 看活跃 todo
4. 读上一个会话的 `handoff-<topic>-<date>.md`(取最新一份)
5. 设置 <2 小时活跃时间预算

### 9.2 启动一条流水线

```bash
# 把视频放到 inbox
cp <视频>.mp4 workspace/inbox/<课程名>/

# 跑流水线(完整 11 阶段)
uv run <cli-name> run workspace/inbox/<课程名>/

# 中断后续跑
uv run <cli-name> resume workspace/work/<课程名>/

# 启动 MCP server(供 Claude Desktop 调用)
<cli-name>-mcp
```

### 9.3 在其它项目里调用本项目

**W9 实装** — PEP 562 `__getattr__` 顶层 re-export,重依赖按需加载:

```python
# Python API(其它项目)
from media_to_doc import (
    # 配置
    WorkflowConfig, LLMConfig, ImagegenConfig,
    # 流水线
    STAGE_ORDER, run_pipeline, run_stage, PipelineResult,
    # 11 stage 函数
    prepare_audio, transcribe, extract_keyframes, run_ocr,
    correct_asr, split_chapters, generate_drafts, generate_images,
    render_outputs, process_long_doc, verify_pipeline,
    # LLM
    BaseLLMProvider, get_provider,
    # LE 健康度(W8)
    get_run_metrics, list_runs, PipelineLogger, gatekeeper_check,
)
```

完整公开 API 列表见 `media_to_doc.__all__`(40 个符号)。

最小可跑示例(其它项目里直接调用):

```python
from pathlib import Path
from media_to_doc import WorkflowConfig, run_pipeline, list_runs

cfg = WorkflowConfig()  # 默认 ollama + skip imagegen
result = run_pipeline(
    inbox=Path("inbox/我的培训"),
    work=Path("output/我的培训"),
    config=cfg,
    stop_after="chapters",  # 先看 LLM 章节质量
)

# 跨 run 健康度查询
runs = list_runs(workspace_root="output", limit=10)
print(f"total_runs={runs['total_runs']}, llm_health={runs['llm_health_global']}")
```

### 9.4 MCP server 配置(Claude Desktop)

**W7 + W8 已实装**(8 工具 + stdio JSON-RPC + Claude Desktop 集成文档):

```json
{
  "mcpServers": {
    "media-to-doc": {
      "command": "uv",
      "args": ["--project", "F:/soft/00selfmade/media-to-doc", "run", "<cli-name>-mcp"]
    }
  }
}
```

完整用法、8 工具签名、错误处理、调试技巧见 [docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md)。

工具清单(W7=6 + W8=2):

- **W7**:`list_courses` / `run_pipeline` / `resume_pipeline` / `check_status` / `list_outputs` / `read_lecture`(后 4 个只读)
- **W8(LE 健康度)**:`get_run_metrics` / `list_runs`(均只读)

---

## 10. 后续规划

> 当前最新发布:**v1.2.1**(2026-07-21,W14-A)—
> [PyPI](https://pypi.org/project/media-to-doc/) +
> [GitHub Release](https://github.com/kizemo/media-to-doc/releases/tag/v1.2.1)。
> 598 pytest / 0 跳过。下表为 v1.0+ 已发布与待开始项。

| 版本 | 内容 | 状态 |
|---|---|---|
| v1.0.0 | First stable release — 11 stage 流水线 + LE 闭环 + 3 种调用方式 | ✅ W11-B + W12-A + W12-B |
| v1.0.1 | mermaid 流程图 + GFM task list HTML 渲染降级修复 | ✅ W12-C |
| v1.1.0 | multi-video layout(`output_final/` 分离 + 真视频名 + `merge_lectures`) | ✅ W12-D |
| v1.2.0 | LLM-driven chapter fusion(W12-D 硬切 → LLM 内容融合) | ✅ W12-E |
| v1.2.1 | longdoc W12-D 3 级 fallback + fusion proxy 隔离(W13-A 撞出的 2 个 P1 bug) | ✅ W14-A |
| v1.2.2 (planned) | OllamaProvider `trust_env=False` 代码层消除 HTTP_PROXY 污染 | ✅ W14-B (`427d963`) |
| **v1.3 Phase 2 — Tauri UI** | 3 次点击跑通 + 桌面壳 + log tail + modal | ✅ W14-B+ + W14-B+2(分支 `feat/w14b-plus-8-commands`,8 commit,39 unit test / 0 failed) |
| **v1.4 Phase 3 — NSIS 安装器** | Win11 桌面一键安装 | 待开始(W14-B+2 完整 UI + log tail 后续) |
| **L3 — 优化** | Prompt 自适应 / 自动重试 / 跨 Agent 经验晋升 | 留作未来 |

### Tauri UI 子项目(独立 repo)

W14-B 启动 + W14-B+ 8 commands 全实装:`F:/soft/00selfmade/media-to-doc-ui/`(独立 git repo,不入主仓)。

- Rust toolchain:`winget install Rustlang.Rustup` → rustc 1.97.1 / cargo 1.97.1
- Tauri CLI:`~/.cargo/bin/tauri.exe` = 2.11.4(GitHub release 直接下 zip + 解压)
- Cargo SSL 撞墙破解(W14-B+ T1):`default crates-io` + `CARGO_NET_TLS_VERIFY=false` env var(handoff 文档错的"verify off 不 work"实际是 sparse 不 work,default work)
- 8 commands 全部实装(W14-B+ T2+T3+T4+T6):list_courses / check_status / list_outputs / read_lecture / run_pipeline / resume_pipeline / cancel_run / list_running / get_run_metrics / list_runs(probe 也走 Tauri command)
- 简版 5 tab SPA 前端(W14-B+ T5 部分):Inbox / Run / Output / Health / Learn,真实 mtd.log tail 留 W14-B+2
- 环境变量:`MEDIA_TO_DOC_PROJECT` / `UV_BIN` / `MEDIA_TO_DOC_WORKSPACE`
- 详见 `ARCHITECTURE.md` 在子项目根 + `handoff-pipeline-w14b-plus-tauri-8cmds-2026-07-22.md`

**W14-B+2 收尾**(2026-07-22,~3h):
- 后端 `read_log` Tauri command(offset 模式 + 5 单测)
- `read_lecture` 改 W12-D output_final 优先 + W3-W11 legacy fallback(+ 4 单测)
- 前端 marked@12.0.0 CDN(SRI 锁版本)+ iframe srcdoc modal
- 前端 log tail 2s 轮询 + offset diff
- Output tab 文件 [read] 按钮
- 39 unit test / 0 failed(baseline 30 + 9 new)
- 详见 `handoff-pipeline-w14b-plus-2-ui-features-2026-07-22.md`

### v1.x 发布流程(已建立)

```bash
# 1. 修改代码 + bump version in pyproject.toml
# 2. 测试
uv run pytest && uv run ruff check
# 3. build
uv build
# 4. publish (keyring 流程,W12-A 已验证)
export UV_PUBLISH_TOKEN="$(uv run --with keyring python -c \
    "import keyring; print(keyring.get_password('https://upload.pypi.org/legacy/', '__token__'))")" \
  && uv publish dist/* \
  && unset UV_PUBLISH_TOKEN
# 5. 验证
uv pip install --upgrade media_to_doc==<NEW_VERSION>
```

完整历史:看 `task.md` §会话历史 + 各 `handoff-*.md`。
