# handoff-template.md — 会话交接模板

> **使用方式**:每次会话结束、撞墙、或主动交接时,复制本模板到
> `handoff-<topic>-<YYYY-MM-DD>.md`,填写后让下一个会话先读这份文件再继续。
>
> 命名规则:`handoff-<topic>-<YYYY-MM-DD>.md`,例如
> - `handoff-research-2026-07-17.md`(本会话使用)
> - `handoff-skeleton-bootstrap-2026-07-18.md`
> - `handochlongdoc-stage-2026-07-20.md`
>
> 不要把 handoff 文件放进 `~/.claude/projects/<proj>/memory/` 文件夹
> (那是语义化记忆,不是会话上下文)。

---

## 元信息

- **会话日期**:YYYY-MM-DD ~ YYYY-MM-DD
- **会话主题**:一句话描述(英文或拼音,用于文件名 slug)
- **活跃时间**:HH:MM ~ HH:MM(总时长)
- **会话主人**:用户(Claude 是助手)
- **模型**:claude-opus-4-7(或当前所用)

---

## 1. 本次会话目标

> 用户最初要求做什么?

示例:

- 完成 `_research/PROJECT_DESCRIPTION.md`
- 把参考实现的 stage X 移植到本项目
- 修复 issue Y

---

## 2. 已完成

> 具体落地的项,带文件路径 / commit hash / 行数 / 测试数。

| 项 | 文件 / Commit | 状态 |
|---|---|---|
| 示例:`longdoc.py` 主函数实现 | `src/media_to_doc/longdoc.py` | [x] |
| 示例:3 个单元测试 | `tests/test_longdoc.py` | [x] |
| 示例:`feat(longdoc): add longdoc stage` | commit `abc1234` | [x] |

---

## 3. 已读 / 已写文件清单

> 新会话可参考的"已读缓存",避免重复读取。

### 已读(<20 次,缓存到下次复用)

- `path/to/file.py` — 关键函数位置 + 行号(不要整文件复述)
- `path/to/another.md` — 章节定位

### 已写

- `path/to/new_file.py` — 主要类/函数清单

### 已修改

- `path/to/old_file.py:L42-L80` — 改了什么

---

## 4. 关键决策与原因

> 选 A 不选 B 的"为什么",避免下一个会话重做同样纠结。

### 决策 1:为什么用 X 不用 Y

**问题**:…

**选项**:

- A:…
- B:…

**选择**:A

**原因**:…

**下次何时再讨论**:…

### 决策 2:…

---

## 5. 撞墙 / 未完成 / 已知问题

### 5.1 撞墙点(下次会话语境)

- **现象**:…
- **已尝试**:…
- **残留**:…

### 5.2 TODO(下次会话继续)

- [ ] 具体子任务(继承自 `task.md` 的对应 phase)
- [ ] …

### 5.3 已知问题 / 技术债

- …

---

## 6. 测试状态

```
$ uv run pytest
XXX passed in X.XXs
```

(如未跑测试,写"N/A — 纯文档工作")

---

## 7. Git 状态

```
$ git log --oneline -10
abc1234 ...
def5678 ...

$ git status
M <modified file>
?? <untracked file>
```

---

## 8. 给下一个会话的提示

> 下一句话应该怎么写,让新会话能立即进入状态?

示例:

- 新会话第一句:`承接 handoff-skeleton-bootstrap-2026-07-18.md,继续 Phase 1 项目骨架`
- 主要任务:`uv init` + `pyproject.toml` + 目录结构
- 别忘了:用 pnpm 而非 npm(全局偏好)

---

## 9. 上下文参考链接

- `CLAUDE.md` — 项目级指引
- `task.md` — 活跃 todo
- `_research/PROJECT_DESCRIPTION.md` — 参考实现逆向报告
- 上一个 handoff:`handoff-<topic>-<YYYY-MM-DD>.md`(同主题上一份)
- 关键 skill:`long-doc-processor` / `claude-mem` / `codebase-memory`
- 关键 memory:`C:\Users\Duanyi\.claude\projects\F--soft-00selfmade-media-to-doc\memory\MEMORY.md`(如有)

---

## 10. 提醒清单

- [ ] 会话结束前必填本文件再 `/exit`
- [ ] 不要在本文件复述完整代码(只写路径 + 行号)
- [ ] 不要把所有对话上下文塞进 memory 文件夹
- [ ] 下次会话引用本文件路径:`承接 <绝对路径>/handoff-<name>.md`
- [ ] 单个 handoff 文件 < 200 行,过长则拆分为 `handoff-<topic>-part1.md` / `part2.md`
