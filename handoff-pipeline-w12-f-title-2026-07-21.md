# handoff-pipeline-w12-f-title-2026-07-21.md — W12-F `<title>` vs H1 cosmetic 修复

> **会话主题**:W12-F — 短期 30min 任务,修 W11-C §4 标记的 cosmetic warning
>
> **会话日期**:2026-07-21,~30min
>
> **会话状态**:**W12-F 完成** ✅ + 582 tests / 0 skipped / ruff clean

---

## 1. 本次会话目标

按用户决策"先后顺序:先 B → 再 A":
- **B 任务**(本次):修 W11-C §4 cosmetic warning `<title>` vs 首个 H1 不一致
- **A 任务**(下会话):真跑 01.mp4 端到端 + LLM fusion 验证

---

## 2. 实施过程

### 2.1 根因

W3 render stage 在 `render_outputs` 中把 HTML `<title>` 设成 `report.video or output_stem`。
当 W10-A 用 NTFS hardlink 隔离 inbox 时,chapters.video fallback "output"(派生失败),
导致产物 `<title>='output'`,但首个 H1 是真实讲义标题(全站运营方法论与实操指南)。

v1.2.0 已修 `chapters.video` 派生(`derive_video_name`),但 `render.py` 本身也需要更鲁棒。

### 2.2 修复

`src/media_to_doc/pipeline/render.py` 加 2 个 helper:

| 函数 | 职责 |
|---|---|
| `_extract_first_h1_text(body_html)` | stdlib regex 提取首个 `<h1>` 的纯文本(去除内嵌标签如链接 / 强调) |
| `_resolve_title(report_video, body_html, fallback_stem)` | 3 级 title 优先级:report_video > 首个 H1 > fallback_stem |

两处调用点都改用 `_resolve_title`:
- `render_outputs` 第 489 行(line 442 旧):`title=report.video or output_stem` → `_resolve_title(report.video, body_html, output_stem)`
- `render_html` 第 527 行:`title=md_path.stem` → `_resolve_title("", body_html, md_path.stem)`

### 2.3 关键设计:stdlib regex 替代 BeautifulSoup

原计划用 BeautifulSoup 提取首个 H1,但 BS4 是 `[longdoc]` extras 依赖。
改用 stdlib `re.compile(r"<h1[^>]*>(.*?)</h1>", re.DOTALL)`,符合 CLAUDE.md §4
"核心 deps 不引入额外依赖"原则。

### 2.4 测试

7 个新测试覆盖:

| 测试 | 验证点 |
|---|---|
| `test_extract_first_h1_text_returns_first_h1_inner_text` | 基本提取 |
| `test_extract_first_h1_text_strips_inner_tags` | 内嵌标签去除(链接 / 强调) |
| `test_extract_first_h1_text_returns_empty_when_no_h1` | 无 H1 → 空字符串 |
| `test_resolve_title_prefers_report_video` | 优先级 1:report.video |
| `test_resolve_title_falls_back_to_first_h1` | 优先级 2:W11-C §4 警告修复 |
| `test_resolve_title_falls_back_to_stem_when_no_h1` | 优先级 3:兜底 |
| `test_render_outputs_html_title_matches_first_h1` | 端到端:HTML `<title>` == 首个 H1 |

---

## 3. 验证

- pytest **582 passed** / 0 skipped(575 → 582,+7 title 测试)
- ruff:All checks passed
- commit `?`(在 release/v1.0 分支,待 push)

---

## 4. 发版建议

本次改动是 bug fix(消除 verify warning)+ 用户原话中"已输出的阶段处理结果"修复,
按 SemVer 应该发 **v1.2.1 patch**(兼容 v1.2.0):
- `pyproject.toml` 1.2.0 → 1.2.1
- `tests/test_smoke.py` test_version_is_1_2_0 → 1_2_1
- `CHANGELOG.md` [1.2.1] 节
- `docs/RELEASE_NOTES_v1.2.1.md`
- build + publish + GitHub Release

但用户原话"修复 `<title>` vs H1"没说发版,**默认只 commit + handoff,等用户决策**。
若用户要发版,流程同 v1.2.0(预计 10min 额外)。

---

## 5. 给下一会话(A 任务)的指引

### 当前状态

- `release/v1.0` HEAD = 新 commit(W12-F 修复)
- `v1.2.0` 已发(PyPI + GitHub Release)
- 01.mp4 = `E:\resource\2026-01-27_年度复训\01_先精准后放大的打爆策略 .mp4` (506MB)
- 02.mp4 = `E:\resource\2026-01-27_年度复训\02_先拉新后成交-潜客规模起爆款 .mp4` (522MB)
- 03.mp4 = 已 W10-A 完整跑过,产物在 `output-w12c/`

### A 任务:真跑 01.mp4 + LLM fusion 端到端

完整 prompt 已在 W12-E handoff 后提供。下次会话第一句可以引用:

> 承接上一个会话任务 W12-F `<title>` vs H1 cosmetic 修复已 commit。
> 见 `F:\soft\00selfmade\media-to-doc\handoff-pipeline-w12-f-title-2026-07-21.md`。
>
> **新任务**:真跑 01.mp4 端到端 pipeline(用户 2026-07-21 第一轮反馈"01.mp4 没处理过")。
>
> **计划步骤**(详细见 W12-E handoff 后给出的完整 prompt):
> 1. cd repo + git status 干净
> 2. 备份 `output/` + `output_final/` → `*-backup-2026-07-21/`
> 3. NTFS hardlink 单文件 inbox:`os.link('01_先精准后放大的打爆策略 .mp4', '_w13a_inbox/01_先精准后放大的打爆策略 .mp4')`
> 4. background `mtd run --no-isolate --imagegen skip --longdoc-llm ollama`(~4-5h)
> 5. 每 5 分钟 polling state.json
> 6. ASR 完成后自动 chapters/draft/longdoc LLM 净化
> 7. 验证 `output_final/01_先精准后放大的打爆策略_{cleaned.md,final.html}` 存在
> 8. **LLM fusion 端到端**:用 03.mp4 + 01.mp4 跑 `mtd merge --fusion ollama --name "年度复训综合"`
> 9. commit + handoff-pipeline-w13-01-real-2026-07-21.md + 更新 task.md
> 10. 跑 pytest + ruff(582 baseline 不破坏)

### 关键监控点(同 W12-E 实跑经验)

- HF 模型下载:`unset proxy + HF_ENDPOINT=hf-mirror.com + HF_HUB_DISABLE_XET=1`
- ASR 卡 50%+:主动 `taskkill /F /PID` 接受 85% transcript
- chapters / draft LLM 失败:`fallback_on_error=True`(已实现,降级规则清理)
- longdoc 失败:`process_long_doc(work, None, ...)` 跑规则清理

### 预算

- 活跃 < 2h(polling + 报告)
- 后台 ~5h
- 撞 2h 边界 → 写 handoff,新会话 polling 收尾

### 不在范围内(W13 不做)

- 02.mp4(留 W13-B)
- 新版本发布(只产出,等 A 跑成功 + 用户确认再发 v1.3.0)
- W11-C §4 cosmetic 03.mp4 既有产物重渲染(本次代码已修,v1.3.0 时一并重渲染 + 重新分发)