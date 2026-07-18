# task.md — 活跃 todo 清单

> 本文件跟踪 `media-to-doc` 项目从启动到 L2 完整闭环的全部待办。
> 状态:`[ ]` 未开始 / `[~]` 进行中 / `[x]` 完成 / `[!]` 撞墙待人工

最后更新:2026-07-18(Phase 1 W3 完成)

---

## Phase 0 — 项目骨架(本会话)

- [x] uv init + `pyproject.toml`(`name=media_to_doc`,`requires-python>=3.11`,extras: llm/asr/frames/ocr/imagegen/longdoc/mcp/dev)
- [x] 目录结构:`src/media_to_doc/` + `tests/` + `workspace/{inbox,work}/` + `.learnings/` + `.github/workflows/`
- [x] `.gitignore`(屏蔽 `_research/`、`workspace/`、`__pycache__/`、`.venv/`、`*.egg-info`、`.env` 等)
- [x] `LICENSE`(MIT,2026 Duanyi)
- [x] `README.md` 初版(项目简介 + 5 分钟快速开始 + 三种调用方式 + 产物布局 + 文档导航 + 路线图)
- [x] `src/media_to_doc/` 5 个占位模块:
  - [x] `__init__.py`(version + lazy import 占位)
  - [x] `cli.py`(Typer mtd 命令:version / paths / run / resume / status / list / doctor / config / model / mcp,`--version` 顶层 callback)
  - [x] `paths.py`(WORKSPACE_ROOT / INBOX / WORK / CONFIG / LEARNINGS + 环境变量覆盖)
  - [x] `config.py`(WorkflowConfig 数据类 + LLMConfig/ImagegenConfig/PathsConfig/PipelineConfig + YAML 序列化)
  - [x] `state.py`(STAGE_ORDER 11 阶段 + StageState + State JSON 持久化)
- [x] `src/media_to_doc/logger/__init__.py`(Phase 5 迁 LE 原型的占位)
- [x] `tests/` 基础:`__init__.py` + `conftest.py` + `test_smoke.py`(14 用例)
- [x] `.learnings/LEARNINGS.md` + `.learnings/ERRORS.md` 空模板
- [x] `.github/workflows/ci.yml`(windows-latest + Python 3.11/3.12 + ruff + mypy + pytest)
- [x] 验证:`uv run pytest` 14/14 通过,`uv run ruff check` 全过,`uv run mtd --version` 输出 `media-to-doc 0.1.0`
- [x] 首个 commit:`chore: bootstrap project skeleton`(含 PRD/TDD/ROADMAP/CLAUDE.md/task.md/handoff-template.md/LICENSE/README.md/.gitignore/pyproject.toml/src/tests/workspace/.learnings/.github/)

---

## Phase 1 — 核心流水线(L1,每阶段独立 commit)

- [ ] `uv init` + `pyproject.toml`(包名 `media_to_doc`,extras 含 imagegen)
- [ ] 目录结构:`src/media_to_doc/` + `tests/` + `workspace/inbox|work/` + `.learnings/`
- [ ] `.gitignore`(屏蔽 `_research/`、`workspace/`、`__pycache__/`、`.venv/`)
- [ ] `README.md` 初版(项目简介 + 快速开始)
- [ ] 第一个 commit:`chore: bootstrap project skeleton`

---

## Phase 2 — 核心流水线(L1,每阶段独立 commit)

> 参考实现的 11 阶段流水线已验证可用,本项目复刻并保持架构一致。
> 每阶段:实现 → 测试 → 跑通 → commit,不积压。

- [x] **`audio`** — ffmpeg 抽音(`ffmpeg_utils.py` + `audio.py`)— **W1**
- [x] **`asr`** — Faster-Whisper 转写,CUDA fp16(`asr.py`)— **W1**
- [x] **`frames`** — PySceneDetect + pHash 去重(`frames.py`)— **W1**
- [x] **`ocr`** — RapidOCR(`ocr.py`)— **W2**
- [x] **`asr_correct`** — OCR × ASR 8s 校对(`asr_correct.py`)— **W2**
- [x] **`chapters`** — LLM 章节切分,新 schema:`summary/key_points/image_refs/illustrations`(`chapters.py`)— **W2**
- [x] **`draft`** — 章节草稿生成(`draft.py`)— **W3**
- [x] **`imagegen`** — SDXL Base + Refiner,可跳过(`imagegen.py`)— **W3**
- [x] **`render`** — Markdown + HTML,相对路径(`render.py`)— **W3**
- [ ] **`longdoc`** — 借鉴 long-doc-processor skill,深度净化 + TOC HTML(`longdoc.py`)— **W4 待办**
- [ ] **`verify`** — gatekeeper + image_refs 校验(`verify.py`)— **W4 待办**

