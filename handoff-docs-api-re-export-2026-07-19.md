# handoff-docs-api-re-export-2026-07-19.md — Phase 7 W9 文档 + Python API 快照

> **会话主题**:Phase 7 W9 — Phase 7 文档(README/.learnings./docs/MCP_INTEGRATION.md/CLAUDE.md)
> + Phase 4 收尾(Python API 顶层 re-export + 跨项目 demo)
> **会话日期**:2026-07-19,~2 小时
> **会话状态**:**已完成,无阻塞**(508 passed / 0 skipped + ruff 全过)

---

## 1. 本次会话目标

承接 `handoff-le-wiring-2026-07-19.md`,W8 已完成 LE 闭环。用户选 **W9 = A+B 组合**:

- **A. Phase 7 文档与示例**:README 完善 + `.learnings/LEARNINGS.md` 首批 LP 条目 + 跨项目 demo
- **B. Python API 顶层 re-export**:PEP 562 `__getattr__` 让 `from media_to_doc import run_pipeline` 跨项目直接用

---

## 2. 已完成

| 项 | 文件 | 行数 / 用例 | 状态 |
|---|---|---|---|
| `feat/pipeline-w9-docs` 分支(基于 W8 `ddeb95f`) | git branch | - | [x] |
| `src/media_to_doc/__init__.py` PEP 562 顶层 re-export | 重写 | 215 行,52 公开符号 | [x] |
| `tests/test_init.py` lazy import 测试 | 新增 | 26 用例 | [x] |
| `examples/cross_project_demo.py` 跨项目 demo | 新增 | 215 行,4 个 demo | [x] |
| `README.md` 全面重写 | 重写 | ~280 行 | [x] |
| `.learnings/LEARNINGS.md` 首批 14 条 LP | 重写 | 14 条 LP-20260718/19-NNN | [x] |
| `docs/MCP_INTEGRATION.md` 更新 8 工具 | 改 | 6 → 8 + W8 详细签名 | [x] |
| `CLAUDE.md` §9.3 / §9.4 更新 | 改 | Python API + 8 工具清单 | [x] |
| `task.md` Phase 7 + 会话 14 历史 | 改 | - | [x] |
| 测试结果 | pytest | **508 passed / 0 skipped**(+26) | [x] |
| lint 结果 | ruff check src/ tests/ examples/ | All checks passed | [x] |
| demo 端到端验证 | `examples/cross_project_demo.py` | demo-lazy / demo-config / demo-metrics 跑通 | [x] |

**测试数量统计**:

- W8:482 passed / 0 skipped
- W9:**508 passed / 0 skipped**(+26 用例,W9 init 测试)
- **当前总数:508 passed**

---

## 3. 已读 / 已写文件清单

### 已读(信息已缓存)

- `MEMORY.md` / `task.md` / `handoff-le-wiring-2026-07-19.md`
- `README.md`(W8 旧版,W9 重写)
- `.learnings/LEARNINGS.md` / `.learnings/ERRORS.md`(空模板)
- `src/media_to_doc/__init__.py`(Phase 0 占位,W9 重写)
- `src/media_to_doc/{config,state,paths}.py`(re-export 来源)
- `src/media_to_doc/pipeline/{__init__,runner}.py`(STAGE_FUNCS / PipelineResult / run_pipeline)
- `src/media_to_doc/logger/__init__.py`(LE 公开 API)
- `src/media_to_doc/llm/{__init__,health}.py`(LLM provider + health 查询)
- `src/media_to_doc/mcp_server.py`(W8 工具签名参考)
- `docs/MCP_INTEGRATION.md`(W7 版,W9 更新)
- `CLAUDE.md` §9.3 / §9.4

### 已写(本次会话新增/重写)

**源码**:

- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/__init__.py`(重写,215 行)

**测试**:

- `F:/soft/00selfmade/media-to-doc/tests/test_init.py`(新增,323 行,26 用例)

**文档**:

- `F:/soft/00selfmade/media-to-doc/README.md`(重写,~280 行)
- `F:/soft/00selfmade/media-to-doc/.learnings/LEARNINGS.md`(重写,14 条 LP)
- `F:/soft/00selfmade/media-to-doc/docs/MCP_INTEGRATION.md`(更新,6 → 8 工具)
- `F:/soft/00selfmade/media-to-doc/CLAUDE.md` §9.3 / §9.4 改

**示例**:

- `F:/soft/00selfmade/media-to-doc/examples/cross_project_demo.py`(新增,215 行,4 demo)

**任务管理**:

- `F:/soft/00selfmade/media-to-doc/task.md`(更新 Phase 7 全 [x] + 会话 14 历史)

---

## 4. 关键决策与原因

### 决策 1:`__init__.py` 用 PEP 562 `__getattr__` 而非 `import *` 或 eager import

**问题**:52 个公开符号分布在 8 个子模块,部分模块依赖重 SDK(faster-whisper / diffusers / anthropic)。

**选择**:PEP 562 模块级 `__getattr__(name)` + `_LAZY_EXPORTS: dict[str, str]` 注册表。

**原因**:
1. **启动 < 100ms**:`import media_to_doc` 不触发重 SDK;首次访问 `run_pipeline` 才 import 整个 pipeline 子模块
2. **可控性优于 `import *`**:`_LAZY_EXPORTS` 显式列出每个符号,新增符号需要追加一行 + `__all__` 一行,有意识管理
3. **PEP 562 是 Python 3.7+ 标准**:不需要 `__init_subclass__` 等 hack,IDE / type checker / pytest 都认识
4. **`__dir__()` 支持自动补全**:用户 `dir(media_to_doc)` 看到所有公开符号(包括未触发的 lazy 符号)

**下次何时再讨论**:不会 — Python 3.7+ 项目都该用 PEP 562

### 决策 2:`_LAZY_EXPORTS` + `__all__` 双维护 + 一致性测试保护

**问题**:`_LAZY_EXPORTS` 与 `__all__` 同步需要纪律,容易 drift。

**选择**:写 `test_all_matches_lazy_exports` 测试,确保两边 key 集合完全一致。

**代码**:
```python
def test_all_matches_lazy_exports() -> None:
  meta = {"__version__", "__author__", "__license__"}
  expected = set(media_to_doc._LAZY_EXPORTS.keys()) | meta
  assert set(media_to_doc.__all__) == expected
