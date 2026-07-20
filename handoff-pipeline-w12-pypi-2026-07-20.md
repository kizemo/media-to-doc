# handoff-pipeline-w12-pypi-2026-07-20.md — W12-A 上 PyPI(media_to_doc 1.0.0)

> **会话主题**:W12-A — 把 media_to_doc 1.0.0 推到 PyPI,公开可装
> **会话日期**:2026-07-20,~30 分钟(含 keyring 调试 + 真上传 + 验证装包)
> **会话状态**:**W12-A 主目标完成** ✅ + 公开 PyPI URL:`https://pypi.org/project/media-to-doc/`

---

## 1. 本次会话目标

按 task.md / handoff-pipeline-w11-quality-2026-07-20.md §11 选项 A:
- 把 dist/media_to_doc-1.0.0-py3-none-any.whl + .tar.gz 推到 PyPI
- 让任何用户能用 `uv pip install media_to_doc` 装

---

## 2. 上传流程(实测踩坑 + 修)

### 2.1 用户提问链路

1. **Q:token 没准备好,为什么要 + 怎么申请** → A:解释 PyPI token 作用 + 申请流程
2. **Q:用户提供 token**(暴露在对话历史)→ A:**警告 + 建议撤销 + 重新生成,改用 keyring**
3. **Q:方案 A,token 已写入 `~/.pypirc`** → A:uv 不读 .pypirc,改方案 1(Windows Credential Locker via keyring)
4. **Q:选项 1,下面怎么做** → A:5 步 keyring 设置
5. **Q:跳过 TestPyPI,直接 PyPI,keyring 已装** → A:keyring set PyPI URL
6. **Q:keyring.exe 不在 system Python,装到 uv tool 后 `python -m keyring` 找不到** → A:装到 system Python + 改用 `keyring get` 测试
7. **Q:方案 A,已 set** → A:debug + 真上传

### 2.2 关键踩坑

| 现象 | 根因 | 修 |
|---|---|---|
| `python -m keyring --version` No module | uv tool install 装到独立 venv,不在 system Python | `uv pip install --python C:/Python314/python.exe keyring` |
| `keyring get ...` 返回 token 但 uv publish "Missing credentials" | uv publish 内嵌 Python 与 system Python 隔离,看不到 keyring 包 | (下一步修复 — uv run keyring trick) |
| uv publish `--keyring-provider subprocess` 仍 missing | uv 内部 Python 跟 keyring 找不到合适的 backend 配置 | **绕路**:keyring 读 token → export UV_PUBLISH_TOKEN → uv publish |

### 2.3 最终成功的命令链

```bash
# 单条链式命令 — keyring 读 token → export env → uv publish → unset
export UV_PUBLISH_TOKEN="$(uv run --with keyring python -c \
    "import keyring; print(keyring.get_password('https://upload.pypi.org/legacy/', '__token__'))")" \
  && echo "token set (len=${#UV_PUBLISH_TOKEN})" \
  && uv publish dist/* \
  && unset UV_PUBLISH_TOKEN
```

输出:
```
token set (len=179)
Publishing 2 files to https://upload.pypi.org/legacy/
Hashing media_to_doc-1.0.0-py3-none-any.whl (120.0KiB)
Uploading media_to_doc-1.0.0-py3-none-any.whl (120.0KiB)
Hashing media_to_doc-1.0.0.tar.gz (496.7KiB)
Uploading media_to_doc-1.0.0.tar.gz (496.7KiB)
```

无错误 → 上传成功。

---

## 3. PyPI 公开验证

### 3.1 项目页面

```bash
$ curl -sI https://pypi.org/project/media-to-doc/
HTTP/1.1 200 OK
```

(上传前是 404,上传后 200)

### 3.2 干净环境装包验证

```bash
$ uv venv C:/tmp/mtd-pypi-verify
$ uv pip install --python C:/tmp/mtd-pypi-verify/Scripts/python.exe media_to_doc
... (9 deps 全装上)

$ C:/tmp/mtd-pypi-verify/Scripts/python.exe -c \
    "from media_to_doc import run_pipeline, get_run_metrics, list_runs, WorkflowConfig; \
     print('lazy import OK, version =', __import__('media_to_doc').__version__)"
lazy import OK, version = 1.0.0

$ C:/tmp/mtd-pypi-verify/Scripts/mtd.exe --version
media-to-doc 1.0.0
```

✅ 完整验证通过 — 公开 PyPI 装包 → lazy import → CLI 全部 OK。

---

## 4. 用户从此可以

```bash
# 任何用户、任何机器
uv pip install media_to_doc

# 或全部功能
uv pip install "media_to_doc[all]"

# 或 LLM provider
uv pip install "media_to_doc[llm]"

# CLI 立即可用
mtd --version
```

详细安装步骤见 [`docs/installation.md`](../docs/installation.md)。

---

## 5. 安全回顾