---

## Phase 3 — LLM provider 抽象(L1)

- [x] `llm/__init__.py` 抽象:统一 `provider.chat(prompt)` 接口
- [x] `ollama` provider(默认)
- [x] `anthropic` provider(`ANTHROPIC_API_KEY`)
- [x] `openai_compatible` provider(`OPENAI_BASE_URL` + `OPENAI_API_KEY`)— 支持 MiniMax/DeepSeek/智谱/Moonshot/混元/OpenRouter

---

## Phase 4 — 跨项目可调用(L1)

- [ ] `__init__.py` 顶层 re-export + lazy import(PEP 562),重依赖按需加载
- [ ] `cli.py` `media-to-doc run <inbox>` / `media-to-doc resume <work>` 命令
- [ ] `pyproject.toml` `[project.scripts]` 注册 CLI 入口
- [ ] `mcp_server.py` stdio MCP server,6 个工具:
  - [ ] `list_courses(workspace_root)`
  - [ ] `run_pipeline(inbox_dir, workspace_root)`
  - [ ] `resume_pipeline(work_dir)`
  - [ ] `check_status(work_dir)`
  - [ ] `list_outputs(inbox_dir)`
  - [ ] `read_lecture(inbox_dir, version, fmt)` — 支持 `raw/cleaned/final`
- [ ] Claude Desktop 配置文档

---

## Phase 5 — 测试(L1)

- [ ] pytest 基础设施(`conftest.py` + fixtures)
- [ ] mock LLM / mock SDXL / mock Faster-Whisper / mock RapidOCR(避免 CI 真跑重依赖)
- [ ] 每个模块配套测试,目标 ≥ 110 用例
- [ ] `uv run pytest` 在 README 标注

---

## Phase 6 — Loop Engineering 闭环(L2)

> **前置研究**:本会话已落地 23 测试全过的原型,见 `_research/le_prototype/`
> 详细设计见 `_research/LE_DESIGN.md`

- [ ] **迁移 LE 原型**
  - [ ] 复制 `_research/le_prototype/{pipeline_logger,gatekeeper,learnings}.py` 到 `src/media_to_doc/logger/`
  - [ ] 引入包内依赖(`paths.py` / `config.py`)
- [ ] **替换 mock stage 为真实 11 stage 函数**(每个 stage 接到 `timed_stage(logger, stage)` 上下文管理器)
- [ ] **`pipeline/runner.py` 集成 LE hooks**(`run_pipeline` 末尾调 `gatekeeper_check` + `logger.finalize` + `post_pipeline_hook`)
- [ ] **`llm/health.py` + MCP 暴露**(`get_run_metrics(work_dir)` + `list_runs(workspace_root)`)
- [ ] **UI:Learnings 页**(读 `.learnings/` 显示)
- [ ] **端到端验证**(跑 3 次示例视频,演示 Pattern-Key 自动晋升)
- [ ] 测试:`test_logger/*` 30+ 用例
- [ ] commit:`feat(pipeline): wire Loop Engineering L1+L2`

---

## Phase 7 — 文档与示例(L2)

- [ ] README 完善:安装 / 4 种调用方式 / API 表 / 环境变量表 / 产物布局图
- [ ] 示例 inbox 视频(可选,公开域名的小样)
- [ ] `.learnings/LEARNINGS.md` 首批 LP-YYYYMMDD-NNN 条目
- [ ] 跨项目使用 demo(其它 Claude 项目里 import 的最小代码片段)

---

## Phase 8 — 进阶(L3,留作未来)

- [ ] Prompt 自适应(累积成功 chapter 摘要 → 风格 prompt)
- [ ] 自动重试 + 自愈循环
- [ ] MCP 暴露 `list_runs` / `get_run_metrics`
- [ ] 多 Agent 协作质量跟踪
- [ ] 跨 Agent 经验晋升

---

## 当前阻塞(等用户决定)

无。本会话纯文档 + 原型工作,等待用户对后续 phase 的优先级排序。

---

## 会话历史

### 会话 1 — 项目启动与研究(2026-07-17,~30 分钟)

- 完成任务:逆向研究 01学习资料 / local-ai-workflow 8 次 commit
- 产出:`_research/PROJECT_DESCRIPTION.md`、`CLAUDE.md`、`task.md`、`handoff-template.md`、`handoff-research-2026-07-17.md`
- 测试:N/A(纯文档)
- 下次会话第一句:参考 `handoff-research-2026-07-17.md` 继续 Phase 1 骨架

### 会话 2 — PRD/TDD/ROADMAP(2026-07-17 晚,~45 分钟)

