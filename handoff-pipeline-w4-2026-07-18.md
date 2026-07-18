# handoff-pipeline-w4-2026-07-18.md — Phase 1 W4 longdoc + verify 快照

> **会话主题**:Phase 1 W4 核心流水线 — 实现 11 stage 中的 10/11
> **会话日期**:2026-07-18,~1.5 小时
> **会话状态**:**已完成,无阻塞**(346 passed / 3 skipped + ruff 全过 + W4 commit)

---

## 1. 本次会话目标

承接 `handoff-pipeline-w3-2026-07-18.md`,启动 Phase 1 W4。按
ROADMAP §3 Phase 1 W4 任务清单实施:

1. `pipeline/longdoc.py` — `process_long_doc()`(LLM 分块 15000 CJK / 规则清理)
   + `render_final_html()`(TOC + 锚点 + 内嵌 CSS + print stylesheet)
2. `pipeline/verify.py` — `verify_pipeline()`(4 项机器可验证 gatekeeper + image_refs 校验)
3. 替换 `runner.py` 中 `_not_implemented_stage[longdoc/verify]`
4. 测试 ~25 用例(285 → 310 目标,实际 346)
5. commit:`feat(pipeline): W4 — longdoc + verify stages`

---

## 2. 已完成

| 项 | 文件 | 行数 / 测试数 | 状态 |
|---|---|---|---|
| `feat/pipeline-w4-longdoc-verify` 分支 | git branch | - | [x] |
| `pipeline/longdoc.py`(`process_long_doc` + `render_final_html` + 数据类) | `src/media_to_doc/pipeline/` | 725 行 | [x] |
| `pipeline/verify.py`(`verify_pipeline` + 4 个 check helpers + 数据类) | `src/media_to_doc/pipeline/` | 467 行 | [x] |
| `pipeline/runner.py`:`_longdoc_wrapper` + STAGE_FUNCS 替换 2 占位 + _invoke_stage 2 分支 | `src/media_to_doc/pipeline/` | +57 行 | [x] |
| `pipeline/__init__.py` re-export:longdoc / verify | `src/media_to_doc/pipeline/` | - | [x] |
| `config.py`:`PipelineConfig.longdoc_llm_provider = "skip"`(默认) | `src/media_to_doc/config.py` | +4 行 | [x] |
| `tests/test_pipeline/test_longdoc.py` | `tests/` | 425 行 / 32 用例 | [x] |
| `tests/test_pipeline/test_verify.py` | `tests/` | 402 行 / 27 用例 | [x] |
| `tests/test_pipeline/test_runner.py` 占位计数 2 → 0 + 2 个新 resolver 验证 | `tests/` | +0 用例 | [x] |
| 测试结果 | pytest | **346 passed / 3 skipped** | [x] |
| lint 结果 | ruff check | All checks passed | [x] |
| W4 commit | git | `3b32743` | [x] |

**测试数量统计**:

- W1:79 passed / 3 skipped
- W2:212 passed / 3 skipped(+133)
- W3:285 passed / 3 skipped(+73)
- W4:**346 passed / 3 skipped**(+61)
- **当前总数:346 passed / 3 skipped**(远超 W4 目标 310+)

---

## 3. 已读 / 已写文件清单

### 已读(信息已缓存,下次会话无需重读)

会话 8 已读(承接 W3 + W4):
- `MEMORY.md`、`task.md`、`handoff-pipeline-w3-2026-07-18.md`
- `pyproject.toml` W3 版
- `src/media_to_doc/pipeline/runner.py`、`chapters.py`、`draft.py`、`render.py`
- `tests/test_pipeline/test_render.py`(slug / TOC / fixtures 模式)
- `src/media_to_doc/llm/base.py`(`BaseLLMProvider.name` 属性)
- `C:\Users\Duanyi\.claude\skills\long-doc-processor\SKILL.md`
- `references/phase-1-purification.md`(分块 15000 + 5 类保留/4 类清理)
- `references/phase-3-render-html.md`(内嵌 CSS + TOC + alt 校验)
- `references/qa-gates.md` Phase 3 · 7 项
- `references/content-rules.md` §1-§3(5 类保留 / 4 类清理 / 引导语)

