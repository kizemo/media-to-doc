# handoff-pipeline-w10-llm-health-2026-07-19.md — Phase 10 W10-C 修 W8 技术债 D 快照

> **会话主题**:Phase 10 W10-C — 修 W8 技术债 D,自动跨 stage 聚合 `pipeline_run.json.llm_health`
> **会话日期**:2026-07-19,~1.5 小时
> **会话状态**:**已完成,无阻塞**(519 passed / 0 skipped + ruff 全过)
> **commit**:`bddc387`(`fix(pipeline): W10-C — auto-aggregate llm_health from chapters/draft/longdoc wrappers`)

---

## 1. 本次会话目标

承接 `handoff-docs-api-re-export-2026-07-19.md`,用户从 v1.0 候选里选 **C**:

> **C. 修 W8 技术债 D**:`_chapters_wrapper` 等接 ctx.metrics 自动聚合 llm_health(W8 在 runner 末尾留 `llm_health={}` TODO,assess_llm_health 全局永远算空)

**W10-C** = W10 的 C 子任务(W10 可能还有 A/B/D 子任务)。

---

## 2. 已完成

| 项 | 文件 | 行数 / 用例 | 状态 |
|---|---|---|---|
| `fix/pipeline-w10-llm-health-auto-aggregate` 分支(基于 W9 `7dfb5f2`) | git branch | - | [x] |
| `StageContext.metrics` 字段 + 默认值 | `src/media_to_doc/pipeline/runner.py` | +4 行 | [x] |
| 3 wrapper 签名 `(work, config)` → `(ctx: StageContext)` | 同上 | +6 / -2 行 | [x] |
| `_invoke_stage` 3 分支 `func(ctx.work, ctx.config)` → `func(ctx)` | 同上 | 3 行替换 | [x] |
| `ctx = StageContext(...)` 创建移到 for loop 外 | 同上 | 1 行移位 | [x] |
| 新增 `_aggregate_llm_health(metrics)` helper | 同上 | +38 行 | [x] |
| `logger.finalize(llm_health=_aggregate_llm_health(...))` 替换 `{}` TODO | 同上 | 1 行替换 | [x] |
| 11 个新单元测试 | `tests/test_pipeline/test_runner.py` | +382 / -21 行 | [x] |
| `tests/test_runner.py` import 增加 `_aggregate_llm_health` + `ChatResponse` 等 | 同上 | +3 / -1 行 | [x] |
| `task.md` 加 W10-C 任务 + 会话 15 历史 | `task.md` | +30 行 | [x] |
| 测试结果 | pytest | **519 passed / 0 skipped**(+11) | [x] |
| lint 结果 | ruff check src/ tests/ examples/ | All checks passed | [x] |
| `mtd --version` 验证 CLI 仍 OK | CLI | `media-to-doc 0.1.0` | [x] |
| W10-C commit | git | `bddc387` | [x] |

**测试数量统计**:

- W9:508 passed / 0 skipped
- W10-C:**519 passed / 0 skipped**(+11 用例)
- **当前总数:519 passed**

---

## 3. 已读 / 已写文件清单

### 已读(信息已缓存,下次会话无需重读)

- `MEMORY.md` / `task.md` / `handoff-docs-api-re-export-2026-07-19.md` / `handoff-le-wiring-2026-07-19.md`
- `src/media_to_doc/llm/base.py`(`BaseLLMProvider.health()` → `HealthReport(total_calls, total_failures, ...)`)
- `src/media_to_doc/logger/pipeline_logger.py`(`finalize(llm_health=...)` → 写 `pipeline_run.json`)
- `src/media_to_doc/logger/learnings.py`(`assess_llm_health()` 期望 `llm_health: dict[provider_key, dict[calls, failures]]`)
- `src/media_to_doc/config.py`(`PipelineConfig.longdoc_llm_provider` 默认 `"skip"`)
- `src/media_to_doc/pipeline/runner.py`(W8 baseline,有 `llm_health={}` TODO 注释)
- `tests/test_pipeline/test_runner.py`(W8 已有 15 用例 + monkeypatch `_invoke_stage` 模式)

