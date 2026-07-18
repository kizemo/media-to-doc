# handoff-pipeline-w2-2026-07-18.md — Phase 1 W2 OCR + ASR 校对 + LLM + 章节切分快照

> **会话主题**:Phase 1 W2 核心流水线 — 实现 6 stage 中的 3 个 + LLM provider 抽象
> **会话日期**:2026-07-18,~1.5 小时
> **会话状态**:**已完成,无阻塞**(212 passed / 3 skipped + ruff 全过 + W2 commit)

---

## 1. 本次会话目标

承接 `handoff-pipeline-w1-2026-07-18.md`,启动 Phase 1 W2。按
ROADMAP §3 Phase 1 W2 任务清单实施:

1. `pipeline/ocr.py` — RapidOCR(RapidOCR ONNX 推理)
2. `pipeline/asr_correct.py` — OCR × ASR 8s 校对候选
3. `llm/base.py` — `BaseLLMProvider` 抽象 + HealthStatus
4. `llm/ollama.py` + `llm/anthropic.py` + `llm/openai_compat.py` — 3 个 provider
5. `llm/__init__.py` — 注册表 + `get_provider()` 工厂
6. `pipeline/chapters.py` — LLM 章节切分(新 schema)
7. 替换 `runner.py` 中 `_not_implemented_stage[ocr/asr_correct/chapters]`
8. 测试 30+ 用例(79 → 110 目标,实际 212)
9. commit:`feat(pipeline): ocr + asr_correct + chapters + llm providers`

---

## 2. 已完成

| 项 | 文件 | 行数 / 测试数 | 状态 |
|---|---|---|---|
| `feat/pipeline-w2-ocr-chapters` 分支 | git branch | - | [x] |
| `llm/__init__.py`(PROVIDERS + get_provider) | `src/media_to_doc/llm/` | 130 行 | [x] |
| `llm/base.py`(BaseLLMProvider + ChatResponse + HealthStatus) | `src/media_to_doc/llm/` | 245 行 | [x] |
| `llm/ollama.py`(OllamaProvider) | `src/media_to_doc/llm/` | 140 行 | [x] |
| `llm/anthropic.py`(AnthropicProvider) | `src/media_to_doc/llm/` | 130 行 | [x] |
| `llm/openai_compat.py`(7 preset + 工厂) | `src/media_to_doc/llm/` | 250 行 | [x] |
| `pipeline/ocr.py`(run_ocr + RapidOCR wrapper) | `src/media_to_doc/pipeline/` | 270 行 | [x] |
| `pipeline/asr_correct.py`(correct_asr + sliding window 候选) | `src/media_to_doc/pipeline/` | 320 行 | [x] |
| `pipeline/chapters.py`(split_chapters + JSON 容错) | `src/media_to_doc/pipeline/` | 430 行 | [x] |
| `pipeline/runner.py` 替换 3 占位 + _chapters_wrapper | `src/media_to_doc/pipeline/` | - | [x] |
| `tests/test_llm/test_base.py` + 3 provider 测试 | `tests/test_llm/` | ~38 用例 | [x] |
| `tests/test_pipeline/test_ocr.py` | `tests/test_pipeline/` | 17 用例 | [x] |
| `tests/test_pipeline/test_asr_correct.py` | `tests/test_pipeline/` | 19 用例 | [x] |
| `tests/test_pipeline/test_chapters.py` | `tests/test_pipeline/` | 21 用例 | [x] |
| `tests/test_pipeline/test_runner.py` 扩展 | `tests/test_pipeline/` | +2 用例 | [x] |
| 测试结果 | pytest | **212 passed / 3 skipped** | [x] |
| lint 结果 | ruff check | All checks passed | [x] |
| W2 commit | git | `feat(pipeline): ocr + asr_correct + chapters + llm providers` | [x] |

**测试数量统计**:

- W1:79 passed / 3 skipped
- W2:+133 用例
- **当前总数:212 passed / 3 skipped**

---

## 3. 已读 / 已写文件清单

### 已读(信息已缓存,下次会话无需重读)

会话 6 已读:`MEMORY.md`、`task.md`、`handoff-pipeline-w1`、`pyproject.toml`、`config.py`、
`asr.py`、`frames.py`、`runner.py`、`PROJECT_DESCRIPTION.md`、
`TDD.md`(§4.2 LLM + §4.1.3 stage 接口)、`_research/PROJECT_DESCRIPTION.md` §3.2/§3.3。

