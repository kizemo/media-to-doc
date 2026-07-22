# Changelog

All notable changes to `media-to-doc` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [1.3.0] - 2026-07-22

### 🛡️ Defense in depth: LLM provider trust_env 全栈隔离

W13-C 撞出"公司 VPN 父 shell 代理劫持子进程 httpx"问题后,W14-B 修了 Ollama 一个 provider,
W14-D E 把修复扩展到 **Anthropic + OpenAI-compatible 两个 provider**,实现三个 LLM provider
全部显式 `httpx.Client(trust_env=False)`,从代码层消除 HTTP_PROXY 污染,与脚本层
子进程 env 过滤形成 defense in depth。

子项目 `media-to-doc-ui` 同步发布 **v1.3.0**(W14-C A+B + W14-D C+Tauri v1.3.0 GitHub Release):
NSIS installer (`media-to-doc-1.3.0-setup.exe` ~1.5MB) + 便携版
(`media-to-doc-1.3.0-portable.exe` ~6.2MB)。Tauri 桌面壳为 macOS / Linux / Windows
用户提供 3-次点击跑通 11 stage 流水线的入口,8 commands 等价对齐 MCP 8 工具。

### Added

- **Tauri UI 子项目 v1.3.0** (W14-C + W14-D):独立 repo `kizemo/media-to-doc-ui`,
  - Tauri 2.11.4 + Rust 1.97.1 + system NSIS 3.12
  - 8 commands 等价对齐 MCP 8 工具(probe / list_courses / check_status / list_outputs / read_lecture / get_run_metrics / list_runs / read_log)
  - 5 tab SPA(Inbox / Run / Output / Health / Learn)
  - 多课程并发(max_concurrent=3 + LRU 100 + 2s cancel)
  - `E2E verify` 脚本 `scripts/_w14d_e2e_verify.py`(主仓端到端验证子仓 8/8 commands)
- **sandbox-verify 真机验证脚本** (W14-D):`F:\soft\00selfmade\sandbox-verify\media-to-doc-ui\`
  (Tauri 桌面壳专用,纯 Python wheel 不走沙箱)

### Fixed

- **trust_env=False 全 provider** (`b283d64` / `427d963`):OllamaProvider / AnthropicProvider /
  OpenAICompatProvider 三个 provider 的 `_ensure_client` 全部透传
  `http_client=httpx.Client(trust_env=False)`,与脚本层 proxy vars 过滤形成
  defense in depth(中国大陆 + 公司 VPN 用户必备)
- **read_lecture html→md fallback** (`3ac1337`):返回 `source=fallback_md` 标识,便于
  上层 UI 区分讲义来源(子仓 Tauri modal 用)
- **read_lecture W12-D output_final 优先** (`90e9b7d`):4 个新单测覆盖
  `output_final/<stem>.md` 优先 + W3-W11 旧布局 fallback
- **read_log Tauri command** (`15ae251`):5 个新单测覆盖 offset-based 2s log tail
- **release notes command count 8 → 9** (`951c9ed`):`cancel_run` 标为 UI-only
  (无 Python API 等价,不在 8 commands 之列)

### Changed

- **CLAUDE.md §5.6 pre-authorize**(`8a916db`):会话级自动合并/审核规则,fix 自动
  merge master / feat 写 handoff 等用户拍板 / Rust 后端双轮 review
- **CLAUDE.md §11 真机装机验证**:`sandbox-verify` 强制时机(改 `tauri.conf.json` /
  `installer.nsi` / `Cargo.toml` / `capabilities/` 后必跑)

### Tested

- **604 pytest 用例 / 0 跳过**(1.2.1 595 → 1.3.0 604,+9)
  - 3 个 Ollama trust_env 透传(W14-B)
  - 6 个 Anthropic + OpenAICompat trust_env 透传(W14-D E)
- **ruff**:All checks passed
- **W14-D E2E 端到端**:60s demo 视频 4m08s 跑通 + 8/8 Tauri commands 后端 API 验证
- **子仓 v1.3.0 NSIS 真编译**:`installer.nsi` 实跑出 setup.exe + portable.exe,
  `gh release create v1.3.0 --target master` 上传 2 assets,SHA256 verified

[1.3.0]: https://github.com/kizemo/media-to-doc/releases/tag/v1.3.0
[Tauri UI v1.3.0]: https://github.com/kizemo/media-to-doc-ui/releases/tag/v1.3.0

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

---

## [1.2.1] - 2026-07-21

### 🩹 Hotfix: longdoc W12-D 兼容 + fusion proxy 隔离

W13-A 真跑 01.mp4 端到端时撞出两个 P1 bug:

1. **`longdoc.py` 找不到 W12-D 后的源讲义**(`d4c1465`)— `process_long_doc` 假设
   `<work>/chapters/raw/<video>.md` 单文件布局,W12-D 把 render 产物移到
   `<final_dir>/<video>.md` 后该路径不存在 → longdoc 找不到源 → 自动 fallback
   到拼装草稿(质量降级)。
2. **`merge_lectures` ollama 子进程 SSL 错误**(`cb992e5`)— 公司 VPN proxy vars
   (`HTTP_PROXY` 等 8 个)泄漏到 fusion 子进程 env,ollama SDK httpx 走代理后
   报 SSL unknown error → fusion 实际走 fallback 硬切(quality 隐性降级)。

### Fixed

- **longdoc W12-D 兼容 3 级 fallback**:`_resolve_source_md(work, video, final_dir)`
  helper,按优先级查找:
  1. `<final_dir>/<video>.md`(W12-D 真相位置,render 已拼装好的讲义)
  2. `<work>/chapters/raw/<video>.md`(W3-W11 旧布局,向后兼容)
  3. `<work>/chapters/raw/<video>/chapter_*.md` 拼装(W12-D 中间产物应急)
- **fusion proxy 隔离**:子进程 env 显式剔除 8 个 proxy vars
  (`HTTP_PROXY` / `HTTPS_PROXY` / `http_proxy` / `https_proxy` /
   `ALL_PROXY` / `all_proxy` / `NO_PROXY` / `no_proxy`),避免 ollama httpx
   误走代理

### Added

- `scripts/_w13b_verify_longdoc_fix.py` — 验证 longdoc fix 的真跑工具
- `scripts/_w13c_diag_fusion_ssl.py` — ollama SSL 健康 + prompt 大小诊断
- `tests/test_pipeline/test_longdoc_w12d_compat.py` — 13 新用例覆盖 3 路径

### Tested

- **595 pytest 用例 / 0 跳过**(1.2.0 575 → 1.2.1 595,+20)
  - 13 longdoc W12-D 兼容测试(3 路径 + 集成 + fallback + 拼装)
  - 7 既有 longdoc 测试不变,3 级 fallback 完全向后兼容
- **ruff**:All checks passed
- **W13-A 真跑 01.mp4 验证**:`_w13a_inbox/output_final/01_先精准后放大的打爆策略.md`
  → longdoc source 自动选 W12-D 真讲义(+1.4% chars,含 TOC/摘要/要点/关键帧)
- **W13-C 重跑 fusion 验证**:proxy 隔离后 7 H2 LLM 融合产物(此前 10 H2 是 fallback 硬切)

[1.2.1]: https://github.com/kizemo/media-to-doc/releases/tag/v1.2.1