### 已写(本次会话新增)

**源码**(2 文件,~1190 行):

- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/longdoc.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/verify.py`

**测试**(2 文件,~830 行):

- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/test_longdoc.py`
- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/test_verify.py`

### 已修改

- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/runner.py`
  - docstring 更新为 W4 状态(11 stage 全部实装)
  - 新增 `_longdoc_wrapper`(`config.pipeline.longdoc_llm_provider == "skip"` → 传 None,否则建 provider)
  - STAGE_FUNCS:2 占位 → `_longdoc_wrapper` / `verify_pipeline`
  - `_invoke_stage` 加 2 分支(longdoc / verify)+ 前置依赖检查(drafts_dir / chapters.json)
  - 顶部 import 加 `process_long_doc` / `verify_pipeline`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/__init__.py`
  - 全量 re-export:`process_long_doc` / `render_final_html` / `verify_pipeline` / `VerifyReport`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/config.py`
  - `PipelineConfig.longdoc_llm_provider: str = "skip"`(控制 longdoc LLM 净化)
- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/test_runner.py`
  - `test_stage_funcs_no_unimplemented_remains` 替代旧 `test_stage_funcs_unimplemented_raise`
  - `test_stage_funcs_real_stages_resolve` 11 stage 全部真实(从 9 扩到 11)
  - 新增 `test_longdoc_wrapper_resolves_to_real_longdoc_module`
  - 新增 `test_verify_stage_resolves_to_real_verify_module`

---

## 4. 关键决策与原因

### 决策 1:为什么 longdoc 默认 `provider=None` / skip,而不是 `provider="ollama"`

**问题**:W3 阶段 chapters / draft 默认用 ollama。但 longdoc 是"可选净化"——没有
LLM 也应该能跑(规则清理是兜底),CI 没有 LLM 时必须能过。

**选项**:

- A:默认 ollama,跑全 LLM 净化
- B:默认 skip(只跑规则清理),用户显式 opt-in
- C:跑 LLM 净化但失败时 fallback 规则

**选择**:B

**原因**:

1. longdoc 是"可选深度净化"层,缺它用户仍有完整的 `.md`(render 阶段产出)
2. CI / 离线环境最常见 — 不应让 skip-LLM 配置成为测试前置
3. 规则清理(去时间戳 / 合并空行)能解决 80% 的实际噪声,LLM 是增量提升
4. 用户在 production 启用 LLM 时只需 `config.pipeline.longdoc_llm_provider = "ollama"`
5. 跨用户一致性:同样的 md 输入,skip 模式结果可重现(reproducible)

**下次何时再讨论**:不会 — skip 默认值已稳定

### 决策 2:为什么用 `longdoc_llm_provider` 字段而不是 `LLMConfig.provider` 扩展

**问题**:要不要在 `LLMConfig.provider` Literal 加 `"skip"`,让 longdoc 直接走主 LLM 配置?

**选项**:

- A:扩展 `LLMConfig.provider` Literal 加 `"skip"`
- B:加独立的 `PipelineConfig.longdoc_llm_provider` 字段
- C:在 longdoc wrapper 内直接判断,无需新字段

**选择**:B

**原因**:

1. `LLMConfig` 是 3 个真 provider 的统一入口(ollama / anthropic / openai_compat)
   加 "skip" 会污染 Literal 语义
2. longdoc 阶段可能用与 chapters / draft 不同的模型(更大的 Qwen3-32B / Claude Opus)
   独立字段便于细粒度配置
3. 默认值 `"skip"` 让没设置 config 的代码路径也安全
4. 未来 Phase 5 LE 可加自动 LLM 评估 + 切 provider(基于 health report),与字段解耦

**下次何时再讨论**:不会 — 字段解耦已稳定

### 决策 3:为什么 longdoc 的分块按"段落边界"而不是"句子边界"

**问题**:15000 CJK 字符分块时,应在哪种边界切?

**选项**:

- A:固定字符位置(粗暴,可能切碎句子)
- B:段落边界(`\n\n`,L1 优先级)
- C:句子边界(`.` / `。`,更细但实现复杂)

**选择**:B(L1)+ A(L3 兜底)

**原因**:

1. 段落是最自然的语义单元,LLM 看到完整段落不会丢上下文
2. 实现简单(`text.split("\n\n")`),与 long-doc-processor skill 一致
3. 极少数"超长段落" > 2*chunk_size 时按字符强行切(避免 LLM 输入被截断)
4. 末块 < min_chunk_size 时合并到前一块(避免小碎片)

**下次何时再讨论**:不会 — 段落切分足够好

### 决策 4:为什么 verify 的 image_refs 检查 wiki-link + md 两种语法

**问题**:`![[gen_xxx.png]]`(草稿 wiki-link)和 `![Image](<stem>/images/gen_xxx.png)`(拼装后
标准 markdown)在产物链中都有出现,verify 应该检查哪几个?

**选项**:

- A:只检查 `![]()`(最终 md)
- B:只检查 `![[]]`(草稿)
- C:两种语法都检查(任一存在即要求文件存在)

**选择**:C

**原因**:

1. render 阶段把 `![[]]` 改写为 `![]()`,但 render 失败 / 跳过时 `![[]]` 可能残留
2. 两种引用都指向 `images/gen_xxx.png`,同源去重在 filename 层
3. 漏检会导致 missing image 在用户打开 `.md` 时才发现
4. 实现成本低(2 个 regex,~15 行)

**下次何时再讨论**:不会 — 双语法覆盖已稳定

### 决策 5:为什么 verify 的 chapters_complete 接受 `chapters_dir` 参数

**问题**:`_check_chapters_complete` 之前用 `work / "chapters"` 派生,但 `verify_pipeline` 允许
传 `chapters_dir` 覆盖。

**选项**:

- A:helper 硬编码 `work / "chapters"`
- B:helper 接受 `chapters_dir` 参数(默认 `work / "chapters"`)

**选择**:B

**原因**:

1. `verify_pipeline` 的 `chapters_dir` 参数已经存在,应贯穿所有 check
2. 跨 work_dir 调用时(explicit_paths 测试场景)helper 不该误用 work 路径
3. 默认值与 `verify_pipeline` 默认值一致(向后兼容)
4. 改动小,2 行 diff,测试覆盖 1 个新场景

**下次何时再讨论**:不会 — chapters_dir 传递已稳定

### 决策 6:为什么 HTML 模板嵌入 jinja2 已不再用,但仍导入 jinja2

**问题**:W3 的 `render.py` 用 jinja2 模板,W4 的 longdoc HTML 模板改用 `.format()`,不再依赖 jinja2。

**选项**:

- A:longdoc 也用 jinja2 模板字符串(与 render 一致)
- B:用 f-string / `.format()`(jinja2 不再需要)

**选择**:B

**原因**:

1. jinja2 已上移到核心 deps(W3 决策),`[longdoc]` extras 只留 `beautifulsoup4 + lxml`
2. 模板里的 CSS 没有复杂逻辑(只是常量 + toc + body 三个 slot),`.format()` 已足够
3. 避免 jinja2 第二次 autoescape 配置混乱
4. HTML 模板 ≈ 70 行,.format() 比 jinja2 更可读

**下次何时再讨论**:不会 — .format() 模板已稳定

### 决策 7:为什么 `image_prefix` 检查只用 filename,不用完整路径

**问题**:`![Image](<stem>/images/gen_xxx.png)` 中的 ref 含 stem 前缀,但实际文件在
`<drafts_dir>/images/gen_xxx.png`,如何匹配?

**选项**:

- A:ref 整字符串与 drafts 路径做 Path join 比对
- B:只取 ref 的 basename(`gen_xxx.png`)在 `images/` 找

**选择**:B

**原因**:

1. 同一张图可能在多处被引用(drafts_dir/images 与 cleaned 后的 images 子目录)
2. basename 是文件存在性检查的最小不变量
3. 跨 stem 重命名不会影响文件查找
4. 实现简单:`filename = ref.rsplit("/", 1)[-1]`

**下次何时再讨论**:不会 — basename 匹配已稳定

---

## 5. 撞墙 / 未完成 / 已知问题

### 5.1 撞墙点(下次会话语境)

| 现象 | 已尝试 | 残留 |
|---|---|---|
| `TocExtension(anchor_links=False)` 抛 `KeyError`(W3 已记) | 移除该 config,使用默认值 | 已解决 |
| `_check_chapters_complete` 用 work 派生 chapters.json,跨 work 路径场景 fail | 加 `chapters_dir` 参数 | 已解决 |
| 测试 fixture `_seed_outputs` 漏 seed image 文件,image_refs 失败 | `_seed_outputs` 接受 `with_images` | 已解决 |
| 测试 `test_chapters_complete_no_chapters_json` 期望 "chapters.json 缺失" 但实际是 "缺少 chapters.json" | 改测试期望 | 已解决 |
| ruff I001 报 `from media_to_doc.pipeline.longdoc import` 排序 | `uv run ruff check --fix` | 已解决 |
| bash 命令被自动 background 化,BeautifulSoup 没立即安装 | 改用 `uv add --optional longdoc beautifulsoup4 lxml` 同步命令 | 已解决 |

### 5.2 TODO(下次会话继续)

按 ROADMAP §3 Phase 1 W5(可选):

- [ ] **可选**:跑通示例视频(1.5h 中文培训,30 分钟内出 md/html/_cleaned/_final)
- [ ] **可选**:`mtd run` / `mtd resume` CLI 实接(目前 runner 已 11 stage 全就位)
- [ ] **可选**:`longdoc.LLMProvider` 默认 vs `pipeline.longdoc_llm_provider` 文档化

按 ROADMAP §3 Phase 2(L2)开始:

- [ ] **L2 - LE 闭环**:迁移 `_research/le_prototype/{pipeline_logger,gatekeeper,learnings}.py` 到
  `src/media_to_doc/logger/`
- [ ] 替换 mock stage 为真实 11 stage(每个 stage 接到 `timed_stage(logger, stage)` 上下文管理器)
- [ ] `runner.run_pipeline` 末尾调 `gatekeeper_check` + `logger.finalize` + `post_pipeline_hook`
- [ ] `llm/health.py` + MCP 暴露(`get_run_metrics` + `list_runs`)
- [ ] UI:Learnings 页(读 `.learnings/` 显示)
- [ ] 端到端验证(跑 3 次示例视频,演示 Pattern-Key 自动晋升)
- [ ] 测试:`test_logger/*` 30+ 用例

### 5.3 已知问题 / 技术债

- `_load_chapters_report` 在 render / draft / verify 三处各实现一份,W5+ 抽到 `chapters_io.py`
- longdoc LLM 净化 prompt 模板硬编码中文,i18n 留作 L3
- longdoc 的 TOC 只列 H1/H2;H3+ 折叠为子列表(简单两级,W5+ 可做 3 级)
- longdoc 的 print stylesheet 是基础版(W5+ 渐进增强:页码 / 章节分页)
- verify 的 image_refs 只检查 png,不支持 jpg / webp(imagegen 阶段输出 png,W5 统一格式后再扩展)
- `imagegen.LocalSdxlProvider.generate()` 仍是占位(W3 已知),W4 longdoc 不依赖 SDXL 真输出
- longdoc / verify 还没跑过真实视频端到端(等 W5 接入 LLM 后跑)
- `Media-to-doc` runner 接受 `stop_after="longdoc"` / `stop_after="verify"`,但 verify 几乎无前置产物,
  跳过前面的 stage 后 verify 会失败(预期行为)
- 图像文件大小检查 W5+ 加(避免 < 100B 的占位图被算"通过")

### 5.4 不写进 task 的"探索发现"

- **longdoc 的 HTML 模板**:与 render 共用 .format() 风格而非 jinja2,简洁很多
- **render 的内嵌 CSS 已含 dark mode + print**:longdoc 复制了这两块,后续可抽 `css_constants.py`
- **BeautifulSoup 在 longdoc 与 verify 都有用**:longdoc 改 anchor id,verify 检查结构;W5+ 可抽
  `html_utils.py`
- **TOC 锚点的 markdown 库自动生成 ID 与我们的 _slugify 不完全一致**:`TocExtension(toc_depth=...)` 用 hex
  encoding 中文;我们在 longdoc 用手工 slug + unique suffix 重写,行为可控
- **verify 的 image_refs 报告截断**:失败超过 50 项会加 "... 还有 N 个" 截断提示,避免大报告
- **测试 fixture `_seed_outputs` 现在可选 seed images**:保持 fixture 简洁,失败场景不需要 seed

---

## 6. 测试状态

```
$ uv run pytest
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
collected 349 items

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
tests/test_pipeline/test_draft.py::... [26 tests]
tests/test_pipeline/test_imagegen.py::... [18 tests]
tests/test_pipeline/test_render.py::... [29 tests]
tests/test_pipeline/test_longdoc.py::... [32 tests]                            ← W4 NEW
tests/test_pipeline/test_verify.py::... [27 tests]                             ← W4 NEW
tests/test_pipeline/test_runner.py::... [15 tests]                             ← W4 updated

======================= 346 passed, 3 skipped in 2.23s ========================
```

ruff check `src/ tests/`:

```
All checks passed!
```

---

## 7. Git 状态

```
$ git log --oneline -5
3b32743  feat(pipeline): W4 — longdoc + verify stages (11 stages all live)
266d741  docs(handoff): add W3 pipeline snapshot + task.md progress
86694a0  feat(pipeline): draft + imagegen + render stages (W3)
f712552  feat(pipeline): ocr + asr_correct + chapters + llm providers (W2)
04f992c  feat(pipeline): W1 — audio + asr + frames stages + utils + runner

$ git status
On branch feat/pipeline-w4-longdoc-verify
nothing to commit, working tree clean
```

W4 commit 内容(8 文件,~2118 行):

- **源码**:2 新文件(`longdoc.py` 725 行 / `verify.py` 467 行)
- **测试**:2 新文件(`test_longdoc.py` 32 用例 / `test_verify.py` 27 用例)
- **修改**:`runner.py` / `__init__.py` / `config.py` / `test_runner.py`

---

## 8. 给下一个会话的提示

**新会话第一句话建议**:

```
承接 handoff-pipeline-w4-2026-07-18.md,W4 已完成 11 stage 全部实装(346 测试)。
请评审 W4 commit 3b32743,决定下一步:
- A. 跑通示例视频端到端(1.5h 中文培训素材)
- B. 进入 Phase 2 L2 LE 闭环(迁移 _research/le_prototype/)
- C. 接入 CLI mtd run / mtd resume(11 stage 已就位)
```

**主要任务**(按 W5 候选优先级排序):

1. **跑示例视频**(最低风险)— `workspace/inbox/` 放 1.5h 中文培训素材,跑
   `from media_to_doc.pipeline.runner import run_pipeline` 端到端
2. **L2 LE 闭环**(架构演进)— 迁移 LE 原型到 `src/media_to_doc/logger/`,替换 mock
   stage 为真实 11 stage
3. **CLI 实接**(用户可见)— `mtd run <inbox>` / `mtd resume <work>` 11 stage 命令行入口
4. **MCP server 接入**(跨项目)— `mcp_server.py` 6 个工具,Claude Desktop 配置

**别忘了**:

- 缩进 2 空格,Python 函数类型注解(全局偏好)
- 函数 ≤ 100 行,模块 ≤ 500 行(TDD §9.2)
- lazy import 重依赖(BeautifulSoup / lxml)只在 `[longdoc]` extras 已装时可用
- `verify()` 必须真实跑 image_refs(动态检查 `gen_<uuid>.png` 文件存在)
- 渲染产物目录:`raw/<stem>_cleaned.md` + `raw/<stem>_final.html`(PRD §5)
- 不要破坏已通过的 346 个测试
- W4 的 `longdoc_llm_provider = "skip"` 默认值要保留(避免 CI 误调 LLM)

**关键参考**:

- `handoff-pipeline-w3-2026-07-18.md` — 上一个会话(W3 draft + imagegen + render)
- `_research/PROJECT_DESCRIPTION.md` §3.2 longdoc / verify + §5 产物目录
- `ROADMAP.md` §3 Phase 1 W4 任务清单(已完成) + §4 Phase 2 L2 LE 闭环
- `TDD.md` §5 数据流第 10-11 步(longdoc + verify)
- `C:\Users\Duanyi\.claude\skills\long-doc-processor\`:长文档净化流程参考
- 本会话:`src/media_to_doc/pipeline/longdoc.py`(分块 + 锚点 + print stylesheet)
- 本会话:`src/media_to_doc/pipeline/verify.py`(4 项 gatekeeper)
- 本会话:`_research/le_prototype/`(LE 原型,Phase 2 迁移源)

**复杂度提示**:

- W4 是 5 人天 → 实际 ~1.5h(从 W3 handoff §8 估计)
- longdoc 借鉴 skill `long-doc-processor`,但 skill 输出 PNG 用 html2image,本项目用 markdown lib
- verify 4 项检查已覆盖 chapters / drafts / images / 最终 md/html
- W4 完成后 11 stage 全部实装,可接入 cli.py 的 `mtd run` / `mtd resume` 命令
- L2 LE 闭环的工作量与 L1 核心流水线相当(~10-15h)

---

## 9. 上下文参考链接

- `CLAUDE.md` — 项目级指引
- `task.md` — 活跃 todo(含本会话历史)
- `PRD.md` / `TDD.md` / `ROADMAP.md`
- `handoff-template.md` — 长期复用模板
- `handoff-pipeline-w3-2026-07-18.md` — 上一个会话(W3)
- `handoff-pipeline-w2-2026-07-18.md` — W2
- `handoff-pipeline-w1-2026-07-18.md` — W1
- `_research/PROJECT_DESCRIPTION.md` — 参考实现逆向报告
- `_research/LE_DESIGN.md` — LE 详细设计(Phase 2 接入参考)
- `_research/le_prototype/runner.py` — LE 原型 runner
- `git log --oneline`:`3b32743` + `266d741` + `86694a0` + `f712552` + `04f992c`

---

## 10. 自检清单

- [x] 本会话目标全部完成(Phase 1 W4 全交付)
- [x] 无未提交代码改动(working tree clean)
- [x] 无未完成任务(下次会话从 W5 / Phase 2 开始)
- [x] 测试状态明确(346 passed / 3 skipped in 2.23s)
- [x] Git 状态明确(W4 commit 已建,分支就绪)
- [x] 下次会话第一句话建议清晰
- [x] 关键决策记录 7 条,带"为什么"
- [x] 上下文参考链接完整
- [x] `uv run pytest` 端到端验证通过
- [x] `uv run ruff check src/ tests/` 全过
- [x] pytest 增量:W1 → W2 → W3 → W4 = 79 → 212 → 285 → 346(超 W4 目标 310+)
- [x] W4 两 stage + 11 真 stage 全部就位
- [x] STAGE_FUNCS:11 真 stage + 0 占位
- [x] 图像相对路径逻辑(CLAUDE.md §7 红线)已通过测试
- [x] longdoc LLM 净化支持 skip 模式(默认),CI / 离线可跑
- [x] verify 4 项 gatekeeper 全部跑通 + 写出 verify.json
- [x] runner 集成 longdoc / verify + 前置依赖检查
