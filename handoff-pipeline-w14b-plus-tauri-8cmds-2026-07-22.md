# Handoff — W14-B+:Tauri 8 commands 全部实装 + Cargo SSL 撞墙破解

**日期**:2026-07-22
**承接会话**:`media-to-doc` / `media-to-doc-ui` 的 `feat/w14b-plus-8-commands` 分支
**本会话主目标**:
- A. W14-B+ 首次 `cargo tauri dev` 跑通(可换网络或 vendor dependencies)
- B. 实装 8 个 Tauri commands

## 全部完成 ✅

| Task | 内容 | Commit | 测试 |
|---|---|---|---|
| T1 | Cargo SSL 撞墙破解 + 全套 Tauri 2 图标 | `a1a81bd` | 1/1 |
| T2 | 4 个只读 FS commands(list_courses / check_status / list_outputs / read_lecture) | `33c412d` | 16/16 |
| T3 | 4 个子进程 commands(run_pipeline / resume_pipeline / cancel_run / list_running) | `cb73825` | 26/26 |
| T4 | 2 个 Python API bridge + probe(get_run_metrics / list_runs / probe) | `cb73825` | 30/30 |
| T6 | app_info 接 probe() 真实探测 | `bf002f8` | 30/30 |
| T5 | 前端 5 tab SPA 布局(部分,日志 tail 留 W14-B+2) | `03ecde6` | — |

**总测试**:30 passed / 0 failed(binary 12.5MB debug)

## T1 关键破解:Cargo SSL

**症状**:公司 VPN proxy 对 crates.io sparse HTTPS 做 MITM,schannel 不信 proxy 证书。
`cargo build` 反复 `SSL connect error (schannel: failed to receive handshake)`。

**撞墙链路(全试过)**:
- ❌ `replace-with = 'rsproxy-sparse'`(原配置)
- ❌ `replace-with = "my-crates-io"` + `registry = "https://github.com/rust-lang/crates.io-index"`(cargo 报"source defines source registry crates-io",URL 是 canonical 不允许 redefine)
- ❌ `registry = "git+https://github.com/rust-lang/crates.io-index"`(cargo 1.97 不剥 `git+` 前缀,git fetch 报 `remote-git+https` 非法)
- ❌ `registry = "https://github.com/rust-lang/crates.io-index.git"`(加 `.git` 后缀,cargo 仍认 canonical)

**最终解**:**default crates-io(不 replace) + `CARGO_NET_TLS_VERIFY=false` 环境变量**。
- handoff 文档说"CARGO_NET_TLS_VERIFY=false 不 work",实测对 default crates-io **work**;
- handoff 文档说"5 种候选任一可",**第 6 种才是最简**:不改 config,只设 env var。

**实操**(每个新 shell 都要做):
```bash
export PATH="/c/Users/Duanyi/.cargo/bin:$PATH"  # cargo 装在 ~/.cargo/bin 但默认 PATH 不含
cd "F:/soft/00selfmade/media-to-doc-ui/src-tauri"
CARGO_NET_TLS_VERIFY=false cargo build
```

**为什么 user-level `~/.cargo/config.toml` 改成无 replace**:原配置 `replace-with = 'rsproxy-sparse'` 强制 sparse,加 env var 没用(已经被强制走 sparse)。改回 default crates-io,让 env var 在 default 路径生效。

**icons**:`cargo tauri icon src-tauri/icons/icon.png` 一键生成全套 Tauri 2 图标(.ico / .icns / iOS / Android / 多分辨率)。

## T2 设计:`CommandResponse<T>` 统一返回壳

**8 个 command 都返回**:
```rust
#[derive(Serialize)]
pub struct CommandResponse<T: Serialize> {
    pub ok: bool,
    pub data: Option<T>,
    pub error: Option<String>,
}
```

**为什么不用 Tauri 推荐的 `Result<T, E>`**:我们的 spec(ARCHITECTURE.md)统一 shape,前端 try/catch 后还要看 error message;`Result<T, String>` 把 error 走 IPC 错误通道,前端拿不到 error string,只能 catch。

**测试覆盖**(16 个):
- `CommandResponse::ok/err` JSON shape
- SUPPORTED_EXTS 大小写不敏感
- list_courses 空 inbox / 有子目录 + 媒体
- check_status 缺 state.json / 正常 parse
- list_outputs 分组(raw/cleaned/final/images/manifests)
- read_lecture 非法 version / html 缺失 fallback 到 md
- PathExpand ~/ 展开 / 绝对路径不变

## T3 关键设计:OnceCell<RunRegistry> 绕开 Tauri 2 限制

**撞墙**:Tauri 2 要求 `async` command + `State` 参数必须返回 `Result<T, E>`。
但我们想返回 `CommandResponse<T>` 保持统一 shape。

**解**:`once_cell::sync::Lazy<RunRegistry>` 全局单例,async command 不接 `State` 参数,直接 `global_registry()` 拿引用。

```rust
static REGISTRY: Lazy<RunRegistry> = Lazy::new(RunRegistry::new);
pub fn global_registry() -> &'static RunRegistry { &REGISTRY }
```

**子进程管理**:
- `tokio::process::Command` spawn `uv --project X run mtd run <inbox>`
- stdout + stderr 合并写 `<work_dir>/mtd.log`(用 `Stdio::from(file)` 同步句柄 OK)
- `kill_on_drop(true)` Tauri 退出时自动清理
- cancel_run:`tokio Child::kill()` + Windows `taskkill /T /F /PID` 兜底杀进程树
- 拒绝同 work_dir 并发跑(registry 里已有 → 返回 err)

