# task.md — 活跃 todo 清单

> 本文件跟踪 `media-to-doc` 项目从启动到 L2 完整闭环的全部待办。
> 状态:`[ ]` 未开始 / `[~]` 进行中 / `[x]` 完成 / `[!]` 撞墙待人工

最后更新:2026-07-19(Phase 1 W5 完成;W6 CLI 实装;W7 MCP server 完成)

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
- [x] **`longdoc`** — 借鉴 long-doc-processor skill,深度净化 + TOC HTML(`longdoc.py`)— **W4**
- [x] **`verify`** — gatekeeper + image_refs 校验(`verify.py`)— **W4**

---

## Phase 3 — LLM provider 抽象(L1)

- [x] `llm/__init__.py` 抽象:统一 `provider.chat(prompt)` 接口
- [x] `ollama` provider(默认)
- [x] `anthropic` provider(`ANTHROPIC_API_KEY`)
- [x] `openai_compatible` provider(`OPENAI_BASE_URL` + `OPENAI_API_KEY`)— 支持 MiniMax/DeepSeek/智谱/Moonshot/混元/OpenRouter

---

## Phase 4 — 跨项目可调用(L1)

- [ ] `__init__.py` 顶层 re-export + lazy import(PEP 562),重依赖按需加载
- [x] `cli.py` `media-to-doc run <inbox>` / `media-to-doc resume <work>` 命令 — **W6 完成**
- [ ] `pyproject.toml` `[project.scripts]` 注册 CLI 入口(已注册 `mtd`,验证 OK)
- [x] `mcp_server.py` stdio MCP server,6 个工具 — **W7 完成**:
  - [x] `list_courses(workspace_root)`
  - [x] `run_pipeline(inbox_dir, workspace_root, llm, imagegen, longdoc_llm, no_longdoc, force, stop_after)`
  - [x] `resume_pipeline(work_dir, inbox_dir, force, stop_after)`
  - [x] `check_status(work_dir)`
  - [x] `list_outputs(inbox_dir)`
  - [x] `read_lecture(inbox_dir, version, fmt)` — 支持 `raw/cleaned/final`
- [x] Claude Desktop 配置文档 — `docs/MCP_INTEGRATION.md` (**W7**)
- [x] `cli.py` `mtd status` / `mtd list` 命令 — **W6 完成**
- [x] `cli.py` `mtd mcp` 子命令(启动 MCP server)— **W7 完成**

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


### 会话 8 — Phase 1 W4 longdoc + verify(2026-07-18,~1.5 小时)

- 完成任务(ROADMAP Phase 1 W4 全完成):
  - 分支:`feat/pipeline-w4-longdoc-verify`(基于 W3)
  - `src/media_to_doc/pipeline/longdoc.py`:`process_long_doc`(分块 15000 CJK / LLM 净化或 skip 规则清理)+ `render_final_html`(TOC + 锚点 + 内嵌 CSS + print stylesheet + dark mode)
  - `src/media_to_doc/pipeline/verify.py`:`verify_pipeline`(4 项机器可验证:outputs_exist / chapters_complete / image_refs / html_structure → verify.json)
  - `src/media_to_doc/pipeline/runner.py`:`_longdoc_wrapper` + STAGE_FUNCS 替换最后 2 占位 + `_invoke_stage` 2 分支 — 11 stage 全部实装
  - `src/media_to_doc/config.py`:`PipelineConfig.longdoc_llm_provider = "skip"`(默认)
  - `tests/test_pipeline/test_longdoc.py`(32 用例)+ `tests/test_pipeline/test_verify.py`(27 用例)+ `test_runner.py` 占位 → 0
  - **pytest:285 → 346 passed (+61 用例)**,3 skip 不变
  - **ruff:** All checks passed
  - W4 commit:`feat(pipeline): W4 — longdoc + verify stages (11 stages all live)`(`3b32743`)
