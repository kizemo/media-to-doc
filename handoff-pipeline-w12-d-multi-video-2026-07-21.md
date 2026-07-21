# handoff-pipeline-w12-d-multi-video-2026-07-21.md — W12-D v1.1.0 multi-video layout + merge

> **会话主题**:W12-D — 按用户 2026-07-21 拍板的新规落地(中间/最终分离 + 真视频名 + 多视频合并)
>
> **会话日期**:2026-07-21,~2 小时
>
> **会话状态**:**W12-D 主目标完成** ✅ + PyPI v1.1.0 live + GitHub Release v1.1.0

---

## 1. 本次会话目标

按用户在 W12-D 拍板 3 条新规:

1. **中间 vs 最终产物分离**:中间产物 → `<video>.parent / output/`;最终 md/html → `<video>.parent / output_final/`
2. **真视频名**:chapters.video + 最终文件名 = 真视频文件名(去后缀、去末尾空格)
3. **多视频合并**:新增 `merge_lectures` 模块,文件名 = 第一个视频名(去除序号),章节重排

兼容性策略:默认新规 + 旧产物只读兼容(gatekeeper / verify 优先 `output_final/`,回退旧布局)。
序号规则:全局重排(## 第一/二/三部分)。
图片路径:重写到 `<merged>/images/<video_stem>_<file>`。

---

## 2. 实施过程

### 2.1 Phase 1:核心拆分(8 个文件,~50 min)

| # | 文件 | 改动 |
|---|---|---|
| 1 | `chapters.py` | `derive_video_name(inbox, target_video)` helper + `split_chapters(video_name=)` 参数 |
| 2 | `render.py` | `final_dir=` 参数,默认 `<work>.parent / "output_final"`,并把 `drafts_dir/images/` 复制到 `<final_dir>/<stem>/images/`(自包含) |
| 3 | `longdoc.py` | `final_dir=` 参数,`_cleaned.md` / `_final.html` 写到 final_dir |
| 4 | `state.py` | `State.final_dir` 字段 + to_dict 同步 |
| 5 | `runner.py` | `StageContext.final_dir / video` 字段 + `run_pipeline(final_dir=, target_video=)` 参数 + `_chapters_wrapper` 调 derive_video_name |
| 6 | `cli.py` | `mtd run --final-dir` / `mtd resume --final-dir` / `mtd status` 显示 final_dir |
| 7 | `gatekeeper.py` | `_resolve_lecture_path` / `_resolve_final_html` 加 final_dir 优先;`gatekeeper_check` 从 `state.final_dir` 读 |
| 8 | `verify.py` | `_check_outputs_exist` / `_check_image_refs` / `verify_pipeline(final_dir=)` 加 final_dir 优先 + 旧布局回退 |

### 2.2 Phase 2:多视频合并模块(~40 min)

| # | 文件 | 改动 |
|---|---|---|
| 9 | 新增 `pipeline/merge_lectures.py` | `merge_lectures(output_final_dir, merged_name=...)` + `discover_lecture_files` + `strip_leading_index` + `MergeResult` |
| 10 | `pipeline/__init__.py` | 注册 `merge_lectures` + 公开 API(MergeResult / merge_lectures / strip_leading_index / derive_video_name) |
| 11 | `cli.py` | `mtd merge <output_final_dir> [--name ...] [--no-html]` |
| 12 | `mcp_server.py` | 工具数 8 → 9:`tool_merge_lectures(output_final_dir, merged_name, no_html)` + INSTRUCTIONS 升级 |

### 2.3 Phase 3:测试(~10 min,期望 559 = 539 + 20)

- 19 个新测试覆盖 `merge_lectures`(strip_leading_index / discover / 自然排序 / 章节重排 / 图片复制 / HTML / manifest)
- `test_merge_lectures_empty_dir_raises` 测试空目录抛错
- `test_render_outputs_html_only_via_write_html_false` 改写 fixture 显式传 final_dir
- `test_chapters_wrapper_registers_provider_in_ctx_metrics` 不再需要 inbox 视频(derive_video_name None 时返回 None)
- `test_cli.py` _patch_runner / _fake_run_pipeline 加 `final_dir / target_video` 形参

### 2.4 Phase 4:文档 + 发布(~10 min)

- `CLAUDE.md §4.1` 拆分为 4.1.1 / 4.1.2 / 4.1.3(中间 vs 最终分离 + 兼容性 + 已有产物保护)
- `CHANGELOG.md` 加 [1.1.0] 节(Multi-video layout + merge)
- `pyproject.toml` version 1.0.1 → 1.1.0(minor bump,breaking layout + 新 feature)
- `tests/test_smoke.py` `test_version_is_1_0_1` → `test_version_is_1_1_0`
- `docs/RELEASE_NOTES_v1.1.0.md`(GitHub Release form 可粘贴)
- 现有产物兜底:`output-w12c/chapters/raw/output_cleaned.md` + `output_final.html`
  → `<video>.parent / output_final/03_全站爆款流程-稳定消耗最重要_{cleaned.md,final.html}`

---

## 3. 关键设计 / 决策

### 3.1 默认新规 + 旧产物只读兼容(用户选项 B)

- 新跑用 `output_final/`,不写旧位置
- `gatekeeper_check` / `verify_pipeline` 从 `state.final_dir` 读最终目录,优先查 final_dir
- 旧产物(只有 `output/chapters/raw/<stem>.md`)仍可被 gatekeeper 旧布局回退读到,不需要迁移脚本

### 3.2 真视频名派生

`derive_video_name(inbox, target_video)`:
- `target_video=None` 时调 `audio.find_media(inbox)`,失败返回 `None`
- 视频 stem 去后缀(`Path.stem`)+ `rstrip()`(用户视频名常含末尾空格,如 `01_先精准后放大 .mp4`)
- 用于:chapters.video 字段 + 最终产物文件名 + render image_prefix

### 3.3 render 自包含布局

新规下 render 把 `drafts_dir/images/` 复制到 `<final_dir>/<stem>/images/`,保证:
- 讲义与图片在同一 `output_final/` 树,整盘复制无 broken link
- `<stem>/images/<file>` 相对路径不变
- 与 W3 既有 layout 一致(只是从 `<drafts_dir>/<stem>/images/` 复制到 `<final_dir>/<stem>/images/`)

### 3.4 多视频合并的章节重排

- 每个视频的 H1 → H2 `## 第一部分:xxx` / `## 第二部分:xxx` ...
- 每个视频的 H2 → H3(降级,避免与 part 标题冲突)
- H3+ 顺延一级
- 第一个视频的章节号 = 全局 1,2,3...;第二个视频接续
- 让读者看到的合并产物像单一讲义,而不是 5 个并列的子讲义

### 3.5 图片路径重写(避免多视频同名冲突)

每张图加 video_stem 前缀:`<video>/<file>` → `<merged>/images/<video>_<file>`
- 例:`01_a/images/gen_0.png` + `02_b/images/gen_0.png`(两个 gen_0.png)
  → `<merged>/images/01_a_gen_0.png` + `<merged>/images/02_b_gen_0.png`
- md-link `![Image](...)` 标准语法 regex 替换
- wiki-link 兼容兜底

### 3.6 序号去除规则

`strip_leading_index(stem)`:
- `r"^\s*(\d+)[_\-\s]+(.*)$"` 匹配 → 提取 `(.*)` 部分并 `strip()`
- 无前缀保留原值(如 `全站运营`)
- 无分隔符(`"03"`)保留原值,避免误删
- 用户视频 `"01_先精准后放大 .mp4"` 末尾空格自动 `rstrip()`

---

## 4. 验证清单

- [x] `merge_lectures.py` 实现(254 行,含 strip_leading_index + discover + 合并 + 图片复制 + chapter 重排)
- [x] chapters.video 字段 = 真视频名(从 inbox 派生)
- [x] render 写到 `output_final/<stem>.md` + `<stem>.html` + `<stem>/images/`
- [x] longdoc 写到 `output_final/<stem>_cleaned.md` + `<stem>_final.html`
- [x] runner 注入 `final_dir` 到 ctx,chapters_wrapper 调 derive_video_name
- [x] cli.py `mtd run --final-dir` / `mtd resume --final-dir` / `mtd merge`
- [x] mcp_server.py 9 工具(W7=6 + W8=2 + W12-D=1 merge)
- [x] gatekeeper / verify 加 final_dir 优先 + 旧布局回退
- [x] pytest 539 → **559 passed** / 0 skipped(+20)
- [x] ruff:All checks passed
- [x] wheel/sdist build OK(130KB + 537KB)
- [x] PyPI v1.1.0 上传 OK
- [x] GitHub Release v1.1.0 + 2 assets SHA256 verified
- [x] commit + push to main + tag v1.1.0
- [x] CLAUDE.md §4.1 拆分更新
- [x] CHANGELOG.md [1.1.0] 节
- [x] docs/RELEASE_NOTES_v1.1.0.md
- [x] 现有产物兜底:`output_final/03_全站爆款流程-稳定消耗最重要_{cleaned.md,final.html}`

---

## 5. v1.0.0 / v1.0.1 / v1.1.0 发布全景

| 平台 | URL | 状态 |
|---|---|---|
| **PyPI v1.0.0** | https://pypi.org/project/media_to_doc/ | ✅ W12-A |
| **PyPI v1.0.1** | https://pypi.org/project/media_to_doc/ | ✅ W12-C |
| **PyPI v1.1.0** | https://pypi.org/project/media_to_doc/ | ✅ W12-D |
| **GitHub Release v1.0.0** | https://github.com/kizemo/media-to-doc/releases/tag/v1.0.0 | ✅ W12-B |
| **GitHub Release v1.0.1** | https://github.com/kizemo/media-to-doc/releases/tag/v1.0.1 | ✅ W12-C |
| **GitHub Release v1.1.0** | https://github.com/kizemo/media-to-doc/releases/tag/v1.1.0 | ✅ W12-D |
| **GitHub Tag v1.0.0 / v1.0.1 / v1.1.0** | pushed to origin | ✅ |

**media-to-doc v1.1.0 GA fully shipped**:
- 11 stage pipeline + 3 调用方式 + LE 五层闭环 + 559 测试
- 多视频支持(input 拆 inbox + output 拆 output/output_final + merge)

---

## 6. 给下一会话的提示

按 task.md §10 / CLAUDE.md §10:

- ✅ A. 上 PyPI(W12-A)
- ✅ B. GitHub release 真实发布(W12-B)
- ✅ E. v1.0.1 patch(W12-C)
- ✅ F. v1.1.0 multi-video layout + merge(W12-D,本次)
- 后续可选:
  - C. Tauri UI v1.1+ Phase 2(1-2 天,3 次点击跑通 + 调用 v1.1.0 Python API)
  - D. NSIS 安装器 v1.2+ Phase 3(1-2 天,Win11 桌面一键安装)
  - 处理 `01_xxx .mp4` / `02_xxx .mp4` 真跑(新视频,W10-A 跑了 03;01 和 02 没跑过)

短期可继续的修缮:
- W11-C §4 标记的 cosmetic warning:`<title>` 与首个 H1 不一致
- `merge_lectures` 加 mermaid 内容合并(目前 mermaid 块直接保留;若跨视频同名冲突需要去重)
- 真跑 01.mp4 / 02.mp4 验证 W12-D layout 在真实场景下不出错