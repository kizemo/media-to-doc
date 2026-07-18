# media-to-doc — Project Execution Roadmap

> 版本:v1.0 · 日期:2026-07-17 · 状态:待评审
>
> 本文档定义 `media-to-doc` 从代码启动到 v1.0 发布的**阶段、里程碑、估算、依赖、风险**。
> 配合 `task.md`(详细 todo)和 `PRD.md`/`TDD.md`(需求/设计)使用。

---

## 0. 文档元信息

| 项 | 值 |
|---|---|
| 项目代号 | media-to-doc |
| 文档版本 | v1.0 |
| 创建日期 | 2026-07-17 |
| 状态 | Draft |
| 关联文档 | `PRD.md`、`TDD.md`、`task.md`、`CLAUDE.md` |

---

## 1. 总览

### 1.1 一句话

从参考实现 `local-ai-workflow`(8 commit / 110 测试已验证)出发,8 周内交付
**Windows 开源桌面工具 v1.0**,包含 11 阶段流水线、Tauri 客户端、NSIS 安装器、
MCP server,支持 Claude Desktop / Codex 原生集成。

### 1.2 阶段总览

```
Phase 0 启动                  ▓░░░░░░░░░░░░░░░░░░░ 1 周
Phase 1 核心流水线            ▓▓▓▓▓░░░░░░░░░░░░░░░ 3 周
Phase 2 客户端 UI(Tauri)     ░░░▓▓▓▓▓▓▓▓░░░░░░░░░ 4 周
Phase 3 安装器 + 配置向导    ░░░░░░░░░▓▓▓░░░░░░░░ 2 周
Phase 4 MCP + 集成文档       ░░░░░░░░░░░░▓▓░░░░░░ 1 周
Phase 5 LE 闭环              ░░░░░░░░░░░░░░▓▓░░░░ 1.5 周
Phase 6 发布准备             ░░░░░░░░░░░░░░░░░▓▓░ 1 周
                              ────────────────────────
                                          总计:8 周(单人全职)
```

### 1.3 关键里程碑

| 里程碑 | 日期(相对开始) | 交付物 | 验收 |
|---|---|---|---|
| **M0 — Kickoff** | W0 | 项目仓库初始化,CI/CD,issue 模板 | 首个 commit,CI 绿 |
| **M1 — Skeleton CLI** | W1 末 | `mtd run` 可跑通 `audio → verify` 占位实现 | pytest 30+ 用例 |
| **M2 — Full Pipeline** | W4 末 | 11 阶段全部真实实现,跑通 1 个示例视频 | pytest 110+ 用例 |
| **M3 — Client MVP** | W5 末 | Tauri 客户端 5 页基本功能 | Playwright 10+ 用例 |
| **M4 — Installer** | W6 末 | NSIS 安装器可在干净 Windows 11 跑通 | 安装 + 卸载测试 |
| **M5 — MCP + Docs** | W7 末 | Claude Desktop / Codex 集成 + 完整文档 | 配置即跑通 |
| **M6 — LE Closed Loop** | W7.5 末 | L1+L2 全部 hook,跑 3 次演示自动晋升 | 实证演示 |
| **M7 — v1.0 Release** | W8 末 | GitHub Release + PyPI + WinGet + Scoop + Chocolatey | 5 渠道全发 |

---

## 2. 工作量估算

### 2.1 估算假设

- 单人全职开发(8 小时/天,5 天/周)
- 已有 `local-ai-workflow` 参考实现可复用(节省 ~40% 设计时间)
- 假设 GPU 资源充足(RTX 3090 可用)
- 假设 Claude / GPT API 可访问
- 不含社区运营 / 用户支持 / 文档撰写(开发期内同步)

### 2.2 Phase 工作量分解