**环境变量**:
- `MEDIA_TO_DOC_PROJECT`:`media-to-doc` Python 项目根(默认 sibling 探测)
- `UV_BIN`:`uv` binary 路径(默认 PATH 找)
- `MEDIA_TO_DOC_WORKSPACE`:workspace root(默认 `~/Documents/media-to-doc`)

## T4 关键设计:`uv run python -c "<script>"` 一次性

每个 Python API command 拼一个一行 Python,stdin 不传,argv 传参,stdout 拿 JSON:

```python
import json, sys
from media_to_doc.llm.health import get_run_metrics
print(json.dumps(get_run_metrics(sys.argv[1])))
```

**为什么这样**:
- 不引入 PyO3 / maturin(编译时间爆炸)
- 复用已发布的 `media-to-doc` pip 包(隔离干净)
- stdout JSON 解析简单,失败 stderr 看错

**probe.py 一次拿三项**:
```python
import media_to_doc; v = media_to_doc.__version__
try: from media_to_doc.llm.health import get_run_metrics, list_runs; api = True
except: api = False
try: from media_to_doc.mcp_server import main; mcp = True
except: mcp = False
print(json.dumps({"version": v, "api": api, "mcp": mcp}))
```

## T5 简版前端(W14-B+2 完整)

**已做**(单文件 `src/index.html` 482 行 vanilla TS):
- 单 SPA + 200px 侧边栏 + 48px header
- 5 tab:Inbox / Run / Output / Health / Learn
- Inbox:workspace_root 输入 + Refresh → list_courses 渲染
- Run:inbox 选中 → LLM/imagegen/stop_after 选项 → run_pipeline / cancel_run
  + 5s poll check_status 渲染 11-stage grid
- Output:list_outputs 分组显示
- Health:get_run_metrics + list_runs JSON dump
- Learn:app_info 真实探测(走 T6 probe)
- Toast 通知

**未做**:
- 真实 mtd.log tail(需要 tauri-plugin-fs 或后端 read_file command)
- read_lecture modal 渲染 md/html
- 多课程并发
- 系统托盘 + 通知
- NSIS 装包

## T6 app_info 真实探测

`app_info()` 改 `async`,内部 `python_bridge::probe().await` 拿探测结果。
返回结构新增:
- `media_to_doc_project: String`(探测的路径,失败时也有)
- `probe_error: Option<String>`(失败时可读消息)

## 文件索引

| 文件 | 路径 | 说明 |
|---|---|---|
| Cargo manifest | `media-to-doc-ui/src-tauri/Cargo.toml` | + tokio + once_cell |
| Commands | `media-to-doc-ui/src-tauri/src/commands.rs` | 8 commands + helpers(750+ 行) |
| Runner | `media-to-doc-ui/src-tauri/src/runner.rs` | SpawnSpec / RunRegistry / spawn / kill |
| Python bridge | `media-to-doc-ui/src-tauri/src/python_bridge.rs` | probe / get_run_metrics / list_runs |
| Types | `media-to-doc-ui/src-tauri/src/types.rs` | CommandResponse + derive_stem + SUPPORTED_EXTS |
| Lib | `media-to-doc-ui/src-tauri/src/lib.rs` | module decl + invoke_handler |
| Frontend | `media-to-doc-ui/src/index.html` | 5 tab SPA(vanilla) |
| Gitignore | `media-to-doc-ui/.gitignore` | + `.cargo/`(本机 SSL workaround) |
| Cargo config | `C:/Users/Duanyi/.cargo/config.toml` | 改回 default(无 replace) |

## W14-B+2 下次会话

**目标**:补完 T5(真实 mtd.log tail / read_lecture modal / 多课程并发 / 系统托盘)。

**W14-B 完整 v1.3 估时**:剩余 3-4h,本会话已用 ~95min。

**Cargo SSL 备忘**(下次开新 shell 必做):
```bash
export PATH="/c/Users/Duanyi/.cargo/bin:$PATH"
cd "F:/soft/00selfmade/media-to-doc-ui/src-tauri"
CARGO_NET_TLS_VERIFY=false cargo build
```

或写进 `~/.bashrc` / `scripts/dev.sh`。

## 分支与 commit

`feat/w14b-plus-8-commands` 分支(W14-B+ 全部 6 commit):
```
03ecde6 feat(ui): W14-B+ T5 部分 — 5 tab SPA 布局(单文件 vanilla)
bf002f8 feat(ui): W14-B+ T6 — app_info 接 probe() 真实探测
cb73825 feat(ui): W14-B+ T3+T4 — 子进程管理 + Python API bridge(8/8 commands)
33c412d feat(ui): W14-B+ T2 — 4 个只读 FS Tauri commands
a1a81bd build(ui): W14-B+ — 解决 Cargo SSL + 全套 Tauri 2 图标就位
839a95f feat(ui): W14-B — Tauri 2 desktop shell 启动骨架 (media-to-doc-ui)
```

**memory 更新建议**:
- `feedback_proxy_env_pollution.md` 加 Tauri 验证:`CARGO_NET_TLS_VERIFY=false` 对 default crates-io work,documented as "sparse 不 work,default work"
- 新增 `feedback_tauri_async_state.md`:`async fn` + `State` 必须返回 `Result<T, E>`,用 `once_cell::Lazy` 绕开

## 下次会话第一句

> 承接 W14-B+ `handoff-pipeline-w14b-plus-tauri-8cmds-2026-07-22.md`,补完 T5(真实 mtd.log tail / read_lecture modal / 系统托盘 / NSIS 装包),然后 merge `feat/w14b-plus-8-commands` 到 `master`。
