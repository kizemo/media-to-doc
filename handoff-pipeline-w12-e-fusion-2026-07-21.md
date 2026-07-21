# handoff-pipeline-w12-e-fusion-2026-07-21.md — W12-E LLM-driven chapter fusion

> **会话主题**:W12-E — 按用户 2026-07-21 反馈,改 hard-cut 章节降级为 LLM 驱动的内容融合
>
> **会话日期**:2026-07-21,~1.5 小时
>
> **会话状态**:**W12-E 主目标完成** ✅ + 端到端 LLM fusion 验证(29.5s,7 个融合章节)

---

## 1. 本次会话目标

按用户 2026-07-21 反馈,W12-D 的"硬切 + H 降级"过于生硬:

> 章节命名,应当根据内容,进行融合,而不是生硬地根据视频确定H1,
> 有可能一个视频的内容末尾,和另一个音视频开头的部分,应该归属于一个章节。
> 为了避免上下文超限,建议在融合前,为每个音视频都建立包含章节和简短摘要的简化版,
> 然后根据简化版,调用大模型优化融合后的章节结构。

新流程:
1. **简化版生成**:每个 cleaned.md → 章节列表 + 摘要(避免上下文超限)
2. **LLM 融合**:把简化版拼成 prompt,LLM 决定全局融合章节结构
3. **按 LLM 规划重组 md**:保持内容驱动,而非视频驱动

---

## 2. 实施过程

### 2.1 核心模块扩展(merge_lectures.py)

新增 3 个 dataclass + 3 个工具函数 + 1 个 apply 函数:

