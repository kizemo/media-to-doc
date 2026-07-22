# W14-D Design — Tauri UI v1.3.0 GitHub Release + 全 Provider trust_env=False

**日期**:2026-07-22
**会话承接**:handoff-w14c-complete-2026-07-22.md(W14-C 全完成)
**主仓分支**:`release/v1.0`(领先 origin/main 19 commit)
**子仓分支**:`master`(已 tag v1.3.0,未推 origin,无 remote)

---

## 0. 目标(用户拍板)

W14-C 的下一步候选里,用户选择 **C+E 组合**(~1.5h):

- **C 推子仓 v1.3.0 GitHub Release** — push `kizemo/media-to-doc-ui` 仓到 GitHub + gh release v1.3.0 + 2 assets(NSIS installer + Tauri portable)
- **E 全 provider trust_env=False** — 仿 W14-B OllamaProvider 模式,补全 AnthropicProvider + OpenAICompatProvider 透传 `trust_env=False`,防止公司 VPN 父 shell 劫持到代理并触发 SSL 失败

> 用户在 A 候选的"真实视频源"问题答了"复用 W13-A 01.mp4 截短",是为下次会话预留,本会话不跑 A。

---

## 1. C 部分 — 推子仓 v1.3.0 Release

### 1.1 关键现状(已 verify)

| 项 | 状态 |
|---|---|
| 子仓路径 | `F:/soft/00selfmade/media-to-doc-ui/`(独立 git repo) |
| 子仓 branch | `master`,working tree clean |
| 子仓 tag | `v1.3.0`(annotated,W14-C C 阶段打的)+ `v1.3.0-alpha` |
| 子仓 remote | **未配置** — `git remote -v` 无输出 |
| Rust 编译产物 | `target/release/media-to-doc-ui.exe` 已存在(6.2MB,W14-B+2 build 出来) |
| NSIS installer | **未编译** — handoff 说 1.5MB,实际 `dist/` 不存在;installer.nsi 已写但 W14-C B 跳过了实编译 |
| `installer.nsi` 引用 `LICENSE.txt` | 子仓只有 `LICENSE`(无后缀),NSIS 编译会 fail — 需在 `src-tauri/nsis/` 下提供 LICENSE.txt |
| `gh` CLI 认证 | `kizemo` 账号已登录,token `ghp_***`,HTTPS 协议 |
| 主仓 origin | `git@github.com:kizemo/media-to-doc.git`(SSH,与子仓同 owner) |

### 1.2 子流程(8 步,~40min)

1. **建 LICENSE.txt**(本地 fix) — `cp LICENSE src-tauri/nsis/LICENSE.txt`(~5s)
2. **建 remote** — `git -C media-to-doc-ui remote add origin git@github.com:kizemo/media-to-doc-ui.git`(~5s,沿用主仓 SSH 协议)
3. **建 GitHub 仓** — 两种方式:
   - **a)** Web UI 手动(用户拍板时已确认 `kizemo/media-to-doc-ui` 不存在 → 用户创建)
   - **b)** `gh repo create kizemo/media-to-doc-ui --public --description "media-to-doc Tauri 2 desktop shell" --source=.`(~10s,推荐)
4. **push master** — `git push -u origin master`(~10s,可能撞 VPN SSH,沿用主仓 W12-B 经验)
5. **push tag** — `git push origin tag v1.3.0`(~5s,tag 必带)
6. **NSIS 编译** — `"/c/Program Files (x86)/NSIS/makensis.exe" src-tauri/nsis/installer.nsi`(~30s,生成 `target/release/bundle/nsis/media-to-doc-1.3.0-setup.exe` ~1.5MB)
7. **复制 portable** — `cp target/release/media-to-doc-ui.exe target/release/bundle/media-to-doc-1.3.0-portable.exe`(~2s)
8. **gh release create v1.3.0** — `gh release create v1.3.0 target/release/bundle/media-to-doc-1.3.0-setup.exe target/release/bundle/media-to-doc-1.3.0-portable.exe --generate-notes --title "media-to-doc-ui v1.3.0"`(~15s)

### 1.3 Release notes 草稿(gh release form 可用,中文)