| Phase | 周 | 主要工作 | 工作量(人天) | 关键风险 |
|---|---|---|---|---|
| **0. 启动** | W0 | 项目骨架 + CI/CD + 文档框架 | 3 | 工具链 |
| **1. 核心流水线** | W1-W4 | 11 stage + LLM provider 抽象 + 测试 | 16 | LLM API 兼容性 |
| **2. 客户端 UI** | W5-W8 | Tauri + React 6 页 + IPC + 测试 | 18 | Tauri 工具链 / Rust 学习曲线 |
| **3. 安装器** | W6-W7 | NSIS 脚本 + 模型下载 + 配置向导 | 8 | Windows 兼容性 / 代码签名 |
| **4. MCP + 集成** | W7 | MCP server 完善 + Claude/Codex 集成文档 | 4 | 协议变更 |
| **5. LE 闭环** | W7.5-W8 | PipelineLogger / Gatekeeper / Hooks | 6 | 设计复杂度 |
| **6. 发布** | W8 | PyPI / GitHub Release / WinGet / Scoop | 4 | 渠道合规 |
| **缓冲** | - | 风险 + Bug 修复 + 重构 | 5 | - |
| **总计** | 8 周 | - | **64 人天** | - |

### 2.3 与参考实现的对照

参考实现 `local-ai-workflow` 已用约 50-60 人天完成核心流水线(8 commit / 110 测试)。
本项目复刻 + 增强,主要增量是:

| 增量 | 工作量(人天) |
|---|---|
| Tauri 客户端(全新) | +18 |
| NSIS 安装器(全新) | +8 |
| 模型下载 / 管理(全新) | +4 |
| 配置向导 UI(全新) | +4 |
| 配置持久化 + DPAPI 加密(全新) | +3 |
| 系统诊断 / Doctor(全新) | +3 |
| OpenAI Compatible provider 自动发现模型 | +2 |
| 文档 / 教程 / 集成示例 | +5 |
| CI/CD + Release 自动化(全新) | +4 |
| **增量总计** | **+51** |
| **复刻核心流水线(参考已有经验)** | +13 |
| **项目总计** | **64 人天** |

---

## 3. 详细阶段计划

### Phase 0 — 项目启动(W0,3 人天)

**目标**:建立项目基础,跑通"开发 → 测试 → 发布"全链路。

**任务清单**:

- [ ] 仓库初始化
  - [ ] `git init` + `.gitignore` + `LICENSE`(MIT)+ `README.md`(占位)
  - [ ] GitHub repo 创建:`media-to-doc/media-to-doc`
  - [ ] 分支保护规则:master 必须 PR + 1 review
- [ ] Python 后端骨架
  - [ ] `uv init` + `pyproject.toml`(name=`media_to_doc`,version=`0.1.0`)
  - [ ] 目录结构:`src/media_to_doc/` + `tests/` + `workspace/`
  - [ ] `src/media_to_doc/__init__.py` 占位
  - [ ] `src/media_to_doc/cli.py` 用 Typer 写空 `mtd` 命令
- [ ] UI 骨架
  - [ ] `ui/` 用 `npm create tauri-app@latest` 初始化
  - [ ] React 18 + TypeScript + Vite + Tailwind + shadcn/ui
  - [ ] 6 个空路由
- [ ] NSIS 骨架
  - [ ] `installer/media-to-doc.nsi` 占位脚本
  - [ ] 编译出空安装器
