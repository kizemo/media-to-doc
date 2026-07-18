# handoff-le-design-2026-07-18.md — LE 落地快照

> **会话主题**:深入研究 Loop Engineering + 落地 L1+L2 核心模块原型
> **会话日期**:2026-07-17 末 ~ 2026-07-18 凌晨,~1.5 小时
> **会话状态**:**已完成,无阻塞**(23 测试全过)

---

## 1. 本次会话目标

用户最初要求:

> 请深入阅读两篇 aiec.fun 文章 + 深入研究 loop engineering + 在本项目中落地 loop engineering

---

## 2. 已完成

| 项 | 文件 | 状态 |
|---|---|---|
| 读文章 1(Loop Engineering:别再当 AI 的监工) | WebFetch | [x] |
| 读文章 2(Harness vs Loop Engineering) | WebFetch | [x] |
| 提取 LE 核心要点 | `_research/LE_KEYPOINTS.md` | [x] |
| 写 LE 详细落地设计 | `_research/LE_DESIGN.md` | [x] |
| **落地 LE L1+L2 核心模块原型** | `_research/le_prototype/` | [x] |
| ├─ `pipeline_logger.py`(L1+L3,210 行) | | [x] |
| ├─ `gatekeeper.py`(L2,95 行) | | [x] |
| ├─ `learnings.py`(L4,180 行) | | [x] |
| ├─ `runner.py`(L5,120 行) | | [x] |
| ├─ `tests/test_le.py`(23 测试全过) | | [x] |
| └─ `README.md`(原型说明) | | [x] |
| 同步 PRD 反映 LE | `PRD.md` §4.1.G | [x] |
| 同步 TDD 反映 LE | `TDD.md` §4.5(扩展为 6 个子节) | [x] |
| 同步 ROADMAP 反映 LE | `ROADMAP.md` Phase 5 | [x] |
| 同步 task.md 反映 LE | `task.md` Phase 0 + Phase 6 | [x] |

---

## 3. 已读 / 已写文件清单

### 已读(信息已缓存,下次会话无需重读)

- `https://www.aiec.fun/harness-engineering-vs-loop-engineering-agent-from-button-to-loop/`(WebFetch)
- `https://www.aiec.fun/loop-engineering%ef%bc%9a%e5%88%ab%e5%86%8d%e5%bd%93ai%e7%9a%84%e7%9b%91%e5%b7%a5%ef%bc%8c%e8%ae%a9%e5%ae%83%e8%87%aa%e5%b7%b1%e8%b7%91%e8%5b%b7%e6%9d%a5/`(WebFetch)

### 已写(本次会话新增)

- `F:/soft/00selfmade/media-to-doc/_research/LE_KEYPOINTS.md` — 13KB / 2 篇摘要
- `F:/soft/00selfmade/media-to-doc/_research/LE_DESIGN.md` — 23KB / 8 章节详细设计
- `F:/soft/00selfmade/media-to-doc/_research/le_prototype/pipeline_logger.py`
- `F:/soft/00selfmade/media-to-doc/_research/le_prototype/gatekeeper.py`
- `F:/soft/00selfmade/media-to-doc/_research/le_prototype/learnings.py`
- `F:/soft/00selfmade/media-to-doc/_research/le_prototype/runner.py`
- `F:/soft/00selfmade/media-to-doc/_research/le_prototype/tests/test_le.py`
- `F:/soft/00selfmade/media-to-doc/_research/le_prototype/README.md`

### 已修改

- `F:/soft/00selfmade/media-to-doc/PRD.md` §4.1.G(扩展 LE 节)
- `F:/soft/00selfmade/media-to-doc/TDD.md` §4.5(扩展为 6 个子节,引用原型验证结果)
- `F:/soft/00selfmade/media-to-doc/ROADMAP.md` Phase 5(增加"迁移"任务清单)
- `F:/soft/00selfmade/media-to-doc/task.md` Phase 0 + Phase 6 + 会话历史(记录本会话)

---

## 4. 关键决策与原因

### 决策 1:为什么 LE 落地在 `_research/le_prototype/` 而非 `src/media_to_doc/logger/`

**问题**:LE L1+L2 的代码应该放在哪里?

**选项**:

- A:立即 `uv init` 启动 Phase 0,在 `src/media_to_doc/logger/` 下实现
- B:在 `_research/le_prototype/` 下写独立可跑通的原型

**选择**:B

**原因**:

1. 当前 Phase 0 还没启动,没有 `src/` 目录,过早写代码会污染未来目录结构
2. 原型阶段重点是验证设计正确性,不需要完整依赖链
3. Phase 5 时整体迁移 4 个 .py 即可,降低 Phase 0 启动风险
4. 用户可在评审阶段独立跑测试,无需先初始化整个项目

**下次何时再讨论**:不会 — 这是阶段性策略,Phase 5 实施时迁移即可。

