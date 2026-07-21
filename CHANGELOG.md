# Changelog

All notable changes to `media-to-doc` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [1.0.0] - 2026-07-20

### 🎉 First stable release

11 阶段流水线全跑通,3 种调用方式(CLI / Python API / MCP server),Loop Engineering 五层闭环端到端接入。
W10-A 真端到端验证:107 分钟中文培训视频 3 小时 57 分钟跑完,529 测试 0 失败。
**Published to PyPI**: https://pypi.org/project/media-to-doc/ — `uv pip install media_to_doc`
W11-C 真分布式文档质量验收:qwen3:14b 净化 107min 视频 4KB → 讲师可分发讲义(9/9 ⭐ 评分)。

### Added

- **11 阶段流水线** (W1-W4):`audio → asr → frames → ocr → asr_correct → chapters → draft → imagegen → render → longdoc → verify`
- **可插拔 LLM**:Ollama(默认) / Anthropic / OpenAI-compatible(MiniMax、DeepSeek、智谱、Moonshot、混元、OpenRouter 等 7 个 preset)
- **可跳过重模块**:`imagegen_provider=skip` 让 Claude 自己做配图,`longdoc_llm_provider=skip` 用规则清理代替 LLM 净化
- **3 种调用方式**(W6 / W7 / W9):
  - **CLI** `mtd run | resume | status | list | doctor | config | mcp`
  - **Python API** PEP 562 `__getattr__` 顶层 re-export,52 个公开符号 lazy import,启动 < 100ms
  - **MCP server** 8 工具(W7=6 + W8=2),stdio JSON-RPC,Claude Desktop / Codex / Cline 原生集成
- **Loop Engineering 五层闭环**(W8,见 `.learnings/` LEARNINGS.md / ERRORS.md):
  - L1 执行层:`timed_stage(logger, stage)` 包裹每 stage
  - L2 审核层:`gatekeeper_check(work)` 4 项机器可验证
  - L3 沉淀层:`pipeline_run.json` 写盘,含 `llm_health` / `gatekeeper_passed` / `quality` / `errors`
  - L4 进化层:`post_pipeline_hook` 扫 Pattern-Key 自动晋升到 `.learnings/ERRORS.md`
  - L5 健康度:`assess_llm_health` 失败率 > 10% → `switch_provider` 建议,> 20% → `reduce_chunk` 建议
- **跨 run 健康度查询** (W8):`get_run_metrics(work)` / `list_runs(workspace)`,Python API + MCP 工具等价
- **状态持久化与断点续跑** (W4 / W6):`state.json` 11 stage 调度真相 + `pipeline_run.json` LE 沉淀双轨;`mtd resume <work>` 自动从 state 派生 inbox
- **可分发的产物**:图片一律相对路径(`<stem>/images/gen_*.png`),产物目录整盘复制到任何电脑/上传网盘/丢知识库路径不失效
- **LEARNINGS 系统**:14 条 LP-YYYYMMDD-NNN best_practice 条目(W1-W8 沉淀)

### Changed

- **产物布局**(W3 / W4):render 输出从 `<drafts_dir>/<stem>.md` 移到 `<drafts_dir>/<stem>/<stem>.md`,longdoc 写 `<drafts_dir>/<stem>_cleaned.md` + `<drafts_dir>/<stem>_final.html`(W5 兼容旧布局)
- **Ollama 默认 num_ctx** = 65536(W5 long transcript 支持 qwen3:14b 32K RoPE 扩展)
- **chapters prompt transcript 截断** = 30000 chars(W5 适配 32K context 留 system 余量)

### Fixed

- **OCR 输出路径不一致**(W5):runner ocr 阶段不传 output_dir → OCR 写 `inbox/img/ocr/`,asr_correct 读 `work/ocr/` 不匹配 → JSONDecodeError;统一写到 `work/ocr/`
- **Ollama 上下文超长**(W5):`num_ctx=None` → Ollama 默认 4096 → 50K tokens 超 32K max → 4 stage 全部失败;`num_ctx=65536` 修
- **transcript 截断缺失**(W5):`_load_transcript` 不限长度 → chapters prompt 50K tokens → 默认 → 显式截 30000 chars
- **longdoc/verify 路径布局兼容**(W5):`db92ac9` `_check_outputs_exist` 兼容新旧两布局
- **W8 llm_health 聚合自动**(W10-C `bddc387`):`StageContext.metrics` 跨 stage 累积,`_aggregate_llm_health` helper 替换原 `{}` TODO
- **Gatekeeper vs Verify 不一致**(W11-A `d2b39d3`):gatekeeper resolver 写死 W4 原型路径,verify 迁 W5 新布局后两者对同一份数据给相反结论;新布局优先 + 旧布局回退,image_refs 加 `<stem>/images/` 候选

### Tested

- **529 pytest 用例 / 0 跳过**:W10-C 519 → W11-A +10 → 529。涵盖 11 stage 单元测试 + LE 闭环 + CLI + MCP server + 一致性回归
- **W5 真实端到端冒烟**:1.3GB / 112min 中文培训视频 CPU 模式 ASR + frames + OCR + LLM 全跑通
- **W10-A 真端到端验收**:395MB / 107min 中文培训视频 CPU 模式 3h57min,llm_health 真聚合 chapters_ollama(1 calls) + draft_ollama(6 calls),0 failures