- 关键决策:
  - longdoc 默认 `provider=None`(skip),规则清理兜底,CI 离线可跑
  - 用 `longdoc_llm_provider` 字段而非扩展 `LLMConfig.provider` Literal(避免污染 3 真 provider 语义)
  - 段落边界分块(L1)+ 超长段落字符切(L3 兜底)
  - image_refs 检查 wiki-link + md 两种语法(覆盖残留 wiki-link 场景)
  - `_check_chapters_complete` 接受 `chapters_dir` 参数(支持跨 work 调用)
  - HTML 模板改用 `.format()` 而非 jinja2(避免重复 autoescape 配置)
  - image 前缀检查只取 basename(跨 stem 重命名鲁棒)
- 下次会话第一句:承接 `handoff-pipeline-w4-2026-07-18.md`,决定 W5 方向:
  - A. 跑通示例视频(端到端冒烟)
  - B. 进入 Phase 2 L2 LE 闭环(迁移 `_research/le_prototype/`)
  - C. 接入 CLI `mtd run` / `mtd resume`(11 stage 已就位)

### 会话 9 — Phase 1 W5 端到端冒烟(部分完成,2026-07-18 ~ 07-19,~1.5h)

- 完成任务(W5 部分完成,撞墙 4 项,ASR 后台跑):
  - 分支:`feat/pipeline-w5-smoke`(基于 W4 `3b32743`)
  - `uv sync --all-extras` 装齐依赖(llm/asr/frames/ocr/imagegen/longdoc/mcp,~5GB)
  - 备份 `output/` 旧产物 → `output-backup-2026-07-18/`
  - `scripts/run_smoke.py`(254 行)— 端到端 smoke runner + inbox 隔离 + 网络环境默认
  - `CLAUDE.md` §4.1 输出目录约定(项目级规则,2026-07-18 用户确认)
  - **inbox isolation bug fix**:`_isolate_inbox` 加 `exclude_dirs=[work]`,避免 rglob 误移 `output/asr/audio.wav`
  - **HF 下载修复**:`HF_ENDPOINT=https://hf-mirror.com` + `HF_HUB_DISABLE_XET=1`,显式 unset 系统代理
  - `transcript.jsonl` 部分产出(bx2o443en 后台跑中,49KB / 382 segments / 1582s)
- 撞墙:
  - HF 模型下载:proxy 502 → 直连超时 → xet 401 → 禁用 xet 走 hf-mirror.com 解决
  - inbox 隔离误移 work_dir 内文件:`rglob` 递归扫到 `output/`,audio.wav 被错误移走 → exclude_dirs 修复
  - CUDA 不可用:`torch.cuda.is_available()=False`,RTX 3090 + Windows + 当前 torch build 不兼容 → CPU 模式 ASR(112min 视频预计 1-2h)
  - 两个 ASR 并发争 CPU:`taskkill /F /PID` 杀掉 bre53o53u,让 bx2o443en 独占
- 关键决策:
  - HF mirror + 禁用 xet 是中国大陆用户默认网络配置
  - inbox 隔离必须排除 work_dir(work 在 inbox 子目录时尤其重要)
  - smoke 脚本顶部内置网络环境(setdefault 不覆盖用户传入)
- 测试:`uv run pytest` 346 passed / 3 skipped(未变,smoke 是产品代码不新增测试)
- 下次会话第一句:承接 `handoff-pipeline-w5-smoke-2026-07-18.md`,等 ASR 完成 + 续跑 + commit + 决定 W6 方向(B/C/D)
  - **W6 候选**:
    - B. Phase 2 L2 LE 闭环(迁移 `_research/le_prototype/`)
    - C. 接入 CLI `mtd run` / `mtd resume`
    - D. MCP server 接入(6 工具 + Claude Desktop 配置)

### 会话 10 — Phase 1 W5 端到端冒烟完成(2026-07-19,~3h)