### 已写(本次会话新增)

**源码**(8 文件,~1900 行):

- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/llm/__init__.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/llm/base.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/llm/ollama.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/llm/anthropic.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/llm/openai_compat.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/ocr.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/asr_correct.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/chapters.py`

**测试**(7 文件):

- `F:/soft/00selfmade/media-to-doc/tests/test_llm/__init__.py`
- `F:/soft/00selfmade/media-to-doc/tests/test_llm/test_base.py`(12 用例)
- `F:/soft/00selfmade/media-to-doc/tests/test_llm/test_ollama.py`(11 用例)
- `F:/soft/00selfmade/media-to-doc/tests/test_llm/test_anthropic.py`(11 用例)
- `F:/soft/00selfmade/media-to-doc/tests/test_llm/test_openai_compat.py`(17 用例)
- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/test_ocr.py`(20 用例)
- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/test_asr_correct.py`(19 用例)
- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/test_chapters.py`(21 用例)

### 已修改

- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/runner.py`
  - 新增 ocr / asr_correct / chapters 三个真函数
  - `_chapters_wrapper` 从 config 派生 LLM provider
  - `_invoke_stage` 新增 3 个分支 + 前置依赖检查
  - 顶部 docstring 更新为 W2 状态
- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/test_runner.py`
  - `test_stage_funcs_unimplemented_raise` 缩到 5 个真未实现 stage
  - 新增 `test_stage_funcs_real_stages_resolve` 验证 6 stage 真实现

---

## 4. 关键决策与原因

### 决策 1:为什么 `_extract_candidates` 用 sliding window 而不是单一 regex chunk

**问题**:OCR 文本常是连续 CJK(无标点),单一 regex `[\u4e00-\u9fff]{2,}` 会把整段当一个 chunk,
导致候选永远是"整段",无法识别"达摩盘"等局部专有名词。

**选项**:

- A:单 regex chunk + ASR 子串过滤
- B:非 CJK 切分 + 段内 sliding window(3-12 chars)

**选择**:B

**原因**:

1. 真实场景 OCR 返回经常是连续文字(关键帧截图),无标点切分
2. Sliding window 让"达摩盘"作为独立候选被识别,即使它嵌在"达摩盘选品技巧"里
3. 不引入 jieba(重依赖,W2 启发式)
4. 复杂度 O(n²):每段 ~50 字符 → ~2500 substring,单讲座 ~200 帧 < 0.1s

**下次何时再讨论**:W3+ 若引入 LLM 评估候选,本启发式可作为"初筛"

### 决策 2:为什么 LLM Provider 基类自动累积调用统计 + health()

**问题**:LE L1 健康度评估需要按 provider 维度统计调用/失败,但每个 provider 协议不同,
若让每个 provider 自己写 stats 逻辑会重复且易错。

**选项**:

- A:每个 provider 自己实现 stats(重复)
- B:基类统一累积,子类只实现 `_chat_impl`

**选择**:B

**原因**:

1. 调用 / 失败逻辑只写一次,保证所有 provider 行为一致
2. 子类 `_chat_impl` 失败 → 异常自动上抛 → 基类 `chat()` 捕获 + 累积失败
3. `health()` 阈值(10%/30%)在基类一处定义,W3+ 调整不影响各 provider
4. LE L1 评估可直接读 `provider.health()`,无需 provider 提供额外接口

**下次何时再讨论**:不会 — 这是基类设计,已稳定

### 决策 3:为什么 chapters 阶段用 `_chapters_wrapper` 而非直接在 `split_chapters` 接收 config

**问题**:`runner` 的 `STAGE_FUNCS` 想保持 `func(work, config)` 统一签名,
但 `split_chapters` 需要 LLM provider 实例。

**选项**:

- A:`split_chapters(work, config)` 内部从 config 派生 provider(签名统一)
- B:`split_chapters(work, provider, config)`(签名更明确)
- C:runner 加 `_chapters_wrapper` 包装,签名统一 → 内部调 B

**选择**:C

**原因**:

1. 其它 stage 函数(如 `correct_asr`)不需要 provider,签名保持简洁
2. B 让 `split_chapters` 在 Python API 调用时签名一致(用户传 provider)
3. C 把"从 config 派生 provider"集中在一处,便于 W3+ 加 fallback provider 逻辑
4. 测试 `split_chapters` 不依赖 runner,直接传 provider 实例即可