### 已写(本次会话新增/修改)

**源码**(1 文件,+103 / -21 行):

- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/runner.py`:
  - `StageContext.metrics` 字段
  - 3 wrapper 签名 `(work, config)` → `(ctx)`
  - `_invoke_stage` 3 分支用 `func(ctx)`
  - `run_pipeline` ctx 外移 + 真 `llm_health` 替换
  - `_aggregate_llm_health(metrics)` 新 helper

**测试**(1 文件,+382 / -21 行):

- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/test_runner.py`:
  - import 增加 `ChatResponse` / `HealthReport` / `HealthStatus` / `_aggregate_llm_health`
  - 新增 `_FakeLLMProvider` 测试 helper(轻量,只实现 `name` / `chat()` / `health()`)
  - 11 个新测试覆盖 StageContext schema / 3 wrapper 注册 / 3 个 _aggregate 边界 / 1 个 E2E

**任务管理**(1 文件,+30 行):

- `F:/soft/00selfmade/media-to-doc/task.md`:Phase 6 加 W10-C 任务行 + 会话 15 历史 + 下次会话提示

---

## 4. 关键决策与原因

### 决策 1:`StageContext.metrics` 默认 `{"llm_providers": {}}` 而非空 `{}`

**问题**:用什么作为 `metrics` 字段的初始结构?

**选择**:`default_factory=lambda: {"llm_providers": {}}`

**原因**:

1. **明确语义**:`ctx.metrics["llm_providers"]` 告诉读者未来要存什么,无需查文档
2. **预留扩展空间**:未来要加 `"timing"` / `"memory"` / `"custom"` 等其他指标时,直接 `ctx.metrics["timing"] = ...` 一致
3. **测试断言友好**:`ctx.metrics["llm_providers"]` 不需要先检查 key 存在

**下次何时再讨论**:不会 — 默认结构已显式,扩展直接在字典内追加 key

### 决策 2:3 个 wrapper 签名 `(work, config)` → `(ctx)`

**问题**:wrapper 怎么拿到 ctx 注册 provider?

**选择**:签名彻底改,从 `(work: Path, config: WorkflowConfig)` 改为 `(ctx: StageContext)`,内部从 `ctx.work` / `ctx.config` 取值。

**原因**:

1. **单一参数接口**:无需 `if ctx is not None: register` 防御分支
2. **wrapper 必然走 ctx(被 `_invoke_stage` 调用)**:让 wrapper 完全依赖 ctx 是单向的,不会同时被 `(work, config)` 和 `(ctx)` 调用的双重约定
3. **未来扩展友好**:如果未来 wrapper 还要写 `ctx.metrics["timing"]["start"]`,直接 `ctx.metrics[...]` 即可,无需改签名
4. **测试可控**:测试用 `StageContext(inbox=..., work=..., config=...)` 构造,语义统一

**下次何时再讨论**:不会 — 三个 wrapper 已统一签名,所有调用点都是 `_invoke_stage` 的 `func(ctx)`

### 决策 3:`_aggregate_llm_health` key 格式 `{stage_name}_{provider.name}`

**问题**:怎么给聚合后的 LLM 健康度字典选 key,既可读又兼容 `assess_llm_health` 聚合?

**选择**:`f"{stage_name}_{provider.name}"`,例 `chapters_ollama` / `draft_anthropic` / `longdoc_openai_compatible`。

**原因**:

1. **可读**:`pipeline_run.json.llm_health["chapters_ollama"]` 人肉一眼能看出"哪 stage + 哪 provider"
2. **跨 stage 不冲突**:chapters 和 draft 都用 `ollama` provider 时,key 仍然区分(W8 时如果只按 provider name 会合并)
3. **`assess_llm_health` 仍正确 sum**:W8 设计聚合所有 provider_key 的 calls/failures,与是否包含 stage 前缀无关
4. **未来多 stage 多 model 时仍可扩展**:providers 用 openai_compatible 时,同一个 provider 类型可绑多个 model,前 stage 名仍然区分

**下次何时再讨论**:不会 — key 格式与 W8 `assess_llm_health` 完全兼容