- [ ] CI/CD
  - [ ] `.github/workflows/ci.yml`(pytest + ruff + mypy + cargo test + npm test)
  - [ ] `.github/workflows/build-windows.yml`(NSIS 打包)
  - [ ] `.github/ISSUE_TEMPLATE/`(bug + feature)
  - [ ] `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] 文档框架
  - [ ] `PRD.md` / `TDD.md` / `ROADMAP.md` / `CLAUDE.md` / `task.md` / `handoff-template.md`(已完成)
- [ ] 第一个 commit:`chore: bootstrap project skeleton`

**验收**:

- `uv sync` 一键装好所有依赖
- `uv run mtd --help` 输出帮助
- `npm run tauri dev` 启动空窗口
- `pytest` 全过
- CI 在 GitHub 跑通

**风险**:

- Tauri 在 Windows 首次编译可能失败 → 提前 W0.5 验证
- NSIS 工具链需手动安装 → 在 README 说明

---

### Phase 1 — 核心流水线(W1-W4,16 人天)

**目标**:11 阶段流水线完整可用,跑通至少 1 个示例视频。

**任务清单**:

#### W1:基础设施 + 前 3 stage(4 人天)

- [ ] `src/media_to_doc/paths.py` — 路径常量
- [ ] `src/media_to_doc/config.py` — 配置数据类 + YAML 加载
- [ ] `src/media_to_doc/state.py` — State + STAGE_ORDER
- [ ] `src/media_to_doc/utils/ffmpeg_utils.py` — ffmpeg 路径探测
- [ ] `src/media_to_doc/utils/hash_utils.py` — pHash
- [ ] `src/media_to_doc/utils/progress.py` — 进度条
- [ ] `src/media_to_doc/pipeline/runner.py` — 编排器骨架
- [ ] `src/media_to_doc/pipeline/audio.py` — `prepare_audio()`
- [ ] `src/media_to_doc/pipeline/asr.py` — `transcribe()`(Faster-Whisper)
- [ ] `src/media_to_doc/pipeline/frames.py` — `extract_keyframes()`
- [ ] 测试:`test_audio` `test_asr` `test_frames`(mock 重依赖)
- [ ] commit:`feat(pipeline): audio + asr + frames stages`

#### W2:OCR + 校对 + 章节(4 人天)

- [ ] `src/media_to_doc/pipeline/ocr.py` — `run_ocr()`(RapidOCR)
- [ ] `src/media_to_doc/pipeline/asr_correct.py` — `correct_asr()`
- [ ] `src/media_to_doc/llm/base.py` + `llm/ollama.py` — LLM 抽象 + Ollama provider
- [ ] `src/media_to_doc/llm/anthropic.py` — Anthropic provider
- [ ] `src/media_to_doc/llm/openai_compat.py` — OpenAI compatible + 自动模型发现
- [ ] `src/media_to_doc/llm/__init__.py` — provider 注册表
- [ ] `src/media_to_doc/pipeline/chapters.py` — `split_chapters()`
- [ ] 测试:`test_ocr` `test_asr_correct` `test_chapters` `test_llm_*`
- [ ] commit:`feat(pipeline): ocr + asr_correct + chapters + llm providers`

#### W3:Draft + Imagegen + Render(4 人天)

- [ ] `src/media_to_doc/pipeline/draft.py` — `generate_drafts()`
- [ ] `src/media_to_doc/pipeline/imagegen.py` — `generate_images()`(SDXL Base + Refiner,可选 skip)
- [ ] `src/media_to_doc/pipeline/render.py` — `render_outputs()` + `render_html()`(相对路径)
- [ ] 测试:`test_draft` `test_imagegen` `test_render`
- [ ] 跑通示例视频:1.5h 中文培训,30 分钟内出 md/html
- [ ] commit:`feat(pipeline): draft + imagegen + render stages`

#### W4:Longdoc + Verify + 跨项目可调用(4 人天)

- [ ] `src/media_to_doc/pipeline/longdoc.py` — `process_long_doc()` + `render_final_html()`
  - 借鉴 `C:\Users\Duanyi\.claude\skills\long-doc-processor\`
  - 分块 15000 CJK,5 类保留 / 4 类清理,TOC + 锚点 + 内嵌 CSS
- [ ] `src/media_to_doc/pipeline/verify.py` — gatekeeper + image_refs 校验
- [ ] `src/media_to_doc/__init__.py` — 顶层 re-export + lazy import(PEP 562)
- [ ] `src/media_to_doc/cli.py` 完整:`run`/`resume`/`status`/`list`/`doctor`/`config`/`model`/`mcp`
- [ ] 测试:`test_longdoc` `test_verify` `test_cli`(110+ 用例)
- [ ] 跑通 3 个不同长度视频(短/中/长)
- [ ] commit:`feat(pipeline): longdoc + verify stages and CLI`

**验收**:

- `uv run mtd run <inbox>` 跑通示例视频
- `uv run mtd resume <work>` 中断后能续跑
- pytest 110+ 用例全过
- 产物可直接打开,图片正常显示
- 产物整盘复制到另一台机器仍正常

**风险**:

- Faster-Whisper / SDXL 首次下载慢 → 在 README 提示
- Ollama 兼容性 → doctor 检测 + 推荐 profile
- LLM API 限流 → 加 retry + fallback

---

### Phase 2 — 客户端 UI(W5-W8,18 人天)

**目标**:Tauri + React 客户端,6 页基本功能,IPC 通顺。

**任务清单**:

#### W5:Doctor + Install Profile(4 人天)

- [ ] `src/media_to_doc/system/doctor.py` — 系统检测(GPU/显存/磁盘/网络/ffmpeg/Python)
- [ ] `src/media_to_doc/system/ollama.py` — Ollama 安装/启动/服务注册
- [ ] `src/media_to_doc/system/models.py` — 模型下载/管理
- [ ] `src/media_to_doc/system/service.py` — Windows Service 注册
- [ ] Tauri 集成:启动时调 doctor,显示 Dashboard
- [ ] UI:Install Profile 页面 + 模型下载进度
- [ ] commit:`feat(system): doctor + install profile`

#### W6:任务管理 + 配置(4 人天)

- [ ] UI:Dashboard 页(近期任务、快速开始、模型状态)
- [ ] UI:Tasks 页(新增/批量/进度/续跑)
- [ ] UI:Settings 页(LLM provider / imagegen provider / 路径配置)
- [ ] Tauri IPC:run_pipeline / resume_pipeline / check_status / list_courses / set_config
- [ ] 测试:`test_system/*` + Playwright 5 个用例
- [ ] commit:`feat(ui): dashboard + tasks + settings pages`

#### W7:LLM 自动配置 + 集成页(4 人天)

- [ ] UI:LlmConfig 组件(选 provider → 输 URL + Key → 自动拉取模型列表)
- [ ] Tauri IPC:test_llm / list_models / set_provider
- [ ] UI:Integration 页(Claude Desktop JSON / Codex JSON 一键复制)
- [ ] UI:Preview 页(HTML 嵌入预览)
- [ ] 测试:Playwright 10+ 用例
- [ ] commit:`feat(ui): llm auto-config + integration pages`

#### W8:托盘 + i18n + LE 可视化(6 人天)

- [ ] Tauri:系统托盘 + 快捷键
- [ ] i18n:react-i18next 中英文切换
- [ ] UI:Learnings 页(`.learnings/LEARNINGS.md` / `ERRORS.md` 可视化)
- [ ] 主题切换(light / dark / auto)
- [ ] E2E 测试覆盖核心流程
- [ ] commit:`feat(ui): tray + i18n + learnings visualization`

**验收**:

- 客户端可启动并连接后端
- 添加任务 → 看到进度 → 完成弹窗
- 切换 provider → 自动拉取模型
- 系统托盘右键菜单正常
- 切换中英文无 bug

**风险**:

- Tauri Rust 编译慢 → 用 GitHub Actions 缓存
- React 状态管理复杂度 → 用 Zustand 简化
- WebView 兼容 → 用 Tauri 默认 webview

---

### Phase 3 — 安装器 + 配置向导(W6-W7,8 人天)

**目标**:NSIS 安装器可在干净 Windows 11 跑通,首次启动配置向导无缝。

**任务清单**:

#### W6(并行):NSIS 脚本基础(3 人天)

- [ ] `installer/media-to-doc.nsi` — 安装器主脚本
- [ ] 欢迎页 / License / 安装路径选择
- [ ] 组件选择(Core / Ollama / qwen3:14b / SDXL Base / Refiner / Desktop / PATH / 关联 / 托盘)
- [ ] 系统检测页(显示 doctor 结果)
- [ ] 部署级别推荐页
- [ ] 模型下载进度页
- [ ] 安装中页
- [ ] 完成页(打开客户端 / 启动 Ollama)
- [ ] 卸载脚本(关闭进程 / 移除注册表 / 询问保留 workspace)
- [ ] commit:`feat(installer): NSIS bootstrap installer`

#### W7:代码签名 + 自更新(5 人天)

- [ ] SignPath.io 集成(`installer/sign.sh`)
- [ ] 自更新检查(每次启动 → GitHub API → 提示)
- [ ] `mtd update` 命令实现
- [ ] 测试:全新 Windows 11 机器安装/卸载/重装
- [ ] commit:`feat(installer): code signing + auto-update`

**验收**:

- 在全新 Windows 11(无 Python)机器安装 < 5 分钟
- 安装后 `mtd --version` 可用
- 卸载干净(不残留 workspace)
- SmartScreen 警告消除(签名后)

**风险**:

- 代码签名证书成本 → 用 SignPath.io 开源免费档
- Windows 11 S Mode 限制 → 文档提供 winget 步骤
- 中文路径编码问题 → 全部用 %APPDATA% / %LOCALAPPDATA%

---

### Phase 4 — MCP + 集成文档(W7,4 人天)

**目标**:Claude Desktop / Codex / Claude Code 三种集成文档完备,跑通示例。

**任务清单**:

- [ ] `src/media_to_doc/mcp_server.py` — MCP stdio server
  - 6 个工具:`list_courses` / `run_pipeline` / `resume_pipeline` / `check_status` / `list_outputs` / `read_lecture`
  - 测试:`test_mcp_server.py` 11+ 用例
- [ ] `docs/mcp-integration.md` — 完整教程
  - Claude Desktop 配置(截图 + JSON)
  - Codex 配置
  - Claude Code 配置(直接 CLI 调 mtd)
- [ ] `docs/api.md` — Python API 完整参考
- [ ] `docs/cli.md` — CLI 完整参考
- [ ] `examples/claude-desktop/` — 示例对话 prompt
- [ ] `examples/codex/` — 示例脚本
- [ ] commit:`feat(mcp): stdio server + integration docs`

**验收**:

- Claude Desktop 安装用户按文档 3 步配通
- Codex / Claude Code 同样可用
- `read_lecture` 三版本(`raw/cleaned/final`)均可读

**风险**:

- MCP 协议更新 → 锁版本,关注上游
- Claude Desktop JSON 路径在 Win/Mac 不同 → 文档分别给

---

### Phase 5 — LE 闭环(W7.5-W8,6 人天)

**目标**:L1(执行/审核/沉淀)+ L2(进化/健康度)全部落地。

> **前置研究**:`_research/le_prototype/` 已落地 23 测试全过的原型,
> Phase 5 主要是**迁移 + 接入真实 stage**,非从零设计。

**任务清单**:

- [ ] **迁移 LE 原型**(1 天)
  - [ ] 复制 `_research/le_prototype/{pipeline_logger,gatekeeper,learnings}.py`
        到 `src/media_to_doc/logger/`
  - [ ] 引入包内依赖(`paths.py` / `config.py`)
  - [ ] 把 4 个 .py 改成包导入路径
- [ ] **替换 mock stage 为真实 11 stage 函数**(2 天)
  - [ ] `pipeline/audio.py` → `prepare_audio`
  - [ ] `pipeline/asr.py` → `transcribe`
  - [ ] `pipeline/frames.py` → `extract_keyframes`
  - [ ] `pipeline/ocr.py` → `run_ocr`
  - [ ] `pipeline/asr_correct.py` → `correct_asr`
  - [ ] `pipeline/chapters.py` → `split_chapters`
  - [ ] `pipeline/draft.py` → `generate_drafts`
  - [ ] `pipeline/imagegen.py` → `generate_images`
  - [ ] `pipeline/render.py` → `render_outputs` + `render_html`
  - [ ] `pipeline/longdoc.py` → `process_long_doc` + `render_final_html`
  - [ ] `pipeline/verify.py` → `verify`
- [ ] **`pipeline/runner.py` 集成 LE hooks**(1 天)
  - [ ] 用 `timed_stage(logger, stage)` 包装每个 stage
  - [ ] 末尾调 `gatekeeper_check` + `logger.finalize` + `post_pipeline_hook`
  - [ ] `cli.py mtd run` 触发完整流水线
- [ ] **`llm/health.py` + MCP 暴露**(0.5 天)
  - [ ] `assess_llm_health()` 已有,接入 `llm_health` 字段填充
  - [ ] MCP server 加 `get_run_metrics(work_dir)` + `list_runs(workspace_root)` 工具
- [ ] **UI:Learnings 页**(0.5 天)
  - [ ] Tauri 读 `.learnings/LEARNINGS.md` / `ERRORS.md` 显示
  - [ ] Dashboard 显示最近 10 run 的 quality 趋势
- [ ] **端到端验证**(1 天)
  - [ ] 跑 3 次示例视频,memory 文件正确,ERRORS.md 累积
  - [ ] 故意触发同一错误 3 次,验证 `.learnings/ERRORS.md` 自动晋升
  - [ ] 测试覆盖:`test_logger/*` 30+ 用例
- [ ] commit:`feat(pipeline): wire Loop Engineering L1+L2`

**验收**:

- 每次 `mtd run` 后 `workspace/work/<course>/memory/YYYY-MM-DD.md` 有 11 行
- `pipeline_run.json` 含 `quality` + `llm_health` + `gatekeeper_passed` 字段
- 跑 3 次触发同一错误后 `.learnings/ERRORS.md` 自动出现新条目
- gatekeeper 失败时 `mtd run` 返回非零退出码 + UI 提示
- MCP `get_run_metrics` 返回单 run 完整指标
- `assess_llm_health` 检测到 > 20% 失败率时返回 `recommendation: switch_provider`

**风险**:

- LE 设计复杂 → 已有原型验证,降低实现风险
- Pattern-Key 误判 → 调阈值 / 人工 review(默认 threshold=3)
- LLM 调用 token 计数 → `llm_health.calls/failures` 字段需各 provider 主动上报

**参考**:

- `_research/LE_DESIGN.md` — 详细设计(§3-4)
- `_research/LE_KEYPOINTS.md` — 两篇文章要点
- `_research/le_prototype/` — 已验证原型
- `_research/PROJECT_DESCRIPTION.md` §8 — 参考实现经验

---

### Phase 6 — 发布准备(W8,4 人天)

**目标**:5 渠道全发,文档完整,社区就绪。

**任务清单**:

- [ ] `pyproject.toml` 完善
  - [ ] 完整依赖锁定
  - [ ] `[project.scripts]` 注册 `mtd` / `mtd-mcp`
  - [ ] classifiers / keywords
- [ ] README 完善
  - [ ] 项目简介 + 截图
  - [ ] 快速开始(5 分钟)
  - [ ] 文档链接
  - [ ] 贡献指南链接
- [ ] LICENSE(MIT)
- [ ] CHANGELOG.md(v1.0.0)
- [ ] 发布
  - [ ] GitHub Release(tag `v1.0.0`)
  - [ ] PyPI 上传(`twine upload`)
  - [ ] WinGet manifest PR
  - [ ] Scoop manifest PR
  - [ ] Chocolatey `.nupkg`
- [ ] SECURITY.md / CONTRIBUTING.md / CODE_OF_CONDUCT.md
- [ ] GitHub Actions:release.yml
- [ ] commit:`docs: complete v1.0 documentation`
- [ ] commit:`chore(release): v1.0.0`

**验收**:

- 5 渠道全发,每个都能下载 + 安装
- 文档可读、截图清晰、链接齐全
- 用户按 README 5 分钟跑通

**风险**:

- WinGet / Scoop / Chocolatey PR 审核慢 → 提前准备
- PyPI 包名校验 → 确认 `media-to-doc` 可用

---

## 4. 依赖关系

```
Phase 0 ──┬──► Phase 1 ──┬──► Phase 2 ──┐
          │              │              │
          │              └──► Phase 4   │
          │                             │
          └──► Phase 3 ────────────────┤
                                        │
                                        ▼
                                    Phase 5
                                        │
                                        ▼
                                    Phase 6
```

关键路径:**Phase 0 → Phase 1 → Phase 5 → Phase 6**(8 周)

并行机会:
- Phase 2(UI)与 Phase 3(Installer)可并行
- Phase 4(MCP)可在 Phase 1 完成后立即开始

---

## 5. 资源计划

### 5.1 人力

| 角色 | 投入 | 备注 |
|---|---|---|
| 主开发(Claude + 用户协作) | 100% | 8 周全职 |
| 用户(stakeholder) | 10-20% | 需求确认、关键决策、验收 |
| 测试(社区贡献) | - | 开源后招募 |

### 5.2 硬件

- 开发机:RTX 3090 / 64GB(用户已有)
- CI:GitHub Actions 免费档(每月 2000 分钟)
- 模型缓存:30GB 磁盘

### 5.3 服务

- GitHub:免费
- PyPI:免费
- SignPath.io 开源档:免费
- WinGet / Scoop / Chocolatey:免费

### 5.4 总预算

- 服务费用:**$0**(全部免费档)
- 人员费用:N/A(开源)
- 总计:**$0**

---

## 6. 风险登记与缓解

| ID | 风险 | 影响 | 概率 | 缓解 |
|---|---|---|---|---|
| R-01 | Tauri Rust 工具链 Windows 编译失败 | M3 延期 2 周 | 中 | W0.5 提前验证;准备降级到 Electron |
| R-02 | SDXL Refiner 首次下载慢 | 用户首次体验差 | 高 | 断点续传;skip provider 文档;云端降级 |
| R-03 | NSIS + 嵌入 Python 兼容性问题 | M4 延期 1 周 | 中 | 参考 `local-ai-workflow` 经验;准备独立 Python 安装回退 |
| R-04 | MCP 协议在发布前变更 | 集成失效 | 低 | 锁版本 + 半年一次升级 |
| R-05 | Faster-Whisper large-v3 显存不足 | 8GB 用户跑不动 | 中 | doctor 推荐;Ollama 用小模型变体;云端 API 兜底 |
| R-06 | Ollama NVIDIA 驱动兼容 | GPU 推理不可用 | 中 | 安装时检测;提示升级驱动;CPU 模式回退 |
| R-07 | 单一开发者 burnout | 延期 1-2 周 | 中 | 阶段性 commit 让用户能接力;LE 闭环文档化 |
| R-08 | 法律风险(音视频版权) | 用户投诉 | 低 | LICENSE 明确 + README 警告 |
| R-09 | 商标 / 域名抢注 | 品牌受损 | 低 | 早期注册 media-to-doc |
| R-10 | 用户隐私担忧 | 不用本地工具 | 中 | 全部 opt-in;明确数据本地化;README 强调 |
| R-11 | 中文路径 Windows 编码 bug | 跑不通 | 中 | 所有路径用 `%APPDATA%`;测试覆盖 |
| R-12 | 长视频 OOM | 大课程失败 | 中 | 自动切片 + 流式处理 |
| R-13 | 安装器 SmartScreen 警告 | 用户不敢装 | 高 | SignPath.io 签名;文档说明 |
| R-14 | WinGet / Scoop 审核慢 | 渠道延期 | 中 | 提前 W6 提交 PR |
| R-15 | 用户测试发现关键 bug | v1.0 延期 | 高 | 留 1 周缓冲 + dogfooding |

---

## 7. 每周 check-in 模板

每周一与用户同步:

```markdown
## Week X Check-in (YYYY-MM-DD)

### 本周完成
- [x] ...
- [x] ...

### 本周阻塞
- 无 / ...

### 测试结果
- pytest: X passed
- E2E: X passed

### 下周计划
- [ ] ...
- [ ] ...

### 决策点(需用户输入)
- ...

### 风险更新
- ...
```

---

## 8. 后续规划(超 v1.0)

| 版本 | 周 | 主要功能 | 估算 |
|---|---|---|---|
| v1.1 | W10 | 多 LLM 交叉验证 + 自动重试 + 批量队列 | +2 周 |
| v1.2 | W12 | Obsidian md 模板 + PDF/EPUB 导出 | +2 周 |
| v1.3 | W14 | 多语言 UI + macOS/Linux 客户端 | +4 周 |
| v2.0 | W20 | 多 Agent 协作 + 自适应 Prompt | +8 周 |

详见 `PRD.md` §4.2(P1)、§4.3(P2)。

---

## 9. ROADMAP 评审清单

- [ ] 阶段划分清晰,每阶段有验收
- [ ] 工作量估算有依据(参考实现 + 增量)
- [ ] 里程碑可量化(M0-M7)
- [ ] 依赖关系明确
- [ ] 资源计划完整(人/硬件/服务)
- [ ] 风险登记覆盖 ≥ 10 项
- [ ] 每周 check-in 模板明确
- [ ] 与 PRD / TDD / task.md 链接
- [ ] 后续规划(P1/P2)清晰