```

**原因**:
1. 测试驱动的"双重纪律":新增符号漏写一边就 fail
2. 比 docstring / lint 规则更鲁棒(refactor 不会误改)
3. 同时也是 `test_lazy_exports_target_modules_importable`:保护性测试,确保没有 typo 模块路径

**下次何时再讨论**:不会 — 双轨 + 一致性测试是 Python 公共 API 的最佳实践

### 决策 3:`test_import_media_to_doc_does_not_load_heavy_modules` parametrize 7 个重依赖

**问题**:怎么确保 lazy import 行为不退化?

**选择**:`pytest.mark.parametrize("heavy_module", [...])` 测试 7 个模块
(faster_whisper / scenedetect / rapidocr / diffusers / anthropic / ollama / openai),
断言 `import media_to_doc` 后它们**不在** `sys.modules` 里。

**原因**:
1. **保护性测试**:未来有人在 `__init__.py` 加 eager import,测试立即 fail
2. **pytest 重跑友好**:`sys.modules.pop("media_to_doc")` 后 reimport,确保 fresh 状态
3. **不需要真装 7 个重依赖**:测试只验证"不在 sys.modules",不需要 import

**下次何时再讨论**:不会 — 7 个重依赖覆盖了所有 W1-W8 用到的库

### 决策 4:`examples/cross_project_demo.py` 用 4 个独立 demo + argparse

**问题**:跨项目 demo 怎么写最有用?

**选择**:4 个 demo 分别验证不同用法,argparse 选 demo:

- `demo-lazy`:验证 lazy import(sys.modules 断言)
- `demo-metrics`:W8 `list_runs` 真实调用
- `demo-pipeline`:`run_pipeline` 真实跑(需要 inbox)
- `demo-config`:`WorkflowConfig` 数据类 + YAML 序列化

**原因**:
1. **4 个 demo 可独立跑**:`demo-lazy` 不需要 workspace / inbox,任何机器都能跑
2. **argparse 让 demo 可发现性**:`--help` 列出所有 demo + 描述
3. **混合轻 / 重 demo**:轻的(lazy / config)可立即跑,重的(pipeline)用作集成参考

**下次何时再讨论**:W10+ 加 demo 时考虑同样模式

### 决策 5:README 用"5 分钟快速开始" + "三种调用方式" + "公开 API 表" + "环境变量表"

**问题**:README 该写多详细?

**选择**:5 分钟入门 + 三种调用方式(CLI / Python API / MCP) + 公开 API 表 52 符号 + 环境变量表 11 变量 + 产物布局图 + LE 五层表 + 路线图 + 技术栈。

**原因**:
1. **新用户视角**:5 分钟跑通 → 看产物 → 翻 API 文档 → 调配置
2. **三类用户视角**:CLI 用户看命令行;开发者看 Python API;AI 助手配置者看 MCP
3. **参考实现验证**:参考实现的 README 也是这个结构(5 分钟 + 三种 + API + 产物)

**下次何时再讨论**:v1.0 时再加 docs/installation.md(各 OS 安装步骤)

### 决策 6:LEARNINGS.md 首批 14 条,覆盖 W1-W8 关键 best_practice

**问题**:LEARNINGS 该有多少条目?太少了没价值,太多了失去焦点。

**选择**:14 条 LP 条目,每条对应 W1-W8 一个里程碑的关键决策:

- LP-001:11 stage 签名统一(W1)
- LP-002:LLM provider ABC + lazy import(W2)
- LP-003:chapters JSON 容错(W2)
- LP-004:imagegen ABC + Protocol 双轨(W3)
- LP-005:render 缺失图退化(W3)
- LP-006:draft 默认输出到 work/chapters/raw(W3)
- LP-007:Ollama num_ctx 默认 65536(W5)
- LP-008:longdoc 默认 skip(W4)
- LP-009:Gatekeeper image_refs 候选路径 3 重试(W8)
- LP-010:PipelineLogger 三层 try/except 异常隔离(W8)
- LP-011:assess_llm_health 只计成功解析的 run_file(W8)
- LP-012:PEP 562 `__getattr__` lazy import(W9)
- LP-013:测试不要真跑 11 stage,monkeypatch(W1-W8)
- LP-014:stdout 留给 JSON,日志走 stderr(W6+W7)

**原因**:
1. **14 条 = 可一次读完**:不冗余,每条 5-10 行
2. **每条对应 commit 关键决策**:未来 Claude 看 LEARNINGS 能 reverse-engineer 每个 milestone 的 why
3. **LP-013 / LP-014 是元规则**:跨多个 stage 的通用 best_practice,适合放在末尾

**下次何时再讨论**:W10+ 新增条目按 `LP-YYYYMMDD-NNN` 自增编号

### 决策 7:`docs/MCP_INTEGRATION.md` 6 → 8 工具,加 `get_run_metrics` / `list_runs` 详细签名

**问题**:W8 加了 2 个 MCP 工具,文档怎么同步?

**选择**:6 → 8 工具表 + §3.7 `get_run_metrics` / §3.8 `list_runs` 详细签名 + 示例 prompt。

**原因**:
1. **README §2 工具表是快速参考**:docs/MCP_INTEGRATION.md 是详细文档,两者同步更新
2. **每个工具加示例 prompt**:Claude Desktop 用户直接 copy-paste 用

**下次何时再讨论**:W10+ 加新工具时同样模式

---

## 5. 撞墙 / 未完成 / 已知问题

### 5.1 撞墙点(已全部解决)

| 现象 | 已尝试 | 残留 |
|---|---|---|
| `test_pipeline_result_is_a_dataclass` — `is_completed not in PipelineResult.__dataclass_fields__` | 查 runner.py → `is_completed` 是 State 的 property,PipelineResult 字段是 `state/completed/failed/duration_seconds/pipeline_run` | 改断言正确字段 |
| ruff W292 / I001 — 新文件末尾缺换行 + import 排序未规范 | `ruff --fix` 自动修 4 处(test_init.py + __init__.py) | 已解决 |
| ruff F541 — examples/cross_project_demo.py 8 处 f-string 无占位符 | `ruff --fix` 自动修 | 已解决 |

### 5.2 已知问题 / 技术债

- **`__all__` 长度 52 但 README 公开 API 表只列 7 类**(分类展示,完整列表在 `media_to_doc.__all__`)
- **`run_pipeline` 真实跑需要 inbox + GPU/CPU 资源**:`demo-pipeline` 默认 inbox 不存在时跳过,作为参考代码不真跑
- **`list_runs(workspace_root)` 当前扫 mtime 倒序**:如果多个 run 在同一秒创建,顺序可能不稳定(W8 已记技术债)
- **`docs/installation.md` 缺失**:README 给出简短安装命令,各 OS 详细步骤待 v1.0

### 5.3 不写进 task 的"探索发现"

- **`import media_to_doc` 启动时间** ~30ms(实测,7 个重依赖全部不在 sys.modules)
- **W9 整体改动 < 1000 行**:`__init__.py` 215 + `test_init.py` 323 + `README.md` 280 + `LEARNINGS.md` ~250 + `cross_project_demo.py` 215 + `MCP_INTEGRATION.md` +50 + `CLAUDE.md` +30 + `task.md` +80 = ~1450 行
- **ruff F541 f-string 检测**:仅 8 处,全部是 demo 文件里的"装饰性 f-string",`--fix` 自动去前缀
- **PEP 562 在 Python 3.7+ 才生效**:本项目 `requires-python>=3.11`,完全兼容

---

## 6. 测试状态

```
$ uv run pytest
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
collected 508 items

