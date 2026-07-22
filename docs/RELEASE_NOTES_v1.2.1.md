# Release Notes — v1.2.1

> **Patch release** — W13-B longdoc W12-D 兼容 + W13-C fusion proxy 隔离。
>
> W13-A 真跑 01.mp4 端到端时撞出的两个 P1 bug,代码侧已修复并通过 595 测试。

---

## 🩹 修了什么

### 1. `longdoc` 找不到 W12-D 后的源讲义(W13-B)

**症状**

跑 v1.1.0+ 之后产生的讲义(`<final_dir>/<video>.md`)走 `longdoc` 阶段时,日志报
`FileNotFoundError`,实际自动 fallback 到拼装草稿章节 — 讲义质量隐性降级。

**根因**

`process_long_doc` 假设 W3-W11 旧布局:`<work>/chapters/raw/<video>.md` 是 render 阶段
已拼装好的讲义。W12-D 之后,render 改写到 `<final_dir>/<video>.md`,
原路径只放中间草稿目录(`<video>/chapter_*.md`),不再有单文件讲义。

**修复**

新增 `_resolve_source_md(work, video, final_dir)` helper,3 级 fallback:

1. `<final_dir>/<video>.md` — W12-D 真相位置,render 已拼装好的讲义(优先)
2. `<work>/chapters/raw/<video>.md` — W3-W11 旧布局,向后兼容
3. `<work>/chapters/raw/<video>/chapter_*.md` 拼装 — W12-D 中间产物应急

`process_long_doc` 重构:`target_dir` 提前计算,作为 W12-D 查找位置。

### 2. `merge_lectures` ollama 子进程 SSL 错误(W13-C)

**症状**

公司 VPN 环境下,`mtd merge --fusion ollama` 实际走 fallback 硬切,LLM 融合
quality 隐性降级;`merge_lectures` 含 LLM 融合失败 warning 但日志不直观。

**根因**

`_w13a_run_fusion.py` 启动子进程时,父 shell 的 `HTTP_PROXY` 等 8 个 VPN proxy
环境变量泄漏到子进程 env,ollama SDK 的 httpx 走代理后报 SSL unknown error。

**修复**

子进程 env 显式剔除 8 个 proxy vars:

```python
PROXY_VARS = (
  "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
  "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy",
)
```

---

## ✅ 验证

- **595 pytest / 0 跳过** (1.2.0 575 → 1.2.1 595,+20):
  - 13 longdoc W12-D 兼容测试(3 路径 + 集成 + fallback + 拼装)
  - 7 既有 longdoc 测试不变,3 级 fallback 完全向后兼容
- **ruff**:All checks passed
- **W13-A 真跑 01.mp4 验证**:`_w13a_inbox/output_final/01_先精准后放大的打爆策略.md`
  → longdoc source 自动选 W12-D 真讲义(+1.4% chars,含 TOC/摘要/要点/关键帧)
- **W13-C 重跑 fusion 验证**:proxy 隔离后 7 H2 LLM 融合产物(此前 10 H2 是 fallback 硬切)

---

## 📦 升级方式

```bash
uv pip install --upgrade media_to_doc==1.2.1
```

无需迁移脚本,新代码兼容旧产物;旧产物再次跑 `mtd resume` 会自动用新 3 级 fallback
找到正确的源讲义。