### 决策 4:`_aggregate_llm_health` 失败隔离(provider.health() 异常 → stderr + 跳过)

**问题**:`provider.health()` 抛错时怎么处理?

**选择**:`except Exception as exc: print(..., file=sys.stderr); continue`,跳过该项,不破坏聚合。

**原因**:

1. **不破坏 `run_pipeline` 返回**:provider 健康度是聚合辅助,不是调度真相 — 与 W8 `gatekeeper_check` / `logger.finalize` / `post_pipeline_hook` 同款 try/except 隔离模式
2. **部分 provider 失败不应让全部聚合失败**:3 个 provider 中 1 个抛错,剩下 2 个仍计入
3. **stderr 给调试者**:stdout 留给 JSON 输出(W6 设计原则,本会话保持)
4. **测试覆盖**:`test_aggregate_llm_health_handles_provider_health_exception` 显式验证

**下次何时再讨论**:不会 — 失败隔离是 LE 沉淀层的稳定模式,W8 PipelineLogger 已用

### 决策 5:`ctx = StageContext(...)` 创建移到 `for` loop 外

**问题**:原代码每次循环都新建 `ctx`(`runner.py` line 543),`ctx.hint_timestamps` / `ctx.metrics` 都不累积。

**选择**:移到 `try` 块内、`for` 循环前。

**原因**:

1. **本会话核心需求**:`ctx.metrics["llm_providers"][...]` 跨 3 个 LLM wrapper 累积,必须同一 ctx 实例
2. **顺带修复 W8 隐 bug**:`asr` 阶段 line 302-303 设置 `ctx.hint_timestamps = _read_segment_endpoints(ctx.work)`,原代码下一轮新建 ctx,W8 时 hint 丢;修复后真传到 frames(frames stage 仍可能不用 hint 自计算,但不丢)
3. **`stop_after` 提前退出不影响**:loop 提前 break 时 finally 块仍跑,ctx 仍可用

**下次何时再讨论**:不会 — ctx 是 run 级别共享数据,跨 stage 累积是基本语义

### 决策 6:`longdoc_llm_provider == "skip"` 模式不注册 provider

**问题**:`longdoc` 阶段默认 `skip` 模式(不调 LLM),要不要在 `ctx.metrics["llm_providers"]` 注册一个"空 provider"?

**选择**:**不注册**。即 `_longdoc_wrapper` 在 skip 模式短路 `return process_long_doc(work, None, config)`,不创建也不注册 provider。

**原因**:

1. **语义准确**:skip 模式 ="没跑 LLM",aggregator 把"未跑的 stage"也算入会让 `total_calls=0, total_failures=0` 占位 key,污染 `assess_llm_health` 的 `total_runs` 统计
2. **测试可验证**:`test_longdoc_wrapper_skip_does_not_register` 显式验证 skip 不在 metrics 里
3. **fallback 友好**:未来长 doc 阶段有别的策略(规则清理 / 第三方模型)同样适用

**下次何时再讨论**:不会 — skip 模式不注册已与 W4 longdoc 默认行为一致

---

## 5. 撞墙 / 未完成 / 已知问题

### 5.1 撞墙点(已全部解决)

| 现象 | 已尝试 | 残留 |
|---|---|---|
| `test_longdoc_wrapper_registers_provider_when_active` — `KeyError: 'longdoc'` | 检查 wrapper 代码 → `WorkflowConfig().pipeline.longdoc_llm_provider` 默认 `"skip"`(W4 设计),wrapper 短路 return 不注册 | 测显式 `cfg.pipeline.longdoc_llm_provider = "ollama"` 走 active 路径 |
| `test_run_pipeline_writes_real_llm_health_into_pipeline_run_json` — `llm_health == {}` | 检查 `_invoke_stage` mock → 它把所有 stage 直接处理,没让 wrapper 跑 → wrapper 没机会注册 | 改 `_invoke_stage` mock:chapters / draft / longdoc 三个分支调 `func(ctx)` 让 wrapper 跑(已 monkeypatch inner stage 为 no-op) |

### 5.2 已知问题 / 技术债(留 W11+)