| 时间 | 风险事件 | 处理 |
|---|---|---|
| 用户贴 PyPI token 到对话 | token 暴露在对话历史 | 立即建议撤销 + 改 keyring |
| 用户撤销旧 token + 写新 keyring | — | 走 Windows Credential Locker(加密) |
| `keyring get` 验证 token 真存 | — | ✅ 179 chars 读到 |
| `uv run --with keyring ...` 拉 token | token 短暂在 shell env | 立即 publish + unset |
| `unset UV_PUBLISH_TOKEN` | — | ✅ 关 shell 自动失效 |

最终 token 状态:**只存在 Windows Credential Locker,加密,GUI 可查可改**。

撤销方式:
```powershell
keyring delete https://upload.pypi.org/legacy/ __token__
```

---

## 6. 后续版本 / 后续工作

### 6.1 v1.0.0 已不可撤销

- 项目名 `media_to_doc` 被占
- 1.0.0 文件只能 yank(隐藏)不能删
- metadata 永久保留

### 6.2 下次发布 v1.0.1 / v1.1.0 流程

```bash
# 1. 修改代码 + bump version in pyproject.toml + __version__
# 2. 测试
uv run pytest && uv run ruff check
# 3. build
uv build
# 4. publish (keyring 流程不变)
export UV_PUBLISH_TOKEN="$(uv run --with keyring python -c \
    "import keyring; print(keyring.get_password('https://upload.pypi.org/legacy/', '__token__'))")" \
  && uv publish dist/* \
  && unset UV_PUBLISH_TOKEN
# 5. 验证装包
uv pip install --upgrade media_to_doc==<NEW_VERSION>
```

### 6.3 CLAUDE.md §10 后续规划更新方向

按 handoff-pipeline-w11-quality-2026-07-20.md §11 选项:

| 选项 | 优先级 | 状态 |
|---|---|---|
| ~~A. 上 PyPI~~ | ✅ | **W12-A 完成** |
| **B. GitHub release 真实发布** | 高 | 待用户实配 GitHub remote + `gh release create v1.0.0 --notes-file docs/RELEASE_NOTES_v1.0.0.md` |
| **C. Tauri UI** | 中 | v1.1+ Phase 2 |
| **D. NSIS 安装器** | 低 | v1.2+ Phase 3 |
| **E. v1.0.1 patch** | 中 | 修 W11-C §4 标记的 2 个 HTML 渲染降级(mermaid / GFM task list) |

---

## 7. 关键发现 / 给后续真用 PyPI 的笔记

### 7.1 uv publish 不读 .pypirc

uv 0.11+ 兼容性:接受 env var / keyring subprocess / pyproject `[tool.uv.publish]`,**不直接读 `~/.pypirc`**。

如果用户已经写了 .pypirc,需要:
- 改用 keyring,或
- 临时 `UV_PUBLISH_TOKEN` env var

### 7.2 uv publish keyring subprocess 兼容性差

`--keyring-provider subprocess` 调 `keyring` CLI 时,**用哪个 Python 解释器不明确**(在 Windows 上经常找不到 credential)。

最稳定的 workaround:**用 `uv run --with keyring python` 拉 token 到 env var**,然后 `uv publish` 不用 `--keyring-provider`:

```bash
export UV_PUBLISH_TOKEN="$(uv run --with keyring python -c \
    "import keyring; print(keyring.get_password('<URL>', '__token__'))")" \
  && uv publish dist/* \
  && unset UV_PUBLISH_TOKEN
```

### 7.3 用户 keyring 重复设没冲突

用户在 uv tool 安装的 keyring 和 system Python 装的 keyring 都 set 了相同 credential。Windows Credential Locker 是 OS 级别共享,任何一个 keyring 都能读。冗余是好事。

---

## 8. W12-A commit

```
docs(pipeline): W12-A — publish media_to_doc 1.0.0 to PyPI

- CHANGELOG.md:加 "Published to PyPI" 行 + PyPI URL
- docs/RELEASE_NOTES_v1.0.0.md:加 "Install" 章节 + PyPI URL
- handoff-pipeline-w12-pypi-2026-07-20.md:本会话快照

PyPI URL:https://pypi.org/project/media-to-doc/
验证:uv pip install media_to_doc → mtd --version → media-to-doc 1.0.0
```

---

## 9. 给下一会话的提示

按 handoff-pipeline-w11-quality-2026-07-20.md §11 + 本次新发现的 PyPI 已上:

- ✅ A. 上 PyPI — **W12-A 完成,公开 PyPI URL 已生效**
- **B. GitHub release 真实发布** — 用户需配置 git remote + push release/v1.0 + tag v1.0.0 + `gh release create`
- **E. v1.0.1 patch** — 修 W11-C §4 标记的 mermaid 流程图 + GFM task list 渲染降级(2 个 longdoc 模板增强)

如选 B,请告诉我 git remote URL。
如选 E,告诉我"开始 v1.0.1 patch"。
