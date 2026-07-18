# handoff-research-2026-07-17.md — 研究阶段快照

> **会话主题**:逆向研究参考实现 `local-ai-workflow`,产出项目启动文档
> **会话日期**:2026-07-17,~30 分钟
> **会话状态**:**已完成,无阻塞**

---

## 1. 本次会话目标

用户最初要求:

> 请从项目 01学习资料 的会话"本地音视频2"复制这个 session 涉及的项目、任务,
> 深入研究已经执行的任务、已经完成的目标,然后写出一份详细的项目说明。

后续要求:

> 请撰写项目的 CLAUDE.md 文档、handoff.md 文档等项目启动必要的文档。

---

## 2. 已完成

| 项 | 文件 | 状态 |
|---|---|---|
| 定位参考会话 | `E:\办公文件\01学习资料`(cwd),会话 ID `2cf14f87-...` | [x] |
| 提取 14 个真实用户指令 | `_research/all_user_messages.txt` | [x] |
| 提取 19 段助手交付汇报 | `_research/assistant_texts.txt` | [x] |
| 解析 159 条 Bash + 72 Read + 34 Write | `_research/tool_operations.txt` + `read_writes.txt` | [x] |
| 写出项目说明文档(25KB / 566 行) | `_research/PROJECT_DESCRIPTION.md` | [x] |
| 创建项目启动文档 | `CLAUDE.md` | [x] |
| 创建活跃 todo | `task.md` | [x] |
| 创建 handoff 模板 | `handoff-template.md` | [x] |
| 创建本次会话快照 | `handoff-research-2026-07-17.md`(本文件) | [x] |

---

## 3. 已读 / 已写文件清单

### 已读(本会话,信息已缓存)

- `C:\Users\Duanyi\.claude\projects\E-------01----\2cf14f87-...jsonl`(4MB / 1330 行)— 参考会话原始数据
- `C:\Users\Duanyi\.claude\CLAUDE.md` — 全局指引
- `C:\Users\Duanyi\.claude\projects\E-------01----\memory\local_training_workflow_goal.md`(Read 1 次)
- `C:\Users\Duanyi\.claude\projects\E-------01----\memory\proxy_usage.md`(Read 1 次)
- 4 个 long-doc-processor skill references(`phase-1-purification.md` / `phase-2-merge.md` / `phase-3-render-html.md` / `purification-prompt.md`)

### 已写

- `F:/soft/00selfmade/media-to-doc/_research/PROJECT_DESCRIPTION.md` — 25KB,12 章节
- `F:/soft/00selfmade/media-to-doc/CLAUDE.md` — 项目级 Claude 指引,10 章节
- `F:/soft/00selfmade/media-to-doc/task.md` — 8 个 Phase 的 todo 清单
- `F:/soft/00selfmade/media-to-doc/handoff-template.md` — 长期复用的会话交接模板
- `F:/soft/00selfmade/media-to-doc/handoff-research-2026-07-17.md` — 本文件

### 已修改

无(本会话纯新增)。

---

## 4. 关键决策与原因

### 决策 1:为什么写 4 份文档而非用户要求的 2 份

**问题**:用户要求 CLAUDE.md + handoff.md,但全局指引建议 `task.md` + `handoff-template.md` 也是必要的。

**选项**:

- A:只写 CLAUDE.md + handoff.md(用户明示)
- B:写 CLAUDE.md + handoff.md + task.md + handoff-template.md(全局指引 + 长期复用)

**选择**:B

**原因**:

1. 全局 CLAUDE.md §"防丢失工程实践"明示 `task.md` 是"会话开始时建立",`handoff-template.md` 是"首次建立后长期复用"
2. 用户口语化的 "handoff.md 文档" 在严格意义上应包含两件:模板(给未来用)+ 实际快照(给当前会话用)
3. 拆分职责清晰:模板不重复写,每个 handoff 快照内容稳定可比较

**下次何时再讨论**:不会 — 这是项目基础结构,后续所有会话都受益。

### 决策 2:为什么复刻参考实现而非另起炉灶

**问题**:参考实现 `local-ai-workflow` 已在 `E:\办公文件\01学习资料` 工作,本项目为什么还要重建?

**选项**:

- A:直接用参考实现,不重建
- B:在 `F:\soft\00selfmade\media-to-doc` 复刻并清理中文路径等历史包袱
- C:从零设计全新架构

**选择**:B

**原因**:

1. 中文路径 + 绝对路径在跨平台分发时是持续痛点(参考实现的 user 已多次踩坑)
2. 参考实现 110 测试 + 8 commit 已验证架构可用,无理由重设计
3. 全新设计风险高,迭代成本高

**下次何时再讨论**:若 L3+ 需要新架构再考虑 C,但 L1/L2 用 B 足够。

### 决策 3:为什么包名待定而非直接用 `media_to_doc`

**问题**:本项目目录叫 `media-to-doc`,Python 包名建议是 `media_to_doc`,但参考实现用了 `local_ai_workflow` 这种描述性命名。

**选项**:

- A:沿用 `media_to_doc`(目录名直接转换)
- B:用 `media_to_doc`(目录名)但更通用,如 `lecture_forge`
- C:沿用 `local_ai_workflow` 风格取新名

**选择**:未定,留给下一会话 + 用户决定