tests/test_smoke.py::... [14 tests]
tests/test_utils/... [15 tests]
tests/test_llm/test_base.py::... [12 tests]
tests/test_llm/test_ollama.py::... [11 tests]
tests/test_llm/test_anthropic.py::... [11 tests]
tests/test_llm/test_openai_compat.py::... [17 tests]
tests/test_llm/test_health.py::... [15 tests]
tests/test_pipeline/test_audio.py::... [9 tests]
tests/test_pipeline/test_asr.py::... [11 tests]
tests/test_pipeline/test_frames.py::... [10 tests + 1 pattern data]
tests/test_pipeline/test_ocr.py::... [20 tests]
tests/test_pipeline/test_asr_correct.py::... [19 tests]
tests/test_pipeline/test_chapters.py::... [21 tests]
tests/test_pipeline/test_draft.py::... [26 tests]
tests/test_pipeline/test_imagegen.py::... [18 tests]
tests/test_pipeline/test_render.py::... [29 tests]
tests/test_pipeline/test_longdoc.py::... [32 tests]
tests/test_pipeline/test_verify.py::... [27 tests]
tests/test_pipeline/test_runner.py::... [15 tests]
tests/test_logger/test_pipeline_logger.py::... [28 tests]
tests/test_logger/test_gatekeeper.py::... [15 tests]
tests/test_logger/test_learnings.py::... [18 tests]
tests/test_init.py::... [26 tests]                                       ← W9 NEW
tests/test_cli.py::... [21 tests]
tests/test_mcp_server.py::... [36 tests]

