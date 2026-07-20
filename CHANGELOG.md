# Changelog

All notable changes to `media-to-doc` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [1.0.0] - 2026-07-20

### 🎉 First stable release

11 阶段流水线全跑通,3 种调用方式(CLI / Python API / MCP server),Loop Engineering 五层闭环端到端接入。
W10-A 真端到端验证:107 分钟中文培训视频 3 小时 57 分钟跑完,529 测试 0 失败。

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

[1.0.0]: https://github.com/media-to-doc/media-to-doc/releases/tag/v1.0.0
[0.1.0-dev]: https://github.com/media-to-doc/media-to-doc/releases/tag/v0.1.0-dev
