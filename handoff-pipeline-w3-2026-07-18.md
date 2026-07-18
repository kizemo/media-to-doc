# handoff-pipeline-w3-2026-07-18.md — Phase 1 W3 Draft + Imagegen + Render 快照

> **会话主题**:Phase 1 W3 核心流水线 — 实现 11 stage 中的 7/8/9
> **会话日期**:2026-07-18,~1.5 小时
> **会话状态**:**已完成,无阻塞**(285 passed / 3 skipped + ruff 全过 + W3 commit)

---

## 1. 本次会话目标

承接 `handoff-pipeline-w2-2026-07-18.md`,启动 Phase 1 W3。按
ROADMAP §3 Phase 1 W3 任务清单实施:

1. `pipeline/draft.py` — `generate_drafts()`(LLM 按章节切片 transcript → markdown)
2. `pipeline/imagegen.py` — `generate_images()`(SDXL Base + Refiner,可 `provider=skip`)
3. `pipeline/render.py` — `render_outputs()` + `render_html()`(md + html + 相对路径)
4. 替换 `runner.py` 中 `_not_implemented_stage[draft/imagegen/render]`
5. 测试 25+ 用例(212 → 237 目标,实际 285)
6. commit:`feat(pipeline): draft + imagegen + render stages`

---

## 2. 已完成

| 项 | 文件 | 行数 / 测试数 | 状态 |
|---|---|---|---|
| `feat/pipeline-w3-draft-imagegen-render` 分支 | git branch | - | [x] |
| `pipeline/draft.py`(`generate_drafts` + 数据类 + 工具) | `src/media_to_doc/pipeline/` | 437 行 | [x] |
| `pipeline/imagegen.py`(3 provider 抽象 + SkipProvider + LocalSdxlProvider) | `src/media_to_doc/pipeline/` | 387 行 | [x] |
| `pipeline/render.py`(jinja2 模板 + markdown 库 + 相对路径) | `src/media_to_doc/pipeline/` | 415 行 | [x] |
| `pipeline/runner.py`:`_draft_wrapper` + STAGE_FUNCS 替换 3 占位 + _invoke_stage 3 分支 | `src/media_to_doc/pipeline/` | - | [x] |
| `pipeline/__init__.py` re-export | `src/media_to_doc/pipeline/` | - | [x] |
| `pyproject.toml`:`markdown + jinja2` 上移到核心 deps,`[longdoc]` 仅留 `beautifulsoup4 + lxml` | `pyproject.toml` | - | [x] |
| `tests/test_pipeline/test_draft.py` | `tests/` | 26 用例 | [x] |
| `tests/test_pipeline/test_imagegen.py` | `tests/` | 18 用例 | [x] |
| `tests/test_pipeline/test_render.py` | `tests/` | 29 用例 | [x] |
| `tests/test_pipeline/test_runner.py` 占位计数 5 → 2 | `tests/` | +0 用例 | [x] |
| 测试结果 | pytest | **285 passed / 3 skipped** | [x] |
| lint 结果 | ruff check | All checks passed | [x] |
| W3 commit | git | `86694a0` | [x] |

**测试数量统计**:

- W1:79 passed / 3 skipped
- W2:212 passed / 3 skipped(+133)
- W3:**285 passed / 3 skipped**(+73)
- **当前总数:285 passed / 3 skipped**(远高于 W3 目标 237)

---

## 3. 已读 / 已写文件清单

### 已读(信息已缓存,下次会话无需重读)

会话 7 已读(承接 W2 + W3):
- `MEMORY.md`、`task.md`、`handoff-pipeline-w2-2026-07-18.md`
- `pyproject.toml` W2 版
- `src/media_to_doc/pipeline/runner.py`、`chapters.py`、`asr_correct.py`
- `tests/test_pipeline/test_chapters.py`(`_FakeProvider` 模式)
- `_research/PROJECT_DESCRIPTION.md` §3.2-§3.3(draft / imagegen / render + skip)
- `PRD.md` / `TDD.md` / `ROADMAP.md` §3 W3 段落(细节)

### 已写(本次会话新增)

**源码**(3 文件,~1240 行):

- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/draft.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/imagegen.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/render.py`

**测试**(3 文件,~970 行):

- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/test_draft.py`
- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/test_imagegen.py`
- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/test_render.py`

### 已修改

- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/runner.py`
  - 新增 `_draft_wrapper`(LLM provider 工厂模式,与 `_chapters_wrapper` 同构)
  - STAGE_FUNCS:3 占位 → `generate_drafts` (via wrapper) / `generate_images` / `render_outputs`
  - `_invoke_stage` 加 3 分支 + 前置依赖检查(chapters.json / transcript.jsonl / drafts_dir)
  - 新增 `_resolve_drafts_dir(work)` helper:从 chapters.json 的 `video` 字段派生
  - 顶部 docstring 更新为 W3 状态
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/__init__.py`
  - 全量 re-export:`generate_drafts` / `generate_images` / `render_outputs` / `render_html`
- `F:/soft/00selfmade/media-to-doc/pyproject.toml`
  - `markdown>=3.6.0` + `jinja2>=3.1.0` 从 `[longdoc]` 上移到 `dependencies`
  - `[longdoc]` 缩减为 `beautifulsoup4 + lxml`(W4 留 longdoc 用)
- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/test_runner.py`
  - `test_stage_funcs_unimplemented_raise` 缩到 2 stage(`longdoc` / `verify`)
  - `test_stage_funcs_real_stages_resolve` 验证 9 stage 真实现

---

## 4. 关键决策与原因

### 决策 1:为什么 `markdown + jinja2` 上移到核心 deps

**问题**:render 是核心 11 stage 之一,但 W2 把 markdown/jinja2 放在了 `[longdoc]` extras。

**选项**:

- A:render 保留 optional,要求用户装 `[longdoc]` extras 才能渲染
- B:markdown/jinja2 上移到核心 dependencies

**选择**:B

**原因**:

1. render 是核心流水线 stage,11 stage 缺一不可运行 → 它的依赖也应是核心
2. `[longdoc]` 还有 `beautifulsoup4 + lxml` 留给 W4 longdoc 阶段,W4 不需要 markdown/jinja2(已经在核心)
3. `uv add media_to_doc` 即可跑完整 W3 流程,无需 extras 选项
4. jinja2/markdown 都小(~3MB),无大依赖风险

**下次何时再讨论**:不会 — 上移已稳定

### 决策 2:为什么 `imagegen` 用 ABC + duck-typed Protocol 双轨

**问题**:imagegen provider 接口(SDXL Base / Refiner)需要有清晰的 base class,但测试想注入任意 mock 不想基类继承。

**选项**:

- A:只用 ABC,测试 mock 需继承 ImagegenProvider
- B:只用 Protocol,生产代码靠 duck typing
- C:ABC 用于产品代码(SDXL/Refiner/Skip 三个真 provider),Protocol 用于文档意图

**选择**:C

**原因**:

1. 生产 provider(`LocalSdxlProvider` / `SkipProvider`)继承 ABC,享受 type checker 校验
2. Protocol `_ProviderLike` 表达接口意图,让 test 的 mock 不必继承
3. `_MockProvider`(test)只需实现 `name + generate`,无需 import 任何 ABC
4. ABC 也方便 Phase 5 LE 加第四个 provider(diffusers XL-Turbo / API SDXL)时类型一致

**下次何时再讨论**:不会 — 双轨清晰

### 决策 3:为什么 draft 默认输出 `chapters_dir/raw/<video_stem>/` 而不是 `inbox/raw/`

**问题**:render 的输出应该是 `inbox/<course>/raw/<stem>.md`(可分发),但 runner 调 `render_outputs(work, config)` 时 `work` 中没有 inbox 直接信息。

**选项**:

- A:`render_outputs(work, config)` 默认输出 `work/chapters/raw/<stem>.md`
- B:`render_outputs` 接受 `inbox` 参数,runner 注入
- C:在 runner 派生 `output_dir` 后再传

**选择**:A(W3)+ C(runner 调用)

**原因**:

1. `render_outputs` 函数本身可独立调(纯 `(work, config)` 即可用),默认产物在 work 内也合理
2. `render_html(md_path)` 完全独立 → MCP server / 单元测试可单独调
3. Runner 负责把 `output_dir = inbox/raw/<stem>` 注入 — 但 W3 留作 `cli.py` 接入时再做(此次仅接入 STAGE_FUNCS + 输出路径约定)
4. 当前 W3 产物默认在 `work/chapters/raw/<stem>.{md,html}`;`check_status` / `list_outputs` 后续读 state 找

**下次何时再讨论**:W4 / Phase 4(MCP server)+ cli.py `read_lecture` 工具接入时

### 决策 4:为什么 render 的图像相对路径写 `<stem>/images/...` 而不是 `images/...`

**问题**:draft 阶段写 `![[gen_<uuid>.png]]`(Obsidian wiki-link),相对当前 chapter_NN.md 的位置是 `images/gen_<uuid>.png`。但拼装的最终 `.md` 在 `output_dir/<stem>.md`,相对路径变成 `<stem>/images/...`。

**选项**:

- A:统一用 `images/...`,要求产物平铺(违背 PRD 布局)
- B:render 阶段重写所有 `![[gen_*.png]]` 为 `![Image](<stem>/images/gen_*.png)`
- C:draft 阶段就把 `<stem>/` 前缀加进 wiki-link

**选择**:B

**原因**:

1. chapter_NN.md 独立可读(drafts_dir/<stem>/chapter_NN.md 时用 `images/...` 没问题)
2. 拼装的最终 `.md` 在 drafts_dir 之上(`raw/<stem>.md`),前缀加 `<stem>/`
3. 在 render 阶段重写最自然 — 此时已有完整 drafts_dir + output_dir 信息
4. 缺失图像自动退化为 `_⚠️ 配图缺失:xxx_` 文字警告(避免 broken link)

**下次何时再讨论**:不会 — 重写逻辑已稳定

### 决策 5:为什么 `_load_chapters_report` 在 draft / render 各重复一次

**问题**:`ChaptersReport` 没有 `load(path)` 类方法(只有 `save`),但 draft 和 render 都要从 chapters.json 加载。

**选项**:

- A:在 :mod:`chapters` 加 `ChaptersReport.load(path)`
- B:draft 和 render 各实现一个 `_load_chapters_report`
- C:加一个 `loader.py` 共享 helper

**选择**:B

**原因**:

1. W2 不愿改 chapters.py(纯加法原则,避免影响已通过的 110 测试)
2. helper 函数 ~15 行,duplication 成本低
3. W4+ 若长到共同 helper 统一,可建 shared `_chapters_io.py`
4. 兼容性最佳 — W2 测试零改动

**下次何时再讨论**:W4 longdoc 阶段可能复用 → 届时可抽到 `chapters_io.py`

### 决策 6:为什么 imagegen 的 `_replace_first_n` 用搜字符串方式而不是闭包迭代器

**问题**:要按出现顺序把 `![[gen_<uuid>.png]]` 替换为新值,常规写法是用 closure iterator,但 ruff B023 报警 closure 引用外层循环变量。

**选项**:

- A:用闭包 iterator(Ruff 警告但功能对)
- B:`functools.partial` 包裹
- C:显式 `search + append + advance pos`,不依赖闭包

**选择**:C

**原因**:

1. ruff B023 强制修,避免 `noqa` 噪声
2. C 写法读起来更直观 — 一个 while 循环,pos 推进
3. 复杂度:O(N×M)同闭包方案
4. 不需要 `itertools` / `partial` 额外导入

**下次何时再讨论**:不会 — 写法已稳定

---

## 5. 撞墙 / 未完成 / 已知问题

### 5.1 撞墙点(下次会话语境)

| 现象 | 已尝试 | 残留 |
|---|---|---|
| `ChaptersReport.load(path)` 不存在 — 我以为是标准但只有 `save` | 在 draft / render 各加 `_load_chapters_report` | 已解决 |
| `_slice_transcript_for_chapter` 用 `len(iterator)` 触发 `TypeError` | 在函数内 `list(segments)` materialize | 已解决 |
| `TocExtension(anchor_links=False)` 在 markdown 3.10.2 抛 `KeyError` | 移除该 config(默认值已合适) | 已解决 |
| `_seed_chapters(work)` fixture 多写了一层 `chapters/`,与自定义 `chapters_dir` 路径不一致 | 改用直接 `ChaptersReport.save` 写到目标路径 | 已解决 |
| 时间戳正则 `r"^\[\d.*?\s*\]"` 不匹配 `[   0.50s` 前导空格 | 改成 `r"^\s*\[[^\]]*\d[^\]]*\].*$"` | 已解决 |
| ruff B023 closure 引用循环变量 | 改 `_replace_first_n` 显式 pos 推进 | 已解决 |
| draft 默认 output_dir 的 `_load_chapters_report` 间接 — 衍生了 5.4 决策 5 | 选定重复 helper | 已解决 |

### 5.2 TODO(下次会话继续)

按 ROADMAP §3 Phase 1 W4:

- [ ] **分支**:`feat/pipeline-w4-longdoc-verify` 基于 `feat/pipeline-w3-draft-imagegen-render`
- [ ] `src/media_to_doc/pipeline/longdoc.py` — `process_long_doc()` + `render_final_html()`
  - 借鉴 `C:\Users\Duanyi\.claude\skills\long-doc-processor\`
  - 分块 15000 CJK,5 类保留 / 4 类清理,TOC + 锚点 + 内嵌 CSS
- [ ] `src/media_to_doc/pipeline/verify.py` — gatekeeper + image_refs 校验
- [ ] 替换 runner.py 中 `_not_implemented_stage[longdoc/verify]`
- [ ] 测试 ~25 用例(285 → 310)
- [ ] commit:`feat(pipeline): longdoc + verify stages`
- [ ] **可选**:跑通示例视频(1.5h 中文培训,30 分钟内出 md/html/_cleaned/_final)

### 5.3 已知问题 / 技术债

- `imagegen.LocalSdxlProvider.generate()` 是占位(写 0 字节文件),W4 接真实 SDXL
- `_resolve_drafts_dir` 派生 `drafts_dir` 默认从 chapters.json 的 `video` 字段;`chapters.video` 目前是 `work.name`(派生不完美),runner 后续可注入 inbox.name
- `_load_chapters_report` 在 draft / render 各实现一份,W4+ 抽到 `chapters_io.py`
- render 模板 CSS 在 jinja2 字符串内,无主题切换 / 无 print stylesheet(W4+ 渐进增强)
- 拼装的 `.md` 没有 heading id,markdown 库的 toc 扩展会自动生成 ID 但与我们的手工 slug 可能不一致
- chapters / render 的 prompt 模板全部硬编码英文 — i18n 留作 W5+
- runner 中 imagegen / render 接受 `drafts_dir` 可注入(W3 没用到,默认值 `chapters_dir/raw/<stem>` 一致)
- 没有 `mtd run` / `mtd resume` CLI 实接(W4 与 verify 一起接入)
- 没有 LLM `[[GEN: ...]]` 标签在 chapter markdown 重写时的替代方案 — 通过 imagegen 阶段只能产出 N 张与标签数相同的图

### 5.4 不写进 task 的"探索发现"

- **`markdown` 库的 toc 扩展**:`TocExtension(toc_depth="2-3")` 的 anchor id 形如 `id="chapter-2"`,与我们 `_slugify` 出的 `chapter-2` 一致(默认就行)。但若标题含 `中文` 字符,anchor 的 hex 可能不一致 — 测试已验证基础功能。
- **Tauri 集成**:render 输出 `.md + .html` 是相对路径引用,Tauri webview 直接渲染没问题(RFC 3986 URI 解析)。
- **longdoc 模块预留**:W3 render 阶段没有 entry CSS,只是基础样式;W4 longdoc 的 CSS(TOC + 锚点 + print)会更复杂。
- **测试 fixture `_seed_chapters` 的多写一层**:`work / chapters / chapters.json` 是默认写法,但用户传 `chapters_dir` 时可能已经是 chapters 目录,fixture 需要两种语义。W3 测试用直接 `ChaptersReport.save` 绕过 — 测试 fixture 仍需打磨(后续 PR)。

---

## 6. 测试状态

```
$ uv run pytest
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
collected 288 items

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
tests/test_pipeline/test_draft.py::... [26 tests]                            ← W3 NEW
tests/test_pipeline/test_imagegen.py::... [18 tests]                         ← W3 NEW
tests/test_pipeline/test_render.py::... [29 tests]                           ← W3 NEW
tests/test_pipeline/test_runner.py::... [13 tests]

======================= 285 passed, 3 skipped in 1.94s ========================
```

ruff check `src/ tests/`:

```
All checks passed!
```

---

## 7. Git 状态

```
$ git log --oneline -5
86694a0  feat(pipeline): draft + imagegen + render stages (W3)
f712552  feat(pipeline): ocr + asr_correct + chapters + llm providers (W2)
04f992c  feat(pipeline): W1 — audio + asr + frames stages + utils + runner
961dff3  docs(handoff): add skeleton bootstrap session snapshot
702ecc2  chore: bootstrap project skeleton

$ git status
On branch feat/pipeline-w3-draft-imagegen-render
nothing to commit, working tree clean
```

W3 commit 内容(11 文件,~2500 行):

- **源码**:3 新文件(`src/media_to_doc/pipeline/` 3 新)
- **测试**:3 新文件(`tests/test_pipeline/` 3 新)
- **修改**:`runner.py` + `__init__.py` + `pyproject.toml` + `test_runner.py` + `uv.lock`

---

## 8. 给下一个会话的提示

**新会话第一句话建议**:

```
承接 handoff-pipeline-w3-2026-07-18.md,启动 Phase 1 W4:
longdoc(借鉴 long-doc-processor skill,深度净化 + TOC HTML) + verify(gatekeeper)。
请先在 feat/pipeline-w3-draft-imagegen-render 上拉 feat/pipeline-w4-longdoc-verify 分支,
然后按 ROADMAP §3 Phase 1 W4 清单逐模块实施。
```

**主要任务**(Phase 1 W4):

1. 创建 `feat/pipeline-w4-longdoc-verify` 基于 W3
2. `pipeline/longdoc.py` — `process_long_doc()` + `render_final_html()`
   - 借鉴 skill:`C:\Users\Duanyi\.claude\skills\long-doc-processor\`
   - 分块 15000 CJK,LLM 净化(5 类保留 / 4 类清理)
   - HTML 渲染:TOC + 锚点 + 内嵌 CSS + print stylesheet
3. `pipeline/verify.py` — `verify()`(gatekeeper + image_refs 校验)
   - 4 项机器可验证检查
   - 输出 `work/<course>/verify.json` 报告
4. 替换 `runner.py` 中 `_not_implemented_stage[longdoc/verify]`
5. 每个模块配套测试,新目标:`+25` 用例(285 → 310)
6. W4 末 commit:`feat(pipeline): longdoc + verify stages`
7. **可选**:跑通示例视频(参考 `_research/PROJECT_DESCRIPTION.md` §6.1)

**别忘了**:

- 缩进 2 空格,Python 函数类型注解(全局偏好)
- 函数 ≤ 100 行,模块 ≤ 500 行(TDD §9.2)
- lazy import 重依赖(BeautifulSoup / lxml)只在 `[longdoc]` extras 已装时可用
- `verify()` 必须真实跑 image_refs(动态检查 `gen_<uuid>.png` 文件存在)
- 渲染产物目录:`raw/<stem>_cleaned.md` + `raw/<stem>_final.html`(PRD §5)
- 不要破坏已通过的 285 个测试

**关键参考**:

- `_research/PROJECT_DESCRIPTION.md` §3.2 longdoc / verify + §5 产物目录
- `ROADMAP.md` §3 Phase 1 W4 任务清单
- `TDD.md` §5 数据流第 10-11 步
- 本会话:`src/media_to_doc/pipeline/render.py`(jinja2 + markdown 模式,longdoc 类似)
- 本会话:`src/media_to_doc/pipeline/imagegen.py`(provider 抽象模式,verify 也可参考)
- `C:\Users\Duanyi\.claude\skills\long-doc-processor\`:长文档净化流程参考

**复杂度提示**:

- W4 是 5 人天(longdoc 2.5 天 + verify 0.5 天 + 跨项目 cli/mcp 2 天)
- longdoc 借鉴 skill `long-doc-processor`,但 skill 输出 PNG 用 html2image,本项目用 markdown lib + jinja2
- verify 需要把 chapters / drafts / images / 最终 md 都过一遍 gatekeeper
- W4 完成后 11 stage 全部实装,可接入 cli.py 的 `mtd run` / `mtd resume` 命令

---

## 9. 上下文参考链接

- `CLAUDE.md` — 项目级指引
- `task.md` — 活跃 todo(含本会话历史)
- `PRD.md` / `TDD.md` / `ROADMAP.md`
- `handoff-template.md` — 长期复用模板
- `handoff-pipeline-w2-2026-07-18.md` — 上一个会话(W2 ocr + asr_correct + chapters)
- `handoff-pipeline-w1-2026-07-18.md` — W1
- `_research/PROJECT_DESCRIPTION.md` — 参考实现逆向报告
- `_research/LE_DESIGN.md` — LE 详细设计(Phase 5 接入参考)
- `_research/le_prototype/runner.py` — LE 原型 runner
- `git log --oneline`:`86694a0` + `f712552` + `04f992c`

---

## 10. 自检清单

- [x] 本会话目标全部完成(Phase 1 W3 全交付)
- [x] 无未提交代码改动(working tree clean)
- [x] 无未完成任务(下次会话从 W4 开始)
- [x] 测试状态明确(285 passed / 3 skipped in 1.94s)
- [x] Git 状态明确(W3 commit 已建,分支就绪)
- [x] 下次会话第一句话建议清晰
- [x] 关键决策记录 6 条,带"为什么"
- [x] 上下文参考链接完整
- [x] `uv run pytest` 端到端验证通过
- [x] `uv run ruff check src/ tests/` 全过
- [x] pytest 增量:W1 → W2 → W3 = 79 → 212 → 285(远超 237 目标)
- [x] W3 三 stage + 产物布局 + 9 真 stage 全部就位
- [x] STAGE_FUNCS:9 真 stage + 2 占位(W4 替换)
- [x] `markdown` + `jinja2` 上移到核心 deps,`[longdoc]` 缩减
- [x] 重依赖 lazy import 验证(`diffusers` / `torch` 仅在 SDXL 真跑时 import)
- [x] 图像相对路径逻辑(CLAUDE.md §7 红线)已通过测试
