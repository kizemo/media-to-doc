# Handoff — W14-E A+B 收尾 v1.3.0/v1.4.0 release

**日期**:2026-07-23
**承接会话**:用户消息 W14-D v1.3.0/v1.4.0 release 待拍板,A+B+C 三选项
**承接源**:W14-D E2E handoff + 子仓 v1.4.0 frontendDist-only handoff

---

## 全部完成 ✅

| 任务 | 内容 | 验收 | 状态 |
|---|---|---|---|
| A | 子仓 `media-to-doc-ui` v1.4.0 GitHub Release | gh release v1.4.0 已存在(2 assets,SHA256 verified)+ `docs/RELEASE_NOTES_v1.4.0.md` 归档 push | ✅ |
| B | 主仓 `media-to-doc` v1.3.0 PyPI publish + GitHub Release | PyPI v1.3.0 = latest(wheel + sdist 齐全)+ gh release v1.3.0 已存在 + CLAUDE.md §11 commit push | ✅ |

---

## 关键发现(实际状态 vs handoff 描述)

### 子仓 v1.4.0

- **handoff 描述**:`tag v1.4.0 未 push origin` 等拍板
- **实际状态**:`git tag -l` 列出 v1.4.0 + `git ls-remote --tags origin` 显示 origin 已有 `refs/tags/v1.4.0`(指向 `c780654`)
- **结论**:用户 2026-07-22 已 push tag + `gh release create v1.4.0`(2 assets, SHA256 verified)
- **本会话增量**:写 `docs/RELEASE_NOTES_v1.4.0.md`(131 行,与现有 release notes 类似但更详细)+ commit `7cafc6a` + push origin
- **commit**:`7cafc6a docs(release): v1.4.0 — release notes archive for gh release v1.4.0`

### 主仓 v1.3.0

- **handoff 描述**:trust_env 全 provider fix `b283d64 → c5c1fb3` 已 merge,需 bump 1.2.1→1.3.0 + uv publish + gh release
- **实际状态**:
  - `pyproject.toml` version = 1.3.0 ✓
  - `uv.lock` name = media-to-doc version = 1.3.0 ✓
  - CHANGELOG.md 有 [1.3.0] 节 ✓
  - PyPI `latest_version = 1.3.0`,upload_time 2026-07-22T14:48:18 ✓
  - gh release v1.3.0 存在(2026-07-22T14:50:49Z,Latest 标记)✓
  - commit `2f22d0b docs(release): v1.3.0 — trust_env 全 provider 隔离 + 子仓 Tauri UI v1.3.0 协同发布` ✓
- **结论**:用户 2026-07-22 已 publish + release 完毕
- **本会话增量**:`CLAUDE.md` §11 新增 sandbox-verify 章节(24 行,本地 mtd-verify.ps1 + rime-verify.ps1 引用)+ commit `25b47a1` + push origin

---

## 本会话实际改动

### 主仓

| 文件 | 改动 | 备注 |
|---|---|---|
| `CLAUDE.md` | §11 sandbox-verify 章节新增(24 行) | `25b47a1 docs(claude): W14-D — add §11 真机装机验证 sandbox-verify 章节` |
| 主仓 master | `2f22d0b..25b47a1` 推 origin | ✓ |

### 子仓

| 文件 | 改动 | 备注 |
|---|---|---|
| `docs/RELEASE_NOTES_v1.4.0.md` | 新建(131 行) | `7cafc6a docs(release): v1.4.0 — release notes archive` |
| 子仓 master | `8fd49dc..7cafc6a` 推 origin | ✓ |

---

## uv publish 行为观察

- 本会话跑 `uv publish dist/*` 撞 `400 File already exists`(sdist 已存在)
- wheel 也因 sdist fail 退出而退出码 2
- 实际 PyPI 状态:v1.3.0 wheel + sdist 齐全,yanked=False,与本会话 build 产物一致(140344 bytes wheel,690463 bytes sdist)
- **关键教训**:`uv publish` 不幂等,二次 publish 同版本会全部 fail;如果需要重新传,得 `--skip-existing` 或换版本

---

## 测试状态

```
$ uv run pytest
604 passed in 15.68s ✓

$ uv build
Successfully built dist\media_to_doc-1.3.0.tar.gz
Successfully built dist\media_to_doc-1.3.0-py3-none-any.whl ✓
```

ruff:本会话无新代码改动,沿用 W14-D E clean 状态。

---

## 当前 release 全景(2026-07-23)

### PyPI `media-to-doc`(主仓)

| Version | Upload Time | Status |
|---|---|---|
| 1.0.0 | 2026-07-20 | ✓ |
| 1.0.1 | 2026-07-20 | ✓ |
| 1.1.0 | 2026-07-21 | ✓ |
| 1.2.0 | 2026-07-21 | ✓ |
| 1.2.1 | 2026-07-21 | ✓ |
| **1.3.0** | **2026-07-22** | **Latest** ✓ |

### GitHub `kizemo/media-to-doc`(主仓)

| Tag | Created | Status |
|---|---|---|
| v1.0.0 | 2026-07-20 | ✓ |
| v1.0.1 | 2026-07-20 | ✓ |
| v1.1.0 | 2026-07-21 | ✓ |
| v1.2.0 | 2026-07-21 | ✓ |
| v1.2.1 | 2026-07-21 | ✓ |
| **v1.3.0** | **2026-07-22** | **Latest** ✓ |

### GitHub `kizemo/media-to-doc-ui`(子仓)

| Tag | Created | Status |
|---|---|---|
| v1.3.0 | 2026-07-22 | ✓ |
| **v1.4.0** | **2026-07-22** | **Latest** ✓ (frontendDist-only) |

---

## 预算使用

- 活跃时间:~15 分钟
- 剩预算:1h45min(全局 §新会话开局守则 <2h)

---

## 下次会话候选

按用户拍板 **A+B+C**,C 待开始:

### C. 子仓前端 UI 内真触发 run_pipeline

- **范围**:`media-to-doc-ui` src/index.html + JS + Rust commands(已有 run_pipeline Tauri command,W14-C 实装)
- **任务**:
  - 前端 Run tab 添加"选 inbox 子目录 + click 启动"按钮
  - 调用 `invoke('run_pipeline', { inbox_dir, ... })` + 状态轮询
  - 实时进度条 + 当前 stage 标签
  - 取消按钮(已有 `cancel_run` Tauri command)
  - 完成后自动跳 Output tab 显示产物
- **时间**:3-4h(超 <2h 预算,**必须开新会话**)
- **技术债**:
  - 已有 8 commands + 9th read_log(W14-B+2),前端只缺 UI 触发入口
  - run_pipeline 是同步阻塞(长任务),需要 background spawn 模式
- **建议新会话第一句**:承接 `handoff-w14e-ab-complete-2026-07-23.md`,开新会话做 C:子仓前端 UI 真触发 run_pipeline。

### 其他候选(备选)

- D. WiX/MSI installer(Tauri bundler 重试) — 2-3h
- E. LE L3 优化(Prompt 自适应 + 自动重试 + 跨 Agent 经验晋升) — 4-6h
- F. 真实长视频 107min Tauri UI 完整跑 — 6-10h 需多 session

---

## 下次会话第一句

> 承接 `handoff-w14e-ab-complete-2026-07-23.md`,A+B 已完成(子仓 v1.4.0 + 主仓 v1.3.0 release 均已 2026-07-22 publish)。本次会话预算 ~15min 已用,C(子仓前端 UI 真触发 run_pipeline,3-4h)在新会话做。