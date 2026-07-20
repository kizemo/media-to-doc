# Release Notes — v1.0.1

> **Patch release** — fix 2 HTML rendering regressions found during W11-C quality review.

---

## 🐛 Fixed

### mermaid 流程图渲染

**问题**:`cleaned.md` 中的 ` ```mermaid ` 围栏在 v1.0.0 最终 HTML 里被渲染成
`<pre><code class="language-mermaid">…</code></pre>` 纯文本,浏览器看不到流程图。

**修复**:HTML 模板底部加 `mermaid@10` CDN script + `mermaid.initialize`,
BeautifulSoup 后处理把 `<pre><code class="language-mermaid">` 改造为
`<pre class="mermaid">…</pre>`,浏览器端自动识别并渲染。

### GFM task list checkbox 渲染

**问题**:`- [ ] xxx` / `- [x] xxx` 在 v1.0.0 最终 HTML 里保持纯文本 `[ ] xxx`,
无法可视化清单状态。W11-C 风险控制清单(`1. [ ] xxx`)同样降级。

**修复**:BeautifulSoup 后处理遍历 `<li>`,把开头的 `[ ]` / `[x]` 替换为
`<input type="checkbox" disabled>`(checked 视原状态)。同时支持有序列表。

---

## 📊 验证

- **W11-C 真产物复用**:`E:/resource/2026-01-27_年度复训/output_cleaned.md`
  (107min 中文培训视频 / qwen3:14b LLM 净化)
  - 1 个 mermaid 流程图 → `<pre class="mermaid">flowchart TD…</pre>` ✅
  - 5 条风险控制项 → 5 个 `<input type="checkbox" disabled>` ✅
  - 原文 `[ ]` `[x]` `[X]` 残留:0 ✅
- **539 pytest 用例 / 0 跳过**(1.0.0 529 → 1.0.1 539,+10)
- **ruff**:All checks passed

---

## 📦 Install

```bash
uv pip install --upgrade media_to_doc==1.0.1
```

或从 GitHub Release 下载 wheel:

```
https://github.com/kizemo/media-to-doc/releases/download/v1.0.1/media_to_doc-1.0.1-py3-none-any.whl
```

---

## 📝 Full Changelog

见 [CHANGELOG.md](https://github.com/kizemo/media-to-doc/blob/main/CHANGELOG.md#101---2026-07-20)。