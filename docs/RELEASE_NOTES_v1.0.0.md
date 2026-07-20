# Release Notes — v1.0.0

> 把本地音视频一键转化为带 AI 配图、可独立分发的 Markdown + HTML 讲义。

**Release date**: 2026-07-20
**Tags**: `v1.0.0`
**Python**: 3.11 / 3.12 / 3.13 / 3.14
**PyPI**: https://pypi.org/project/media-to-doc/
**License**: MIT
**Status**: 🎉 First stable release

---

## Install

```bash
# PyPI 装
uv pip install media_to_doc

# 或装全部功能依赖(~5GB: faster-whisper / scenedetect / rapidocr / diffusers 等)
uv pip install "media_to_doc[all]"

# 验证
mtd --version  # media-to-doc 1.0.0
```

---

## TL;DR

`media-to-doc` 1.0.0 是首个 GA(Generally Available)发布。11 阶段流水线端到端跑通,3 种调用方式(CLI / Python API / MCP server),Loop Engineering 五层闭环全接入,529 测试 0 失败,W10-A 真端到端验证 107 分钟中文培训视频 3h57min 跑完。

---

## What's New

### 11 阶段流水线(audio → ... → verify)

```
audio → asr → frames → ocr → asr_correct → chapters → draft → imagegen → render → longdoc → verify
```

- `audio`:ffmpeg 抽音(wav/mp3/m4a 直接 copy 跳过转码)
- `asr`:Faster-Whisper large-v3(CPU fp16 / CUDA fp16)
- `frames`:PySceneDetect ContentDetector + pHash 去重
- `ocr`:RapidOCR(ONNX 本地推理)
- `asr_correct`:OCR × ASR 8s 滑动窗口校对
- `chapters`:LLM 切章节 + 标题/摘要/关键点/关键帧引用
- `draft`:LLM 按章节切片 + 双 prompt 草稿生成
- `imagegen`:SDXL Base + Refiner(可 `skip` 让 Claude 自己做配图)
- `render`:jinja2 + markdown 拼装讲义(TOC / 锚点 / 内嵌 CSS / dark mode / print stylesheet)
- `longdoc`:LLM 净化或规则清理(可 `skip`)
- `verify`:4 项机器可验证(产物存在 / 章节完整 / 图像引用 / HTML 结构)

### 3 种调用方式(W6 / W7 / W9)

| 调用方式 | 入口 | 适用 |
|---|---|---|
| **CLI** | `mtd run / resume / status / list / doctor / config / mcp` | 终端用户 + CI |
| **Python API** | `from media_to_doc import run_pipeline, get_run_metrics, ...` | 嵌入其它项目,52 个公开符号,PEP 562 lazy import,启动 < 100ms |
| **MCP Server** | `mtd-mcp` (stdio JSON-RPC) | Claude Desktop / Codex / Cline,8 工具(LIST / RUN / RESUME / CHECK / OUT / READ + W8 健康度) |

### Loop Engineering 五层闭环(W8)

```
执行层 → 审核层 → 沉淀层 → 进化层 → 健康度
  L1      L2       L3       L4       L5
```

- **L1 执行**:`timed_stage(logger, stage)` 包裹每 stage 写 LE L1 即时记忆
- **L2 审核**:`gatekeeper_check(work)` 4 项机器可验证,W11-A 修完后与 verify 一致
- **L3 沉淀**:`pipeline_run.json` 含 `llm_health` / `gatekeeper_passed` / `quality` / `errors`
- **L4 进化**:Pattern-Key 自动晋升到 `.learnings/ERRORS.md`(同 Pattern-Key ≥ 3 次触发)
- **L5 健康度**:`assess_llm_health` 失败率 > 10% → `switch_provider` 建议,> 20% → `reduce_chunk` 建议

### 可分发的产物(CLAUDE.md §7)

讲义目录整盘复制 / 上传网盘 / 丢知识库,**路径不失效**:

```
output/我的培训/
├── output.md                   # 拼装讲义(相对路径图片)
├── output.html                 # 单文件 HTML(含 TOC / 锚点 / CSS)
├── output_cleaned.md           # longdoc 净化后(可分发主版本)
├── output_final.html           # longdoc 最终 HTML(TOC + dark mode + print)
├── chapters/                   # 章节 JSON + 草稿
├── drafts/drafts.json          # 配图 manifest
├── pipeline_run.json           # LE L3 沉淀(llm_health 等)
└── verify/verify.json          # 4 项机器可验证报告
```

### 跨 run 健康度查询(W8)

```python
from media_to_doc import get_run_metrics, list_runs

m = get_run_metrics("output/我的培训")
print(m["pipeline_run"]["llm_health"])
# {'chapters_ollama': {'calls': 1, 'failures': 0},
#  'draft_ollama':    {'calls': 6, 'failures': 0}}

runs = list_runs(workspace_root="output", limit=10)
print(runs["llm_health_global"])
```

MCP 工具等价:`get_run_metrics` / `list_runs`。

---

## Tested

