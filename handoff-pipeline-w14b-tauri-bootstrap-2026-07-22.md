# Handoff — W14-B:trust_env=False + Tauri UI 启动骨架

**日期**:2026-07-22
**承接会话**:`media-to-doc` release/v1.0
**本会话主目标**:
- A. 修 OllamaProvider `trust_env=False`(W13-C 仅修了脚本侧,代码层更彻底)
- B. Tauri UI(Phase 2 / v1.3)启动

## A 完成 ✅ — `427d963 fix(llm): W14-B — OllamaProvider._ensure_client 透传 trust_env=False`

**改动**:
- `src/media_to_doc/llm/ollama.py`:`_ensure_client` 构造 `ollama.Client(host, trust_env=False)`,把 `trust_env=False` 透传给内部 httpx,httpx 不再读 `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` 等环境变量,localhost:11434 调用直连不被公司 VPN 父 shell 劫持
- `tests/test_llm/test_ollama.py`:+3 用例
  - `test_ensure_client_passes_trust_env_false_to_ollama_sdk`:拦截 `ollama.Client`,断言 kwargs 含 `trust_env=False`
  - `test_ensure_client_unaffected_by_proxy_env_vars`:设 8 个 proxy env vars,验证 `_ensure_client` 不抛 SSL/proxy 错
  - `test_ensure_client_idempotent_after_first_init`:回归保护(防止重复构造)

**测试**:595 → **598 passed** / 0 skipped / ruff clean

**为什么不在 anthropic/openai_compat 加**:严格按用户"修 OllamaProvider"指令,只动一处。anthropic SDK 0.117 接受 `http_client: httpx.Client` 自定义 client,openai SDK 同,二者都可后续加 `trust_env=False` 自定义 client,留 W14-B+ follow-up。

**memory 更新建议**:把 feedback `feedback_proxy_env_pollution.md` 第 45 行的"W14-B+ 候选"标注改为"✅ W14-B 已实装,anthropic/openai_compat 留 W14-B+ follow-up"。

## B 启动(不完整) 🔄 — Tauri UI 骨架在 `F:/soft/00selfmade/media-to-doc-ui/`

**已完成**:
- **工具链就位**(本机全局):
  - `winget install Rustlang.Rustup` → rustc 1.97.1 / cargo 1.97.1(默认 stable MSVC toolchain;Rust 1.97 自带 `lld-link`,**无需 MS Build Tools**)
  - `curl -sL https://github.com/tauri-apps/tauri/releases/download/tauri-cli-v2.11.4/cargo-tauri-x86_64-pc-windows-msvc.zip` → `~/.cargo/bin/tauri.exe`(7.4MB,2min 下载)
  - 验证:`tauri --version` = `tauri-cli 2.11.4`
- **Cargo mirror 配置**:`~/.cargo/config.toml`:rsproxy.cn sparse + git-fetch-with-cli
- **项目骨架**(独立 repo `media-to-doc-ui`,独立 git 仓):
  ```
  F:/soft/00selfmade/media-to-doc-ui/
  ├── src-tauri/
  │   ├── Cargo.toml          (tauri 2 + serde)
  │   ├── build.rs
  │   ├── tauri.conf.json     (productName=media-to-doc, identifier=com.duanyi.mediatodoc)
  │   ├── src/main.rs + lib.rs  (2 commands: app_info, ping)
  │   ├── capabilities/default.json  (core:default)
  │   └── icons/icon.png      (32x32 占位)
  ├── src/index.html          (vanilla HTML+CSS+JS,IPC 调用 backend)
  ├── README.md
  ├── ARCHITECTURE.md         (10 节设计:进程模型 / 8 commands / 子进程 / 错误处理 / NSIS)
  └── .gitignore
  ```
- **commit**: `839a95f feat(ui): W14-B — Tauri 2 desktop shell 启动骨架 (media-to-doc-ui)`

**未完成 / 下次会话继续**:
- **`cargo tauri dev` 未跑**(撞公司 VPN HTTPS MITM,Cargo sparse 拉 Tauri 数百个依赖 crate 时 `SSL connect error`)
- 8 个 Tauri commands 未实装(仅 `app_info` + `ping` 2 个 demo,W14-B+ 接着实装)
- 系统托盘 + 进度条 UI 未做
- NSIS 装包未做(Phase 3)

## 关键设计决策(继承 + W14-B 新增)

