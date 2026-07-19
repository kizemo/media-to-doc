# handoff-pipeline-w11-gatekeeper-2026-07-19.md — W11-A Gatekeeper vs Verify 一致性修复

> **会话主题**:W11-A 修复 W10-A 顺带发现的 Gatekeeper vs Verify 不一致 bug
> **会话日期**:2026-07-19,~30 分钟
> **会话状态**:**W11-A 主目标完成** ✅ + 测试 519 → 529 + W10-A 真跑产物一致性验证通过

---

## 1. 本次会话目标

承接 `handoff-pipeline-w10-real-LE-verify-2026-07-19.md` §5:Gatekeeper 与 Verify 对同一份数据给出相反结论。修 bug,让两者一致。

---

## 2. Bug 根因

`src/media_to_doc/logger/gatekeeper.py` 两个 resolver 写死了 W4 原型布局,W3+ render + W4 longdoc 早已迁移到新布局:

| Resolver | W4 原型(实际读) | W3+/W4 实际产物布局 |
|---|---|---|
| `_resolve_lecture_path` | `<work>/chapters/raw/<stem>/<stem>.md` | `<work>/chapters/raw/<stem>.md`(drafts_dir parent) |
| `_resolve_final_html` | `<work>/output_final.html` | `<work>/chapters/raw/<stem>_final.html`(drafts_dir parent) |

verify.py 在 W5 (`db92ac9`) 已通过 `_resolve_drafts_dir` + `_check_outputs_exist` 处理双布局,但 gatekeeper 没同步 → **同一份产物,两套结论相反**。

---

## 3. 修复

### 3.1 `_resolve_lecture_path`(gatekeeper.py:25-65)

- 优先 `<work>/chapters/raw/<stem>.md`(W3+ 新布局)
- 回退 `<work>/chapters/raw/<stem>/<stem>.md`(W4 旧布局)
- 都没有 → 返回新布局路径(诊断用,触发 `lecture.md not found`)
- `chapters.json` 不存在 → 返回 `None`

### 3.2 `_resolve_final_html`(gatekeeper.py:68-100)

- 优先 `<work>/chapters/raw/<stem>_final.html`(W4+ 新布局)
- 回退 `<work>/output_final.html`(W4 原型)
- 都没有 → 返回默认诊断路径
- `chapters.json` 缺失时回退旧布局路径(向后兼容)

### 3.3 新增 `_read_video_stem(work)` helper

避免 `_resolve_final_html` 和 `gatekeeper_check` image_refs 重复解析 `chapters.json`。

### 3.4 image_refs 候选路径加第 4 项

W3 render 实际图片位置:images 在 `<stem>/images/` 子目录(drafts_dir 内):

```python
candidates = [
    lecture_dir / ref,                              # 原路径
    lecture_dir / basename,                         # 同目录 basename
    lecture_dir / "images" / basename,              # 旧 images 子目录
    lecture_dir / stem / "images" / basename,       # W3+: <stem>/images/
]
```

---

## 4. 测试覆盖(+10 用例,519 → 529)

| 测试类 | 用例 | 覆盖 |
|---|---|---|
| TestResolvePaths(扩展) | 4 新 | new_layout_no_file / new_layout_exists / old_layout_fallback / chapters_no_video |
| TestGatekeeperNewLayout | 3 | W10-A 布局 PASS / 缺 final html FAIL / image_refs 命中 `<stem>/images/` |
| TestGatekeeperVerifyConsistency | 2 | **核心不变量**:`gatekeeper.ok == verify.overall_passed`(完整产物 / 缺 final html) |

更新:原 `test_resolve_lecture_with_chapters_json` 现期望 new layout 路径(旧 layout fallback 由 `test_resolve_lecture_old_layout_fallback` 独立覆盖)。

---

## 5. W10-A 真跑验证

`E:/resource/2026-01-27_年度复训/output/`(107min 中文培训视频,3h57min 跑完):

```
=== gatekeeper ===
ok: True
passed: [lecture_md_exists, lecture_md_nonempty, lecture_chapter_count,
         final_html_exists, image_refs_valid_no_images]
failed: []
issues: []

=== verify ===
overall_passed: True
failures: []
warnings: [[image_refs] 没有可校验的 markdown (rendered/cleaned 都缺)]

=== CONSISTENCY ===
gatekeeper.ok == verify.overall_passed: True
```