- 完成任务:基于用户确认的 4 项决策(media-to-doc/Tauri/MIT/NSIS)产出 PRD/TDD/ROADMAP
- 产出:`PRD.md`(378 行)、`TDD.md`(1061 行)、`ROADMAP.md`(563 行)
- 测试:N/A
- 下次会话第一句:评审 PRD/TDD/ROADMAP,确定 Phase 0 启动

### 会话 3 — LE 落地(2026-07-17 末 ~ 2026-07-18 凌晨,~1.5 小时)

- 完成任务:
  - 读 aiec.fun 两篇文章 + 提取 LE 核心要点
  - 写 `_research/LE_KEYPOINTS.md`(两篇摘要)
  - 写 `_research/LE_DESIGN.md`(详细落地设计,五层 + 三层 Memory + 反模式 + 度量)
  - **落地 LE L1+L2 核心模块原型**(`_research/le_prototype/`)
    - `pipeline_logger.py` / `gatekeeper.py` / `learnings.py` / `runner.py` / `tests/test_le.py` / `README.md`
    - **23 测试全过**(`python -m pytest tests/ -v`)
  - 同步 PRD/TDD/ROADMAP/task.md 反映 LE 落地
- 关键设计:
  - Pattern-Key = `ShortType:keyword`(例:`Connection:ollama`)
  - Gatekeeper 4 项机器可验证检查
  - 幂等晋升(已存在 Pattern-Key 不重复写入)
  - `assess_llm_health` 失败率 > 20% → switch_provider
- 下次会话第一句:承接 `handoff-le-design-2026-07-18.md`,评审 LE 原型,启动 Phase 0 项目骨架

### 会话 4 — Phase 0 项目骨架(2026-07-18,~1 小时)

- 完成任务(Phase 0 全完成):
  - `.gitignore` / `LICENSE`(MIT)/ `README.md` 初版
  - `uv init --bare` 创建 `pyproject.toml`,`name=media_to_doc`,`requires-python>=3.11`
  - `src/media_to_doc/` 5 个占位模块(`__init__`/`cli`/`paths`/`config`/`state`) + `logger/__init__.py`
  - `tests/test_smoke.py` — 14 测试全过
  - `.github/workflows/ci.yml` — windows-latest + Python 3.11/3.12 + ruff + mypy + pytest
  - `.learnings/LEARNINGS.md` + `.learnings/ERRORS.md` 空模板
  - git init + 首个 commit:`chore: bootstrap project skeleton`
- 关键决策(用户确认):
  - Phase 0 范围:仅 Python 后端骨架,UI/NSIS 留到 Phase 2/3
  - LE 原型:不纳入 git(`.gitignore` 屏蔽 `_research/`)
  - 首 commit 含 PRD/TDD/ROADMAP/LE 设计文档
  - Python `>=3.11`(与参考实现一致)
- 验证:`uv run pytest` 14/14 + `uv run ruff check` 全过 + `uv run mtd --version` = `media-to-doc 0.1.0`
- 下次会话第一句话:承接 `handoff-skeleton-bootstrap-2026-07-18.md`,启动 Phase 1 核心流水线(11 stage 逐阶段实施)

### 会话 5 — Phase 1 W1 核心流水线前 3 stage(2026-07-18,~1.5 小时)

- 完成任务(ROADMAP Phase 1 W1 全完成):
  - 分支:`feat/pipeline-w1-audio-asr-frames`
  - `src/media_to_doc/utils/`:ffmpeg_utils / hash_utils / progress(3 模块)
  - `src/media_to_doc/pipeline/`:audio / asr / frames / runner(4 模块)+ 顶层 `__init__.py`
  - `tests/test_utils/` + `tests/test_pipeline/` 共 8 个测试文件
  - **pytest:14 → 79 passed (+65 用例)**,3 skip(可选 imagehash 依赖)
  - **ruff:**All checks passed
  - W1 commit:`feat(pipeline): W1 — audio + asr + frames stages + utils + runner`
- 关键设计:
  - 11 个 stage 全部在 STAGE_FUNCS 占位,W1 真做 3 个,其余抛 `NotImplementedError`
  - runner 用 `_invoke_stage(stage, func, ctx)` 分发,测试可注入 mock 函数
  - stage 函数全部 lazy import 重依赖(faster-whisper / scenedetect / imagehash),缺库时给清晰 ImportError
  - `stop_after` 在已跳过 stage 上也生效(resume 语义正确)
  - ffmpeg 抽音频输入(mp3/wav/m4a)→ 直接 shutil.copy2 省一次转码
- 下次会话第一句话:承接 `handoff-pipeline-w1-2026-07-18.md`,启动 W2(OCR + asr_correct + LLM providers + chapters)

### 会话 6 — Phase 1 W2 OCR + ASR 校对 + LLM + 章节(2026-07-18,~1.5 小时)