**原因**:命名影响 CLI 命令名 / import 路径 / PyPI 包名,需要用户偏好输入。

**下次何时再讨论**:Phase 1 骨架开始前必须定。

### 决策 4:为什么把 `_research/PROJECT_DESCRIPTION.md` 放在 `_research/` 而非根目录

**问题**:研究材料放在哪里?

**选项**:

- A:根目录顶层
- B:`_research/` 子目录(不进 git)
- C:`docs/research/`

**选择**:B

**原因**:

1. 全局指引:"`_research/` 不进 git,只在项目启动/调研阶段保留"
2. 项目根目录应保持工作区清洁,只放活跃文件
3. 下划线前缀约定为"研究/草稿",git 默认会追踪但可通过 `.gitignore` 屏蔽

**下次何时再讨论**:不会 — 这是命名约定,稳定。

---

## 5. 撞墙 / 未完成 / 已知问题

### 5.1 撞墙点

无。本次会话顺利完成所有任务,无技术撞墙。

### 5.2 TODO(下次会话继续)

按 `task.md` Phase 1 起:

- [ ] 与用户确认包名(`media_to_doc` 还是 `lecture_forge` 或其它)
- [ ] `uv init` + `pyproject.toml`
- [ ] 目录结构 `src/` + `tests/` + `workspace/` + `.learnings/`
- [ ] `.gitignore` 编写
- [ ] `README.md` 初版
- [ ] 第一个 commit:`chore: bootstrap project skeleton`

### 5.3 已知问题 / 技术债

- 用户偏好:用 pnpm(Python 优先 uv)—— 全局指引已说明,本项目一致沿用
- 用户的真实 LLM 是 MiniMax(不是 Claude/OpenAI),任何 provider 设计都必须支持 OpenAI 兼容协议
- SDXL Refiner 首次跑会下载约 6GB,首次用户体验可能慢(参考实现就踩过这个坑)
- 参考实现的 `feat/long-doc-skill-progressive-disclosure` 分支未合 master,本项目复刻时直接基于最新 commit `29ae2d5`

---

## 6. 测试状态

N/A — 本会话纯文档工作,无代码改动,无测试可跑。

下次会话第一个 commit 后,期望 `uv run pytest` 显示空(无测试)或 N 测试通过。

---

## 7. Git 状态

当前不是 git 仓库。本会话未做 git 操作。

下次会话开始时需 `git init` + `git add` + `git commit`(按 task.md Phase 1)。

---

## 8. 给下一个会话的提示

**新会话第一句话建议**:

```
承接 handoff-research-2026-07-17.md,继续 Phase 1 项目骨架。
请先确认包名(media_to_doc 还是其它?),然后 uv init 开始。
参考 _research/PROJECT_DESCRIPTION.md §3-4 了解完整架构和模块划分。
```

**主要任务**(Phase 1,见 `task.md`):

1. `uv init`
2. `pyproject.toml` 配置:`name = "media_to_doc"`(或用户确认的其它名字)+ `version = "0.1.0"` + `[project.scripts]` 占位
3. 目录结构 `src/media_to_doc/`, `tests/`, `workspace/inbox|`, `workspace/work/`, `.learnings/`
4. `.gitignore`:`_research/`, `workspace/`, `__pycache__/`, `.venv/`, `*.egg-info`, `dist/`, `build/`
5. `README.md` 初版
6. 第一个 commit

**别忘了**:

- 缩进 2 空格,Python 函数类型注解(全局偏好)
- 中文注释 / docstring 允许,但代码标识符用英文
- 关键路径用 `pathlib.Path`,不用 `os.path`
- 不要硬编码 `C:\Users\Duanyi\...`(全局红线)

**关键参考**:

- `_research/PROJECT_DESCRIPTION.md` §4 模块结构 — 复刻目标
- `_research/PROJECT_DESCRIPTION.md` §7 任务里程碑 — 各阶段 commit 历史
- 全局 `C:\Users\Duanyi\.claude\CLAUDE.md` — 沟通偏好 / 安全红线 / 会话健康
- `C:\Users\Duanyi\.claude\projects\F--soft-00selfmade-media-to-doc\memory\MEMORY.md`(如已存在)

---

## 9. 上下文参考链接

- `CLAUDE.md` — 项目级指引(本项目)
- `task.md` — 活跃 todo(本项目)
- `handoff-template.md` — 会话交接模板(本项目,长期复用)
- `_research/PROJECT_DESCRIPTION.md` — 参考实现逆向报告(25KB / 566 行 / 12 章节)
- 参考会话:`C:\Users\Duanyi\.claude\projects\E-------01----\2cf14f87-f1c6-4c3d-997a-5a5fc93869c2.jsonl`
- 关键 skill:`long-doc-processor`(在 `C:\Users\Duanyi\.claude\skills\long-doc-processor\`)

---

## 10. 自检清单

- [x] 本会话目标全部完成(4 份文档已落地)
- [x] 无未提交代码改动
- [x] 无未完成任务(下一会话从 Phase 1 开始,正常推进)
- [x] 测试状态明确(N/A)
- [x] Git 状态明确(非仓库,下次 init)
- [x] 下次会话第一句话建议清晰
- [x] 关键决策记录 4 条,带"为什么"
- [x] 上下文参考链接完整
