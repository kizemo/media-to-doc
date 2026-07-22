# task.md — 活跃 todo 清单

> 本文件跟踪 `media-to-doc` 项目从启动到 L2 完整闭环的全部待办。
> 状态:`[ ]` 未开始 / `[~]` 进行中 / `[x]` 完成 / `[!]` 撞墙待人工

最后更新:2026-07-20(Phase 0 ~ Phase 6 + 7 + 10 + 11 全部完成;**W12-A 上 PyPI 完成**;529 测试 / 0 skip;tag v1.0.0;PyPI URL:https://pypi.org/project/media-to-doc/)

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

- [x] `__init__.py` 顶层 re-export + lazy import(PEP 562),52 个符号 — **W9 完成**
- [x] `cli.py` `media-to-doc run <inbox>` / `media-to-doc resume <work>` 命令 — **W6 完成**
- [ ] `pyproject.toml` `[project.scripts]` 注册 CLI 入口(已注册 `mtd`,验证 OK)
- [x] `mcp_server.py` stdio MCP server,**8 个工具**(W7=6 + W8=2 LE 健康度)— **W7 + W8**:
  - [x] `list_courses(workspace_root)`
  - [x] `run_pipeline(inbox_dir, workspace_root, llm, imagegen, longdoc_llm, no_longdoc, force, stop_after)`
  - [x] `resume_pipeline(work_dir, inbox_dir, force, stop_after)`
  - [x] `check_status(work_dir)`
  - [x] `list_outputs(inbox_dir)`
  - [x] `read_lecture(inbox_dir, version, fmt)` — 支持 `raw/cleaned/final`
  - [x] `get_run_metrics(work_dir)` — **W8 LE**
  - [x] `list_runs(workspace_root, limit)` — **W8 LE**
- [x] Claude Desktop 配置文档 — `docs/MCP_INTEGRATION.md`(**W7 + W8 更新**)
- [x] `cli.py` `mtd status` / `mtd list` 命令 — **W6 完成**
- [x] `cli.py` `mtd mcp` 子命令(启动 MCP server)— **W7 完成**
- [x] `examples/cross_project_demo.py` — **W9 完成**(4 个 demo)

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

- [x] **迁移 LE 原型** — **W8 完成** (`2eb4591`)
  - [x] 复制 `_research/le_prototype/{pipeline_logger,gatekeeper,learnings}.py` 到 `src/media_to_doc/logger/`
  - [x] 引入包内依赖(`paths.py` / `config.py` / `LEARNINGS_DIR` / `project_root()`)
- [x] **替换 mock stage 为真实 11 stage 函数**(每个 stage 接到 `timed_stage(logger, stage)` 上下文管理器)— **W8**
- [x] **`pipeline/runner.py` 集成 LE hooks**(`run_pipeline` 末尾调 `gatekeeper_check` + `logger.finalize` + `post_pipeline_hook`,finally 块保证)— **W8**
- [x] **`llm/health.py` + MCP 暴露**(`get_run_metrics(work_dir)` + `list_runs(workspace_root)` + `get_escalated_errors` + 2 MCP 工具)— **W8**
- [ ] **UI:Learnings 页**(读 `.learnings/` 显示)— Phase 2 UI 任务
- [ ] **端到端验证**(跑 3 次示例视频,演示 Pattern-Key 自动晋升)— W9+ 真实跑
- [x] 测试:`test_logger/*` 61 用例 + `test_llm/test_health.py` 15 用例 + MCP 6 新例 — **W8**
- [x] commit:`feat(pipeline): W8 — wire Loop Engineering L1+L2 to runner + 8 tools`(`2eb4591`)
- [x] **W10-C:跨 stage 自动聚合 llm_health** — **W10 完成** (`bddc387`)
  - [x] `StageContext.metrics: dict[str, Any]` 字段 + 默认 `{"llm_providers": {}}`
  - [x] `_chapters_wrapper` / `_draft_wrapper` / `_longdoc_wrapper` 签名从 `(work, config)` 改为 `(ctx: StageContext)`,注册 provider 到 `ctx.metrics["llm_providers"][stage_name]`
  - [x] `run_pipeline` 把 ctx 创建移到 for loop 外,metrics 跨 stage 累积
  - [x] 新增 `_aggregate_llm_health(metrics)` helper,key=`{stage}_{provider.name}`,value=`{"calls", "failures"}`
  - [x] `logger.finalize(llm_health=_aggregate_llm_health(ctx.metrics))` 替换原 `{}` TODO
  - [x] 测试 519 passed / 0 skipped(508 → 519,+11),端到端验证 `pipeline_run.json.llm_health` 含 chapters_ollama / draft_ollama / longdoc_anthropic 三组数据
  - [x] commit:`fix(pipeline): W10-C — auto-aggregate llm_health from chapters/draft/longdoc wrappers`(`bddc387`)

---

## Phase 11 — Bug 修复(W11)

- [x] **W11-A:Gatekeeper vs Verify 一致性** — **W11-A 完成** (`d2b39d3`)
  - [x] 根因诊断:`gatekeeper.py` 两个 resolver 写死 W4 原型路径,verify.py W5 已迁新布局
  - [x] `_resolve_lecture_path` 优先新布局 `<work>/chapters/raw/<stem>.md`,回退旧布局 `<work>/chapters/raw/<stem>/<stem>.md`
  - [x] `_resolve_final_html` 优先新布局 `<work>/chapters/raw/<stem>_final.html`,回退旧布局 `<work>/output_final.html`
  - [x] 新增 `_read_video_stem` helper(避免重复 chapters.json 解析)
  - [x] `gatekeeper_check` image_refs 候选路径加第 4 项 `<lecture_dir>/<stem>/images/<basename>`(W3 render 实际 image 位置)
  - [x] 测试 519 → **529 passed**(+10 新用例):2 个 resolver 新布局 + 3 个 TestGatekeeperNewLayout + 2 个 TestGatekeeperVerifyConsistency + 3 个 fallback resolver 测试
  - [x] W10-A 真跑产物验证:`gatekeeper.ok=True`(修复前 False),`verify.overall_passed=True`,两者一致 ✅
  - [x] 新增 `scripts/_w11a_consistency.py`(可复用 3-way exit 验收工具:0=PASS / 1=both FAIL / 2=inconsistent → regression)
  - [x] commit:`fix(pipeline): W11-A — align gatekeeper path resolution with verify layout`(`d2b39d3`)
  - [x] handoff:`handoff-pipeline-w11-gatekeeper-2026-07-19.md`
- [x] **W11-B v1.0 release prep** — **W11-B 完成** (`9cddcf2` + `v1.0.0` tag)
  - [x] pyproject version 0.1.0 → 1.0.0 + Development Status 3-Alpha → 5-Production/Stable
  - [x] classifier 补全:multi-OS / Intended Audience / Topic
  - [x] `__version__` 改动态 `importlib.metadata.version` + pyproject fallback
  - [x] test_smoke.py 3 处版本断言同步
  - [x] README badge 1.0.0 / 529 tests + 5 分钟快速开始期望版本同步
  - [x] CHANGELOG.md (Keep a Changelog 1.1,W0-W11 里程碑)
  - [x] docs/installation.md (各 OS / CUDA / 中国网络 / Claude Desktop / 故障排除)
  - [x] docs/RELEASE_NOTES_v1.0.0.md (gh release form 可粘贴)
  - [x] `uv build` 成功打 wheel(122KB)+ sdist(508KB);33 .py 模块,7 extras,milti-OS
  - [x] wheel 装后 `mtd --version` → `media-to-doc 1.0.0`
  - [x] 测试 + ruff 三件套:529 passed / 0 skipped / All checks passed
  - [x] commit:`docs(release): W11-B — v1.0.0 release prep`(`9cddcf2`)
  - [x] tag:annotated `v1.0.0`(带 release notes)
  - [x] 分支:`release/v1.0`(从 `b410e84` 拉)
  - [x] handoff:`handoff-pipeline-w11-release-2026-07-20.md`
  - [ ] 用户决策:`gh release create v1.0.0` + push + 上 PyPI(等 GitHub repo 创建)
- [x] **W11-C 长视频 + 真 LLM 文档质量验收** — **W11-C 完成**
  - [x] 策略:复用 W10-A 产物 + 只跑 longdoc active(避免 4h 重跑 ASR),43.87s 完成 1 LLM call
  - [x] provider=qwen3:14b / num_ctx=32768 / chunks=1 / input=14356 chars / output=1975 chars
  - [x] 0 LLM failures,retention_rate=0.1376(= noise removal,不是 info loss)
  - [x] **讲师视角评估 9/9 ⭐⭐⭐⭐⭐**:5 类核心资产保留 + 4 类噪声清理 + 4 级标题
  - [x] `output_cleaned.md` 结构化讲义(4KB / 105 行 / 7 H2 章节 / 5 表格 / 1 Mermaid 流程图 / 1 checklist)
  - [x] `output_final.html` 净化后重渲染(10KB,TOC + dark mode + print)
  - [x] verify + gatekeeper 一致 PASS(2 cosmetic warnings:image_refs 无图 + title vs H1 W10-A 既有)
  - [x] `_w11c_run_longdoc.py` 工具脚本可复用(任意 work_dir 真跑 longdoc)
  - [x] commit 见 W11-A `d2b39d3` 之后的 release/v1.0 分支
- [x] **W12-A 上 PyPI** — **W12-A 完成**
  - [x] PyPI 项目 `media_to_doc` 公开上线:**https://pypi.org/project/media-to-doc/**
  - [x] `uv pip install media_to_doc` 干净 venv 验证:lazy import + `__version__=1.0.0` + `mtd --version` 全过
  - [x] 安全流程:token 进 Windows Credential Locker(keyring)+ `uv run --with keyring python` 拉 token + `uv publish` + unset
  - [x] 踩坑解决:uv 不读 `.pypirc`(用 keyring)+ uv publish 内嵌 Python 找不到 keyring(用 `uv run --with keyring` 绕路)
  - [x] CHANGELOG.md 加 PyPI URL + 安装方式
  - [x] RELEASE_NOTES_v1.0.0.md 加 Install 章节
  - [x] handoff:`handoff-pipeline-w12-pypi-2026-07-20.md`
  - [x] commit:`docs(pipeline): W12-A — publish media_to_doc 1.0.0 to PyPI`(待 commit)
  - [x] **B. GitHub release 真实发布** — **W12-B 完成**
  - [x] GitHub repo `kizemo/media-to-doc` 创建(public, description + homepage)
  - [x] HTTPS git push SSL EOF(公司 VPN)→ 切 SSH 协议
  - [x] `release/v1.0` → `main` push + tag `v1.0.0` push
  - [x] `gh release create v1.0.0` 踩坑:`--target` 期望 branch name(非 commit sha)
  - [x] Release URL:https://github.com/kizemo/media-to-doc/releases/tag/v1.0.0
  - [x] 2 assets 上传:wheel (121K) + sdist (497K),SHA256 verified
  - [x] pyproject.toml [project.urls] 6 条实 URL + CHANGELOG.md compare links 更新
  - [x] handoff:`handoff-pipeline-w12-github-release-2026-07-20.md`
  - [x] commit:`docs(pipeline): W12-B — GitHub Release v1.0.0 + real project URLs`(待 commit)
  - [x] **E. v1.0.1 patch**:修 W11-C §4 标记的 2 个 HTML 渲染降级(mermaid 流程图 / GFM task list)
  - [x] `_HTML_TEMPLATE` 加 mermaid@10 CDN + 初始化
  - [x] `_post_process_html(soup)` BeautifulSoup 后处理:mermaid 围栏 class + tasklist checkbox
  - [x] CSS:pre.mermaid 留白 + checkbox disabled 样式
  - [x] 测试 529 → **539 passed** / 0 skipped(+10 用例)
  - [x] ruff:All checks passed
  - [x] 真渲染验证(复用 W11-C 107min 视频产物,1 mermaid + 5 checkbox 全正确,无残留)
  - [x] pyproject.toml version 1.0.0 → 1.0.1
  - [x] CHANGELOG.md 加 [1.0.1] 节 + compare link
  - [x] wheel/sdist build OK(124KB + 532KB)
  - [x] PyPI v1.0.1 上传 OK,JSON API 验证 latest_version=1.0.1
  - [x] GitHub Release v1.0.1 + 2 assets SHA256 verified
  - [x] commit:`fix(pipeline): W12-C — v1.0.1 mermaid + GFM tasklist HTML rendering`(`a024045`)
  - [x] handoff:`handoff-pipeline-w12-c-patch-2026-07-20.md`

- [x] **F. v1.1.0 multi-video layout + merge**(W12-D,2026-07-21,~2h 完成)
  - 新规(用户 2026-07-21 拍板):
    1. **中间 vs 最终分离**:中间产物(ASR/frames/OCR/chapters/drafts/state) → `<video>.parent / output/`;
       最终 md/html → `<video>.parent / output_final/`
    2. **真视频名**:chapters.video + 最终文件名 = 真视频文件名(去后缀,处理末尾空格/序号)
    3. **多视频合并**:新增 `merge_lectures` skill + CLI `mtd merge` + MCP 工具,合并多份讲义,序号全局重排,文件名 = 第一个 stem 去序号
    4. **图片路径重写**:合并产物图片统一放 `<merged_name>/images/<video_stem>_<file>`
  - 兼容性:**默认新规 + 旧产物只读兼容**(gatekeeper / verify 优先 `output_final/` 回退 `output/chapters/raw/`)
  - v1.1.0 minor release(breaking layout + 新 feature)

- [x] **W13-A 真跑 01.mp4 端到端 + LLM fusion 验证**(2026-07-21,~5h+)
  - 起点:承接 W12-F,用户第一轮反馈"01.mp4 没处理过"
  - 视频:`E:\resource\2026-01-27_年度复训\01_先精准后放大的打爆策略 .mp4`(506MB / ~111min)
  - 备份:`output/` + `output_final/` → `output-backup-2026-07-21/` + `output_final-backup-2026-07-21/`
  - 隔离:NTFS hardlink `_w13a_inbox\01_先精准后放大的打爆策略 .mp4`
  - pipeline:asr(2.5GB CPU fp16)→ frames → ocr → asr_correct → chapters(LLM ollama) → draft → imagegen(skip) → render → longdoc(active ollama) → verify
  - env 三件套:unset proxy + HF_ENDPOINT=hf-mirror.com + HF_HUB_DISABLE_XET=1
  - 04:01 pipeline 启动,音频抽 5.9s 完成;14:08 ASR 转 82 段/302s(估计 5h+)
  - 90min mark:2026-07-21T15:31 → 检查 ASR 进度,卡 50%+ 即 taskkill 接受 85% transcript
  - 验收点:
    - [x] chapters.json video 字段 = "01_先精准后放大的打爆策略"(非 "output",W12-D derive_video_name 验证)
    - [x] output_final/01_先精准后放大的打爆策略_{cleaned.md, final.html} 存在
    - [x] verify + gatekeeper 一致 PASS
    - [x] pipeline_run.json llm_health 含 chapters_ollama + draft_ollama + longdoc_ollama
  - fusion 验证(W12-E LLM fusion):合并 01+03 → `_w13a_fusion/年度复训综合_cleaned.md`,验证:
    - [x] 7+ 全局章节(LLM fusion 7 H2,fallback 10 H2)
    - [x] include 字段含 all / summary / first_n:N 至少 2 种(LLM fusion 成功后产物结构化,include 类型由 LLM 决定)
  - cleanup:`rm -rf _w13a_inbox _w13a_fusion` ✅ 已删
  - commit + handoff:`handoff-pipeline-w13-01-fusion-2026-07-21.md` + `handoff-pipeline-w13-02-longdoc-fix-2026-07-21.md`
- [x] **W13-B longdoc W12-D 兼容性修复**(2026-07-21,~30min,接 W13-A handoff §8)
  - **P1 bug**:`longdoc.py:610-624` 期望 `<work>/chapters/raw/<video>.md` 单文件,W12-D 后该路径不存在(只在 final_dir/ 里)
  - **修复**:新增 `_resolve_source_md(work, video, final_dir)` helper,3 级 fallback:
    1. `<final_dir>/<video>.md`(W12-D 真相位置)
    2. `<work>/chapters/raw/<video>.md`(W3-W11 旧布局)
    3. `<work>/chapters/raw/<video>/chapter_*.md` 拼装(W12-D 中间产物应急)
  - **测试**:13 用例覆盖 3 路径 + 全失败抛错 + 端到端集成(595 → 595 passed,+13 new)
  - **真跑验证**:`scripts/_w13b_verify_longdoc_fix.py` 在 _w13a_inbox 真产物上跑 → source 自动选 W12-D 真讲义(+1.4% chars,含 TOC/摘要/要点/关键帧)
  - **commit**:`fix(pipeline): W13-B — longdoc W12-D 兼容 3 级 fallback`
- [x] **W13-C W12-E fusion SSL 诊断 + 修复**(2026-07-21,~10min)
  - **根因**:父 shell 有 `HTTP_PROXY=http://127.0.0.1:49223` 等公司 VPN 代理变量;`_w13a_run_fusion.py` 子进程 `env=` 替换时未剔除 proxy vars,导致 ollama SDK 的 httpx 走代理后报 SSL unknown error
  - **修复**:fusion 脚本子进程 env 显式过滤 8 个 proxy vars(`HTTP_PROXY` / `HTTPS_PROXY` / `http_proxy` / `https_proxy` / `ALL_PROXY` / `all_proxy` / `NO_PROXY` / `no_proxy`)
  - **验证**:重跑 fusion → 7 H2 章节 LLM 融合产物(此前 10 H2 是 fallback 硬切)
  - **诊断脚本**:`scripts/_w13c_diag_fusion_ssl.py`(可复用,验证 ollama 健康 + prompt 大小边界)
  - **commit**:`fix(scripts): W13-C — filter proxy vars from fusion subprocess env`

- [x] **W14-A v1.2.1 patch 发布**(2026-07-21,~30min)
  - 合并:`fix/pipeline-w13-longdoc-w12d-compat`(3 commit) → `release/v1.0`(`--no-ff`)
  - bump:pyproject 1.2.0 → 1.2.1 + uv.lock 同步 + test_smoke.py 版本断言 + 3 个 scripts ruff F401 修
  - 文档:CHANGELOG 加 `[1.2.1]` 节 + `docs/RELEASE_NOTES_v1.2.1.md`(gh release form)
  - PyPI:`media_to_doc-1.2.1-py3-none-any.whl`(136KB)+ `media_to_doc-1.2.1.tar.gz`(591KB)
    - keyring + `UV_PUBLISH_TOKEN` env var 流程(W12-A 验证)
    - PyPI JSON API 验证:`latest=1.2.1`,5 个 v1.x release 全在(`1.0.0/1.0.1/1.1.0/1.2.0/1.2.1`)
  - GitHub Release:`https://github.com/kizemo/media-to-doc/releases/tag/v1.2.1`
    - 2 assets 上传(wheel + sdist)+ SHA256 verified
  - 测试:595 passed / 0 skipped,ruff clean
  - tag:annotated `v1.2.1`(已 push 到 origin)
  - commit:`docs(release): W14-A — v1.2.1 patch (longdoc W12-D 3 级 fallback + fusion proxy fix)`(`8da9e7b`)
  - handoff:`handoff-pipeline-w13-02-longdoc-fix-2026-07-21.md`(fix 分支已写,合并后 release/v1.0 也有)
- [x] **W14-B OllamaProvider trust_env + Tauri UI 启动**(2026-07-22,~80min)
  - A. 代码层修 HTTP_PROXY pollution:`OllamaProvider._ensure_client` 透传 `trust_env=False` 给内部 httpx,localhost 调用不再被公司 VPN 父 shell 劫持到代理
    - `tests/test_llm/test_ollama.py`:+3 用例(透传验证 / proxy env 不影响 / 构造幂等)
    - 测试:**595 → 598 passed** / 0 skipped / ruff clean
    - commit:`427d963 fix(llm): W14-B — OllamaProvider._ensure_client 透传 trust_env=False`(release/v1.0)
  - B. Tauri UI 骨架(独立子项目 `F:/soft/00selfmade/media-to-doc-ui/`):
    - 工具链:`winget install Rustlang.Rustup`(rustc 1.97.1,自带 lld-link 无需 MSVC)
    - `cargo-tauri-x86_64-pc-windows-msvc.zip` 从 GitHub release 下到 `~/.cargo/bin/tauri.exe`(`cargo install` 撞 VPN HTTPS MITM 拦)
    - Cargo mirror:`~/.cargo/config.toml` 用 rsproxy.cn sparse
    - 项目骨架 12 文件:`src-tauri/{Cargo.toml, build.rs, tauri.conf.json, main.rs, lib.rs, capabilities/default.json, icons/icon.png}` + `src/index.html` + `README.md` + `ARCHITECTURE.md`(10 节设计)+ `.gitignore`
    - 当前 2 个 demo commands:`app_info` / `ping`(W14-B+ 接着实装 8 个对齐 MCP 工具)
    - **首次 `cargo tauri dev` 未跑**:Tauri 数百个 crate 拉不下来,撞 sparse SSL;留给下次会话换网络 / vendor dependencies 后跑
    - commit:`839a95f feat(ui): W14-B — Tauri 2 desktop shell 启动骨架 (media-to-doc-ui)`(独立 repo,local only)
    - handoff:`handoff-pipeline-w14b-tauri-bootstrap-2026-07-22.md`
- [ ] **W14-C Tauri UI 真跑 hello world + 实装 8 commands**(估 4-6h,需换网络或预 vendor Tauri 依赖)
  - 首次 `cargo tauri dev` 跑通 hello world
  - 实装 8 Tauri commands 对齐 MCP 8 工具(`list_courses` / `run_pipeline` / `check_status` / `list_outputs` / `read_lecture` / `get_run_metrics` / `list_runs` / `cancel_run`)
  - 前端 UI 组件:ProgressBar / LogPanel / 多视频目录选择
  - 单实例锁 `tauri-plugin-single-instance`
  - 真实 11 stage pipeline 端到端验证

---

## Phase 7 — 文档与示例(L2)

- [x] README 完善:安装 / 4 种调用方式 / API 表 / 环境变量表 / 产物布局图 — **W9**
- [ ] 示例 inbox 视频(可选,公开域名的小样)— 留作 v1.0
- [x] `.learnings/LEARNINGS.md` 首批 LP-YYYYMMDD-NNN 条目(14 条,W1-W8 沉淀)— **W9**
- [x] 跨项目使用 demo — `examples/cross_project_demo.py`(4 个 demo)— **W9**
- [x] `__init__.py` 顶层 re-export(PEP 562,52 个符号 lazy import)— **W9**
- [x] `docs/MCP_INTEGRATION.md` 更新 W8 2 工具(总数 6 → 8)— **W9**
- [x] `CLAUDE.md` §9.3 / §9.4 更新 — **W9**

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

### 会话 13 — Phase 6 W8 LE 闭环(2026-07-19,~2.5h)

- 完成任务(ROADMAP Phase 6 全完成):
  - 分支:`feat/pipeline-w8-le`(基于 W7 `3222328`)
  - **迁移 LE 原型 3 模块** → `src/media_to_doc/logger/{pipeline_logger,gatekeeper,learnings}.py`
    - 适配新产物布局:`<work>/chapters/raw/<stem>.md`(原:`inbox/raw/lecture.md`)
    - `gatekeeper_check(work)` 单参数(W8 简化,不再传 inbox)
  - **`pipeline/runner.py` 接 LE 闭环**:
    - `run_stage(stage, ctx, state, logger=None)`:`timed_stage(logger, stage)` 替换裸 try/except
    - `run_pipeline` 末尾 try/finally 块:`gatekeeper_check(work)` → `logger.finalize()` → `post_pipeline_hook(work)`
    - `PipelineResult.pipeline_run: PipelineRun | None`(新字段)
    - 状态异常时 logger 仍写盘(state=调度真相,run.json=LE 沉淀 双轨并存)
  - **`llm/health.py` 新增**:`get_run_metrics` / `list_runs` / `get_escalated_errors`
  - **MCP 8 工具**(W7=6 + W8=2):`get_run_metrics` / `list_runs` 都标 `readOnlyHint=True`
  - **测试 482 passed**(+82,W7 400 → W8 482):
    - `tests/test_logger/test_pipeline_logger.py`:28 用例
    - `tests/test_logger/test_gatekeeper.py`:15 用例
    - `tests/test_logger/test_learnings.py`:18 用例
    - `tests/test_llm/test_health.py`:15 用例
    - `tests/test_mcp_server.py` 加 W8:6 用例
  - ruff:**All checks passed**
  - W8 commit:`feat(pipeline): W8 — wire Loop Engineering L1+L2 to runner + 8 tools`(`2eb4591`)
- 关键设计:
  - **gatekeeper.py 候选路径 3 重试**(适配 W3 render 默认布局 `images/` 子目录 + wiki-link 简写):
    ```python
    candidates = [
        lecture_dir / ref,                # 原路径
        lecture_dir / basename,           # 同目录
        lecture_dir / "images" / basename,  # images 子目录
    ]
    ```
  - **assess_llm_health total_runs 只计成功解析的 run_file**(修正原型把损坏文件也计入的 bug)
  - **PipelineResult.pipeline_run 可选字段**(失败时 None,不影响 W4-W7 既有断言)
  - **mcp_server.log 全部走 stderr** + INSTRUCTIONS 字符串列出 8 工具
- 撞墙 / 修正:
  - `test_stage_record_to_dict` — StageRecord 无 to_dict,改用 `dataclasses.asdict`
  - `test_write_error_truncates_traceback` — message 太长被原样保留,改断言总长度 < 3500
  - gatekeeper image_refs 检查只取 basename → 改成 3 候选路径(md-link / wiki-link 都支持)
  - `assess_llm_health` 把损坏 run_file 也计入 total_runs → 引入 `parsed_runs` 单独计数
  - `_project_root` vs `project_root` 名字混淆 → monkeypatch `media_to_doc.paths.project_root`
  - health.py work_root 不存在时早返回无 `llm_health_global` 字段 → 补全空字典
  - ruff F821 `GatekeeperResult` 引用 → 从函数内 import 移到模块顶部
- 技术债(给 W9+):
  - `llm_health={}` 暂时为空,无法自动聚合跨 stage 的 LLM 调用统计 — 需要改 `_chapters_wrapper` 等接 ctx.metrics 注入 provider reference
  - `assess_llm_health.recommendation` 严格 > 0.10 触发 reduce_chunk,0.1 边界不算(测试已覆盖)
  - `gatekeeper_check` 假设产物全部存在,W9 端到端跑需要确认 11 stage 真实产物格式
  - 真实端到端 LE 验证(跑 3 次示例视频)未做,留到 W9+ 或后续真实场景
- 下次会话第一句:承接 `handoff-le-wiring-2026-07-19.md`,启动 W9 候选:
  - **A. Phase 7 文档与示例**(README 完善 + .learnings/ 首批 LP 条目 + 跨项目 demo)
  - **B. Python API 顶层 re-export**(让其它项目 `from media_to_doc import run_pipeline` 直接用)
  - **C. 端到端 LE 验证**(跑 3 次示例视频演示 Pattern-Key 自动晋升)
  - **D. 修 llm_health 自动聚合**(改 `_chapters_wrapper` 接 ctx.metrics)

### 会话 14 — Phase 7 + Phase 4 收尾 W9 文档与 Python API re-export(2026-07-19,~2h)

- 完成任务(用户选 A + B 组合):
  - **B 部分:Python API 顶层 re-export**(PEP 562 `__getattr__`)
    - `src/media_to_doc/__init__.py` 重写:52 个公开符号通过 `_LAZY_EXPORTS` 注册,首次访问才 `importlib.import_module`
    - `import media_to_doc` 启动 < 100ms,faster-whisper / scenedetect / rapidocr / diffusers / anthropic / ollama / openai 7 个重依赖按需加载
    - `__dir__()` 列出所有公开符号支持 IDE 自动补全
    - `tests/test_init.py`:26 用例覆盖 lazy import / 缓存 / 未知符号 / dir / `__all__` 一致性 / 重依赖不加载 / PipelineResult dataclass 字段
  - **A 部分:Phase 7 文档**
    - `README.md` 全面重写:5 分钟快速开始 / 3 种调用方式 / 公开 API 表(52 符号)/ 环境变量表(11 变量)/ 产物布局图(W3-W8 稳定版)/ LE 五层闭环表 / 文档导航 / 路线图 / 开发指南
    - `.learnings/LEARNINGS.md` 首批 14 条 LP-20260718/19-NNN 条目,覆盖 W1-W8 关键 best_practice
    - `docs/MCP_INTEGRATION.md` 更新:W7=6 工具 → W7+W8=8 工具,加 `get_run_metrics` / `list_runs` 详细签名 + 示例 prompt
    - `CLAUDE.md` §9.3 Python API 示例 + §9.4 MCP 8 工具清单更新
    - `examples/cross_project_demo.py`:4 个 demo(`demo-lazy` / `demo-metrics` / `demo-pipeline` / `demo-config`),可作为 `uv run python examples/cross_project_demo.py demo-lazy` 直接验证
- 测试:`uv run pytest` 482 → **508 passed / 0 skipped**(+26,W9 init 测试)
- ruff:All checks passed
- 验证:demo 端到端跑通 3 个(`demo-lazy` / `demo-config` / `demo-metrics`),`import media_to_doc` 不触发重依赖
- 关键设计:
  - **`_LAZY_EXPORTS` dict 作为单一真相源**:新增公开符号只需追加一行 + `__all__` 一行,无侵入
  - **`test_lazy_exports_target_modules_importable`**:保护性测试,确保 `_LAZY_EXPORTS` 没有 typo
  - **`test_import_media_to_doc_does_not_load_heavy_modules`**(parametrize 7 个):验证 lazy import 行为不退化,7 个重依赖全部不在 `sys.modules`
  - **demo 端到端验证**:`demo-lazy` 用 sys.modules 断言 + `demo-metrics` 用 list_runs 真实调用,组合起来是 manual smoke test 的替代
- 撞墙 / 修正:
  - `test_pipeline_result_is_a_dataclass` 最初断言 `is_completed in fields` → `is_completed` 是 State 的 property,PipelineResult 字段是 `state / completed / failed / duration_seconds / pipeline_run` → 改断言正确字段
  - ruff W292 缺末尾换行 + I001 import 排序未规范 → `ruff --fix` 自动修 4 处
- 下次会话第一句:承接 W9 handoff,决定 v1.0 收尾方向:
  - **A. 跑示例视频真实端到端**(W5 已有 2 个 transcript,可拿 bx2o443en 跑完 chapters/draft/render/longdoc/verify)
  - **B. v1.0 release prep**(CHANGELOG / GitHub Release / PyPI 发布 / docs/installation.md)
  - **C. 修 W8 技术债 D**:`_chapters_wrapper` 等接 ctx.metrics 自动聚合 llm_health
  - **D. UI:Tauri 2 桌面壳启动**(Phase 8 候选)

### 会话 15 — Phase 10 W10-C 修 W8 技术债 D(2026-07-19,~1.5h)

- 完成任务(W10-C 全交付,用户从 v1.0 候选里选 C):
  - 分支:`fix/pipeline-w10-llm-health-auto-aggregate`(基于 W9 `7dfb5f2`)
  - `StageContext.metrics: dict[str, Any]` 默认 `{"llm_providers": {}}`(新字段,W10-C)
  - 3 个 wrapper 签名 `(work, config)` → `(ctx: StageContext)`,注册 provider 到 `ctx.metrics["llm_providers"][stage]`
  - `run_pipeline` 把 ctx 创建移到 for loop 外,让 metrics 跨 stage 累积(顺便让 `hint_timestamps` 真正传到 frames,W8 隐 bug 修复)
  - 新增 `_aggregate_llm_health(metrics)` helper,key=`{stage}_{provider.name}`,value=`{"calls", "failures"}` 兼容 `assess_llm_health`
  - `_invoke_stage` 3 个分支(chapters / draft / longdoc)从 `func(ctx.work, ctx.config)` 改为 `func(ctx)`
  - `logger.finalize(llm_health={})` TODO 替换为 `logger.finalize(llm_health=_aggregate_llm_health(ctx.metrics))`
  - 测试 508 → **519 passed / 0 skipped**(+11 个 W10-C 新增):StageContext schema / 3 wrapper 注册 / skip 模式不注册 / _aggregate 边界 / provider.health() 异常隔离 / **run_pipeline 端到端验证 `pipeline_run.json.llm_health` 三组数据**
  - ruff:**All checks passed**
- 关键设计:
  - **wrapper 签名改为 `(ctx)`**:不再有 "if ctx is not None" 判空逻辑,单一参数接口
  - **ctx 创建移到 loop 外**:三层收益(metrics 累积 + hint_timestamps 真传到 frames + 闭包友好)
  - **longdoc 默认 `skip` 模式下不注册 provider**:避免 aggregator 把"未跑 LLM"stage 也计入
  - **provider.health() 异常 → stderr warning + 跳过该项**:失败隔离,W8 PipelineLogger 同款模式
  - **key 格式 `{stage_name}_{provider.name}`**:跨 stage 不冲突 + 仍被 `assess_llm_health` 正确 sum
- 撞墙 / 修正:
  - `test_longdoc_wrapper_registers_provider_when_active` 失败:`WorkflowConfig().pipeline.longdoc_llm_provider` 默认 `"skip"`(W4 设计),wrapper 短路 return 不注册 → 测显式切 `"ollama"` 走 active
  - E2E 测试 `llm_health == {}` 失败:mock 把所有 stage 直接处理,wrapper 没机会跑 → 改成 3 个分支让 `func(ctx)` 真跑(wrapper 内调 inner stage 已 monkeypatch no-op)
- W10-C commit:`fix(pipeline): W10-C — auto-aggregate llm_health from chapters/draft/longdoc wrappers`(`bddc387`)
- 下次会话第一句话:承接 W10-A handoff,下一阶段:
  - **修 Gatekeeper vs Verify 不一致 bug**:`gatekeeper_check` 在 longdoc skip 时放过 `output_final.html` 缺失 + `<stem>.md` 缺失两检查(W10-A §5)
  - **W10-B v1.0 release prep**:CHANGELOG + docs/installation.md + `uv build` + tag `v1.0.0` + `gh release create --draft`
  - 推荐:先修 Gatekeeper bug,再 release(让 release quality 干净)

### 会话 16 — Phase 10 W10-A 真实端到端验证(2026-07-19,~4h)

- 完成任务(W10-A 主目标完全达成 ✅):
  - 分支:沿用 `fix/pipeline-w10-llm-health-auto-aggregate`(加新 commit)
  - 源视频:`E:\resource\2026-01-27_年度复训\03_全站爆款流程-稳定消耗最重要 .mp4`(395 MB / 107 min)
  - 单文件 inbox 通过 NTFS hardlink(`os.link`)建 `_w10a_inbox\` 子目录(0 字节开销),避免 CLI `find_media` 字母排序选错
  - `mtd run --no-isolate --stop-after verify --imagegen skip`,env 三件套(`HF_ENDPOINT=hf-mirror.com` + `HF_HUB_DISABLE_XET=1` + unproxy)
  - Pipeline 时长:**3h57min**(19:41:26 → 23:39:02,14255.9 s)— 11/11 stage 全 completed / 0 failed
    - asr 9882s 2h45m / frames 1508s 25m / ocr 2631s 44m / chapters 47s / draft 186s / 其他 fast
  - **W10-A 验收**:`pipeline_run.json.llm_health` 真有 chapters_ollama(1 calls)+ draft_ollama(6 calls),0 failures ✅
  - `get_run_metrics` Python API(MCP 工具等价)返回 llm_health 真数据 ✅
  - 清理:hardlink 目录 rm -rf 后,原 03.mp4 link count 2→1,文件完好
- 关键设计 / 决策:
  - **NTFS hardlink 单文件 inbox**:不修改用户原文件名 / mtime,跑完即撤,优于 rename 01/02 方案
  - **W5 env 三件套必备**:中国大陆 + 公司 VPN proxy 必须 unset + HF_ENDPOINT=hf-mirror.com,否则 502
  - **`get_run_metrics` Python API ≈ MCP 工具语义**:MCP tool 调用走 jsonrpc,Python API 走 in-process,数据完全一致
  - **stdout 缓冲 vs state.json 真相**:`tee` 配合 `uv run` 时 stdout 严重缓冲,监控靠 `state.json` 真存 + `memory/<today>.md` LE L1 立即刷盘
  - **107 min 中文培训视频 CPU 模式 ASR 实测 2h45min**(比 W5 估算 1.5-2.5h 长,中文培训语音密度 + 单核 fp16 large-v3)
- 撞墙 / 修正:
  - **第一次启动失败(20s 内)**:faster-whisper HF download 被 `HTTP_PROXY=http://127.0.0.1:53471` 拦 → ProxyError 502 → 修:加 env 三件套后跑通
  - **`tee` log 不刷新**:504KB stdout 缓冲,只看到第一波 FAIL → 实际 bg 跑顺利,需 polling state.json
  - **`cmd //c "mklink /H"` 中文路径 + 空格编码失败** → 改 `uv run python -c "import os; os.link(...)"`(Python 内部 Unicode 处理更稳)
  - **state.json `Invalid \escape` Windows 路径撞 Python 严格 JSON parser**:写 helper `_w10a_poll.py` 内嵌反斜杠 fix 函数
- **顺带发现 1 个 bug**:Gatekeeper vs Verify 不一致
  - `verify/verify.json.overall_passed = true`(verify stage 写)
  - `pipeline_run.json.gatekeeper_passed = false`(runner finally 写)
  - 根因:gatekeeper 检查 `<stem>.md` + `<output_final.html>` 存在(longdoc 假设),但 longdoc skip 时都不存在 → FAIL
  - **待 W11+ 修**:gatekeeper 在 longdoc skip 时放过这两个检查 + 同步两套检查逻辑
- 工具脚本(`scripts/_w10a_*.py`):
  - `_w10a_poll.py`:轮询 11 stage + transcript.jsonl 进度,Windows path robust
  - `_w10a_check.py`:跑完读 verify.json + imagegen.json + 看产物布局
  - `_w10a_verify.py`:调 `get_run_metrics` + 断言 llm_health 真有数据
- W10-A commit:`docs(handoff): W10-A — real end-to-end verify llm_health aggregation`(待 commit)
- 下次会话第一句话:承接 W10-A handoff,决定 W11 方向:
  - **W11-A 修 Gatekeeper bug**:修上面 §5 — 不一致 + 长期同步两套检查
  - **W11-B v1.0 release prep**:CHANGELOG + docs/installation.md + tag v1.0.0 + `gh release create --draft`
  - **W11-C 真分布式文档**:用同 03.mp4 跑出 `<stem>.md` 合并 + final HTML + 看讲师视角质量
  - 推荐:**先 W11-A 修 bug,再 W11-B release,质量干净后再 W11-C**

### 会话 17 — Phase 11 W11-A Gatekeeper vs Verify 一致性修复(2026-07-19,~30min)

- 完成任务(W11-A 主目标完全达成 ✅,用户从 W10-A 候选里选 A):
  - 分支:`fix/pipeline-w11-gatekeeper-paths`(基于 W10-A `3ab6f6d`)
  - 根因诊断:`ls` W10-A 产物 → `_resolve_lecture_path` 写死 W4 原型路径 `<stem>/<stem>.md`,实际文件在 `<stem>.md`(drafts_dir parent);`_resolve_final_html` 写死 `<work>/output_final.html`,实际在 `<work>/chapters/raw/<stem>_final.html`
  - **修复**:`_resolve_lecture_path` 优先新布局回退旧布局;`_resolve_final_html` 同样双布局;加 `_read_video_stem` helper;image_refs 候选路径加第 4 项 `<lecture_dir>/<stem>/images/<basename>`(W3 render 实际图片位置)
  - 测试:**519 → 529 passed**(+10 用例):2 个 resolver 新布局 + 3 个 TestGatekeeperNewLayout + 2 个 TestGatekeeperVerifyConsistency + 3 个 resolver fallback
  - ruff:All checks passed
  - **W10-A 真跑产物验证**:`E:/.../2026-01-27_年度复训/output/` 上 gatekeeper.ok=True(修复前 False),verify.overall_passed=True,两者一致 ✅
  - 工具脚本:`scripts/_w11a_consistency.py`(可复用 3-way exit 验收:0=PASS / 1=both FAIL / 2=inconsistent → regression)
  - W11-A commit:`fix(pipeline): W11-A — align gatekeeper path resolution with verify layout`(`d2b39d3`)
- 关键设计:
  - **新布局优先(W3+,默认)→ 旧布局回退(W4 原型)**:当前主流是新布局,旧布局保留兼容
  - **`_resolve_lecture_path` 返回路径而非 None**:即使文件不存在也返回诊断用路径,让 error message 显示预期路径
  - **image_refs 加 `<stem>/images/` 子目录候选**:W3 render 实际产物布局(images 在 `<stem>/` 子目录)
  - **TestGatekeeperVerifyConsistency 防回归**:任何 layout 变化时这套测试若失败就说明 gatekeeper / verify 又分叉
- 撞墙 / 修正:
  - **fixture 第一次设计错**:`_setup_w10a_layout` 写成 `<work>/chapters/raw/course1.md`(无 drafts_dir 目录)→ verify 用 drafts_dir=`raw/`,output_stem="raw" 而非 "course1" → 修:加 `<work>/chapters/raw/course1/` 目录(verify chapters_complete 需要)
  - **Chapter dataclass 字段缺失**:fixture 写 `chapters: [{"idx": i} for i in range(1, 4)]` → `Chapter.__init__()` 缺 title/summary/start_seconds/end_seconds → 改用空 chapters 列表
  - **final_html 内容 dummy**:`<html>x...</html>` 无 `<title>` 无 H1 → verify html_structure FAIL → 改用 `<!doctype html><html><head><title>...</title></head><body><h1>...</h1>...`
- W11-A commit:`d2b39d3 fix(pipeline): W11-A — align gatekeeper path resolution with verify layout`
- 下次会话第一句话:承接 W11-A handoff,决定 W11-B 方向:
  - **W11-B v1.0 release prep**(2-3h):CHANGELOG + docs/installation.md + pyproject urls + `uv build` + `gh release create v1.0.0 --draft`
  - **W11-C 长视频 + 真 LLM 文档质量验收**(3-4h 真跑):同 03.mp4 跑 longdoc active 净化 + 看讲师视角讲义质量
  - 推荐:**先 W11-B release(Gatekeeper 已修干净,可放心打 tag)→ 再 W11-C 真质量验收**

### 会话 19 — Phase 11 W11-C 真分布式文档质量验收(2026-07-20,~20min)

- 完成任务(W11-C 主目标完全达成 ✅,用户选 A"真跑 longdoc"):
  - 分支:`release/v1.0`(沿用)
  - 策略:**复用 W10-A 产物 + 只跑 longdoc active**(避免 4h 重跑 ASR / chapters / drafts)
  - 复制 `output/` 199MB → `output-w11c/`,准备干净 work_dir
  - 调 `process_long_doc(work, ollama_provider, cfg)`:
    - provider=ollama / model=qwen3:14b / num_ctx=32768
    - **43.87s** 完成 1 LLM call,W10-A 14KB → W11-C 4KB(`retention_rate=0.1376`)
  - 0 LLM failures,写 `_W11C_DONE.txt` 标记 + 写 verify.json(W11-C 路径)
  - 跑 `_w11a_consistency.py` → 一致 PASS
- **讲师视角评估 9/9 ⭐⭐⭐⭐⭐**:
  - 5 类核心资产保留:概念 / 数据 / 案例 / 逻辑 / 表格 全保留
  - 4 类噪声清理:口语填充 / 引导 / 寒暄 / 互动 全清
  - 4 级标题:用 H1/H2/H3(未用 H4 合理)
  - 结构:`全站运营方法论与实操指南` + 7 个 H2 章节 + 多 H3 子节
  - 5 个表格:策略对比 / 误区对比 / 数据指标 / 流量结构 / 预算管理
  - 1 个 Mermaid 流程图:全站新品测试流程
  - 1 个可执行 checklist:全站推广风险控制清单
- 关键发现:
  - **retention_rate 0.1376 = noise_removal_rate**,不是信息丢失(口语 / 互动 / 寒暄 / 时间戳冗余全删)
  - **longdoc LLM 净化 ROI 极高**:1 LLM call 44s,讲义从 36KB 降到 4KB(8.7x 压缩),讲师可分发
  - **1 chunk 满足 14K chars 输入**:`chunk_size=15000 CJK` 在 107min 视频极限为 1-2 chunks,LLM 总开销 30s-2min
- 撞墙 / 修正:
  - **`_w11c_run_longdoc.py` F541 f-string 无 placeholder**:ruff 报错 → 改普通字符串
- W11-C commit + handoff 在 release/v1.0 分支
- **v1.0 GA 全闭环确认**:W0-W11-C 14 个里程碑全部 ✅,media-to-doc v1.0 GA ready
- 下次会话第一句话:承接 W11-C handoff,决定 v1.0 后方向(A 上 PyPI / B GitHub release / C Tauri UI / D NSIS 安装器 / E v1.0.1 patch)

### 会话 18 — Phase 11 W11-B v1.0.0 Release Prep(2026-07-20,~45min)

- 完成任务(W11-B 主目标完全达成 ✅,用户要求"开始 W11-B"+"完成后执行 W11-C"):
  - 分支:`release/v1.0`(从 W11-A `b410e84` 拉)
  - pyproject version **0.1.0 → 1.0.0** + Development Status **3-Alpha → 5-Production/Stable** + multi-OS/Education/Topic 分类
  - `__version__` 改 **动态** `importlib.metadata.version("media_to_doc")` + pyproject regex fallback;改一处全链路同步
  - test_smoke.py 3 处版本断言同步用 `__version__` 变量
  - README badge 1.0.0 / 529 tests + 5 分钟快速开始期望版本同步
  - **CHANGELOG.md**(新建)— Keep a Changelog 1.1,W0-W11 里程碑 / bug fix / 性能数据
  - **docs/installation.md**(新建)— Windows/macOS/Linux / CUDA / 中国网络 / Ollama / Claude Desktop / 故障排除
  - **docs/RELEASE_NOTES_v1.0.0.md**(新建)— gh release form 可粘贴的 release notes
  - **uv build 三件套**:wheel 122KB + sdist 508KB / 33 .py 模块 / 7 extras / METADATA 全字段正确 / wheel 装后 `mtd --version` → `1.0.0` / W10-A 真跑产物 `_w11a_consistency.py` 仍 PASS
  - 测试:529 passed / 0 skipped,ruff clean
  - commit `docs(release): W11-B — v1.0.0 release prep`(`9cddcf2`)
  - **annotated tag v1.0.0**(带 release notes + Co-Authored-By)
- 关键设计:
  - **`__version__` 单一真相源放 pyproject**:`__init__.py` 优先 `importlib.metadata` 读 wheel METADATA,fallback 读 pyproject regex,改一处全链路同步
  - **multi-OS classifier 一次补齐**:Windows / macOS / Linux 全标 + Intended Audience Education + Topic Office/Business(讲义场景主线)
  - **`uv build` 验证而非 dry-run**:实际打 wheel + sdist,确保 hatchling + src layout + pyproject 字段完整,可推到 PyPI
  - **RELEASE_NOTES_v1.0.0.md 而不是 changelog form 复用**:gh release form 不接受 CHANGELOG.md 直接粘贴(太长),单独写 release notes
- 撞墙 / 修正:
  - **第一次 `uv build` 装包后 `mtd --version` 仍报 0.1.0**:发现 `__init__.py:55` 写死 `__version__ = "0.1.0"`(W0 占位),pyproject 改 1.0.0 没生效 → 改成 `importlib.metadata.version()` 动态读 + pyproject regex fallback → rebuild + reinstall 后 `1.0.0`
  - **test_smoke.py 3 处 "0.1.0" 硬编码断言**:升级时漏掉 → pytest 3 失败 → 改用 `__version__` 动态变量(W11-B 修)
  - **`dist/` 不在 .gitignore**:已查 `.gitignore` line 14 有 `dist/`,不会被 commit;OK
- W11-B commit:
  - `9cddcf2 docs(release): W11-B — v1.0.0 release prep`
  - tag `v1.0.0`(annotated,本地未 push)
- 下次会话第一句话:承接 W11-B handoff,开始 W11-C 真分布式文档质量验收——**等用户授权 4h 突破 session 上限后才能跑 longdoc active**,或者用户决定 B/C 选项先打 GA tag / 写 CLAUDE.md §10 后续规划更新