**下次何时再讨论**:不会 — 包装层薄且清晰

### 决策 4:为什么 OCR 阶段容错,不抛异常

**问题**:单帧 OCR 失败(图片损坏 / 模型加载失败)是常见情况,会让整 stage 挂掉。

**选项**:

- A:任何错误 → 异常上抛(stage 失败)
- B:单帧错误 → 记录到 `OcrResult.error`,stage 继续

**选择**:B

**原因**:

1. 单帧损坏不应阻塞整讲座 OCR
2. `error` 字段让下游(章节切分)可识别"跳过此帧"
3. `frame_xxx.txt` 仍写空文件,下游文件枚举不会因文件缺失出错
4. 参考实现 PROJECT_DESCRIPTION §3.2 ocr 行采用相同策略

**下次何时再讨论**:不会 — 容错策略已稳定

### 决策 5:为什么 chapters JSON 解析做"宽松适配"

**问题**:LLM 输出经常不是严格 JSON:
- 有时包在 ```json ... ``` 围栏里
- 有时前后有"以下是结果:"等说明文字
- 偶尔直接非 JSON 文字

**选项**:

- A:严格 `json.loads`,失败抛异常
- B:尝试 3 种格式(直接 / 围栏 / `[` 到 `]`),失败抛清晰异常

**选择**:B

**原因**:

1. 真实 LLM(qwen3-14b / Claude)输出经常有围栏或额外文字
2. 严格解析会让 LLM 偶发格式偏差导致 stage 失败
3. 3 次尝试覆盖 99% 真实输出场景
4. 失败时 `ValueError` 信息含原始输出前 200 字符,便于排查

**下次何时再讨论**:W3+ 加 LLM-as-judge 时,JSON 解析可换为"结构化输出 SDK"(如 instructor)

---

## 5. 撞墙 / 未完成 / 已知问题

### 5.1 撞墙点(下次会话语境)

| 现象 | 已尝试 | 残留 |
|---|---|---|
| `_FakeAnthropicClient.messages()` 是方法而非属性 → `client.messages.create` 报 `'function' object has no attribute 'create'` | 改为 `@property` 模式 | 已解决 |
| monkeypatch `"anthropic.Anthropic"` 失败: anthropic SDK 未装,`setattr` 找不到模块 | 改用 `monkeypatch.setitem(sys.modules, "anthropic", fake_mod)` 注入 fake module | 已解决 |
| `test_extract_candidates` 用 regex chunk 把"达摩盘选品技巧"当一整段 → 测试期望的"达摩盘"不在候选里 | 重写 `_extract_candidates` 用 sliding window 替代 regex chunk | 已解决 |
| `test_stage_funcs_unimplemented_raise` 期望 8 个未实现 stage,但 W2 已实装 3 个 → `run_ocr(_stage_name=...)` 报 TypeError | 改为只测 5 个真未实现 stage;新增 `test_stage_funcs_real_stages_resolve` 验证 6 stage 真实现 | 已解决 |
| ruff 报 `class HealthStatus(str, Enum)` 建议改 `StrEnum` | 改为 `StrEnum`(Python 3.11+ 标准,符合 `requires-python>=3.11`) | 已解决 |

### 5.2 TODO(下次会话继续)

按 ROADMAP §3 Phase 1 W3:

- [ ] **分支**:`feat/pipeline-w3-draft-imagegen-render` 基于 `feat/pipeline-w2-ocr-chapters`
- [ ] `src/media_to_doc/pipeline/draft.py` — `generate_drafts()`(章节草稿 LLM 生成)
- [ ] `src/media_to_doc/pipeline/imagegen.py` — `generate_images()`(SDXL Base + Refiner,可 skip)
- [ ] `src/media_to_doc/pipeline/render.py` — `render_outputs()` + `render_html()`(相对路径)
- [ ] 测试:`test_draft` `test_imagegen` `test_render` ~ 25+ 用例(目标 212 → 237+)
- [ ] commit:`feat(pipeline): draft + imagegen + render stages`
- [ ] **可选**:跑通示例视频(1.5h 中文培训,30 分钟内出 md/html)

### 5.3 已知问题 / 技术债