> 摘自:8 commands 实装(W14-B+)+ multi-course 并发(W14-C A)+ NSIS installer(W14-C B)+ v1.3.0 tag(W14-C C)
>
> **media-to-doc-ui v1.3.0** — Tauri 2 桌面壳首次稳定版
>
> ## 亮点
> - **8 个 Tauri commands 全部实装**:`list_courses` / `run_pipeline` / `resume_pipeline` / `cancel_run` / `check_status` / `list_outputs` / `read_lecture` / `get_run_metrics` / `list_runs`,与 MCP 8 工具语义对齐
> - **多课程并发**:`max_concurrent=3`(env 可调)+ LRU 100 + cancel 2s 超时 + auto-reap + 3s 前端 poll
> - **log tail 按 run_id 分桶**:前端 per-run 独立 offset 跟踪,2s 轮询真实 mtd.log
> - **marked@12.0.0 CDN(SRI 锁版本)**:lecture modal 渲染稳定
> - **NSIS installer**:`Program Files\MediaToDoc\` + desktop + start menu + .mtdproj 关联;Release assets 提供 installer 和 portable 两种形态
>
> ## 测试
> - **43 cargo test / 0 failed**(W14-C A baseline)
> - **跨平台**:Windows 11 验证;macOS / Linux 编译需 Rust 1.97+ 用户自查
>
> ## 安装
> 1. 下载 `media-to-doc-1.3.0-setup.exe`(~1.5MB,推荐,需管理员)
> 2. 或下载 `media-to-doc-1.3.0-portable.exe`(~6.2MB,免安装便携)
> 3. 设置 `MEDIA_TO_DOC_PROJECT=F:/soft/00selfmade/media-to-doc` 环境变量
> 4. 启动后 Inbox 选择课程目录,3 次点击跑通 pipeline
>
> ## 已知问题
> - Rust toolchain 需 1.97+(自带 lld-link 无需 MSVC)
> - 公司 VPN 用户需设 `CARGO_NET_TLS_VERIFY=false`(构建侧,不影响运行)

### 1.4 错误处理

| 风险 | 应对 |
|---|---|
| `gh repo create` 撞 GitHub API rate limit | 重试一次;不行就改为 Web UI 手动建 + `git remote add` |
| SSH push 撞 VPN | 切 HTTPS + PAT(主仓 W12-B 验证过) |
| NSIS 编译失败 | 检查 `LICENSE.txt` 是否就位;查 makensis 日志行号 |
| `target/release/bundle/nsis/` 路径不存在 | 已 mkdir,可重做 |

### 1.5 验收

- [ ] `https://github.com/kizemo/media-to-doc-ui` 仓存在且 master 推到 origin
- [ ] `v1.3.0` tag 推到 origin
- [ ] `gh release view v1.3.0` 显示 2 assets 且 SHA256 正确
- [ ] Release URL `https://github.com/kizemo/media-to-doc-ui/releases/tag/v1.3.0` 可访问
- [ ] `docs/RELEASE_NOTES_v1.3.0.md`(主仓 docs/,不在子仓)记录本会话发布动作

---

## 2. E 部分 — Anthropic + OpenAICompat trust_env=False

### 2.1 现状(已 verify)

- `OllamaProvider._ensure_client` line 154:`ollama.Client(host=..., trust_env=False)` — W14-B `427d963` 已修 ✅
- `AnthropicProvider._ensure_client` line 121-124:`Anthropic(**kwargs)`,kwargs 只有 `api_key` + 可选 `base_url` — **未修**
- `OpenAICompatProvider._ensure_client` line 243:`OpenAI(api_key=..., base_url=...)` — **未修**
- 已有 `tests/test_llm/test_ollama.py` 3 个 W14-B 测试(passes_trust_env_false + unaffected_by_proxy_env_vars + idempotent)
- `test_anthropic.py` 现有 11 测试,`test_openai_compat.py` 现有 23 测试,均无 trust_env 相关
- pytest baseline: **598 passed / 0 skipped**

### 2.2 设计原则

**trust_env=False 永远**(沿用 W14-B Ollama 模式):
- 不依赖环境变量配置
- 公司 VPN 父 shell 永不污染
- 用户若真要走代理,自己 `os.environ["HTTP_PROXY"]` 在代码里显式设 + 自己用 `httpx.Client(proxy=...)` 包
- 这是 **defense in depth**:即便显式 proxy 用户,公司 VPN proxy 也不会被自动劫持

### 2.3 代码改动(3 文件)

#### 2.3.1 `src/media_to_doc/llm/anthropic.py`

`_ensure_client` 改为:

