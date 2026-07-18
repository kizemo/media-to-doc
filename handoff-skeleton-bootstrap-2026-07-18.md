# handoff-skeleton-bootstrap-2026-07-18.md — Phase 0 项目骨架会话快照

> **会话主题**:Phase 0 项目骨架落地(从 0 到首个 commit)
> **会话日期**:2026-07-18,~1 小时
> **会话状态**:**已完成,无阻塞**(14/14 测试 + 0 ruff error + 首 commit `702ecc2`)

---

## 1. 本次会话目标

用户最初要求:

> 请全面阅读项目文档,对项目建立全面/深入的理解,然后制定第一阶段的任务计划。如存在任何疑问,进行提问,确保对任务完全理解。
> 启动 Phase 0 实施

承接会话 3(`handoff-le-design-2026-07-18.md`)的"下次会话从 Phase 1 起",实际执行 Phase 0 启动。

---

## 2. 已完成

| 项 | 文件 | 状态 |
|---|---|---|
| 全面阅读 PRD/TDD/ROADMAP/CLAUDE.md/3 份 handoff/LE 设计/LE 原型 | 全文已缓存 | [x] |
| 验证 LE 原型测试仍过(23/23) | `_research/le_prototype/` | [x] |
| AskUserQuestion 确认 4 项关键决策 | (会话对话) | [x] |
| `.gitignore`(屏蔽 `_research/`、`workspace/`、`__pycache__/`、`.venv/` 等) | `.gitignore` | [x] |
| `LICENSE`(MIT,2026 Duanyi) | `LICENSE` | [x] |
| `README.md` 初版(用户视角 5 分钟快速开始 + 三种调用方式 + 产物布局) | `README.md` | [x] |
| `uv init --bare` + 自定义 `pyproject.toml`(`name=media_to_doc`,`requires-python>=3.11`,extras: llm/asr/frames/ocr/imagegen/longdoc/mcp/dev) | `pyproject.toml` + `uv.lock` | [x] |
| `src/media_to_doc/__init__.py`(version + lazy import 占位) | | [x] |
| `src/media_to_doc/cli.py`(Typer mtd: version/paths/run/resume/status/list/doctor/config/model/mcp + `--version` 顶层 callback) | | [x] |
| `src/media_to_doc/paths.py`(WORKSPACE_ROOT/INBOX/WORK/CONFIG/LEARNINGS + 环境变量覆盖 + `project_root()` 解析) | | [x] |
| `src/media_to_doc/config.py`(WorkflowConfig + LLMConfig/ImagegenConfig/PathsConfig/PipelineConfig + YAML 序列化) | | [x] |
| `src/media_to_doc/state.py`(STAGE_ORDER 11 阶段 + StageState + State JSON 持久化) | | [x] |
| `src/media_to_doc/logger/__init__.py`(Phase 5 迁 LE 原型的占位) | | [x] |
| `tests/__init__.py` + `tests/conftest.py` + `tests/test_smoke.py`(**14 测试全过**) | | [x] |
| `.learnings/LEARNINGS.md` + `.learnings/ERRORS.md` 空模板 | | [x] |
| `.github/workflows/ci.yml`(windows-latest + Python 3.11/3.12 + ruff + mypy + pytest) | | [x] |
| `task.md` 更新:Phase 0 全完成 + 新增会话 4 历史 | | [x] |
| `git init -b master` + `git config user.name/email` | | [x] |
| 首 commit `702ecc2`:`chore: bootstrap project skeleton`(26 文件) | | [x] |

---

## 3. 已读 / 已写文件清单

### 已读(信息已缓存,下次会话无需重读)

- `CLAUDE.md`(全文)
- `PRD.md`(全文 378 行)
- `TDD.md`(全文 1061 行)
- `ROADMAP.md`(全文 563 行)
- `task.md`(全文 175 行)
- `handoff-research-2026-07-17.md`(全文)
- `handoff-le-design-2026-07-18.md`(全文)
- `handoff-template.md`(全文)
- `_research/PROJECT_DESCRIPTION.md`(§1-4 + §5-6)
- `_research/LE_DESIGN.md`(§0-3)
- `_research/LE_KEYPOINTS.md`(核心要点)
- `_research/le_prototype/README.md`(全文)
- `_research/le_prototype/pipeline_logger.py`(全文 287 行)
- `_research/le_prototype/gatekeeper.py`(全文 109 行)
- `_research/le_prototype/learnings.py`(全文 254 行)
- `pyproject.toml` (uv 默认 + 重写后版本)