### 决策 2:为什么 Pattern-Key 用 `ShortType:keyword` 而非整个异常消息

**问题**:同一异常类型但消息不同(IP、端口、超时值),如何稳定识别?

**选项**:

- A:`ExceptionType:FullMessage`(消息差异导致不同 key,误判严重)
- B:`ExceptionType:FirstKeyword`(取第一个 token,稳定)
- C:仅 `ExceptionType`(太粗,不同 ConnectionError 无法区分)

**选择**:B(变体:`ShortType:keyword` — 去 "Error" 后缀,keyword 转小写去掉非字母数字)

**原因**:

1. 实际测试验证:3 个 `ConnectionError("Ollama ...")` 都能产出相同 key(`Connection:ollama`)
2. 不同服务(`Ollama` / `Whisper`)产生不同 key,跨任务聚合准确
3. 实现简单,字符串操作即可

**下次何时再讨论**:如果未来需要更细粒度分类(如不同阶段、不同参数),可考虑加 phase 前缀。

### 决策 3:为什么 `escalate_recurring_errors` 必须幂等

**问题**:每次 run 完成后会扫描 ERRORS.md,如何避免重复写入同一条目?

**选项**:

- A:每次都覆盖写入(简单但丢失历史)
- B:检查标题已存在则跳过(幂等)
- C:用 timestamp 去重(不可靠,内容相同 timestamp 不同仍重复)

**选择**:B

**原因**:

1. 测试 `test_escalate_is_idempotent` 验证:第二次相同输入返回空列表
2. 用 `## [key]` 标题匹配,简单且可读
3. 用户多次跑同主题不会重复 spam `.learnings/ERRORS.md`

**下次何时再讨论**:不会 — 这是正确性要求,不变。

### 决策 4:为什么 Gatekeeper 用 4 项机器可验证检查

**问题**:停止条件应该是什么?

**选项**:

- A:"感觉差不多"(文章中明确反对)
- B:LLM-as-judge(独立模型评估,但成本高、慢)
- C:确定性规则(文件存在 / 大小 / 章节数 / 图片引用)

**选择**:C

**原因**:

1. 文章核心原则:"停止条件必须是机器可验证的命令,不是'感觉'"
2. 实现简单,无需额外 LLM 调用
3. 测试可独立跑(mock 文件即可)
4. 未来 L3 可加 LLM-as-judge 作为补充,但 P0 不需要

**下次何时再讨论**:L3 Multi-Agent 时考虑加二次 LLM 验证。

---

## 5. 撞墙 / 未完成 / 已知问题

### 5.1 撞墙点(下次会话语境)

无。本次会话顺利完成所有任务,无技术撞墙。

### 5.2 TODO(下次会话继续)

按 `task.md` Phase 1 起:

- [ ] 评审本会话的 PRD/TDD/ROADMAP/LE_DESIGN/le_prototype
- [ ] 与用户确认是否启动 Phase 0(uv init + 项目骨架)
- [ ] Phase 0 完成后启动 Phase 1 核心流水线
- [ ] Phase 5 时迁移 `_research/le_prototype/` → `src/media_to_doc/logger/`

### 5.3 已知问题 / 技术债

- LE 原型 `runner.py` 用 mock stage,真实 stage 需 Phase 1 实施后接入
- `assess_llm_health` 需要各 LLM provider 主动上报 `calls` / `failures` 计数
- Gatekeeper 阈值(`lecture.md >= 100 bytes`、`final.html >= 1000 bytes`)是启发式,可能需根据实际数据调整
- i18n 未实现,LEARNINGS.md 当前中文/英文混排
- 测试覆盖 23 用例,目标 Phase 5 后 ≥ 50 用例

---

## 6. 测试状态

```
$ cd _research/le_prototype && python -m pytest tests/ -v
============================= test session starts ==============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
collected 23 items

tests/test_le.py::TestPipelineLogger::test_init_creates_memory_file PASSED
tests/test_le.py::TestPipelineLogger::test_append_stage_writes_row PASSED
tests/test_le.py::TestPipelineLogger::test_write_error_creates_pattern_key PASSED
tests/test_le.py::TestPipelineLogger::test_finalize_writes_run_json PASSED
tests/test_le.py::TestPipelineLogger::test_extract_pattern_key_stable PASSED
tests/test_le.py::TestTimedStage::test_success_marks_completed PASSED
tests/test_le.py::TestTimedStage::test_failure_marks_failed_and_writes_error PASSED
tests/test_le.py::TestTimedStage::test_exception_propagates PASSED
tests/test_le.py::TestGatekeeper::test_all_pass PASSED
tests/test_le.py::TestGatekeeper::test_missing_lecture_md PASSED
tests/test_le.py::TestGatekeeper::test_too_few_chapters PASSED
tests/test_le.py::TestGatekeeper::test_missing_final_html PASSED
tests/test_le.py::TestGatekeeper::test_missing_image_refs PASSED
tests/test_le.py::TestLearnings::test_write_runtime_error_extracts_pattern PASSED
tests/test_le.py::TestLearnings::test_escalate_below_threshold_no_action PASSED
tests/test_le.py::TestLearnings::test_escalate_at_threshold_promotes PASSED
tests/test_le.py::TestLearnings::test_escalate_is_idempotent PASSED
tests/test_le.py::TestLearnings::test_find_known_pattern_keys PASSED
tests/test_le.py::TestLearnings::test_assess_llm_health_no_runs PASSED
tests/test_le.py::TestLearnings::test_assess_llm_health_high_failure_rate PASSED
tests/test_le.py::TestLearnings::test_post_pipeline_hook PASSED
tests/test_le.py::TestRunPipelineEnd2End::test_success_path PASSED
tests/test_le.py::TestRunPipelineEnd2End::test_failure_path_writes_error_and_blocks PASSED

============================= 23 passed in 1.82s ==============================
```

