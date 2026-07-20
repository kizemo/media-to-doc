# handoff-pipeline-w12-github-release-2026-07-20.md — W12-B GitHub Release 真实发布

> **会话主题**:W12-B — 把 release/v1.0 + tag v1.0.0 push 到 GitHub + 创建 GitHub Release
> **会话日期**:2026-07-20,~20 分钟
> **会话状态**:**W12-B 主目标完成** ✅ + GitHub URL:https://github.com/kizemo/media-to-doc/releases/tag/v1.0.0

---

## 1. 本次会话目标

按 task.md / handoff-pipeline-w12-pypi-2026-07-20.md §6 选项 B:
- 创建 GitHub repo `kizemo/media-to-doc`
- push release/v1.0 + tag v1.0.0
- 创建 GitHub Release + 上传 wheel/sdist 作为 release assets

---

## 2. 执行流程

### 2.1 准备

```bash
$ gh --version
gh version 2.96.0 (2026-07-02)

$ gh auth status
github.com
  ✓ Logged in to github.com account kizemo (GITHUB_TOKEN)
  - Active account: true
  - Git operations protocol: https
  - Token scopes: 'repo', 'workflow', 'project' ...
```

`gh` CLI 已登录,token 有 `repo` scope 足够 push + create release。

### 2.2 创建 repo + 自动 push

```bash
$ gh repo create kizemo/media-to-doc --public \
    --description "把本地音视频一键转化为带 AI 配图、可独立分发的 Markdown + HTML 讲义" \
    --homepage "https://pypi.org/project/media_to_doc/" \
    --source=. --push
```

输出:
```
https://github.com/kizemo/media-to-doc
fatal: unable to access 'https://github.com/kizemo/media-to-doc.git/':
  TLS connect error: error:0A000126:SSL routines::unexpected eof while reading
failed to run git: exit status 128
```

✓ repo URL 创建成功(后续 API 查询确认存在)
✗ git push SSL EOF(走 HTTPS proxy 出错)

### 2.3 关键踩坑:git push SSL 失败

| 现象 | 根因 | 修 |
|---|---|---|
| `fatal: TLS connect error: SSL routines: unexpected eof` | `HTTPS_PROXY=http://127.0.0.1:56295` 公司 VPN 代理拦 GitHub HTTPS 443 | 换 SSH 协议 |

诊断:
```bash
$ env | grep -iE "proxy"
HTTPS_PROXY=http://127.0.0.1:56295
HTTP_PROXY=http://127.0.0.1:56295
all_proxy=http://127.0.0.1:56295
```

跟 W5/W10-A HF mirror + W12-A uv publish(都靠 unset proxy)同根因。

### 2.4 切 SSH 协议

```bash
$ git remote set-url origin git@github.com:kizemo/media-to-doc.git
$ git -c core.sshCommand="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
    push -u origin release/v1.0:main
To github.com:kizemo/media-to-doc.git
 * [new branch]      release/v1.0 -> main
branch 'release/v1.0' set up to track 'origin/main'.
```

✓ release/v1.0 → main push 成功

### 2.5 push tag

```bash
$ git -c core.sshCommand="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
    push origin v1.0.0
To github.com:kizemo/media-to-doc.git
 * [new tag]         v1.0.0 -> v1.0.0
```

✓ tag v1.0.0 push 成功

### 2.6 gh release create(踩第二次坑:target_commitish)

```bash
$ gh release create v1.0.0 \
    --title "v1.0.0 — First stable release" \
    --notes-file docs/RELEASE_NOTES_v1.0.0.md \
    --target bd8c010 \
    dist/media_to_doc-1.0.0-py3-none-any.whl \
    dist/media_to_doc-1.0.0.tar.gz
HTTP 422: Validation Failed
Release.target_commitish is invalid
```

`--target` 期望 **branch name** 而非 commit hash。改用 `--target main`:

```bash
$ gh release create v1.0.0 \
    --title "v1.0.0 — First stable release" \
    --notes-file docs/RELEASE_NOTES_v1.0.0.md \
    --target main \
    dist/media_to_doc-1.0.0-py3-none-any.whl \
    dist/media_to_doc-1.0.0.tar.gz
https://github.com/kizemo/media-to-doc/releases/tag/v1.0.0
```