### 已写(本次会话新增)

- `F:/soft/00selfmade/media-to-doc/.gitignore`(63 行)
- `F:/soft/00selfmade/media-to-doc/LICENSE`(21 行)
- `F:/soft/00selfmade/media-to-doc/README.md`(用户视角,约 130 行)
- `F:/soft/00selfmade/media-to-doc/pyproject.toml`(重写,约 150 行)
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/__init__.py`(版本 + lazy import 占位)
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/cli.py`(Typer CLI,约 240 行)
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/paths.py`(路径常量,约 100 行)
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/config.py`(数据类 + YAML,约 130 行)
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/state.py`(STAGE_ORDER + State,约 165 行)
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/logger/__init__.py`(占位)
- `F:/soft/00selfmade/media-to-doc/tests/__init__.py`(包说明)
- `F:/soft/00selfmade/media-to-doc/tests/conftest.py`(基础 fixtures)
- `F:/soft/00selfmade/media-to-doc/tests/test_smoke.py`(14 测试,约 200 行)
- `F:/soft/00selfmade/media-to-doc/.learnings/LEARNINGS.md`(空模板)
- `F:/soft/00selfmade/media-to-doc/.learnings/ERRORS.md`(空模板)
- `F:/soft/00selfmade/media-to-doc/.github/workflows/ci.yml`(占位 CI)
- `F:/soft/00selfmade/media-to-doc/workspace/inbox/.gitkeep`
- `F:/soft/00selfmade/media-to-doc/workspace/work/.gitkeep`

### 已修改

- `F:/soft/00selfmade/media-to-doc/task.md` Phase 0 全完成 + 新增会话 4 历史
- `F:/soft/00selfmade/media-to-doc/.gitignore` 修复 `_research/` 实际屏蔽(原注释被 ruff 误删)
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/paths.py` 添加 `LEARNINGS_DIR` 常量供 cli.py 导入
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/cli.py` 添加 `--version` 顶层 callback(`is_eager=True` + `invoke_without_command=True`)

---

## 4. 关键决策与原因

### 决策 1:为什么 `mtd --version` 用 Typer callback 而非 `main()` 前置拦截

**问题**:Typer 默认不识别 `--version`,需要在顶层注册。

**选项**:

- A:在 `main()` 中检查 `sys.argv`,如有 `--version` 直接打印并退出
- B:用 `@app.callback(invoke_without_command=True)` + `typer.Option(is_eager=True)`
- C:把 `--version` 改成 `version` 子命令(用户用 `mtd version`)

**选择**:B

**原因**:

1. README.md 与 ROADMAP 都承诺 `mtd --version` 可用(Unix 习惯)
2. B 是 Typer 官方推荐方式,代码更声明式
3. A 的拦截会被 Typer 的参数解析报错(`No such option: --version`),必须放在 `app()` 之前
4. C 与 Unix 习惯不符,文档需同步改

**下次何时再讨论**:不会 — `--version` 是 CLI 习惯,稳定。

### 决策 2:为什么 Phase 0 仅 Python 后端,UI/NSIS 留后续

**问题**:Phase 0 是否一次性搭好 UI 空壳 + NSIS 占位?

**选项**:

- A:Python + UI + NSIS 全搭
- B:仅 Python 后端
- C:极简(只 git + uv init)

**选择**:B(用户确认)

**原因**:

1. Tauri Rust 工具链 Windows 首次编译 5-10 分钟,Phase 0 引入会拖慢首 commit
2. NSIS 工具链需手动安装,过早引入会让 CI 复杂
3. Phase 0 目标仅"项目能跑通 `mtd --version`",UI/NSIS 留到各自 phase 自然展开
4. 单聚焦 = 更快看到 Phase 0 价值