| 名称 | 职责 |
|---|---|
| `ChapterSummary` | (video, chapter, summary) 三元组,LLM fusion prompt 输入 |
| `FusionSource` | fusion_plan 一项,含 (video, chapter, include) |
| `FusionChapter` | 融合章节,含 (title, sources[]) |
| `FusionPlan` | 整体融合规划,chapters[] |
| `chapters_summary(md, max=800)` | 提取 H2 章节 + 前 800 字摘要,跳过代码块围栏 |
| `_build_fusion_prompt(summaries)` | 构造 LLM prompt(含视频列表 + 章节简化版) |
| `_parse_fusion_plan(raw)` | JSON 容错解析(支持 ```json 围栏 + 空 sources 跳过) |
| `apply_fusion_plan(plan, source_mds, name)` | 按 plan 重写合并 md,模糊匹配章节名 |

### 2.2 merge_lectures 主流程

新增 `fusion_provider` / `fusion_model` / `fallback_on_error` 参数:

```python
def merge_lectures(
    output_final_dir: Path,
    merged_name: str | None = None,
    *,
    no_html: bool = False,
    prefer_cleaned: bool = True,
    fusion_provider: Any | None = None,   # W12-E 新增
    fusion_model: str = "",               # W12-E 新增
    fallback_on_error: bool = True,       # W12-E 新增
) -> MergeResult:
```

- `fusion_provider=None` → 旧硬切行为(向后兼容,559 测试不破坏)
- `fusion_provider=<ollama>` → 走 LLM 融合
- LLM 失败 + `fallback_on_error=True` → 降级到硬切 + stderr warning
- LLM 失败 + `fallback_on_error=False` → 抛错

### 2.3 include 指令(LLM 控制原章节正文范围)

| include | 行为 |
|---|---|
| `all` | 引用该源章节全文(默认) |
| `first_n:N` | 引用前 N 段(适合只取关键观点) |
| `summary` | 仅写引用提示,不搬正文(适合重复 / 收尾) |

### 2.4 CLI / MCP

**CLI**:
```bash
# 旧(硬切)
mtd merge <output_final_dir>

# 新(LLM 融合)
mtd merge <output_final_dir> --fusion ollama [--fusion-model qwen3:14b]
```

**MCP** (`merge_lectures` 工具):
- `fusion`: `"ollama" | "anthropic" | "openai_compatible"`
- `fusion_model`: 模型名(空时用 provider 默认)

### 2.5 测试

- 16 个新测试覆盖 fusion 全流程:
  - `chapters_summary` 提取 / 代码块跳过 / 截断
  - `_parse_fusion_plan` 标准 JSON / 围栏 / 空 sources 跳过
  - `apply_fusion_plan` H1 重写 / first_n / summary / fuzzy 匹配 / unmatched fallback
  - `merge_lectures` 端到端 with_fusion / fallback_on_error / 抛错 / 真实图片 / prompt 内容

### 2.6 端到端真 LLM fusion 验证

```bash
# 复制 W11-C 03.mp4 产物,模拟 2 视频(同内容)
# 跑 mtd merge --fusion ollama

# 实际结果:
duration = 29.5s
chapters: 7 个融合章节(原 14 个章节融合成 7 个)
"01_先精准后放大" / 章节 "一、冬季产品策略..." → 完整内容
"02_先拉新后成交" / 同章节 → summary(因内容雷同)
```

完美实现用户需求:章节命名根据内容,LLM 自动决定"重复内容用 summary,新内容用 all"。

---

## 3. 关键设计 / 决策

### 3.1 简化版 vs 全文

- **简化版**:每章 800 字摘要
- 3 视频 × 7 章节 × 800 字 ≈ 17K 字符,加上 prompt 模板 ≈ 20K 字符
- qwen3:14b num_ctx=32K 余量充足
- 大视频(>10 章节)可降低 `max_summary_chars` 到 500

### 3.2 fuzzy 匹配容错

LLM 返回的 chapter 名可能与原文略不同(如同义改写、错别字)。用 `difflib.SequenceMatcher`:
- 相似度阈值 0.6
- 找不到时降级为 `> (源未找到,fallback)` 引用提示

### 3.3 include 指令降低 LLM 决策负担

LLM 不必"全用 full 文本",可以决定:
- 主体内容(不重复)→ `all`
- 关键观点(只取前 N 段)→ `first_n:2`
- 收尾 / 重复(仅引用)→ `summary`

让 LLM 决定内容呈现的"粒度"。

### 3.4 fallback_on_error 默认 True

- 实战中 LLM 偶有 JSON 解析失败 / 网络超时
- 默认降级到硬切 + stderr warning,**不让融合功能破坏主流程**
- 严格场景可设 `fallback_on_error=False` 抛错

### 3.5 兼容性

- 旧测试 20 个(硬切路径)+ 16 个新测试(fusion 路径)= 36 个,全过
- 整体 539 → 575(+16)
- ruff clean
- 向后兼容:`fusion_provider=None` 走旧路径,产物结构与 v1.1.0 相同

---

## 4. 验证清单

- [x] `chapters_summary()` 提取 H2 章节 + 摘要(跳代码块/截断)
- [x] `_parse_fusion_plan()` JSON 容错(围栏/空 sources)
- [x] `apply_fusion_plan()` H1 重写 + first_n / summary / fuzzy / unmatched fallback
- [x] `merge_lectures(fusion_provider=...)` 端到端
- [x] `merge_lectures` LLM 失败 → 降级硬切(fallback_on_error=True)
- [x] `merge_lectures` LLM 失败 + fallback_on_error=False → 抛错
- [x] CLI `mtd merge --fusion ollama` / `--fusion-model`
- [x] MCP `merge_lectures(fusion, fusion_model)` 工具参数
- [x] pytest 575 passed / 0 skipped
- [x] ruff:All checks passed
- [x] 端到端 LLM fusion 实跑:29.5s,7 融合章节(原 14)
- [x] commit + push to main (`3592d2b`)

---

## 5. v1.x.x 版本规划

当前 `release/v1.0` 分支 HEAD = `3592d2b`,含 v1.1.0 + W12-E fusion 扩展。

发版选择:
- **A. 不发版** — fusion 已经在 release 分支(待 v1.2.0 统一发)
- **B. v1.1.1 patch** — 兼容性更新,不动功能 API
- **C. v1.2.0 minor** — 新功能 fusion(标准 SemVer)

按用户反馈决定。建议 **C. v1.2.0 minor**,因为:
- 新增公开 API(`fusion_provider` / `fusion_model` / `chapters_summary` / `apply_fusion_plan`)
- 新增 CLI 选项(`--fusion` / `--fusion-model`)
- 新增 MCP 工具参数
- 行为变更(默认模式可改 LLM)

---

## 6. 给下一会话的提示

按 task.md / CLAUDE.md §10:

- v1.1.1 vs v1.2.0 发版决策(待用户拍板)
- C. Tauri UI v1.1+ Phase 2
- D. NSIS 安装器 v1.2+ Phase 3
- 处理 01.mp4 / 02.mp4 真跑(新视频,目前只有 03.mp4 产物)
- 短期 cosmetic:W11-C §4 标记的 `<title>` vs 首个 H1 不一致

W12-E 后续可能的扩展:
- fusion 模式加 mtime/缓存(避免重复跑 LLM)
- 多轮 LLM 自我批评(refine pass)
- LLM 输出带 mermaid 块的章节,合并时跨视频去重