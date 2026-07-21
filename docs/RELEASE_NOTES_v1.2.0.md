# Release Notes — v1.2.0

> **Minor release** — LLM-driven chapter fusion(W12-E)。
>
> 按用户 2026-07-21 反馈,W12-D 硬切过于生硬,改 LLM 驱动的内容融合。

---

## 🎯 用户反馈与新流程

> 章节命名,应当根据内容,进行融合,而不是生硬地根据视频确定H1,
> 有可能一个视频的内容末尾,和另一个音视频开头的部分,应该归属于一个章节。
> 为了避免上下文超限,建议在融合前,为每个音视频都建立包含章节和简短摘要的简化版,
> 然后根据简化版,调用大模型优化融合后的章节结构。

### 3 阶段流程

1. **简化版生成** — `chapters_summary()` 提取 H2 章节 + 前 800 字摘要(避免上下文超限)
2. **LLM 融合规划** — 把所有视频的"章节+摘要"拼成 prompt,LLM 决定全局融合章节结构
3. **按规划重组** — `apply_fusion_plan()` 按 LLM 输出重写 md,模糊匹配章节名,找不到降级引用提示

### `include` 指令(LLM 控制原章节正文范围)

- `all` — 引用全文(默认)
- `first_n:N` — 引用前 N 段
- `summary` — 仅引用提示,不搬正文(适合重复 / 收尾)

---

## ✨ 改动详情

### 新公开 API(`media_to_doc.pipeline.merge_lectures`)

- `chapters_summary(md_text, max_summary_chars=800, video_name="")` — 提取简化版
- `apply_fusion_plan(plan, source_mds, merged_name)` — 按 LLM 规划重组
- `_build_fusion_prompt(summaries)` — 构造 fusion prompt(供调试 / 测试)
- `_parse_fusion_plan(raw)` — JSON 容错解析
- 3 dataclass:`ChapterSummary` / `FusionSource` / `FusionChapter` / `FusionPlan`

### `merge_lectures` 新参数

- `fusion_provider: Any | None = None` — None = 硬切(向后兼容)
- `fusion_model: str = ""` — fusion 模式下的 LLM 模型名
- `fallback_on_error: bool = True` — LLM 失败时降级硬切

### CLI

```bash
mtd merge <output_final_dir> --fusion ollama [--fusion-model qwen3:14b]
```

### MCP

- `merge_lectures(output_final_dir, merged_name, no_html, fusion, fusion_model)`
- `fusion`: `"ollama" | "anthropic" | "openai_compatible"`

### 兼容性

- **向后兼容**:`fusion_provider=None` 走 v1.1.0 硬切路径,559 测试不破坏
- **新加 16 个测试**:覆盖 fusion 全流程
- **端到端真 LLM fusion 实跑**:qwen3:14b,29.5s,7 融合章节(原 14 个)

---

## 📊 验证

- **575 pytest 用例 / 0 跳过**(1.1.0 559 → 1.2.0 575,+16)
- **ruff**:All checks passed
- **PyPI**:https://pypi.org/project/media_to_doc/(latest_version: 1.2.0)

---

## 📦 Install

```bash
uv pip install --upgrade media_to_doc==1.2.0
```

或从 GitHub Release 下载 wheel:

```
https://github.com/kizemo/media-to-doc/releases/download/v1.2.0/media_to_doc-1.2.0-py3-none-any.whl
```

---

## 📝 Full Changelog

见 [CHANGELOG.md](https://github.com/kizemo/media-to-doc/blob/main/CHANGELOG.md#120---2026-07-21)。