**下次何时再讨论**:Phase 2 启动 UI 时,届时 `npm create tauri-app@latest` 一次性搭好。

### 决策 3:为什么 LE 原型暂不纳入 git

**问题**:`_research/le_prototype/`(829 行 + 460 行测试)是否进 git?

**选项**:

- A:不纳入(`.gitignore` 屏蔽 `_research/`)
- B:复制到 `src/media_to_doc/logger/` 当首版
- C:原型 + 测试一并提交

**选择**:A(用户确认)

**原因**:

1. 原型是研究阶段产物,Phase 1-4 期间 11 stage 接口可能变化,过早纳入主分支会让未来重构成本变高
2. `.gitignore` 屏蔽 `_research/` 是全局 CLAUDE.md §4 + ROADMAP §0 的既定约定
3. Phase 5 实施时按真实 11 stage 接口整体迁移,中间不污染主分支历史
4. LE 原型 23 测试已在原位固化,需要时随时可复跑

**下次何时再讨论**:Phase 5 启动时,届时复制 `_research/le_prototype/{pipeline_logger,gatekeeper,learnings,runner}.py` 到 `src/media_to_doc/logger/`。

### 决策 4:为什么 pyproject.toml 用 `>=3.11` 而非 `==3.11`

**问题**:Python 版本基线?

**选项**:

- A:`requires-python = ">=3.11"`(参考实现 3.11,但本地跑的是 3.14.6)
- B:`==3.11.*`(锁版本)
- C:`>=3.12`(利用 3.12+ 新特性)

**选择**:A(用户确认)

**原因**:

1. LE 原型已用 Python 3.14.6 跑通测试(`requires-python` 实际范围 3.11-3.14 都行)
2. 锁 `==3.11.*` 会导致 3.12/3.13/3.14 用户无法安装,但本地开发机用 3.14,会冲突
3. Faster-Whisper / PySceneDetect / RapidOCR 等依赖在 3.11+ 兼容性最稳定
4. `requires-python = ">=3.11"` 与参考实现一致,但允许升级

**下次何时再讨论**:如果某依赖在 3.14 出问题,再考虑收紧到 `>=3.11,<3.14`。

---

## 5. 撞墙 / 未完成 / 已知问题

### 5.1 撞墙点(下次会话语境)

| 现象 | 已尝试 | 残留 |
|---|---|---|
| `pytest` collect error: `cannot import name 'LEARNINGS_DIR'` | 在 `paths.py` 添加 `LEARNINGS_DIR = project_root() / LEARNINGS_DIR_NAME` | 已解决 |
| `mtd --version` 子进程报 "No such option" / "Missing command" | 改用 Typer callback + `is_eager=True` + `invoke_without_command=True` | 已解决 |
| `_research/` 未被 `.gitignore` 屏蔽 | 原 `.gitignore` 中 `_research/` 行被 ruff fix 误判为注释 | 已修复(显式加 `_research/`) |
| ruff 报告 22 个 lint 错误 | `ruff check --fix` 自动修复 17 个,剩余 5 个是 `B008`(typer.Argument/Option 默认值),在 `pyproject.toml` 显式忽略 | 已解决 |

### 5.2 TODO(下次会话继续)

按 `task.md` Phase 1(11 阶段核心流水线)起:

- [ ] 启动 `feat/pipeline-w1-audio-asr-frames` 分支
- [ ] W1:基础设施 + 前 3 stage(4 人天)
  - [ ] `src/media_to_doc/utils/ffmpeg_utils.py` — ffmpeg 路径探测
  - [ ] `src/media_to_doc/utils/hash_utils.py` — pHash
  - [ ] `src/media_to_doc/utils/progress.py` — 进度条
  - [ ] `src/media_to_doc/pipeline/audio.py` — `prepare_audio()`
  - [ ] `src/media_to_doc/pipeline/asr.py` — `transcribe()`(Faster-Whisper mock)
  - [ ] `src/media_to_doc/pipeline/frames.py` — `extract_keyframes()`(PySceneDetect + pHash)
  - [ ] `src/media_to_doc/pipeline/runner.py` — 编排器骨架(暂用 mock stage,Phase 5 接入 LE)
  - [ ] 测试:mock 重依赖,确保每个 stage 独立可测
  - [ ] commit:`feat(pipeline): audio + asr + frames stages`