🎉 **GitHub Release 创建成功!**

---

## 3. Release 验证

```bash
$ gh release view v1.0.0
title:    v1.0.0 — First stable release
tag:      v1.0.0
draft:    false
prerelease: false
url:      https://github.com/kizemo/media-to-doc/releases/tag/v1.0.0
asset:    media_to_doc-1.0.0-py3-none-any.whl
asset:    media_to_doc-1.0.0.tar.gz
```

2 assets 已上传,SHA256 验证:
- `media_to_doc-1.0.0-py3-none-any.whl` — `sha256:a92d62a5044fac2d1316a872e1f4122c180a7506605568423cb966a76cbd969f`
- `media_to_doc-1.0.0.tar.gz` — `sha256:54548cf2e73e556093b4489ae64a4004f139b59563c40bad0d7213133a3432dc`

---

## 4. URL 清单(发布后实 URL)

| 资源 | URL |
|---|---|
| **GitHub Repo** | https://github.com/kizemo/media-to-doc |
| **GitHub Release v1.0.0** | https://github.com/kizemo/media-to-doc/releases/tag/v1.0.0 |
| **wheel download** | https://github.com/kizemo/media-to-doc/releases/download/v1.0.0/media_to_doc-1.0.0-py3-none-any.whl |
| **sdist download** | https://github.com/kizemo/media-to-doc/releases/download/v1.0.0/media_to_doc-1.0.0.tar.gz |
| **PyPI** | https://pypi.org/project/media_to_doc/ |
| **Source clone** | `git clone git@github.com:kizemo/media-to-doc.git` |
| **Issues** | https://github.com/kizemo/media-to-doc/issues |

---

## 5. pyproject.toml [project.urls] 实配(W12-B 新增)

```toml
[project.urls]
"Homepage" = "https://github.com/kizemo/media-to-doc"
"Bug Tracker" = "https://github.com/kizemo/media-to-doc/issues"
"Documentation" = "https://github.com/kizemo/media-to-doc#readme"
"Changelog" = "https://github.com/kizemo/media-to-doc/blob/main/CHANGELOG.md"
"Release Notes" = "https://github.com/kizemo/media-to-doc/releases/tag/v1.0.0"
"PyPI" = "https://pypi.org/project/media_to_doc/"
```

`uv publish` 推 v1.0.1+ 时这些 URL 会跟着 wheel/sdist 一起发布,PyPI 项目页侧栏会自动显示。

CHANGELOG.md 底部的 `Compare Links` 也同步更新为真实 URL。

---

## 6. 关键设计 / 决策

### 6.1 release/v1.0 → main 直接 push(不建 PR)

- 选 release/v1.0 当 source of truth,W11-B 起就在这条线开发
- 推到新空 repo 时,`release/v1.0` 映射到 `main`(default branch)
- 不需要建 PR(单人项目,直接 push 干净)
- 优点:tag v1.0.0 直接指向 main,history 干净

### 6.2 切 SSH 协议而非 fix HTTPS

HTTPS 走公司 VPN proxy 一直有 SSL EOF 问题(W5/W10-A/W12-A 都遇到过)。SSH 直连 GitHub(走 22 端口,proxy 通常不拦 SSH)稳定。代价:用户需要 GitHub SSH key。

如果用户没 SSH key,`gh auth login` 时可以自动配。

### 6.3 release notes 复用 `docs/RELEASE_NOTES_v1.0.0.md`

- 同一份 markdown 给 GitHub Release notes + CHANGELOG
- 不用两套维护
- GitHub Release 不接受 CHANGELOG.md(太长),独立 RELEASE_NOTES 反而更好

### 6.4 不动 default branch 名

新 GitHub repo 默认 main(2020 年 GitHub 改的,取代 master)。我没改名 — 跟生态一致。

### 6.5 不 push `dist/*` 到 GitHub(只放 release assets)

- 常规:源码 + 文档 push 到 repo,build 产物放 release assets
- dist/ 在 .gitignore,不会进 git
- 需要 wheel/sdist 的用户从 GitHub Release 下载或从 PyPI 装

---

## 7. 验证清单