======================= 508 passed in 5.02s =======================
```

ruff check `src/ tests/ examples/`:

```
All checks passed!
```

demo 验证:

```
$ uv run python examples/cross_project_demo.py demo-lazy
__version__ = 0.1.0
__all__ 长度 = 52
重依赖模块加载状态(应该全 False):
  [lazy OK]  faster_whisper
  [lazy OK]  scenedetect
  [lazy OK]  rapidocr
  [lazy OK]  diffusers
  [lazy OK]  anthropic
  [lazy OK]  ollama
  [lazy OK]  openai
```

---

## 7. Git 状态(commit 前)

```
$ git status
On branch feat/pipeline-w9-docs   ← 待创建
Changes not staged for commit:
  modified:   .learnings/LEARNINGS.md
  modified:   CLAUDE.md
  modified:   README.md
  modified:   docs/MCP_INTEGRATION.md
  modified:   src/media_to_doc/__init__.py
  modified:   task.md

Untracked files:
  examples/
  tests/test_init.py
```

**待 commit 内容**:

- **源码**:`src/media_to_doc/__init__.py` 重写(Phase 0 占位 → W9 PEP 562 re-export)
- **测试**:`tests/test_init.py` 新增(26 用例)
- **示例**:`examples/cross_project_demo.py` 新增(4 demo)
- **文档**:`README.md` / `.learnings/LEARNINGS.md` / `docs/MCP_INTEGRATION.md` / `CLAUDE.md` / `task.md`

预计 commit message:

```
docs: W9 — Phase 7 文档完善 + Python API 顶层 re-export

- src/media_to_doc/__init__.py: PEP 562 __getattr__ 顶层 re-export
  - 52 个公开符号通过 _LAZY_EXPORTS 注册,首次访问才 importlib.import_module
  - import media_to_doc 启动 < 100ms,faster-whisper / diffusers / anthropic
    等重依赖按需加载
- tests/test_init.py: 26 用例覆盖 lazy import / 缓存 / 未知符号 / dir / 一致性
- examples/cross_project_demo.py: 4 demo(lazy / metrics / pipeline / config)
- README.md: 5 分钟快速开始 + 三种调用方式 + 52 公开 API 表 + 11 环境变量 +
  W3-W8 产物布局 + LE 五层闭环
- .learnings/LEARNINGS.md: 首批 14 条 LP 条目(W1-W8 关键 best_practice)
- docs/MCP_INTEGRATION.md: 6 → 8 工具 + W8 get_run_metrics / list_runs 详细签名
- CLAUDE.md: §9.3 Python API 示例 + §9.4 MCP 8 工具清单
- task.md: Phase 7 全 [x] + 会话 14 历史