### 5.3 已知问题 / 技术债

- `cli.py` 中多个子命令(`run` / `resume` / `status` / `list` / `doctor` / `config` / `model` / `mcp`)仅占位,Phase 1-4 逐阶段实装
- `config.py` 的 `WorkflowConfig` 字段尚未做 env 变量覆盖(Phase 2 实施)
- `paths.py` 的 `LEARNINGS_DIR` 是模块加载时静态解析,可能在某些安装场景(如 pip install)失效
- `state.py` 的 `State` 未做并发控制(单进程假设,Phase 2 视情况加锁)
- 测试覆盖 14 用例,目标 Phase 5 后 ≥ 110 用例
- `tests/test_smoke.py::test_uv_run_mtd_version` 是 subprocess 测试,在 Windows 上略慢(约 0.6s)
- `pyproject.toml` 中 `[project.optional-dependencies]` 包含较重依赖(torch/diffusers),仅在 `extras` 中,默认安装不会触发
- `mcp_server` 模块尚未创建(Phase 4 实施),但 `pyproject.toml` 已注册 `mtd-mcp` 入口,可能 `uv run mtd-mcp` 会报 ImportError

---

## 6. 测试状态

```
$ uv run pytest tests/ -v
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
configfile: pyproject.toml
plugins: cov-7.1.0
collecting ... collected 14 items

tests/test_smoke.py::test_version_is_0_1_0 PASSED                        [  7%]
tests/test_smoke.py::test_stage_order_has_11_stages PASSED               [ 14%]
tests/test_smoke.py::test_paths_resolve PASSED                           [ 21%]
tests/test_smoke.py::test_default_workflow_config PASSED                 [ 28%]
tests/test_smoke.py::test_workflow_config_yaml_roundtrip PASSED          [ 35%]
tests/test_smoke.py::test_state_new_initializes_all_stages PASSED        [ 42%]
tests/test_smoke.py::test_state_mark_running_then_completed PASSED       [ 50%]
tests/test_smoke.py::test_state_save_and_load_roundtrip PASSED           [ 57%]
tests/test_smoke.py::test_state_next_stage_skips_completed PASSED        [ 64%]
tests/test_smoke.py::test_cli_version PASSED                             [ 71%]
tests/test_smoke.py::test_cli_help PASSED                                [ 78%]
tests/test_smoke.py::test_cli_paths PASSED                               [ 85%]
tests/test_smoke.py::test_cli_run_not_implemented PASSED                 [ 92%]
tests/test_smoke.py::test_uv_run_mtd_version PASSED                      [100%]

============================= 14 passed in 0.62s ==============================
```

ruff 检查:`All checks passed!`(已通过 `ruff check --fix` + 显式忽略 B008)

---

## 7. Git 状态

```
$ git log --oneline
702ecc2 chore: bootstrap project skeleton

$ git status
On branch master
nothing to commit, working tree clean
```

分支策略:Phase 0 直接基于 `master` 提交(骨架阶段,后续 phase 必须基于 `feat/<name>` 分支)。

首次 commit 内容(26 文件):

- 文档:`PRD.md` / `TDD.md` / `ROADMAP.md` / `CLAUDE.md` / `task.md` / `handoff-template.md` / `handoff-research-2026-07-17.md` / `handoff-le-design-2026-07-18.md`
- 代码:`src/media_to_doc/` 6 文件 + `tests/` 3 文件 + `pyproject.toml` + `uv.lock`
- 基础设施:`.gitignore` / `LICENSE` / `README.md` / `.github/workflows/ci.yml` / `.learnings/{LEARNINGS,ERRORS}.md` / `workspace/{inbox,work}/.gitkeep`

