# Handoff — W14-C A:多课程并发(feat commit,等用户拍板)

**日期**:2026-07-22
**分支**:子仓 `media-to-doc-ui` / `feat/w14c-multi-course`(基于 master)
**本会话主目标**:A 多课程并发(完成)→ B/C/E 待拍板

## 全部完成 ✅

| Item | 内容 | 文件 | 测试 |
|---|---|---|---|
| ① | CLAUDE.md §5.6 session-level pre-authorize | 主仓 CLAUDE.md | — |
| ② | ~/.bashrc mtd-dev alias | ~/.bashrc | 验证可解析 |
| A1 | RunRegistry max_concurrent=3 + completed LRU 100 + cancel 2s 超时 | runner.rs | +8 新用例 |
| A2 | run/resume 处理 insert Result + list_all_runs 新命令 | commands.rs | — |
| A3 | lib.rs 注册 list_all_runs + 导出新类型 | lib.rs | — |
| A4 | Run tab 多卡片视图 + 3s poll + per-run log tail | index.html | — (手测) |

**总测试**:43 passed / 0 failed / 0 warnings(baseline 39 + 4 新增)

## 关键设计

### RunRegistry(max_concurrent=3)

```rust
pub struct RunRegistry {
    inner: Arc<Mutex<HashMap<String, ChildEntry>>>,
    max_concurrent: usize,        // env MEDIA_TO_DOC_MAX_CONCURRENT,默认 3
    completed: Arc<Mutex<Vec<CompletedRun>>>,  // LRU 100
}
```

**insert() 返回 `Result<(), String>`**:
- 超并发上限 → kill 刚 spawn 的进程 + 返回错误
- 成功 → 存 registry + spawn 后台监控(tokio::spawn)

**后台监控**:
- 插入 registry → 释放锁 → tokio::spawn 等 child.wait()
- 子进程退出 → g.remove(&wd) → push_completed
- 若 cancel 已拿走 child → remove 返回 None → 直接 return(不双写)

**cancel() 2s 超时**:
- child.kill() → tokio::time::timeout(2s, child.wait())
- 超时 → kill_tree(taskkill /T /F) 兜底
- 一律 push_completed(status="cancelled")

### list_all_runs(新命令)

返回 `runs: Vec<RunStatusInfo>`(running + completed 混合,按 started_at 降序)
+ `max_concurrent` + `active_count`。

前端调用这个渲染多卡片;每 3 秒刷新。

### 前端多卡片

- `state.activeRuns: Map<work_dir, {logPath, logOffset}>`
- 3s `setInterval` 调 `list_all_runs` → 渲染卡片 + 清理已完成的 activeRuns
- 每卡独立 `read_log(offset)` tail
- 停止条件:`activeRuns.size === 0` → clearInterval

## Round 2 Rust Review 结论

- ✅ 并发上限检查正确(insert reject + kill spawned child)
- ✅ cancel vs monitor 竞争安全(双 remove 互斥,不会双写 completed)
- ✅ monitor 不持锁 wait(无死锁)
- ✅ `#[derive(Default)]` 已移除(防 max_concurrent=0 latent bug)
- ✅ 43 测试全过

## 待用户拍板

按 pre-authorize 规则:A(feat) → 写 handoff 等拍板。B/C/E 待用户确认后执行:

- **B**(release build + NSIS 安装器):`F:/soft/00selfmade/media-to-doc-ui/` 上 `cargo tauri build` + NSIS bundler 配置
- **C**(合并 master + v1.3.0 release):merge `feat/w14c-multi-course` → master + tag + GitHub release
- **E**(真实端到端 30s demo):用短 demo 视频在 Tauri UI 内跑 11 stage

## 文件索引

| 文件 | 路径 | 改动 |
|---|---|---|
| CLAUDE.md | `F:\soft\00selfmade\media-to-doc\CLAUDE.md` | +§5.6 pre-authorize(已 commit `8a916db`) |
| runner.rs | `media-to-doc-ui/src-tauri/src/runner.rs` | +max_concurrent + LRU + monitor + cancel 2s |
| commands.rs | `media-to-doc-ui/src-tauri/src/commands.rs` | insert Result + list_all_runs |
| lib.rs | `media-to-doc-ui/src-tauri/src/lib.rs` | list_all_runs 注册 + 导出 |
| index.html | `media-to-doc-ui/src/index.html` | 多卡片 Run tab + per-run log tail |

## 下次会话第一句

> 承接 `handoff-w14c-multi-course-2026-07-22.md`,A 多课程并发完成(43 test / 0 failed / 0 warn),feat commit 等拍板。B/C/E 待确认后继续。
