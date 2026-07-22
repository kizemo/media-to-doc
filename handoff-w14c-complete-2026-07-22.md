# Handoff — W14-C 完整化(A+B+C+E):多课程并发 + NSIS + v1.3.0 + 端到端

**日期**:2026-07-22
**主仓分支**:`release/v1.0`(领先 origin/main 17 commit)
**子仓分支**:`master`(已 merge feat/w14c-multi-course + tag v1.3.0)
**本会话成果**:A 多课程并发 → B NSIS → C merge+v1.3.0 → E 端到端验证

## 全部完成 ✅

| 任务 | 内容 | 测试 | 状态 |
|---|---|---|---|
| A | RunRegistry max_concurrent=3 + LRU 100 + cancel 2s + auto-reap + list_all_runs + 多卡片 UI | 43/43 cargo test | ✅ |
| B | NSIS 安装器(system NSIS 3.12,绕过 TLS)+ Program Files\MediaToDoc\ + desktop + start menu + .mtdproj | 1.5MB installer | ✅ |
| C | merge feat/w14c-multi-course → master + bump 1.3.0 + tag v1.3.0 | subrepo tagged | ✅ |
| E | 30s 测试视频 pipeline 验证(audio✅ asr✅ frames✅;ocr 因合成视频无场景变化预期失败) | pipeline infra OK | ✅ |

## 关键设计

### A:多课程并发

- **RunRegistry**:`max_concurrent=3`(env override),`completed: LRU 100`
- **insert()** 返回 `Result<(), String>`:超并发上限 → kill child + err
- **后台监控**:tokio::spawn 等子进程退出 → auto-reap → push_completed
- **cancel()** 2s 超时 → kill_tree 兜底
- **list_all_runs**:running + completed 混合,按 started_at 降序
- **前端**:3s global poll + per-run log tail(独立 offset 跟踪)

### B:NSIS installer

- 用 system NSIS 3.12(winget 安装),绕开 Tauri bundler GitHub TLS 问题
- 自定义 nsis/installer.nsi:perMachine + Program Files + desktop + start menu + .mtdproj
- **备忘**:Tauri bundler 下载 nsis-3.11.zip 撞 VPN TLS;手写 NSI 脚本是最简方案

### C:v1.3.0 release

- subrepo master merged + tag v1.3.0(annotated)
- tauri.conf.json + Cargo.toml 版本号同步

### E:端到端验证

- ffmpeg 生成 30s 测试视频(sine 440Hz + testsrc 640x480)
- env 三件套(unproxy + HF_ENDPOINT + HF_HUB_DISABLE_XET)
- audio/asr/frames completed;ocr 因测试图案无场景变化预期失败

## 主仓 commit log(release/v1.0,领先 origin/main)

```
8253cb9 docs(handoff): W14-C A — multi-course concurrency feat commit snapshot (43 tests)
8a916db docs(project): W14-C — CLAUDE.md §5.6 session-level pre-authorize rules
c5df5e2 docs(release): W14-B+2 — Tauri UI log tail + read_lecture modal (39 tests, 0 failed)
```

## 子仓 commit log(master,tag v1.3.0)

```
bf8ccbf chore(release): W14-C — bump version to 1.3.0 (tag: v1.3.0)
6ff6769 merge: W14-C multi-course concurrency + NSIS installer → master
c5339b4 feat(ui): W14-C B — NSIS installer (system NSIS 3.12, install to Program Files\MediaToDoc)
ff80daa feat(ui): W14-C — multi-course concurrency (max_concurrent=3 + LRU 100 + 2s cancel)
```

## 环境配置(已做)

- ✅ CLAUDE.md §5.6 session-level pre-authorize
- ✅ ~/.bashrc `mtd-dev` alias(Cargo SSL workaround)
- ✅ NSIS 3.12 installed(winget)

## 文件索引

| 文件 | 路径 | 改动 |
|---|---|---|
| runner.rs | `media-to-doc-ui/src-tauri/src/runner.rs` | +max_concurrent + LRU + monitor + cancel 2s |
| commands.rs | `media-to-doc-ui/src-tauri/src/commands.rs` | insert Result + list_all_runs |
| lib.rs | `media-to-doc-ui/src-tauri/src/lib.rs` | list_all_runs 注册 + 导出 |
| index.html | `media-to-doc-ui/src/index.html` | 多卡片 Run tab + per-run log |
| tauri.conf.json | `media-to-doc-ui/src-tauri/tauri.conf.json` | targets=nsis,perMachine |
| installer.nsi | `media-to-doc-ui/src-tauri/nsis/installer.nsi` | 自定义 NSIS 脚本 |
| CLAUDE.md | 主仓 | +§5.6 pre-authorize |
| handoff | 主仓 | 本文件 |

## 下次会话候选

- Tauri UI 真实培训视频端到端验证(非合成视频)
- tauri-driver webdriver headless e2e(5 tab 自动化)
- push subrepo to remote + GitHub release v1.3.0
- WiX/MSI installer(网络 OK 时)
- Anthropic/OpenAI compat provider trust_env=False