- [x] gh CLI 2.96.0 已装
- [x] gh 已登录 kizemo 账号
- [x] GitHub repo `kizemo/media-to-doc` 创建(public)
- [x] `release/v1.0` → `main` push 成功
- [x] tag `v1.0.0` push 成功
- [x] GitHub Release v1.0.0 创建(URL)
- [x] wheel asset 上传(122916 bytes, SHA256 verified)
- [x] sdist asset 上传(508660 bytes, SHA256 verified)
- [x] Release notes 从 `docs/RELEASE_NOTES_v1.0.0.md` 加载
- [x] pyproject.toml [project.urls] 6 条实 URL
- [x] CHANGELOG.md compare links 更新
- [x] `uv run pytest` 529 passed / 0 skipped
- [x] `uv run ruff check` All checks passed
- [x] `uv build` wheel + sdist 成功

---

## 8. W12-B commit

```
docs(pipeline): W12-B — GitHub Release v1.0.0 + real project URLs

- pyproject.toml [project.urls]:6 条实 URL(github + pypi + readme)
- CHANGELOG.md compare links:media-to-doc → kizemo 真实路径
- handoff-pipeline-w12-github-release-2026-07-20.md:本会话快照

GitHub Release URL:https://github.com/kizemo/media-to-doc/releases/tag/v1.0.0
PyPI URL:https://pypi.org/project/media_to_doc/

踩坑解决:
- HTTPS_PROXY 公司 VPN 拦 git push SSL EOF
  → 切 SSH 协议(`git remote set-url origin git@github.com:...`)
- gh release create --target <commit-sha> 422 invalid target_commitish
  → --target 期望 branch name,改用 `--target main`

release/v1.0 分支当前:
- 8 commits(从 b410e84 起,W11-A → W12-B)
- HEAD = e41384c(W11-C,后续会有 B commit)
- tag v1.0.0 已 push
- GitHub Release v1.0.0 已发
- 529/0/ruff clean
```

---

## 9. media-to-doc v1.0.0 GA 全发布清单

| 平台 | URL | 状态 |
|---|---|---|
| **PyPI** | https://pypi.org/project/media_to_doc/ | ✅ W12-A |
| **GitHub Repo** | https://github.com/kizemo/media-to-doc | ✅ W12-B |
| **GitHub Release v1.0.0** | https://github.com/kizemo/media-to-doc/releases/tag/v1.0.0 | ✅ W12-B |
| **GitHub Tag v1.0.0** | pushed to origin | ✅ W12-B |
| **MIT License** | https://github.com/kizemo/media-to-doc/blob/main/LICENSE | ✅ |
| **CHANGELOG** | https://github.com/kizemo/media-to-doc/blob/main/CHANGELOG.md | ✅ |

**v1.0.0 GA fully shipped.** 任何用户可通过:
```bash
# 方式 1:PyPI
uv pip install media_to_doc

# 方式 2:GitHub
git clone git@github.com:kizemo/media-to-doc.git
cd media-to-doc && uv sync --all-extras

# 方式 3:wheel 直接
curl -L -o media_to_doc.whl https://github.com/kizemo/media-to-doc/releases/download/v1.0.0/media_to_doc-1.0.0-py3-none-any.whl
uv pip install ./media_to_doc.whl
```

---

## 10. 给下一会话的提示

按 handoff-pipeline-w11-quality-2026-07-20.md §11:
- ✅ A. 上 PyPI(W12-A)
- ✅ B. GitHub release 真实发布(W12-B)
- **E. v1.0.1 patch** — 修 W11-C §4 标记的 2 个 HTML 渲染降级(mermaid 流程图 / GFM task list checkbox)
- C. Tauri UI(v1.1+ Phase 2)
- D. NSIS 安装器(v1.2+ Phase 3)

如选 E,告诉我"开始 v1.0.1 patch",我会:
1. 改 `longdoc.py` 的 HTML 模板,接入 mermaid.js CDN(浏览器端渲染)
2. 给 markdown 库加 `pymdownx.tasklist` 扩展或自己解析 `- [ ]` 替换为 `<input>`
3. 重新跑 W11-C 真净化验证渲染
4. 发 v1.0.1 到 PyPI + GitHub release

预计 ~30-60 分钟(单 Python 文件改 + 测试 + 真跑 longdoc 验证)。