- 完成任务(W5 完整跑通 + 修复 4 项真实 bug):
  - 起点:`bx2o443en` ASR 在 CPU 模式跑到 85.7%(5780/6743s)未完,主动 `taskkill //F //PID 30192` 接受部分 transcript
  - **Bug 1(OCR 路径)**:`runner.py` ocr 阶段不传 output_dir → OCR 写 `inbox/img/ocr/`,asr_correct 读 `work/ocr/` 不匹配 → JSONDecodeError
  - **Bug 2(Ollama 上下文)**:`LLMConfig.num_ctx` 默认 None → Ollama 用 4096 → 长 transcript 50816 tokens 超过 qwen3:14b max 40960
  - **Bug 3(transcript 截断)**:`_load_transcript` 不限长度 → chapters prompt 50k tokens
  - **Bug 4(longdoc/verify 路径布局)**:render W3 把 `<stem>.md` 写到 `<work>/chapters/raw/`,但 longdoc/verify 按旧布局找 `<drafts_dir>/<stem>.md`
  - **完整 11 stage 跑通**:audio → asr → frames → ocr → asr_correct → chapters → draft → imagegen(skip) → render → longdoc(skip) → verify
  - **`verify.json` overall_passed=true**,4 check 全 pass(outputs_exist / chapters_complete / image_refs / html_structure)
  - 最终产物:`output.md` 270 行 + `output_final.html` 25.8KB + `verify.json`
- 关键决策:
  - 主动 kill ASR 接受 85% transcript(避免 session 超时)
  - Ollama num_ctx 默认 65536(qwen3:14b 原生 32k,RoPE 扩展可接受)
  - chapters transcript 截断 30000 chars(适配 32k context,留 system prompt 余量)
  - longdoc/verify 兼容新旧两种布局(避免破坏 W4 测试)
- 测试:`uv run pytest` 349 passed / 3 skipped(+3 from W4 baseline,num_ctx integration)
- ruff:All checks passed
- W5 commits(3 个,feat/pipeline-w5-smoke 分支):
  - `db92ac9` fix(pipeline): W5 smoke fixes — OCR output path, num_ctx, transcript truncate, longdoc/verify layout
  - `82af24c` docs(handoff): add W5 pipeline snapshot + task.md progress
  - `29f018e` feat(scripts): W5 — smoke runner with inbox isolation
- 下次会话第一句:承接 `handoff-pipeline-w5-smoke-2026-07-19.md`,决定 W6 方向:
  - **B. Phase 2 L2 LE 闭环**(迁移 `_research/le_prototype/`)— 1.5-2h,基础设施
  - **C. CLI `mtd run`/`resume`**(11 stage 已就位,W5 smoke 验证过端到端)— 1h,最直接 win
  - **D. MCP server 接入**(6 工具 + Claude Desktop 配置)— 2-3h,产品价值最大

### 会话 11 — Phase 4 W6 CLI 实装(2026-07-19,~1.5h)

- 完成任务(ROADMAP Phase 4 W6 全完成):
  - 分支:`feat/cli-w6-run-resume`(基于 W5)
  - `src/media_to_doc/state.py`:加 `inbox_path: str | None = None` 字段(to_dict 同步)+ 让 resume 不必传 inbox
  - `src/media_to_doc/pipeline/runner.py`:`run_pipeline(inbox: Path | None, ...)` — inbox=None 时从 state.inbox_path 派生,自动写回
  - `src/media_to_doc/pipeline/audio.py`:`find_media(exclude_dirs=...)` — 让 CLI 在 work_dir 在 inbox 内时正确选目标视频
  - `src/media_to_doc/cli.py`:实装 4 条命令
    - `mtd run <inbox>`:`--work-dir`/`--llm`/`--llm-model`/`--imagegen`/`--longdoc-llm`/`--no-longdoc`/`--stop-after`/`--force`/`--no-isolate`/`--json`
    - `mtd resume <work>`:`--inbox`/`--force`/`--stop-after`/`--json`(默认从 state.json 派生)
    - `mtd status <work>`:`--json`(只读)
    - `mtd list [--workspace]`:`--json`(扫 inbox 子目录 + 媒体文件)
    - inbox 自动隔离 helper(从 smoke runner 抽出 + `--no-isolate` opt-out)
    - `eprint()` helper(走 stdout,绕开 Typer CliRunner 的 stderr 捕获限制)
  - `tests/test_cli.py`:21 用例覆盖全部 4 命令