---

## [0.1.0-dev] - 2026-07-18

开发起点。骨架 + 5 个占位模块(14 测试)。

### Added

- 项目骨架:uv init + pyproject.toml + src/ + tests/ + workspace/ + .learnings/ + .github/workflows/
- 5 个占位模块:`__init__` / `cli` / `paths` / `config` / `state` + `logger/__init__`
- 14 测试 (`tests/test_smoke.py`) + ruff + mypy + pytest CI

[1.0.0]: https://github.com/kizemo/media-to-doc/releases/tag/v1.0.0
[0.1.0-dev]: https://github.com/kizemo/media-to-doc/releases/tag/v0.1.0-dev

---

## [1.0.1] - 2026-07-20

### Fixed

- **mermaid 流程图在最终 HTML 中渲染**(W12-C):W11-C 验收发现的第 1 个降级。
  `cleaned.md` 中的 ```` ```mermaid ```` 围栏此前被渲染成 `<pre><code>` 纯文本,
  浏览器看不到流程图。修复:
  - `_HTML_TEMPLATE` 底部加 `mermaid@10` CDN script + `mermaid.initialize`
    (浏览器端自动渲染 `<pre class="mermaid">` 块,响应 prefers-color-scheme)
  - `_post_process_html` 检测 `<pre><code class="language-mermaid">`,
    把 `<code>` 内容移到 `<pre>` 自身,class 改为 `mermaid`
  - CSS 加 `pre.mermaid` 留白 + dark mode 适配

- **GFM task list checkbox 渲染**(W12-C):W11-C 验收发现的第 2 个降级。
  `- [ ] xxx` / `- [x] xxx` 此前保持纯文本,无法可视化清单状态。
  修复:`_post_process_html` 遍历 `<li>`,把开头的 `[ ]` / `[x]` 替换为
  `<input type="checkbox" disabled>` (checked 视原状态)。
  兼容有序列表 `1. [ ] xxx`(W11-C 风险清单实测形式)。

### Added

- 内联 CSS `input[type="checkbox"][disabled]`(只读视觉提示)+ `pre.mermaid` 留白
- +9 个 longdoc 单元测试覆盖 mermaid / tasklist 路径(42 → 51 个 longdoc 用例)

### Tested

- **539 pytest 用例 / 0 跳过** (1.0.0 529 → 1.0.1 539,+10)
- **ruff**:All checks passed
- **真渲染验证**:复用 W11-C 107min 视频产物 `output_cleaned.md`(1 mermaid 流程图 +
  5 条 risk control checkbox)→ `output_final.html`(11KB) 验证全部降级修复

[1.0.1]: https://github.com/kizemo/media-to-doc/releases/tag/v1.0.1

---

## [1.1.0] - 2026-07-21

### 🎉 Multi-video layout + merge

按用户 2026-07-21 拍板的新规落地:

1. **中间 vs 最终产物分离**(W12-D):中间产物(asr/frames/ocr/chapters/drafts/state)→
   `<video>.parent / output/`;最终 md/html → `<video>.parent / output_final/`,
   自包含(`images/` 在讲义同目录),整盘分发路径不失效
2. **真视频名**:chapters.video + 最终产物文件名 = 真视频文件名(去后缀、
   去末尾空格)。W10-A 跑出的 `output.md` 降级问题修复——runner 从 inbox + target_video
   派生 `derive_video_name()`,透传到 chapters / render / longdoc
3. **多视频合并**:新增 `merge_lectures` 模块 + `mtd merge` CLI + MCP 工具
   - 文件名 = 第一个视频 stem 去除序号(`01_xxx` → `xxx`)
   - 章节全局重排(## 第一部分 / 第二部分 ...)+ H2 降级为 H3
   - 图片路径重写到 `<merged>/images/<original_stem>_<file>`(避免多视频同名冲突)
   - 自然排序(数字按数值比较),`_cleaned.md` 优先,`_merged` 后缀跳过自合
4. **兼容性策略**:**默认新规 + 旧产物只读兼容**(gatekeeper / verify 优先
   `output_final/`,回退 `output/chapters/raw/`)。无需迁移脚本

### Added

- `media_to_doc.pipeline.merge_lectures.merge_lectures()` 公开 API
- `media_to_doc.pipeline.merge_lectures.MergeResult` 数据类 + `save_manifest()`
- `media_to_doc.pipeline.chapters.derive_video_name()` 公开 API
- `media_to_doc.pipeline.merge_lectures.strip_leading_index()` 公开 API
- CLI `mtd merge <output_final_dir> [--name ...] [--no-html]`
- CLI `mtd run --final-dir <path>` / `mtd resume --final-dir <path>`
- MCP 工具 `merge_lectures(output_final_dir, merged_name, no_html)`
- `StageContext.final_dir` 字段(供 render / longdoc 使用)
- `State.final_dir` 字段(持久化,resume 时自动派生)
- `verify_pipeline(final_dir=...)` / `gatekeeper_check()` 自动从 `state.final_dir` 读

### Changed

- **render.py**:`render_outputs()` 加 `final_dir` 参数,默认 `<work>.parent / "output_final"`,
  并把 `drafts_dir/images/` 复制到 `<final_dir>/<stem>/images/`(自包含)
- **longdoc.py**:`process_long_doc()` 加 `final_dir` 参数,`_cleaned.md` /
  `_final.html` 写到 final_dir
- **chapters.py**:`split_chapters()` 加 `video_name` 参数(由 runner 注入)
- **runner.py**:`run_pipeline()` 加 `final_dir` + `target_video` 参数
- **state.py**:`State.final_dir` 字段 + to_dict 同步
- **cli.py**:`mtd status` JSON 输出含 `final_dir` 字段
- **gatekeeper.py / verify.py**:路径解析加 `output_final/` 优先,旧布局回退
- **mcp_server.py**:`INSTRUCTIONS` 升级到 9 工具

### Tested

- **559 pytest 用例 / 0 跳过**(1.0.1 539 → 1.1.0 559,+20 merge_lectures 测试)
- **ruff**:All checks passed
- 19 个新测试覆盖:`strip_leading_index` / `discover_lecture_files`(优先 _cleaned /
  fallback / 跳过 _merged / 自然排序)+ `merge_lectures`(基本合并 / 显式名 / 单个抛错 /
  no_html / 章节重排 / manifest / 图片复制 / mermaid CDN)

### Migration from 1.0.x

新规默认开启,无需迁移脚本:

- **新跑**:`mtd run <inbox>` 自动用 `output_final/` 新布局
- **旧产物**:`gatekeeper / verify` 同时支持新旧路径回退读取,但新跑不会再写旧位置
- **手动迁移**(可选):`cp output/chapters/raw/output.md output_final/<真视频名>.md`

[1.1.0]: https://github.com/kizemo/media-to-doc/releases/tag/v1.1.0

---

## [1.2.0] - 2026-07-21

### 🎯 LLM-driven chapter fusion

按用户 2026-07-21 反馈,改 W12-D 硬切(每个视频作为独立 part + H 降级)为
**LLM 驱动的内容融合**(章节命名根据内容,跨视频连续内容归属同一全局章节)。

### 核心改动

- **`chapters_summary(md, max=800)`** — 从 cleaned.md 提取 H2 章节 + 前 800 字摘要,
  跳过代码块围栏(避免误切)。为 LLM fusion prompt 提供压缩输入(避免上下文超限)
- **`_build_fusion_prompt(summaries)`** — 构造融合 prompt(把多视频章节列表拼成可读格式)
- **`_parse_fusion_plan(raw)`** — JSON 容错解析(支持 ```json 围栏 + 空 sources 跳过)
- **`apply_fusion_plan(plan, source_mds, name)`** — 按 LLM 规划重组 md
  - 模糊匹配章节名(`difflib.SequenceMatcher`,阈值 0.6)
  - 找不到时降级为 `> (源未找到,fallback)` 引用提示
  - 图片路径重写同前