**修复前**:gatekeeper FAIL(找不到 `<stem>.md` + 找不到 `<output_final.html>`),verify PASS。
**修复后**:两者都 PASS。**bug 闭环**。

---

## 6. scripts/_w11a_consistency.py(新)

可复用的 gatekeeper vs verify 一致性手动验收工具:

```bash
uv run python scripts/_w11a_consistency.py <work_dir>
```

退出码:
- `0` — 两边都 PASS(健康)
- `1` — 两边都 FAIL(产物不完整,需关注)
- `2` — 不一致(**bug 回归**,W11-A 修的就是这种)

JSON 输出到 stdout,便于管道 + CI 接入。

---

## 7. 关键设计决策

1. **layout 优先级**:新(W3+,默认)优先 → 旧(W4 原型)回退。新布局是当前主流;旧布局保留兼容但不是首选。
2. **`_resolve_lecture_path` 返回路径而非 None**:即使文件不存在也返回新布局路径(诊断用),让 `gatekeeper_check` 的 `lecture.md not found` 错误信息能展示预期路径。
3. **`_resolve_final_html` 无 chapters.json 时回退旧布局**:保持向后兼容,旧调用方无 chapters.json 时仍能正确工作。
4. **image_refs 加第 4 候选**:W3 render 把 images 写在 `<stem>/images/` 子目录,原 3 候选不够。
5. **TestGatekeeperVerifyConsistency**:W10-A bug 模式的回归测试,任何 layout 变化时这套测试若失败就说明 gatekeeper / verify 又分叉。

---

## 8. 验证 / 回归

```bash
uv run pytest          # 529 passed / 0 skipped(原 519 + W11-A 新增 10)
uv run ruff check      # All checks passed
```

W10-A 真跑产物(`E:/.../output/`):
- `gatekeeper.ok=True`(修复前 False)
- `verify.overall_passed=True`(不变)
- `_w11a_consistency.py` exit 0

---

## 9. 修改文件

```
src/media_to_doc/logger/gatekeeper.py   | 99 +++++++++++--
tests/test_logger/test_gatekeeper.py    | 268 +++++++++++++++++++++++++++++++++-
scripts/_w11a_consistency.py            | (新增,118 行)
3 files changed, 472 insertions(+), 16 deletions(-)
```

---

## 10. W11-A commit

```
d2b39d3 fix(pipeline): W11-A — align gatekeeper path resolution with verify layout
```

Branch:`fix/pipeline-w11-gatekeeper-paths`(基于 W10-A `3ab6f6d`)

---

## 11. 当前状态 / 给下一会话的提示

W11-A 完成,W10-A 三个候选已首个走完。推荐下一会话:

### W11-B v1.0 release prep(2-3h)

按 W10-A handoff §10 推荐顺序:修 bug → release prep → 真质量验收。

- `CHANGELOG.md` — W0-W11 关键 commit 摘要
- `docs/installation.md` — 各 OS / CUDA / CPU / Ollama 步骤
- `pyproject.toml` `[project.urls]` 加 repo / docs
- `uv build` dry-run
- `gh release create v1.0.0 --draft`(本会话可选)

**质量干净 release** —— Gatekeeper 已修,529 测试全过,W10-A 真跑产物一致性验证。

### W11-C 长视频 + 真 LLM 文档质量验收(3-4h)

W11-A 修完后可以让长视频真正跑完整 11 stage + longdoc active 净化 + 看讲师视角讲义质量。

- 用同 03.mp4 跑 `mtd run --longdoc-llm ollama`(真用 LLM 净化)
- 检查 `<stem>_cleaned.md` 净化效果
- 检查 `<stem>_final.html` 排版
- 讲师分发反馈循环

---

## 12. 复杂度提示

W11-A 实际耗时 ~30 分钟,远低于 handoff §10 估算的 1.5-2h:

- bug 根因诊断:`ls` 实际产物布局 → 5 分钟定位
- 修复:`_resolve_lecture_path` + `_resolve_final_html` + image_refs 候选 ~10 行修改
- 测试:10 个新用例 + fixture 重写 ~15 分钟
- W10-A 真跑验证:`_w11a_consistency.py` 跑通 ~5 分钟

主要节省时间因素:
- W10-A handoff 已准确描述现象和方案候选
- `_resolve_drafts_dir` 已存在作为参考实现
- 529 测试基础设施完备,新增测试 boilerplate 极简