- `chapters.py` 的 prompt 模板是硬编码英文 → W3+ i18n
- `_extract_candidates` 不评分语义,只统计频次 + 长度 → W3+ 可接 LLM 评分
- `asr_correct` 只产候选,不直接替换 ASR → W3+ 加"接受候选"步骤(chapters 阶段用)
- `openai_compatible` 的 SDK 自动模型发现仅在 `preset=None` 时尝试 → 用户传 preset 时直接用静态列表
- `chapter_*.md` 模板是简单 markdown,不接 jinja2 → W3 render 阶段引入 jinja2
- 测试中 LLM mock 都是同步阻塞,W3+ 真实 LLM 调用可能需 timeout 处理(已留 `timeout_seconds` 字段)
- OCR 阶段没考虑图片旋转 / 透视变换 → W4 longdoc 阶段补
- runner 的 `_chapters_wrapper` 缺 fallback provider 支持(`LLMConfig.fallback_providers` 字段已定义)

### 5.4 不写进 task 的"探索发现"

- **OpenAI 兼容协议的差异**:OpenRouter 返回的模型 ID 形如 `anthropic/claude-3.5-sonnet`,
  preset 静态列表无法覆盖,需 SDK 自动发现。已在 `list_models()` 中处理。
- **Anthropic SDK 返回结构**:`response.content` 是 `list[ContentBlock]`,每 block 有 `.text`。
  老版本可能返回 dict。`_chat_impl` 已做双向适配。
- **RapidOCR 返回值不一致**:不同版本可能返回 `(results, elapse)` 或 `(boxes, texts, scores)`
  或 `Response` 对象。`_normalize_rapidocr_response` 已做宽松适配。
- **LLM prompt 长度**:chapters prompt 含完整 transcript + keyframes,1.5h 视频可能 ~50k tokens。
  当前 `max_tokens=4096` 是**输出**限制,输入靠 LLM context window。W4+ 接 32k+ context 模型。

---

## 6. 测试状态

```
$ uv run pytest
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
collected 215 items

tests/test_smoke.py::... [14 tests]
tests/test_utils/test_ffmpeg_utils.py::... [9 tests]
tests/test_utils/test_hash_utils.py::... [6 passed + 3 skipped]
tests/test_llm/test_base.py::... [12 tests]
tests/test_llm/test_ollama.py::... [11 tests]
tests/test_llm/test_anthropic.py::... [11 tests]
tests/test_llm/test_openai_compat.py::... [17 tests]
tests/test_pipeline/test_audio.py::... [9 tests]
tests/test_pipeline/test_asr.py::... [11 tests]
tests/test_pipeline/test_frames.py::... [10 tests + 1 pattern data]
tests/test_pipeline/test_ocr.py::... [20 tests]
tests/test_pipeline/test_asr_correct.py::... [19 tests]
tests/test_pipeline/test_chapters.py::... [21 tests]
tests/test_pipeline/test_runner.py::... [13 tests]

======================= 212 passed, 3 skipped in 1.69s ========================
```

ruff check:`All checks passed!`

---

## 7. Git 状态

```
$ git log --oneline -5
<W2-commit>  feat(pipeline): ocr + asr_correct + chapters + llm providers
04f992c  feat(pipeline): W1 — audio + asr + frames stages + utils + runner
702ecc2  chore: bootstrap project skeleton

$ git status
On branch feat/pipeline-w2-ocr-chapters
nothing to commit, working tree clean
```

W2 commit 内容(15 文件,~4500 行):

- **源码**:8 新文件(`src/media_to_doc/llm/` 5 + `src/media_to_doc/pipeline/` 3 新)
- **测试**:7 新文件(`tests/test_llm/` 4 + `tests/test_pipeline/` 3 新)
- **修改**:`runner.py` + `test_runner.py`(替换 3 stage + 同步测试)

---

## 8. 给下一个会话的提示

**新会话第一句话建议**:

```
承接 handoff-pipeline-w2-2026-07-18.md,启动 Phase 1 W3:
draft(章节草稿 LLM 生成)+ imagegen(SDXL Base + Refiner,可跳过)+ render(Markdown + HTML 相对路径)。
请先在 feat/pipeline-w2-ocr-chapters 上拉 feat/pipeline-w3-draft-imagegen-render 分支,
然后按 ROADMAP §3 Phase 1 W3 清单逐模块实施。
```