- `**chapters/draft 用同一 ollama provider 的去重**:`assess_llm_health` 把 `chapters_ollama` + `draft_ollama` 看作两个独立 provider 聚合,而不是一个 ollama 看 calls=5。如果用户视角是"ollama 总统计",未来可加 secondary aggregation。
- **`hint_timestamps` 现在跨 stage 真传到 frames,但 frames stage 是否使用未验证**:W8 路径就忽略 hint 自算,本次修复让 hint 真到 frames 但是否改善未测。frames stage 是 W1 实现,后续可加 hint-aware 测试。
- **`_FakeLLMProvider` 仅测试用**:放在 `tests/test_pipeline/test_runner.py` 是测试 fixture,如果未来需要可考虑移 `tests/conftest.py`。
- **真实端到端验证未跑**:W10-A(本会话后)候选。

### 5.3 不写进 task 的"探索发现"

- `default_factory=lambda: {"llm_providers": {}}` 的 lambda 与 `dict` 字面量结合,保证每个 `StageContext` 实例有独立字典(`# noqa: B008` 风格已避免)
- `_chapters_wrapper` / `_draft_wrapper` 内仍走 `from ..llm import get_provider` — lazy import 模式,W1 已验证;monkeypatch `media_to_doc.llm.get_provider` 时这层 import 仍能 hook 到(因为每次调用函数时重新 resolve)
- `_invoke_stage` 3 个分支从 `(ctx.work, ctx.config)` 改 `func(ctx)`,测试用 monkeypatch 整套 `_invoke_stage` 时不需要感知(没有 line 改动能传出)
- 测试用 `_FakeLLMProvider.name = "anthropic"` + `cfg.pipeline.longdoc_llm_provider = "ollama"` 是合法的:`pipeline.longdoc_llm_provider` 控制 provider_type / `provider.name` 控制实际返回实例的 name(测试 fixture 完全可控)
- 改动合计 +464 / -21 行,小于 W9 的 ~1450 行,符合 TDD §9.2 模块 ≤ 500 行原则(`test_runner.py` 现在 ~720 行,pytest 单文件可大)
- 旧 TODO 注释 `# TODO(W9+): 跨 stage 累积 LLM provider.health()` 已在 W10-C 实现后保留为历史注释(给后人看出设计演化;也方便 grep 找到本 commit)

---

## 6. 测试状态

```
$ uv run pytest
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
collected 519 items

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
tests/test_pipeline/test_runner.py::... [26 tests]                               ← W10-C +11
tests/test_logger/test_pipeline_logger.py::... [28 tests]
tests/test_logger/test_gatekeeper.py::... [15 tests]
tests/test_logger/test_learnings.py::... [18 tests]
tests/test_init.py::... [26 tests]                                              ← W9
tests/test_cli.py::... [21 tests]
tests/test_mcp_server.py::... [36 tests]

======================= 519 passed in 4.27s =======================
```

ruff check `src/ tests/ examples/`:

```
All checks passed!
```

---

## 7. Git 状态

```
$ git log --oneline -3
bddc387 fix(pipeline): W10-C — auto-aggregate llm_health from chapters/draft/longdoc wrappers
7dfb5f2 docs: W9 — Phase 7 文档完善 + Python API 顶层 re-export
ddeb95f docs(handoff): add W8 LE wiring snapshot + task.md progress
$ git status
On branch fix/pipeline-w10-llm-health-auto-aggregate
Changes not staged for commit:
  modified:   task.md
```

W10-C commit 内容:

- **源码**:`src/media_to_doc/pipeline/runner.py`(1 文件,+103 行)
- **测试**:`tests/test_pipeline/test_runner.py`(1 文件,+382 行)
- 合计:2 文件,+464 / -21 行

---

## 8. 给下一个会话的提示

**新会话第一句话建议**:

```
承接 handoff-pipeline-w10-llm-health-2026-07-19.md,W10-C 已完成(519 测试,
llm_health 自动聚合跑通)。请决定下一阶段:
- A. 跑示例视频真实端到端(用 W10-C 真聚合的 llm_health 验证 get_run_metrics)
- B. v1.0 release prep(CHANGELOG / docs/installation.md / uv build / tag v1.0.0)
```