### Tauri vs Electron
CLAUDE.md §10 已定 Tauri。理由(README + ARCHITECTURE.md):
- 运行时小(~10MB vs Electron ~150MB)
- 后端用 Rust(可直接 spawn `mtd` 子进程,无 Node 层)
- 系统 Edge WebView2 复用,无需打包 Chromium

### 进程模型(ARCHITECTURE.md §1)
- 1 个 Rust 主进程 + 1 个 WebView2 + N 个 mtd 子进程
- IPC: Tauri JSON-RPC(走 named pipe / 共享内存)
- 单实例锁:`tauri-plugin-single-instance`(W14-B+)

### 8 个 Tauri commands(ARCHITECTURE.md §2)
对齐 media-to-doc MCP 8 工具(W7+W8):
1. `list_courses(root)` — 读目录
2. `run_pipeline(inbox, opts)` — spawn `uv run mtd run`(后台,立即返回 work_dir)
3. `check_status(work_dir)` — 读 state.json
4. `list_outputs(inbox)` — 读 output_final/
5. `read_lecture(inbox, version, fmt)` — 读 .md / .html
6. `get_run_metrics(work_dir)` — 调 media_to_doc Python API
7. `list_runs(workspace, limit)` — 同上
8. `cancel_run(work_dir)` — kill subprocess(taskkill /T /F)

### 子进程管理(ARCHITECTURE.md §3)
- `run_pipeline` 立即返回,后台 spawn
- `tokio::process::Command` + `Child` handle → `tauri::State<RunRegistry>`
- 启动时 attach 上次未完成 run(state.json 标记)

### 进度监控(ARCHITECTURE.md §4)
双轨(继承 LE 设计):
- `state.json` 轮询(5s)
- `mtd.log` 实时转发到前端

## 网络环境栈(W14-B 实测)

**撞墙链路**(全试过):
- ❌ `cargo install tauri-cli`(crates.io sparse HTTPS,被 MITM 拦)
- ❌ `npm install -g @tauri-apps/cli`(ECONNRESET,大文件传输中断)
- ❌ `winget install` 下载 rustup-install.exe 后 `cargo install`(同上)

**成功路径**:
- ✅ `winget install Rustlang.Rustup` → rustup-init 自动装 stable toolchain
- ✅ 直接下 GitHub release zip(`curl -sL .../cargo-tauri-x86_64-pc-windows-msvc.zip`)+ unzip + cp
- ✅ 配置 `~/.cargo/config.toml` 用 rsproxy.cn 镜像(为 `cargo build` 准备)

**Cargo SSL 修复候选(W14-B+ 未做,等首次 cargo build 时再决定)**:
- `CARGO_NET_TLS_VERIFY=false`(已试,sparse 不走 cargo 控制,在 schannel 层拦)
- 公司根证书导入 Windows Trusted Root
- `cargo vendor` 预下载(复杂)
- 换网络环境(脱离 VPN)
- 切到 `git+https://github.com/rust-lang/crates.io-index` 而非 sparse(走 git protocol)

## 下次会话第一句

> 承接 W14-B `handoff-pipeline-w14b-tauri-bootstrap-2026-07-22.md`,完成 Tauri 首次 `cargo tauri dev` 跑通(可换网络或 vendor dependencies),然后实装 8 个 Tauri commands。

## 预算与时间

- 本会话已用 ~80min(< 2h 预算)
- 主要耗时:Rust 安装 + SSL 撞墙诊断 + 预编译 binary 下载(2min) + 写文档 + commit
- 后续:`cargo tauri dev` 首次构建预计 5-15min(若 SSL 解决)
- 实装 8 commands + UI 组件预计 4-6h
- NSIS 装包预计 2-3h
- **总 v1.3 估 8h+**,需 3-4 个会话

## 文件索引

| 文件 | 路径 | 说明 |
|---|---|---|
| 主仓 CLAUDE.md | `F:/soft/00selfmade/media-to-doc/CLAUDE.md` | §10 已更新(W14-B 标注) |
| 主仓 commit A | `427d963 fix(llm): W14-B — OllamaProvider._ensure_client 透传 trust_env=False` | release/v1.0 |
| Tauri UI repo | `F:/soft/00selfmade/media-to-doc-ui/` | 独立 git repo |
| Tauri UI commit | `839a95f feat(ui): W14-B — Tauri 2 desktop shell 启动骨架` | local only,未 push |
| Rust toolchain | `~/.cargo/bin/{cargo,rustc,tauri}.exe` | 1.97.1 + 2.11.4 |
| Cargo mirror | `~/.cargo/config.toml` | rsproxy.cn sparse |