- 测试:`uv run pytest` 349 → **370 passed**(+21),3 skip 不变
- ruff:All checks passed
- 端到端:`uv run mtd --version` / `mtd list` / `mtd list --json` / `mtd resume` 验证 OK
- 关键决策:
  - **resume 不必传 inbox**:state.inbox_path 持久化,`run_pipeline(inbox=None)` 自动派生
  - **JSON 输出绕开 Rich markup**:`sys.stdout.write(_json.dumps(...))` 而非 `console.print(json_str)`(Rich 把 `[...]` 当 markup 解析破坏 JSON)
  - **eprint 走 stdout**:Typer 0.12+ CliRunner 不支持 mix_stderr,让 eprint 走 stdout 便于测试 + MCP + 管道一致捕获
- W6 commit:`feat(cli): W6 — mtd run/resume/status/list with inbox isolation + JSON output`
- 下次会话第一句:承接 `handoff-pipeline-w6-cli-2026-07-19.md`,启动 W7(MCP server 或 LE 闭环):
- **推荐排序**:C → D → B(W6=C CLI ✅,W7=D MCP ✅,W8=B LE 待启动)

### 会话 12 — Phase 4 W7 MCP server(2026-07-19,~2h)

- 完成任务(ROADMAP Phase 4 W7 全完成):
  - 分支:`feat/pipeline-w7-mcp`(基于 W6 `23c1f96`)
  - `src/media_to_doc/mcp_server.py`(479 行):6 工具纯函数 + Server 单例 + handler 包装 try/except
  - `src/media_to_doc/cli.py`:`mtd mcp` 子命令实装(W7 占位 → 调 `mcp_server.main()`)
  - `tests/test_mcp_server.py`(30 用例):覆盖 6 工具纯函数 + 协议层 + 错误路径
  - `docs/MCP_INTEGRATION.md`:Claude Desktop 配置 + 6 工具签名 + 错误处理 + 调试
  - `README.md` + `CLAUDE.md` §9.4:同步 MCP 配置 + 6 工具清单
  - `task.md` Phase 4 全部 [x]
  - 测试:**400 passed / 3 skipped**(W6 370 + W7 30 MCP 用例)
  - ruff:**All checks passed**
  - W7 commit:`feat(cli): W7 — mcp_server.py + mtd mcp + 6 工具`
- 关键设计:
  - handler 同步 + 全部日志走 stderr(stdout 留给 JSON-RPC,参考实现 c80abaf)
  - 6 工具纯函数 + `handle_call_tool` 统一包装 try/except → `isError=True` TextContent
  - read-only 工具带 `ToolAnnotations(readOnlyHint=True)`(MCP 客户端可显示提示)
  - `tool_run_pipeline` 复用 cli 的 inbox 自动隔离 + 多视频场景处理
  - `tool_list_outputs` 用 `Path.parts[0] == "images"` 分类(Windows 路径分隔符兼容)
- 撞墙 / 修正:
  - `.srt` 不在 `SUPPORTED_EXTS` → 测试改用 `.mkv`
  - `rel.startswith("images/")` Windows 失败 → 改用 `Path.parts` 检查
  - `inbox` 空目录应抛错(原代码吞错) → `find_media` 直接抛 `FileNotFoundError`
  - ruff F401:`InitializationOptions` / `INBOX_DIR` / `contextlib` 未使用 → 删 import
- 技术债(给 W8+):
  - `read_lecture` 一次性读全文:大讲义(>1MB)可撑爆上下文,后续可加分页
  - `run_pipeline` 同步阻塞:长任务会卡住 MCP session,建议 `stop_after="chapters"` 先看 LLM 质量
  - `tool_run_pipeline` 在 transport 断开时不会自动停,后续可加 cancellation token
  - Claude Desktop 配置需要用户手改路径,F8+ 可加 `mtd init` 命令写默认配置
- 下次会话第一句:承接 `handoff-pipeline-w7-mcp-2026-07-19.md`,启动 W8(LE 闭环 + Phase 5 测试巩固):
  - **W8 候选**:
    - **A. Phase 6 L2 LE 闭环**(迁移 `_research/le_prototype/` 到 `src/media_to_doc/logger/`)+ 接到 11 真 stage
    - **B. Python API 顶层 re-export** + lazy import(PEP 562)— 让其它项目 `from media_to_doc import run_pipeline` 直接用
    - **C. 测试巩固**:Phase 5(目标 110+ 用例已超额完成,可选优化覆盖率)