---

## 7. Git 状态

当前不是 git 仓库。本会话未做 git 操作。

下次会话开始时需 `git init` + `git add` + `git commit`(按 task.md Phase 1)。

建议首次 commit 内容:

```
chore: bootstrap project skeleton

- PRD.md / TDD.md / ROADMAP.md
- _research/ (PROJECT_DESCRIPTION / LE_KEYPOINTS / LE_DESIGN / le_prototype)
- CLAUDE.md / task.md / handoff-template.md / handoff-*.md
- .gitignore
```

---

## 8. 给下一个会话的提示

**新会话第一句话建议**:

```
承接 handoff-le-design-2026-07-18.md,准备启动 Phase 0 项目骨架。
请先评审 PRD/TDD/ROADMAP 和 LE 原型(在 _research/le_prototype/ 跑测试验证),
然后 uv init + pyproject.toml + 目录结构,提交第一个 commit。
```

**主要任务**(Phase 1,见 `task.md`):

1. `uv init` + `pyproject.toml`(`name = "media_to_doc"`,extras 含 imagegen)
2. 目录结构 `src/media_to_doc/`,`tests/`,`workspace/`,`.learnings/`
3. `.gitignore`(屏蔽 `_research/`、`workspace/`、`__pycache__/`、`.venv/`)
4. `README.md` 初版
5. 第一个 commit:`chore: bootstrap project skeleton`

**评审重点**:

- PRD §4.1.G 是否符合产品目标(LE 5 层完整?)
- TDD §4.5 接口定义是否清晰(便于 Phase 5 实施)
- ROADMAP Phase 5 工作量(6 天够吗?原型已落地可压缩到 4 天)
- LE 原型测试是否真的验证了 LE 五层(推荐:跑一次 `test_le.py` 看到所有 23 用例绿)

**别忘了**:

- 缩进 2 空格,Python 函数类型注解(全局偏好)
- 包名暂定 `media_to_doc`(用户已确认 brand)
- API Key 加密用 Windows DPAPI
- LE 原型先不动,Phase 5 再迁移

**关键参考**:

- `_research/LE_DESIGN.md` §3-4 — LE 详细设计
- `_research/le_prototype/README.md` — 原型说明 + 迁移清单
- `PRD.md` §4.1.G — LE 功能定位
- `TDD.md` §4.5 — LE 模块接口
- `ROADMAP.md` Phase 5 — LE 实施节奏
- 全局 `C:\Users\Duanyi\.claude\CLAUDE.md` — 沟通偏好 / 安全红线

---

## 9. 上下文参考链接

- `CLAUDE.md` — 项目级指引
- `task.md` — 活跃 todo(含本会话历史)
- `PRD.md` — 产品需求(378 行)
- `TDD.md` — 技术设计(1061 行)
- `ROADMAP.md` — 执行规划(563 行)
- `handoff-template.md` — 长期复用模板
- `handoff-research-2026-07-17.md` — 上一个会话(逆向研究)
- `_research/PROJECT_DESCRIPTION.md` — 参考实现逆向报告
- `_research/LE_KEYPOINTS.md` — LE 两篇文章摘要
- `_research/LE_DESIGN.md` — LE 详细设计
- `_research/le_prototype/` — LE 原型(23 测试全过)

---

## 10. 自检清单

- [x] 本会话目标全部完成(LE 设计 + L1+L2 原型 + 文档同步)
- [x] 无未提交代码改动(原型在 `_research/`,不进 git)
- [x] 无未完成任务(下次会话从 Phase 1 开始)
- [x] 测试状态明确(23 passed in 1.82s)
- [x] Git 状态明确(非仓库,下次 init)
- [x] 下次会话第一句话建议清晰
- [x] 关键决策记录 4 条,带"为什么"
- [x] 上下文参考链接完整
- [x] LE 落地可独立跑通(`cd _research/le_prototype && python -m pytest tests/ -v`)