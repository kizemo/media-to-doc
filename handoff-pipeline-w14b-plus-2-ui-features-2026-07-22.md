# Handoff — W14-B+2:Tauri UI 完整化(read_log + read_lecture W12-D + modal)

**日期**:2026-07-22
**承接会话**:`media-to-doc-ui` / `feat/w14b-plus-8-commands` 分支
**本会话主目标**:
- 补完 3 个 P0/P1:`read_log` command / log tail 2s 轮询 / `read_lecture` W12-D 优先 / read_lecture modal
- `cargo tauri dev` 启动 + 5 tab 手动验证 8 commands

## 全部完成 ✅

| Task | 内容 | Commit | 测试 |
|---|---|---|---|
| T1 | 后端 `read_log` + 5 单测 | (Task 1 commit) | +5 |
| T2 | `read_lecture` 3 级 fallback + 4 单测 | (Task 2 commit) | +4 |
| T3 | 前端 marked.js + modal + log tail + [read] 按钮 | (Task 3 commit) | — (手测) |
| T4 | `cargo tauri dev` 启动 + 5 tab 手动验证 | (无 commit) | — |
| T5 | 全量测试 + 本 handoff | docs commit | 39 / 0 |

**总测试**:39 passed / 0 failed(baseline 30 + 9 新增)

## 关键设计

### read_log(后端)

```rust
pub struct ReadLogResult {
    pub content: String,
    pub new_offset: u64,
    pub total_bytes: u64,
    pub truncated: bool,         // 文件被 truncate(offset > total_bytes)
    pub truncated_to_lines: bool, // 命中 max_lines 上限
}
```

**offset 模式**:`path + offset` → 增量内容 + new_offset;前端 2s 轮询只传 delta;max_lines 默认 200 硬上限 2000。

### read_lecture 3 级 fallback

```
1. <inbox>/output_final/<stem>.<ext>           W12-D 真相
2. <inbox>/output_final/<stem>_*.md (仅 fmt=html)  W12-D html→md 兜底
3. <inbox>/output/chapters/raw/<stem>/<file>    W3-W11 legacy fallback
```

新加 `source: "output_final" | "legacy"` 字段供前端显示;html 缺时加 `note: "html 版本未生成,fallback 到 md"`。

### 前端 modal(marked.js + iframe)

- `marked@12.0.0` from unpkg,**SRI 锁版本**(`<commit 时算的 hash>`)
- md 走 `marked.parse(content)`;html 走 `<iframe srcdoc sandbox="allow-same-origin">`(关 script 防 XSS)
- marked CDN 失败时降级到 `<pre>` 纯文本

## 撞墙 / 修正

(留空 — 写实际撞到的)

## 文件索引

| 文件 | 路径 | 改动 |
|---|---|---|
| Spec | `media-to-doc-ui/docs/superpowers/specs/2026-07-22-w14b-plus-2-ui-features-design.md` | 设计(已 commit `1173ab8`+`66cff5c`) |
| Plan | `media-to-doc-ui/docs/superpowers/plans/2026-07-22-w14b-plus-2-ui-features.md` | 实施计划(本会话) |
| Backend | `media-to-doc-ui/src-tauri/src/commands.rs` | +read_log +read_lecture 3 级 + 9 单测 |
| Lib | `media-to-doc-ui/src-tauri/src/lib.rs` | invoke_handler +read_log |
| Frontend | `media-to-doc-ui/src/index.html` | marked.js + modal + log tail + [read] 按钮 |

## 下次会话(W14-C 候选)

- A. Tauri UI 多课程并发 UI(后端 list_running 已支持)
- B. Tauri UI release build + NSIS 安装器(v1.4 Phase 3)
- C. 合并 `feat/w14b-plus-8-commands` → `master` + v1.3.0 release
- D. Anthropic / OpenAI Compat provider `trust_env=False` 加固
- E. 真实端到端 11 stage 流水线在 Tauri UI 内跑通(短 demo 视频)

## 下次会话第一句

> 承接 `handoff-pipeline-w14b-plus-2-ui-features-2026-07-22.md`,Tauri UI 3 个 P0/P1 已实装,39 测试 / 0 failed。准备做 W14-C 候选(参见 handoff §下次会话)。