**主要任务**(按 v1.0 路径优先级排序):

1. **W10-A 真实端到端验证** — 找一段 2-5min 短视频 → `mtd run` 端到端 → 验证 `get_run_metrics` 返回非空 `llm_health`
2. **W10-B v1.0 release** — CHANGELOG + installation.md + `uv build` + `gh release create --draft`
3. **合并 W10-A/B 到 main / release 分支**
4. **LE 健康度真实数据验收**(跑 3 次示例视频,看 Pattern-Key 自动晋升)

**别忘了**:

- 缩进 2 空格,Python 函数类型注解(全局偏好)
- 函数 ≤ 100 行,模块 ≤ 500 行(TDD §9.2)
- 测试不要真跑 11 stage(monkeypatch 是已验证模式)
- 不要破坏已通过的 519 个测试
- `cfg.pipeline.longdoc_llm_provider` 默认 `"skip"`,CI 跑要显式切 active
- 修改源码前先简述计划(全局偏好)

**关键参考**:

- `handoff-docs-api-re-export-2026-07-19.md` — 上一会话(W9 文档)
- `handoff-le-wiring-2026-07-19.md` — W8 LE 闭环 + `llm_health` 当时为空的来源
- `handoff-pipeline-w5-smoke-2026-07-19.md` — 真实端到端跑通参考(W5 1.3GB 视频)
- 本会话:`src/media_to_doc/pipeline/runner.py`(`StageContext.metrics` / 3 wrapper / `_aggregate_llm_health`)
- 本会话:`tests/test_pipeline/test_runner.py`(11 个新测试 + `_FakeLLMProvider`)
- 本会话:`_aggregate_llm_health` 是关键 helper,所有 LLM 健康度都从它走

**复杂度提示**:

- W10-C 实际 ~1.5h(与 handoff 估算一致)
- 改动 +464 / -21 行,wrapper 签名变化最大但影响面收敛到 3 个 wrapper
- W10-A 真实跑需要 ~2-5min 短视频 + Ollama running + 预计 5-10min 跑完
- W10-B release 是 2-3h,先写 CHANGELOG → commit → 再 tag + gh release

---

## 9. 上下文参考链接

- `CLAUDE.md` — 项目级指引
- `task.md` — 活跃 todo(含本会话历史 + W10-A/B 候选)
- `PRD.md` / `TDD.md` / `ROADMAP.md`
- `handoff-template.md` — 长期复用模板
- `handoff-docs-api-re-export-2026-07-19.md` — 上一会话(W9 文档)
- `handoff-le-wiring-2026-07-19.md` — W8 LE 闭环
- `handoff-pipeline-w5-smoke-2026-07-19.md` — 真实端到端参考
- `_research/LE_DESIGN.md` — LE 详细设计
- `git log --oneline`:W10-C `bddc387` + W9 `7dfb5f2`

---

## 10. 自检清单

- [x] 本会话目标全部完成(Phase 10 W10-C 全交付)
- [x] 代码改动已 commit(`bddc387`)
- [x] 测试状态明确(519 passed / 0 skipped in 4.27s)
- [x] ruff 状态明确(All checks passed,src/ + tests/ + examples/)
- [x] `mtd --version` 仍输出 `media-to-doc 0.1.0`(未变)
- [x] 下次会话第一句话建议清晰
- [x] 关键决策记录 6 条,带"为什么"
- [x] 上下文参考链接完整
- [x] `uv run pytest` 端到端验证通过(519/519)
- [x] `uv run ruff check src/ tests/ examples/` 全过
- [x] pytest 增量:W9 → W10-C = 508 → 519(+11)
- [x] W10-C 3 wrapper 全部接受 ctx 注册 provider
- [x] longdoc skip 模式不污染 metrics(测试覆盖)
- [x] `_aggregate_llm_health` 兼容 `assess_llm_health` 期望格式
- [x] 失败隔离(provider.health() 异常 → stderr + 跳过,W8 同款)
- [x] `task.md` Phase 6 加 W10-C 任务行 + 会话 15 历史