- **529 pytest / 0 跳过**:W11-A(W10-C 519 → 529)涵盖 11 stage 单元测试 + LE 闭环 + CLI + MCP server + 一致性回归
- **W5 端到端冒烟**:1.3GB / 112min 中文培训视频 CPU 模式全跑通,verify.json overall_passed=true
- **W10-A 真端到端验收**:395MB / 107min 视频 3h57min,11 stage 全部 completed,llm_health 真聚合 `chapters_ollama:1 calls + draft_ollama:6 calls`,0 failures
- **W11-A 一致性回归**:同一份数据 gatekeeper.ok == verify.overall_passed,`scripts/_w11a_consistency.py` 防回归工具就位
- **ruff check**:All checks passed

---

## Bug Fixes Since 0.1.0-dev

W11-A 修的核心 bug(必须在升级说明里强调):

- **Gatekeeper vs Verify 不一致**:W4 原型时 gatekeeper 写死了 `<work>/chapters/raw/<stem>/<stem>.md` + `<work>/output_final.html` 路径,而 W3+ render + W4 longdoc 已迁移到新布局 `<work>/chapters/raw/<stem>.md` + `<work>/chapters/raw/<stem>_final.html`。verify.py 在 W5 (`db92ac9`) 已用 `_resolve_drafts_dir` 处理两布局,但 gatekeeper 没同步。结果:**同一份数据,verify PASS 但 gatekeeper FAIL**。W11-A (`d2b39d3`) 修。

升级后用户应该看不到 `pipeline_run.json.gatekeeper_passed=false` 但 `verify/verify.json.overall_passed=true` 这种矛盾状态。

其它小修:`bddc387` (W10-C) `llm_health` 自动聚合、`db92ac9` (W5) OCR 路径 / num_ctx / transcript 截断 / longdoc-verify 布局兼容。

---

## Breaking Changes (from 0.1.0-dev)

无。0.1.0-dev 是骨架,公开 API 不稳定,直接跳 1.0.0 是合法的。

---

## Upgrade Instructions

### 全新安装

```bash
git clone https://github.com/media-to-doc/media-to-doc.git
cd media-to-doc
uv sync --all-extras
uv run mtd --version
# media-to-doc 1.0.0
```

### 从 0.1.0-dev 升级

```bash
cd media-to-doc
git fetch origin
git checkout release/v1.0
uv sync --all-extras
uv run pytest  # 验证 529 全过
```

### 重跑已中断流水线

旧的 `state.json` 与 1.0.0 完全兼容。直接 `mtd resume <work>` 续跑即可:

```bash
uv run mtd resume output/我的课程/
```

### W10-A 之前跑的产物

如果旧的产物目录里 `pipeline_run.json.gatekeeper_passed=false` 但 `verify/verify.json.overall_passed=true`,**别担心**,W11-A 已修。

新跑流水线就会一致。旧产物的 gatekeeper 历史值不需要改 — `pipeline_run.json` 是 LE L3 沉淀真相,留着供 LE 学习用。

---

## Known Limitations

v1.0 范围明确**不做**(留给 v1.1+):

- **UI(Tauri 2 + React 18)**:Phase 2 才引入,1.0 仅 CLI / Python API / MCP
- **NSIS 安装器**:Phase 3 才引入,1.0 用 `uv` 安装
- **3 次点击跑通**:需要 UI(v1.1+),1.0 是 CLI 流程
- **断点续跑 100% 跨 OS**:已支持 Windows + macOS + Linux,跨 OS resume **不保证**(状态机本地化)
- **多视频并发**:每次 `mtd run` 处理一个视频,批量需手动循环
- **CUDA 在 Apple Silicon 上的 MPS 加速**:要 `--config-settings` 手配,默认 CPU

---

## Documentation

| 文档 | 路径 | 用途 |
|---|---|---|
| README | [README.md](../README.md) | 5 分钟快速开始 + 3 种调用方式 |
| Changelog | [CHANGELOG.md](../CHANGELOG.md) | 完整变更历史 |
| Installation | [docs/installation.md](installation.md) | 各 OS / CUDA / 中国网络 / Claude Desktop |
| MCP Integration | [docs/MCP_INTEGRATION.md](MCP_INTEGRATION.md) | Claude Desktop 配置 + 8 工具签名 |
| Project Guide | [CLAUDE.md](../CLAUDE.md) | 项目指引 + 设计约束 + 11 阶段产物布局 |
| Roadmap | [ROADMAP.md](../ROADMAP.md) | v1.0 后的 Phase 2 / 3 规划 |
| PRD | [PRD.md](../PRD.md) | 产品需求 |
| TDD | [TDD.md](../TDD.md) | 技术设计 |

---

## Acknowledgments

- 参考实现:`E:\办公文件\01学习资料\local-ai-workflow`(8 次 commit / 110 测试)
- Loop Engineering 五层闭环设计参考 aiec.fun 两篇文章
- 14 条 LP-YYYYMMDD-NNN best_practice 条目沉淀到 `.learnings/LEARNINGS.md`

---

## Full Changelog

See [CHANGELOG.md](../CHANGELOG.md) for the complete milestone summary (W0-W11) and per-commit changes.