- **3 个 dataclass**:`ChapterSummary` / `FusionSource` / `FusionChapter` / `FusionPlan`
- **`merge_lectures` 新参数**:`fusion_provider` / `fusion_model` / `fallback_on_error`
  - `fusion_provider=None` → 旧硬切行为(向后兼容,v1.1.0 测试不破坏)
  - `fusion_provider=<ollama>` → 走 LLM 融合路径
  - LLM 失败 + `fallback_on_error=True` → 降级硬切 + stderr warning
  - LLM 失败 + `fallback_on_error=False` → 抛错

### `include` 指令(LLM 控制原章节正文范围)

- `all` — 引用全文(默认,适合主体内容)
- `first_n:N` — 引用前 N 段(适合只取关键观点)
- `summary` — 仅引用提示,不搬正文(适合重复 / 收尾章节)

### CLI

```bash
# 旧(硬切,与 v1.1.0 一致)
mtd merge <output_final_dir>

# 新(LLM 融合)
mtd merge <output_final_dir> --fusion ollama [--fusion-model qwen3:14b]
```

### MCP

- `merge_lectures` 工具加 `fusion` / `fusion_model` 参数
- description 标注支持的 provider(ollama / anthropic / openai_compatible)

### Tested

- **575 pytest 用例 / 0 跳过**(1.1.0 559 → 1.2.0 575,+16 fusion 测试)
  - `chapters_summary` 提取 / 代码块跳过 / 截断
  - `_parse_fusion_plan` 标准 JSON / 围栏 / 空 sources 跳过
  - `apply_fusion_plan` H1 重写 / first_n / summary / fuzzy 匹配 / unmatched fallback
  - `merge_lectures` with_fusion_provider / fallback_on_error / 抛错 / 真实图片 / prompt 内容
- **ruff**:All checks passed
- **端到端 LLM fusion 实跑**:qwen3:14b,29.5s,7 融合章节(原 14 个),`include=summary` 正确处理雷同内容

[1.2.0]: https://github.com/kizemo/media-to-doc/releases/tag/v1.2.0