**不纳入 git**:`_research/`(LE 原型 23 测试)/ `.venv/` / `__pycache__/` / `.pytest_cache/` / `.ruff_cache/` / `workspace/{inbox,work}/*`

---

## 8. 给下一个会话的提示

**新会话第一句话建议**:

```
承接 handoff-skeleton-bootstrap-2026-07-18.md,启动 Phase 1 核心流水线 W1(音频 + ASR + 关键帧)。
请先创建 feat/pipeline-w1-audio-asr-frames 分支,然后按 ROADMAP Phase 1 W1 清单逐 stage 实施。
参考 _research/PROJECT_DESCRIPTION.md §4 了解参考实现的模块结构,
参考 _research/le_prototype/runner.py 了解编排层模板。
```

**主要任务**(Phase 1 W1,见 `task.md` 与 `ROADMAP.md`):

1. 创建 `feat/pipeline-w1-audio-asr-frames` 分支
2. 复制参考实现的 `audio.py` / `asr.py` / `frames.py` 到 `src/media_to_doc/pipeline/`
3. 添加对应的 `tests/test_pipeline/test_{audio,asr,frames}.py`,mock 重依赖
4. 实现 `pipeline/runner.py` 编排骨架(暂用 mock stage,Phase 5 接入 LE hooks)
5. 每个 stage 独立 commit,确保 `uv run pytest` 与 `uv run ruff check` 全过
6. W1 末 commit:`feat(pipeline): audio + asr + frames stages`

**别忘了**:

- 缩进 2 空格,Python 函数类型注解(全局偏好)
- 函数 ≤ 100 行,模块 ≤ 500 行(TDD §9.2 可维护性)
- mock 阶段重依赖(Faster-Whisper / PySceneDetect / ffmpeg),不在 CI 真跑
- `cli.py` 中已有占位 `mtd run`,实装时可复用 `run` 子命令
- 不要破坏 `mtd --version` 与 `mtd version` 已有行为(测试覆盖)

**关键参考**:

- `_research/PROJECT_DESCRIPTION.md` §3.1 端到端流水线 + §4 模块结构
- `_research/PROJECT_DESCRIPTION.md` §5 产物目录布局
- `ROADMAP.md` Phase 1 — 16 人天 4 周规划
- `TDD.md` §4.1.3 `pipeline/runner.py` 编排器伪代码
- 全局 `C:\Users\Duanyi\.claude\CLAUDE.md` — 沟通偏好 / 安全红线 / 会话健康
- `_research/le_prototype/runner.py` — 编排层原型(Phase 5 接入 LE)

---

## 9. 上下文参考链接

- `CLAUDE.md` — 项目级指引
- `task.md` — 活跃 todo(含本会话历史)
- `PRD.md` — 产品需求(378 行)
- `TDD.md` — 技术设计(1061 行)
- `ROADMAP.md` — 执行规划(563 行)
- `handoff-template.md` — 长期复用模板
- `handoff-research-2026-07-17.md` — 会话 1:逆向研究
- `handoff-le-design-2026-07-18.md` — 会话 3:LE 落地
- `_research/PROJECT_DESCRIPTION.md` — 参考实现逆向报告(25KB / 566 行)
- `_research/LE_DESIGN.md` — LE 详细设计(23KB)
- `_research/le_prototype/` — LE L1+L2 原型(23 测试全过)
- `git log --oneline` — `702ecc2 chore: bootstrap project skeleton`

---

## 10. 自检清单

- [x] 本会话目标全部完成(Phase 0 全交付)
- [x] 无未提交代码改动(working tree clean)
- [x] 无未完成任务(下次会话从 Phase 1 开始)
- [x] 测试状态明确(14 passed in 0.62s)
- [x] Git 状态明确(首 commit `702ecc2` 已建)
- [x] 下次会话第一句话建议清晰
- [x] 关键决策记录 4 条,带"为什么"
- [x] 上下文参考链接完整
- [x] `uv run mtd --version` 端到端验证通过
- [x] `uv run ruff check src/ tests/` 全过
- [x] `_research/` 正确屏蔽(不入 git)
- [x] LE 原型保留在 `_research/`(23 测试可独立复跑)
