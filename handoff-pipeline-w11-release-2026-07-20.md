# handoff-pipeline-w11-release-2026-07-20.md — W11-B v1.0.0 Release Prep

> **会话主题**:W11-B v1.0.0 release prep — version bump + CHANGELOG + installation docs + uv build 验证
> **会话日期**:2026-07-20,~45 分钟
> **会话状态**:**W11-B 主目标完成** ✅ + 529 测试 0 失败 + uv build 成功打 wheel + sdist
> **下次**:W11-C 真分布式文档质量验收(用 longdoc active 跑同 03.mp4)

---

## 1. 本次会话目标

按 `handoff-pipeline-w10-real-LE-verify-2026-07-19.md` §10 / task.md Phase 11 W11-B:

1. ✅ version 0.1.0 → 1.0.0(首次 stable)
2. ✅ CHANGELOG.md(Keep a Changelog 1.1,W0-W11 里程碑)
3. ✅ docs/installation.md(各 OS / CUDA / China 网络 / Claude Desktop)
4. ✅ docs/RELEASE_NOTES_v1.0.0.md(gh release form 可粘贴)
5. ✅ `__version__` 动态从安装元数据读(避免再写死)
6. ✅ uv build 验证(122KB wheel + 508KB sdist)
7. ✅ 测试 + ruff 三件套验证(529 / 0 / clean)

---

## 2. 关键改动

| 文件 | 改动 |
|---|---|
| `pyproject.toml` | version 0.1.0 → 1.0.0;classifier 3-Alpha → 5-Production/Stable;加 multi-OS / Education / Topic 分类 |
| `src/media_to_doc/__init__.py` | `__version__ = "0.1.0"` 写死 → `importlib.metadata.version("media_to_doc")` + pyproject fallback |
| `tests/test_smoke.py` | 3 处 "0.1.0" 断言改用 `__version__` 动态变量 |
| `README.md` | badge 版本号 + 5 分钟快速开始期望版本同步 |
| `CHANGELOG.md` | **新建**,Keep a Changelog 1.1 规范,W0-W11 关键 commit / bug fix / 性能数据 |
| `docs/installation.md` | **新建**,Windows(主要) / macOS / Linux / CUDA / China 网络 / Ollama / Claude Desktop / 故障排除 |
| `docs/RELEASE_NOTES_v1.0.0.md` | **新建**,gh release create --draft 可粘贴的 release notes |
| `uv.lock` | 同步 pyproject version bump |

---

## 3. uv build 验证

```bash
$ uv build
Building source distribution...
Building wheel from source distribution...
Successfully built dist\media_to_doc-1.0.0.tar.gz
Successfully built dist\media_to_doc-1.0.0-py3-none-any.whl
```

### dist/ 产物

| 文件 | 大小 | 内容 |
|---|---|---|
| `media_to_doc-1.0.0.tar.gz` | 508KB | sdist(源码包) |
| `media_to_doc-1.0.0-py3-none-any.whl` | 122KB | pure-Python wheel |

### wheel METADATA 关键字段

```
Name: media_to_doc
Version: 1.0.0
Summary: 把本地音视频一键转化为带 AI 配图、可独立分发的 Markdown + HTML 讲义
License: MIT License
Classifier: Development Status :: 5 - Production/Stable
Requires-Python: >=3.11
Provides-Extra: all / asr / dev / frames / imagegen / llm / longdoc / mcp / ocr (9 个)
```

### wheel 内 33 个 .py 模块

覆盖:11 stage(pipeline/)+ 4 LLM provider(llm/)+ 3 LE 模块(logger/)+ mcp_server + cli + config + state + paths + llm/health(W8)+ __init__ 等。

### Smoke test

```bash
$ uv pip install --force-reinstall dist/media_to_doc-1.0.0-py3-none-any.whl
$ uv run mtd --version
media-to-doc 1.0.0
$ uv run python -c "from media_to_doc import run_pipeline, get_run_metrics, list_runs, gatekeeper_check; print('lazy import OK')"
lazy import OK
```

✓ 装 wheel → CLI 报 1.0.0 → 52 公开符号 lazy import 无回归。

---

## 4. 关键设计决策

### 4.1 `__version__` 动态读取

W0 时 `__version__ = "0.1.0"` 写死在 `__init__.py`,升版本时需同时改两处(易漏)。
本次改为:

```python
try:
  from importlib.metadata import version as _pkg_version
  __version__ = _pkg_version("media_to_doc")
except Exception:
  # 源码直接 ``import media_to_doc`` 而未安装时(开发模式),fallback 到 pyproject
  from pathlib import Path
  _pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
  ...  # regex 读 pyproject version
```

- 安装场景(uv/pip 装的 wheel):`importlib.metadata.version` 读 METADATA,准确
- 开发场景(`python -c "import media_to_doc"` 在 src 目录):fallback 到 pyproject 解析 regex
- 单一真相源在 pyproject.toml,改一处全链路同步

