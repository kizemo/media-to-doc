# Release Notes — media-to-doc-ui v1.3.0

**发布日期**:2026-07-22
**子仓 tag**:`v1.3.0`(annotated)
**发布地址**:https://github.com/kizemo/media-to-doc-ui/releases/tag/v1.3.0
**主仓 handoff**:见同目录 `handoff-w14d-*.md`

---

## 亮点

### 1. 8 个 Tauri commands 全部实装(W14-B+ 系列)

| Command | 语义 | 与 MCP 8 工具对齐 |
|---|---|---|
| `list_courses` | 扫描 inbox 课程目录 | ✅ |
| `run_pipeline` | 启动 11 stage pipeline | ✅ |
| `resume_pipeline` | 中断后续跑 | ✅ |
| `cancel_run` | 同步取消(≤2s 超时) | ✅ |
| `check_status` | 读 state.json | ✅ |
| `list_outputs` | 列 output_final 产物 | ✅ |
| `read_lecture` | 读 md/html,优先 W12-D 布局 | ✅ |
| `get_run_metrics` | LE L1 健康度查询 | ✅ |
| `list_runs` | LE 跨 run 健康度 | ✅ |

### 2. 多课程并发(W14-C A)

- `max_concurrent=3`(env override)
- completed LRU 100
- cancel 2s 超时 + kill_tree 兜底
- list_all_runs 混合 running + completed
- 前端 3s global poll + per-run log tail(独立 offset)

### 3. NSIS installer(W14-C B + W14-D 实编译)

- 系统 NSIS 3.12(绕开 Tauri bundler GitHub TLS)
- 装到 `Program Files\MediaToDoc\`
- 桌面 + 开始菜单快捷方式
- `.mtdproj` 文件关联
- Release assets:installer + portable 2 种

### 4. 真跑 30s 测试视频(W14-C E)

- env 三件套(unset proxy + HF_ENDPOINT + HF_HUB_DISABLE_XET)
- audio → asr → frames 完成
- ocr 因合成图无场景变化预期失败(pipeline 基础设施 OK)

---

## Assets

| Asset | Size | SHA256 |
|---|---|---|
| `media-to-doc-1.3.0-setup.exe` | 1,577,388 bytes (1.50 MiB) | `6c96e356cf4e42d4dfe44f8e6658213bd60bbe9beb4be14ce47a884201e8a635` |
| `media-to-doc-1.3.0-portable.exe` | 6,233,600 bytes (5.95 MiB) | `508834a9e8ef9009ecd68979bce34c4fd1aa513ca6fe1c5751414de61e489aad` |

---

## 安装

### Windows(installer,推荐)

1. 下载 `media-to-doc-1.3.0-setup.exe`
2. 管理员运行(perMachine 安装)
3. 装到默认 `C:\Program Files\MediaToDoc\`
4. 桌面 / 开始菜单启动 `media-to-doc`

### Windows(portable,免安装)

1. 下载 `media-to-doc-1.3.0-portable.exe`
2. 双击运行(无需安装)

### 环境配置(必做)

```bash
# 主仓路径
setx MEDIA_TO_DOC_PROJECT "F:\soft\00selfmade\media-to-doc"

# (可选)uv 路径
setx UV_BIN "C:\Users\Duanyi\.local\bin\uv.exe"

# (可选)workspace
setx MEDIA_TO_DOC_WORKSPACE "F:\soft\00selfmade\media-to-doc\workspace"
```

### macOS / Linux

跨平台编译需 Rust 1.97+ + WebKit/GTK 依赖。Tauri 官方文档见 https://tauri.app/start/prerequisites/。

---

## 测试

- **43 cargo test / 0 failed**(W14-C A baseline)
- 8 commands 全部经 cargo test 验证
- 端到端 30s 合成视频 audio/asr/frames 通过

---

## 已知问题

- Rust toolchain 需 1.97+(自带 lld-link 无需 MSVC)
- 公司 VPN 用户构建时需设 `CARGO_NET_TLS_VERIFY=false`(运行不受影响)
- macOS / Linux 编译需用户自查环境
- pip 包 `media_to_doc` 仍是 v1.2.1(主仓独立版本,等 v1.3.x 整合)

---

## 上游

主仓 `media-to-doc` v1.2.1(`pip install media_to_doc` 装的 Python 后端)已发布:
- PyPI:https://pypi.org/project/media-to-doc/
- GitHub:https://github.com/kizemo/media-to-doc/releases/tag/v1.2.1

UI 端调用此 Python 后端做实际 pipeline,UI 自身只做 orchestrator + log tail + 输出展示。