```python
def _ensure_client(self) -> object:
    """lazy init Anthropic 客户端,透传 trust_env=False(W14-D 防 VPN 污染)。"""
    if self._client is not None:
        return self._client
    if not self._api_key:
        raise RuntimeError(...)
    try:
        from anthropic import Anthropic
        import httpx
    except ImportError as exc:
        raise ImportError(...)
    kwargs: dict[str, object] = {
        "api_key": self._api_key,
        "http_client": httpx.Client(trust_env=False),  # W14-D 新增
    }
    if self._base_url:
        kwargs["base_url"] = self._base_url
    self._client = Anthropic(**kwargs)
    return self._client
```

顶部 module docstring 加 W14-D 说明(同 Ollama line 12-17 模式)。

#### 2.3.2 `src/media_to_doc/llm/openai_compat.py`

`_ensure_client` 改为:

```python
def _ensure_client(self) -> object:
    """lazy init OpenAI 客户端,透传 trust_env=False(W14-D 防 VPN 污染)。"""
    if self._client is not None:
        return self._client
    if not self._api_key:
        raise RuntimeError(...)
    if not self._base_url:
        raise RuntimeError(...)
    try:
        from openai import OpenAI
        import httpx
    except ImportError as exc:
        raise ImportError(...)
    self._client = OpenAI(
        api_key=self._api_key,
        base_url=self._base_url,
        http_client=httpx.Client(trust_env=False),  # W14-D 新增
    )
    return self._client
```

顶部 module docstring 加 W14-D 说明。

### 2.4 测试改动(2 文件,+6 用例)

#### 2.4.1 `tests/test_llm/test_anthropic.py` — 加 3 个

照 `test_ensure_client_passes_trust_env_false_to_ollama_sdk`(line 245-271)模式:

- `test_ensure_client_passes_trust_env_false_to_anthropic_sdk` — 用 `_CaptureClient` capture `http_client` 参数,断言是 `httpx.Client(trust_env=False)`
- `test_ensure_client_unaffected_by_proxy_env_vars` — 设 8 个 proxy vars,断言 client 构造不抛错且 `http_client.trust_env=False`
- `test_ensure_client_idempotent_after_first_init` — _ensure_client 第一次构造后,后续复用 self._client(不重复传 kwargs)

注:anthropic SDK 用 `httpx.Client` 透传(W14-D 验证 SDK 接受),实际若 SDK 不接受 `http_client` 参数会抛 TypeError,测试中用 mock module 拦截。

#### 2.4.2 `tests/test_llm/test_openai_compat.py` — 加 3 个

照同样模式,`_CaptureClient` capture `http_client` 参数。

### 2.5 验收

- [ ] pytest 598 → 604 passed / 0 skipped
- [ ] ruff:All checks passed
- [ ] `from media_to_doc.llm import AnthropicProvider, OpenAICompatProvider` lazy import 路径不破坏
- [ ] 现有 11 + 23 = 34 个测试不退化

---

## 3. Commit 计划(2 个,符合 CLAUDE.md §5.6)

按 session-level pre-authorize:

| Commit | Scope | 触发 | 行为 |
|---|---|---|---|
| `fix(llm): W14-D — extend trust_env=False to Anthropic + OpenAICompat providers` | E 代码 | fix + 测试通过 + ruff | **自动 merge release/v1.0** |
| `docs(release): W14-D — subrepo v1.3.0 NSIS installer build + GitHub Release` | C 发布 | feat + 验证通过 | **写 handoff 等拍板**(C 是发布动作,不自动 merge) |

主仓: `release/v1.0` 分支(已领先 origin/main 19 commit)
子仓: `master` 分支(本次 push,tag v1.3.0)

---

## 4. Session budget(目标 <2h)

| 步骤 | 时间预算 |
|---|---|
| 1.1 LICENSE.txt + remote + GitHub 仓 + push | 5min |
| 1.2 NSIS 编译 + portable copy | 5min |
| 1.3 gh release create + 2 assets | 5min |
| 1.4 主仓 docs/RELEASE_NOTES_v1.3.0.md | 5min |
| 1.5 验收:gh release view + URL 访问 | 5min |
| 2.1 改 anthropic.py + openai_compat.py | 10min |
| 2.2 加 6 个测试 | 15min |
| 2.3 uv run pytest + uv run ruff | 5min |
| 2.4 commit + merge | 5min |
| 3. handoff + task.md 更新 + 收尾 | 5min |
| **总计** | **~65min** |

session <2h 预算内有 1h 缓冲(撞墙 / 复测 / 修 bug)。

---

## 5. 风险与回退