### 4.2 classifier 升级

- `Development Status :: 3 - Alpha` → **5 - Production/Stable**(GA release 标志)
- 加 `Intended Audience :: Education`(讲义场景)
- 加 `Operating System :: POSIX :: Linux` + `MacOS`(多 OS 支持)
- 加 `Topic :: Office/Business`(培训音视频主线场景)

### 4.3 不动 `[project.urls]` 的占位

`pyproject.toml` 已有:

```toml
[project.urls]
"Homepage" = "https://github.com/media-to-doc/media-to-doc"
"Bug Tracker" = "https://github.com/media-to-doc/media-to-doc/issues"
"Documentation" = "https://github.com/media-to-doc/media-to-doc#documentation"
```

指向占位 github org `media-to-doc/media-to-doc`(尚未创建)。
留给用户实配 git remote 后再改;1.0.0 release notes 假定该 URL 已创建。

---

## 5. W11-B commit + tag

### Branch

```
release/v1.0  (从 fix/pipeline-w11-gatekeeper-paths b410e84 拉)
```

### Commit

```
docs(release): W11-B — v1.0.0 release prep (version bump + CHANGELOG + installation docs + dynamic __version__)
```

### Tag(待用户确认后打)

```
v1.0.0
```

---

## 6. gh release create(留给用户执行)

当前 git remote 未配置,gh CLI 无法 release。留给用户在 media-to-doc GitHub org 创建后:

```bash
# 1. 配 remote
cd F:/soft/00selfmade/media-to-doc
git remote add origin git@github.com:media-to-doc/media-to-doc.git
git push -u origin release/v1.0
git push origin v1.0.0  # 等用户打 tag 后

# 2. gh release create(用 docs/RELEASE_NOTES_v1.0.0.md 当 notes)
gh release create v1.0.0 \
  --title "v1.0.0 — First stable release" \
  --notes-file docs/RELEASE_NOTES_v1.0.0.md \
  --target release/v1.0 \
  dist/media_to_doc-1.0.0-py3-none-any.whl \
  dist/media_to_doc-1.0.0.tar.gz
```

`docs/RELEASE_NOTES_v1.0.0.md` 内容已格式化为 gh release form 可粘贴的 markdown。

---

## 7. 不在 W11-B 范围(留给未来)

按 PRD §5.1 + Roadmap:

- **Phase 2 UI** (Tauri 2 + React 18)— W12+
- **NSIS 安装器** — W13+
- **PyPI 发布** — 等 v1.0 GA 后,如果用户决定上 PyPI 用 `uv publish`(已配 PEP 621 + setuptools 兼容)
- **签名 release** — `gh release sign` + GPG key(用户实配)
- **`pyproject.toml [project.urls]` 实 URL** — 等 GitHub repo 创建

---

## 8. 验证清单

- [x] pyproject.toml version = 1.0.0
- [x] __init__.py 动态读版本(dev + wheel 都 OK)
- [x] test_smoke.py 3 处版本断言同步
- [x] README.md badge 1.0.0 / 529 tests
- [x] CHANGELOG.md (Keep a Changelog 1.1)
- [x] docs/installation.md (各 OS / CUDA / China 网络)
- [x] docs/RELEASE_NOTES_v1.0.0.md
- [x] `uv build` 成功(wheel + sdist)
- [x] wheel 装后 CLI 报 1.0.0
- [x] `uv run pytest` 529 passed / 0 skipped
- [x] `uv run ruff check` All checks passed
- [x] W10-A 真跑产物 `_w11a_consistency.py` 一致

---

## 9. 给下一会话的提示(W11-C)

按 `handoff-pipeline-w10-real-LE-verify-2026-07-19.md` §10:
- 用同 03.mp4(395MB / 107min)跑完整 11 stage + longdoc active 净化(qwen3:14b 真净化)
- 期望产物:`<stem>_cleaned.md`(LLM 净化版本)+ `<stem>_final.html`(TOC + dark mode + print)
- 讲师视角看讲义质量:结构 / 信息密度 / 校对率 / 配图

`mtd run ... --longdoc-llm ollama --longdoc-model qwen3:14b --stop-after longdoc`

### 决策点(等用户)

- **A. W11-C 真跑 longdoc active**:CPU ASR 已 3h57min,longdoc active(qwen3:14b 净化 30K chars 估计 30-60min)+ render < 1min。总 ~4h30min。需 user 授权突破 session 上限(W10-A 经验)。
- **B. 直接进 v1.0 GA tag**:把当前 release/v1.0 merge 到 main + 打 v1.0.0 tag + 准备 PyPI/发布(用户来执行)。
- **C. 写 CLAUDE.md §10 后续规划表** 更新(v1.0 GA 已实现,后续指向 UI / NSIS / 上 PyPI)。