- 完成任务(ROADMAP Phase 1 W2 全完成):
  - 分支:`feat/pipeline-w2-ocr-chapters`(基于 W1)
  - `src/media_to_doc/llm/`:base / ollama / anthropic / openai_compat + `__init__` 注册表(5 模块)
  - `src/media_to_doc/pipeline/`:ocr / asr_correct / chapters(3 模块)
  - `runner.py` 替换 3 占位 + 新增 `_chapters_wrapper`(从 config 派生 LLM provider)
  - `tests/test_llm/` + `tests/test_pipeline/` 新增 7 测试文件
  - **pytest:79 → 212 passed (+133 用例)**,3 skip(可选 imagehash 依赖)
  - **ruff:**All checks passed
  - W2 commit:`feat(pipeline): ocr + asr_correct + chapters + llm providers`
- 关键设计:
  - LLM provider 基类自动累积调用/失败 + `health()`(LE L1 健康度评估用)
  - `_extract_candidates` 用 sliding window 替代单 regex chunk,让"达摩盘"等局部专有名词被识别
  - OCR 阶段单帧容错,失败时记录到 `OcrResult.error` 而不阻塞整 stage
  - chapters JSON 解析做宽松适配(围栏 / 前缀文字 / `[` 到 `]` 切片)
  - 7 个 LLM 厂商 preset(minimax / deepseek / zhipu / moonshot / openrouter / dashscope / hunyuan)
- 下次会话第一句话:承接 `handoff-pipeline-w2-2026-07-18.md`,启动 W3(draft + imagegen + render)

### 会话 6 — Phase 1 W2 OCR + ASR 校对 + LLM + 章节切分(2026-07-18,~1.5 小时)

- 完成任务(ROADMAP Phase 1 W2 全完成,211 → 212 测试):
  - 分支:`feat/pipeline-w2-ocr-chapters`
  - `src/media_to_doc/llm/`:base.py(ABC + HealthStatus)+ ollama + anthropic + openai_compat(7 preset) + __init__
  - `src/media_to_doc/pipeline/`:ocr(RapidOCR 容错)+ asr_correct(sliding window)+ chapters(LLM JSON 容错)
  - 测试:79 → 212(+133 用例,3 skip)
  - ruff:All checks passed
  - W2 commit:`feat(pipeline): ocr + asr_correct + chapters + llm providers`(`f712552`)
- 关键设计:
  - `BaseLLMProvider` 自动累积调用统计 + health()(子类只实现 `_chat_impl`)
  - chapters 用 LLM 输出新 schema(title/summary/start_seconds/end_seconds/key_points/image_refs/illustrations)
  - `_chapters_wrapper` 把 config.llm 派生 provider,与 stages 的 `(work, config)` 签名一致
- 下次会话第一句:承接 `handoff-pipeline-w3-2026-07-18.md`(刚刚写),启动 W4(longdoc + verify)

### 会话 7 — Phase 1 W3 Draft + Imagegen + Render(2026-07-18,~1.5 小时)

- 完成任务(ROADMAP Phase 1 W3 全完成):
  - 分支:`feat/pipeline-w3-draft-imagegen-render`
  - `src/media_to_doc/pipeline/`:draft(LLM 按章节切片 transcript + 双 prompt)+ imagegen(SDXL Base+Refiner + SkipProvider + ABC/Protocol 双轨)+ render(jinja2 + markdown lib + 相对路径 + TOC)
  - `src/media_to_doc/pipeline/runner.py`:`_draft_wrapper` + STAGE_FUNCS 替换 3 占位 + `_invoke_stage` 3 分支 + `_resolve_drafts_dir` helper
  - 测试:212 → 285(+73 用例,3 skip 不变)
  - ruff:All checks passed
  - W3 commit:`feat(pipeline): draft + imagegen + render stages`(`86694a0`)
- 关键决策:
  - `markdown + jinja2` 从 `[longdoc]` extras 上移到核心 deps(render 是核心 stage)
  - imagegen 用 ABC + Protocol 双轨(产品代码 ABC,测试 duck-typed)
  - draft 默认输出 `chapters_dir/raw/<stem>/`(work 内),runner 后续可注入 `inbox/`
  - render 在拼装时把 `![[gen_*.png]]` 重写为 `![Image](<stem>/images/gen_*.png)`,缺失图自动退化为警告文字
  - `_load_chapters_report` 在 draft / render 各重复一次(15 行 helper,纯加法原则不动 chapters.py)
  - B023 closure 问题用显式 `search + append + advance pos` 替代 iterator 闭包
- 下次会话第一句:承接 `handoff-pipeline-w3-2026-07-18.md`,启动 W4(longdoc + verify)