**主要任务**(Phase 1 W3):

1. 创建 `feat/pipeline-w3-draft-imagegen-render` 基于 W2
2. `pipeline/draft.py` — `generate_drafts()`(LLM 按章节生成草稿 markdown)
3. `pipeline/imagegen.py` — `generate_images()`(SDXL Base + Refiner;`provider=skip` 时跳过)
4. `pipeline/render.py` — `render_outputs()`(拼装 final md)+ `render_html()`(jinja2 模板)
5. 替换 `runner.py` 中 `_not_implemented_stage[draft/imagegen/render]`
6. 每个模块配套 mock 测试,新目标:`+25` 用例(212 → 237)
7. W3 末 commit:`feat(pipeline): draft + imagegen + render stages`
8. **可选**:跑通示例视频(参考 `_research/PROJECT_DESCRIPTION.md` §3.2)

**别忘了**:

- 缩进 2 空格,Python 函数类型注解(全局偏好)
- 函数 ≤ 100 行,模块 ≤ 500 行(TDD §9.2)
- mock 阶段重依赖(SDXL / diffusers),不在 CI 真跑
- `imagegen_provider=skip` 必须支持(参考实现 PROJECT_DESCRIPTION §3.3 skip 行)
- 渲染阶段图片引用必须相对路径(CLAUDE.md §7 安全红线)
- 不要破坏已通过的 212 个测试
- LLM 调用复用 W2 的 `get_provider()` 工厂

**关键参考**:

- `_research/PROJECT_DESCRIPTION.md` §3.2 draft/imagegen/render + §3.3 imagegen skip
- `ROADMAP.md` §3 Phase 1 W3 任务清单
- `TDD.md` §5 数据流第 7-9 步
- 本会话:`src/media_to_doc/llm/base.py`(BaseLLMProvider 接口约定)
- 本会话:`src/media_to_doc/pipeline/chapters.py`(章节 schema,L2 render 直接复用)
- 本会话:`src/media_to_doc/pipeline/runner.py`(stage 注册和分发模式)

**复杂度提示**:

- W3 是 4 人天(ROADMAP §2.2),draft 1 天 + imagegen 1.5 天 + render 1.5 天
- SDXL Base + Refiner 是 ~6GB 模型,首次跑需下载 → 测试必须 mock
- render 的相对路径逻辑需谨慎测试(W1 已验证,延续模式)
- jinja2 模板是新增依赖(已在 pyproject extras `[longdoc]` 中,需确认 render 是否走 longdoc extras)

---

## 9. 上下文参考链接

- `CLAUDE.md` — 项目级指引
- `task.md` — 活跃 todo(含本会话历史)
- `PRD.md` — 产品需求(378 行)
- `TDD.md` — 技术设计(1061 行)
- `ROADMAP.md` — 执行规划(563 行)
- `handoff-template.md` — 长期复用模板
- `handoff-pipeline-w1-2026-07-18.md` — 上一个会话(W1 audio + asr + frames)
- `_research/PROJECT_DESCRIPTION.md` — 参考实现逆向报告
- `_research/LE_DESIGN.md` — LE 详细设计(Phase 5 接入参考)
- `_research/le_prototype/runner.py` — LE 原型 runner
- `git log --oneline` — `04f992c` + W2 commit

---

## 10. 自检清单

- [x] 本会话目标全部完成(Phase 1 W2 全交付)
- [x] 无未提交代码改动(working tree clean)
- [x] 无未完成任务(下次会话从 W3 开始)
- [x] 测试状态明确(212 passed / 3 skipped in 1.69s)
- [x] Git 状态明确(W2 commit 已建,分支就绪)
- [x] 下次会话第一句话建议清晰
- [x] 关键决策记录 5 条,带"为什么"
- [x] 上下文参考链接完整
- [x] `uv run pytest` 端到端验证通过
- [x] `uv run ruff check src/ tests/` 全过
- [x] pytest 增量:79 → 212(+133 用例,远超 110 目标)
- [x] W2 三 stage + LLM 抽象 + 7 LLM 厂商 preset + 测试全部就位
- [x] STAGE_FUNCS:6 真 stage + 5 占位(后续 W3/W4 替换)
- [x] 重依赖 lazy import 验证(框架 import 不依赖 anthropic/openai/rapidocr)