| 风险 | 触发 | 回退 |
|---|---|---|
| GitHub 仓已存在(其它 owner) | `gh repo create` 报 422 | 用户确认是否覆盖;否则换名 |
| makensis 找不到 | PATH 不含 `Program Files (x86)/NSIS` | 绝对路径 `"/c/Program Files (x86)/NSIS/makensis.exe"`;winget list 确认装好 |
| NSIS 编译报 LICENSE.txt not found | installer.nsi line 12 `MUI_PAGE_LICENSE "LICENSE.txt"` 找不到 | cp LICENSE LICENSE.txt 已规划;若仍失败可改用 `!define MUI_PAGE_LICENSE` 跳过 |
| gh release create 撞 GitHub API limit | 403 / rate limit | 等待 60s 重试;或 Web UI 手动 + `gh release upload` 补 assets |
| anthropic SDK 不接受 http_client 参数 | TypeError on init | 改为 monkeypatch 测试;生产代码改用 `httpx.Client` 包整个 `Anthropic` 客户端(SDK ≥ 0.20 支持,已查) |
| 测试 baseline 不匹配 | 598 → <598 | 立即停止 commit,逐个排查 |
| Session 超时(<2h) | 累计工具调用 > 80 次 | 已记 `feedback_push_through_long_tasks.md`;切 background + state.json 监控,或 /exit 新开会话 |

---

## 6. 关键文件索引

| 文件 | 用途 | 本会话改动 |
|---|---|---|
| `F:/soft/00selfmade/media-to-doc-ui/src-tauri/nsis/installer.nsi` | NSIS 安装脚本 | 不改 |
| `F:/soft/00selfmade/media-to-doc-ui/src-tauri/nsis/LICENSE.txt` | NSIS MUI 许可页 | **新建**(从 `LICENSE` copy) |
| `F:/soft/00selfmade/media-to-doc-ui/target/release/bundle/nsis/media-to-doc-1.3.0-setup.exe` | NSIS installer 输出 | **新生成** |
| `F:/soft/00selfmade/media-to-doc-ui/target/release/bundle/media-to-doc-1.3.0-portable.exe` | portable 副本 | **新建**(cp) |
| `F:/soft/00selfmade/media-to-doc-ui/.git/config` | git remote | **+remote**(SSH `git@github.com:kizemo/media-to-doc-ui.git`) |
| `F:/soft/00selfmade/media-to-doc-ui/src/media_to_doc/llm/anthropic.py` | E provider 1 | **改 `_ensure_client`** |
| `F:/soft/00selfmade/media-to-doc/src/media_to_doc/llm/openai_compat.py` | E provider 2 | **改 `_ensure_client`** |
| `F:/soft/00selfmade/media-to-doc/tests/test_llm/test_anthropic.py` | E 测试 1 | **+3 用例** |
| `F:/soft/00selfmade/media-to-doc/tests/test_llm/test_openai_compat.py` | E 测试 2 | **+3 用例** |
| `F:/soft/00selfmade/media-to-doc/docs/RELEASE_NOTES_v1.3.0.md` | 主仓 release notes(记录 subrepo 发布) | **新建** |
| `F:/soft/00selfmade/media-to-doc/handoff-w14d-*.md` | 本会话 handoff | **写** |
| `F:/soft/00selfmade/media-to-doc/task.md` | 活跃 todo | **+W14-D 节** |
| `F:/soft/00selfmade/media-to-doc/CLAUDE.md` | 项目指引 | **+§10 W14-D 节** |

---

## 7. 与 LE 闭环的关系

本会话 **不** 跑真实 pipeline,只发布 + 修代码层。LE L1 沉淀:
- 复用 `feedback_proxy_env_pollution.md` 的"8 proxy env vars"清单,沿用到 E provider 透传测试
- 新增 `.learnings/LEARNINGS.md` 条目 `LP-20260722-W14D-001`:`全 LLM provider 一律 trust_env=False,httpx.Client 是 SDK 的 http_client 参数入口`
- 新增 `feedback_tauri_async_state.md` 不变(与 C 无关);`feedback_proxy_env_pollution.md` 加 1 行参考 W14-D

---

## 8. 完成后状态

- 子仓 v1.3.0 GitHub Release 公开:https://github.com/kizemo/media-to-doc-ui/releases/tag/v1.3.0
- 主仓 release/v1.0:598 → 604 passed,新增 E fix commit
- 主仓 v1.3.x line 在 ROADMAP 表里首次出现(subrepo v1.3.0)
- CLAUDE.md §10 加 W14-D 行
- 下次会话候选:A(真实 30s 培训视频 e2e)+ D(WiX/MSI 网络 OK 时)+ L3(LE 优化)