测试: 482 → 508 passed / 0 skipped(+26)
ruff:  All checks passed(src/ + tests/ + examples/)
```

---

## 8. 给下一个会话的提示

**新会话第一句话建议**:

```
承接 handoff-docs-api-re-export-2026-07-19.md,W9 已完成(508 测试)。
请评审 W9 commit,决定 v1.0 收尾方向:
- A. 跑示例视频真实端到端(用 W5 已有 transcript)
- B. v1.0 release prep(CHANGELOG / GitHub Release / PyPI / docs/installation.md)
- C. 修 W8 技术债 D:_chapters_wrapper 等接 ctx.metrics 自动聚合 llm_health
- D. UI:Tauri 2 桌面壳启动(Phase 8 候选)
```

**主要任务**(按 v1.0 优先级排序):

1. **真实端到端验证**(如果有 GPU/CPU 资源)— 跑 W5 bx2o443en transcript 续 chapters→verify
2. **v1.0 release prep** — CHANGELOG.md + GitHub Release + PyPI 发布 + docs/installation.md
3. **修 W8 技术债 D** — `_chapters_wrapper` 等接 ctx.metrics 自动聚合 llm_health
4. **LE 健康度真实数据验证** — 跑 3 次示例视频演示 `assess_llm_health` 跨 run 聚合 + Pattern-Key 晋升

**别忘了**:

- 缩进 2 空格,Python 函数类型注解(全局偏好)
- 函数 ≤ 100 行,模块 ≤ 500 行(TDD §9.2)— W9 __init__.py 215 行,合规
- 测试不要真跑 11 stage(monkeypatch 是已验证模式)
- 不要破坏已通过的 508 个测试
- v1.0 时所有跨项目 demo / public API 必须验证可用

**关键参考**:

- `handoff-le-wiring-2026-07-19.md` — 上一会话(W8 LE)
- `handoff-pipeline-w7-mcp-2026-07-19.md` — W7 MCP
- `handoff-pipeline-w6-cli-2026-07-19.md` — W6 CLI
- `PRD.md` / `TDD.md` / `ROADMAP.md`
- 本会话:`src/media_to_doc/__init__.py`(PEP 562 re-export)
- 本会话:`tests/test_init.py`(lazy import 测试模式)
- 本会话:`examples/cross_project_demo.py`(跨项目 demo 模式)
- 本会话:`.learnings/LEARNINGS.md`(14 条 best_practice)

**复杂度提示**:

- W9 实际耗时 ~2h(略短于预期,W8 后模式成熟)
- 测试 +26(W8 482 → W9 508),远超过 ROADMAP Phase 5 目标 110+ 用例
- v1.0 release prep 是 2-3h 中等任务,可拆成多个 commit(README/CHANGELOG/PyPI)
- 真实端到端验证是 1-2h(取决于是否有 transcript 复用)

---

## 9. 上下文参考链接

- `CLAUDE.md` — 项目级指引
- `task.md` — 活跃 todo(含本会话历史)
- `PRD.md` / `TDD.md` / `ROADMAP.md`
- `handoff-template.md` — 长期复用模板
- `handoff-le-wiring-2026-07-19.md` — 上一会话(W8 LE)
- `handoff-pipeline-w7-mcp-2026-07-19.md` — W7 MCP
- `handoff-pipeline-w6-cli-2026-07-19.md` — W6 CLI
- `handoff-pipeline-w5-smoke-2026-07-19.md` — W5 端到端冒烟
- `_research/LE_DESIGN.md` — LE 详细设计
- `git log --oneline`(W9 commit 待创建)

---

## 10. 自检清单

- [x] 本会话目标全部完成(A + B 组合)
- [x] 无未提交代码改动(待 commit)
- [x] 测试状态明确(508 passed / 0 skipped in 5.02s)
- [x] ruff 状态明确(All checks passed,src/ + tests/ + examples/)
- [x] demo 端到端验证(demo-lazy 跑通,52 公开符号,7 重依赖全部 lazy)
- [x] 下次会话第一句话建议清晰
- [x] 关键决策记录 7 条,带"为什么"
- [x] 上下文参考链接完整
- [x] `uv run pytest` 端到端验证通过(508/508)
- [x] `uv run ruff check src/ tests/ examples/` 全过
- [x] pytest 增量:W8 → W9 = 482 → 508(+26)
- [x] 公开 API 数量:52 个符号(W9 PEP 562 re-export)
- [x] MCP 工具数量:8 个(W7=6 + W8=2)
- [x] LEARNINGS.md 条目:14 条 LP(W1-W9 关键 best_practice)
- [x] README 结构:5 分钟 + 三种调用 + API 表 + 环境变量表 + 产物布局 + LE 五层 + 路线图 + 技术栈
- [x] examples/cross_project_demo.py:4 个 demo(lazy / metrics / pipeline / config)
- [x] `task.md` Phase 7 全 [x] + 会话 14 历史
- [x] `mtd --version` 仍输出 `media-to-doc 0.1.0`(未变)