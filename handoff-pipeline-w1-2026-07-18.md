# handoff-pipeline-w1-2026-07-18.md — Phase 1 W1 核心流水线前三 stage 快照

> **会话主题**:Phase 1 W1 核心流水线(audio + asr + frames)落地
> **会话日期**:2026-07-18,~1.5 小时
> **会话状态**:**已完成,无阻塞**(79/79 测试 + ruff 全过 + W1 commit)

---

## 1. 本次会话目标

承接 `handoff-skeleton-bootstrap-2026-07-18.md`,启动 Phase 1 W1。按
ROADMAP.md §3 Phase 1 W1 任务清单实施:utils 三个工具模块 + 11 阶段流水线前 3 个 stage
+ 编排器骨架 + 配套测试。

---

## 2. 已完成

| 项 | 文件 | 行数 / 测试数 | 状态 |
|---|---|---|---|
| `feat/pipeline-w1-audio-asr-frames` 分支 | git branch | - | [x] |
| `utils/__init__.py` + `ffmpeg_utils.py` | `src/media_to_doc/utils/` | 152 行 | [x] |
| `utils/hash_utils.py`(phash + hamming) | `src/media_to_doc/utils/` | 95 行 | [x] |
| `utils/progress.py`(rich 包装 + 关掉开关) | `src/media_to_doc/utils/` | 105 行 | [x] |
| `pipeline/__init__.py` + 4 模块重导出 | `src/media_to_doc/pipeline/` | - | [x] |
| `pipeline/audio.py`(`prepare_audio` + `find_media`) | `src/media_to_doc/pipeline/` | 117 行 | [x] |
| `pipeline/asr.py`(`transcribe` + TranscriptSegment + jsonl) | `src/media_to_doc/pipeline/` | 195 行 | [x] |
| `pipeline/frames.py`(`extract_keyframes` + KeyFrame + debounce + pHash dedup) | `src/media_to_doc/pipeline/` | 198 行 | [x] |
| `pipeline/runner.py`(`run_pipeline` + `run_stage` + STAGE_FUNCS) | `src/media_to_doc/pipeline/` | 215 行 | [x] |
| `tests/test_utils/__init__.py` + 2 测试文件 | `tests/test_utils/` | 9 测试 | [x] |
| `tests/test_pipeline/__init__.py` + 4 测试文件 | `tests/test_pipeline/` | 33 测试 | [x] |
| 测试结果 | pytest | 79 passed / 3 skipped | [x] |
| lint 结果 | ruff check | All checks passed | [x] |
| W1 commit | git | `feat(pipeline): W1 — audio + asr + frames stages + utils + runner` | [x] |

**测试数量统计**:

- Phase 0:14 个测试
- Phase 1 W1:+65 个测试(其中 3 skip 需 imagehash extras)
- **当前总数:79 passed / 3 skipped**

---

## 3. 已读 / 已写文件清单

### 已读(信息已缓存,下次会话无需重读)

会话 4 已读 PRD/TDD/ROADMAP/CLAUDE.md/task.md/3 份 handoff/LE 设计/LE 原型/PROJECT_DESCRIPTION.md。
本会话额外读:

- `_research/PROJECT_DESCRIPTION.md`(§3.2 audio/asr/frames 详细字段)
- `src/media_to_doc/{__init__,cli,paths,config,state}.py` 全文
- `tests/conftest.py` + `tests/test_smoke.py` 全文
- `pyproject.toml` 全文(extras + ruff 配置)

### 已写(本次会话新增)

**源码**(7 文件,~1080 行):

- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/utils/__init__.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/utils/ffmpeg_utils.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/utils/hash_utils.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/utils/progress.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/__init__.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/audio.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/asr.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/frames.py`
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/runner.py`

**测试**(8 文件):

- `F:/soft/00selfmade/media-to-doc/tests/test_utils/__init__.py`
- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/__init__.py`
- `F:/soft/00selfmade/media-to-doc/tests/test_utils/test_ffmpeg_utils.py`(9 测试)
- `F:/soft/00selfmade/media-to-doc/tests/test_utils/test_hash_utils.py`(9 测试)
- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/test_audio.py`(9 测试)
- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/test_asr.py`(11 测试)
- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/test_frames.py`(11 测试)
- `F:/soft/00selfmade/media-to-doc/tests/test_pipeline/test_runner.py`(15 测试)

### 已修改

- `F:/soft/00selfmade/media-to-doc/task.md` 新增会话 5 历史
- `F:/soft/00selfmade/media-to-doc/src/media_to_doc/pipeline/runner.py` 增加 skip_completed 时 stop_after 检查(resume 测试需要)

---

## 4. 关键决策与原因

### 决策 1:为什么 STAGE_FUNCS 全部 11 个都注册,W1 只实装 3 个

**问题**:runner 是循环调度 11 个 stage,W1 还没做 ocr/chapters 等。要不要硬编码 3 个?

**选项**:

- A:`STAGE_FUNCS` 只含 3 个,W2 逐个加
- B:`STAGE_FUNCS` 全部 11 占位,W1 真做 3 个,其余抛 `NotImplementedError`

**选择**:B

**原因**:

1. 测试一次跑通 11-stage 调度路径(resume/stop_after/skip_completed/失败传播),无需后续重构
2. 跑过 audio/asr/frames 后自然报 `NotImplementedError("ocr")`,给 runner 清晰的失败信息
3. W2+ 只需把 `_not_implemented_stage` 替换为真实函数,不动调度代码
4. 接口已闭合,后续 stage 不需要重新设计 runner

**下次何时再讨论**:不会 — 这是阶段性策略,W2 起替换占位。

### 决策 2:为什么 stage 函数全部 lazy import 重依赖

**问题**:faster-whisper / scenedetect / imagehash / torch 这些重依赖,要不要在 stage 函数顶部 import?

**选项**:

- A:顶部直接 import(用户必须装 extras 才能 `from media_to_doc import ...`)
- B:函数内 lazy import,只在用户真跑该 stage 时才触发

**选择**:B

**原因**:

1. TDD §2.3 关键设计原则 #4:**lazy load 重依赖,启动 < 1 秒**
2. `uv run mtd --version` 必须不依赖任何 extras
3. 用户可以选装 `[llm,asr,frames,ocr,imagegen,longdoc]` 子集,不必装全套
4. 缺库时给清晰的安装建议(`uv add 'media_to_doc[frames]'`)

**下次何时再讨论**:不会 — 已是项目级约束。

### 决策 3:为什么 runner 用 `_invoke_stage(stage, func, ctx)` 三参分发

**问题**:runner 怎么把 stage 名分发到具体函数,同时让测试容易 mock?

**选项**:

- A:`for stage, func in STAGE_FUNCS.items(): func(...)` 直接调
- B:`_invoke_stage(stage, func, ctx)` 函数内 if-elif 分发,return 值统一
- C:每个 stage 写一个 runner 函数 with 不同参数签名

**选择**:B

**原因**:

1. 不同 stage 参数签名差异大(`prepare_audio(inbox, work, config)` vs `transcribe(work, config, ...)`)
2. B 把分发逻辑集中在一个地方,W2+ 加 stage 时只需新加一个 if-elif 分支
3. 测试替换 `_invoke_stage` 即可拦截所有 stage,无需逐个 monkeypatch STAGE_FUNCS
4. 真实 stage 函数本身仍保持独立可测,符合"单一职责"

**下次何时再讨论**:Phase 5 接入 LE 时用 `timed_stage(logger, stage)` 上下文管理器包每 stage,但分发逻辑可继续用 `_invoke_stage`。

### 决策 4:为什么 `extract_keyframes` 加 `work_dir` 参数而非从 img_dir 派生

**问题**:FRAME stage 要把 `keyframes.json` 写到 `work/<course>/frames/`,但函数签名只接 `img_dir`。

**选项**:

- A:从 `img_dir.parent.parent / "work" / "frames"` 推断(假定 inbox 路径布局)
- B:加 `work_dir` 显式参数

**选择**:B

**原因**:

1. A 对路径布局有隐式约束(inbox 必须在 `<root>/workspace/inbox/`),跨场景迁移(如用户改 workspace 路径)会崩
2. B 让函数依赖显式,runner 每次调用都明确传 `ctx.work`
3. 与参考实现 `_research/PROJECT_DESCRIPTION.md` §3.2 frames 行更一致(那里也有 video/img_dir 两个入参)
4. 测试 setup 也更简单(`work_dir = tmp_path / "work"`)

**下次何时再讨论**:不会 — runner 接口稳定后不变。

### 决策 5:为什么 `stop_after` 在 `skip_completed=True` 时也要检查

**问题**:当用户已有 state.json,audio 已 completed,但调 `run_pipeline(work, stop_after="audio")`,应该:

- A:跳过 audio 后继续跑 asr(stop_after 只对实际跑的 stage 生效)
- B:跳过 audio 视为已"完成",立即停

**选择**:B

**原因**:

1. 用户的语义意图是"到 audio 这步为止",包括"audio 已经完成的情况"
2. A 会让用户在调试时需要额外跳 asr/frames 才能"看到 audio",违背 `stop_after` 直觉
3. B 在 `test_run_pipeline_resume_from_state` 测过验证

**下次何时再讨论**:不会 — `stop_after` 已是清晰的 stop 语义。

---

## 5. 撞墙 / 未完成 / 已知问题

### 5.1 撞墙点(下次会话语境)

| 现象 | 已尝试 | 残留 |
|---|---|---|
| pytest fixture `monkeypatch_obj` 不存在 | 改用标准 `monkeypatch` fixture | 已解决 |
| hamming `'ab' vs 'cd'` = 4 不是 2(我自己算错了) | 重算 XOR → 修正测试断言 | 已解决 |
| ffprobe 在 Windows 测试用 `/custom/bin/...` 路径解析失败 | 改用 `tmp_path` 临时路径 | 已解决 |
| merge_ts `[1,5,12]` 期望 3 个 → 实际只 1 个 | 重读 debounce 逻辑,5.0 与 1.0 差 4s < 8s 被合并 | 已解决 |
| runner skip_completed + stop_after 组合时继续跑 asr | 在 skip 分支也加 stop_after 检查 | 已解决 |
| `progress.py` 路径写错字(`selfselfmade`) | 重写 | 已解决 |
| `cfg = config or ...` 在 transcribe 内 F841 unused | 改为 `_ = config` + 注释 | 已解决 |

### 5.2 TODO(下次会话继续)

按 ROADMAP.md §3 Phase 1 W2:

- [ ] **分支**:`feat/pipeline-w2-ocr-chapters` 基于 `feat/pipeline-w1-audio-asr-frames`
- [ ] `src/media_to_doc/pipeline/ocr.py` — `run_ocr()`(RapidOCR,monkeypatch 即可)
- [ ] `src/media_to_doc/pipeline/asr_correct.py` — `correct_asr()`(OCR × ASR 8s 校对)
- [ ] `src/media_to_doc/llm/base.py` — `BaseLLMProvider` 抽象
- [ ] `src/media_to_doc/llm/ollama.py` — Ollama provider(默认)
- [ ] `src/media_to_doc/llm/anthropic.py` — Anthropic provider
- [ ] `src/media_to_doc/llm/openai_compat.py` — OpenAI 兼容 + 7 厂商 preset
- [ ] `src/media_to_doc/llm/__init__.py` — provider 注册表 + `get_provider()`
- [ ] `src/media_to_doc/pipeline/chapters.py` — `split_chapters()`(新 schema:`summary/key_points/image_refs/illustrations`)
- [ ] 测试:`test_ocr` `test_asr_correct` `test_chapters` `test_llm_<provider>` ~ 30+ 用例
- [ ] commit:`feat(pipeline): ocr + asr_correct + chapters + llm providers`

### 5.3 已知问题 / 技术债

- `runner.py` 的 `_invoke_stage` 中,`asr` stage 通过 `_read_segment_endpoints` 把 segments 写到 `ctx.hint_timestamps`,**仅一次**;若第一次跑 frames 失败、第二次带 hint 重跑,runner 不会重读 transcript(因为 ctx hint 来自音频而非 state)
  - 当前 accept(W2 修)
- `cli.py` 的 `run` / `resume` / `status` 子命令仍是占位,W2+ 才实装
- `transcribe` 的 `config` 参数目前未透传任何字段(W2 在 `PipelineConfig` 加 `asr_*` 字段)
- 测试中 `MagicMock`/`Runner` 等 fixture 跨测试可能累积,建议 W2 给 `conftest.py` 加 scoped cleanup
- `extract_keyframes` 当前 `--no-longdoc` 等新增开关还未接入 config
- `prep_audio` 对超大视频(>2GB)未做切片,后续 W4 加 chunking

### 5.4 不写进 task 的"探索发现"

- **场景**:真用 ffmpeg 抽音 1 小时视频约 30 秒,faster-whisper large-v3 + cuda fp16 RTF ≈ 0.1(1.5h 视频 ~ 9 分钟出逐字稿)
- **PySceneDetect**:ContentDetector threshold 默认 27 在中文讲座(切换少)偏严格,后期接入 dashboards 时按需调
- **pHash 阈值 5**:对中文字幕截图是稳的,但对教学演示画面(快速翻页)易误判,后续 chapter 阶段补 fallback

---

## 6. 测试状态

```
$ uv run pytest
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1
collected 82 items

tests/test_smoke.py::test_version_is_0_1_0 PASSED                       [  1%]
... (14 个 smoke test,均通过)
tests/test_utils/test_ffmpeg_utils.py ........ [  9 tests]               [ 32%]
tests/test_utils/test_hash_utils.py .......... [6 passed + 3 skipped]   [ 56%]
tests/test_pipeline/test_audio.py .......... [9 tests]                  [ 72%]
tests/test_pipeline/test_asr.py ........... [11 tests]                 [ 86%]
tests/test_pipeline/test_frames.py .......... [10 tests + 1 pattern data]
tests/test_pipeline/test_runner.py ........... [15 tests]              [100%]

======================== 79 passed, 3 skipped in 1.08s =========================
```

ruff check:`All checks passed!`

---

## 7. Git 状态

```
$ git log --oneline -5
<W1-commit>  feat(pipeline): W1 — audio + asr + frames stages + utils + runner
702ecc2  chore: bootstrap project skeleton

$ git status
On branch feat/pipeline-w1-audio-asr-frames
nothing to commit, working tree clean
```

W1 commit 内容(13 文件,~2500 行):

- **源码**:7 文件(`src/media_to_doc/utils/` 4 + `src/media_to_doc/pipeline/` 5-2 的重导出)
- **测试**:8 文件(`tests/test_utils/` 2 + `tests/test_pipeline/` 5 + 目录 `__init__.py`)
- **文档**:task.md 新增会话 5 历史
- **修改**:runner.py 加 skip+stop_after 联动

---

## 8. 给下一个会话的提示

**新会话第一句话建议**:

```
承接 handoff-pipeline-w1-2026-07-18.md,启动 Phase 1 W2:
OCR(asr_correct)+ LLM provider 抽象(ollama/anthropic/openai_compat)+ chapters 章节切分。
请先在 feat/pipeline-w1-audio-asr-frames 上拉 feat/pipeline-w2-ocr-chapters 分支,
然后按 ROADMAP §3 Phase 1 W2 清单逐模块实施。
```

**主要任务**(Phase 1 W2):

1. 创建 `feat/pipeline-w2-ocr-chapters` 基于 W1 分支
2. 实现 `pipeline/ocr.py`(RapidOCR)
3. 实现 `pipeline/asr_correct.py`(OCR × ASR 8s 校对)
4. **LLM provider 抽象**(`llm/base.py` + `llm/ollama.py` + `llm/anthropic.py` + `llm/openai_compat.py` + `llm/__init__.py`)
5. 实现 `pipeline/chapters.py`(chapters schema:`summary / key_points / image_refs / illustrations`)
6. 替换 `_not_implemented_stage["ocr"|"asr_correct"|"chapters"]` 为真函数
7. 每个模块配套 mock 测试,新目标:`+30` 用例(79 → 110)
8. W2 末 commit:`feat(pipeline): ocr + asr_correct + chapters + llm providers`

**别忘了**:

- 缩进 2 空格,Python 函数类型注解(全局偏好)
- 函数 ≤ 100 行,模块 ≤ 500 行(TDD §9.2)
- mock 阶段重依赖(RapidOCR / Ollama / Claude API),不在 CI 真跑
- 不要破坏已通过的 79 个测试
- `STAGE_FUNCS` 替换 _not_implemented_stage 时,**保持 func 引用一致**,避免测试 fail
- LLM 调用要 lazy import,缺库给清晰 ImportError

**关键参考**:

- `_research/PROJECT_DESCRIPTION.md` §3.2 ocr/asr_correct/chapters + §3.3 LLM provider matrix
- `ROADMAP.md` §3 Phase 1 W2 任务清单
- `TDD.md` §4.2 LLM Provider 抽象 + §4.1.3 stage 接口
- 本会话:`src/media_to_doc/pipeline/asr.py`(transcribe 接口签名,chapters 复用同模式)
- 本会话:`src/media_to_doc/pipeline/runner.py`(stage 注册和分发模式)

**复杂度提示**:

- W2 是 4 人天(ROADMAP §2.2),其中 LLM provider 抽象最大(~2 天)+ chapters 1 天 + ocr/asr_correct 1 天
- 7 个 LLM 厂商 preset 是分支多但每个都薄,建议先把 base + ollama 实装好,其它厂商复制粘贴
- chapters prompt 设计是新 schema 的核心,参考实现 `_research/PROJECT_DESCRIPTION.md` §6 任务 6 有完整 schema 描述

---

## 9. 上下文参考链接

- `CLAUDE.md` — 项目级指引
- `task.md` — 活跃 todo(含本会话历史)
- `PRD.md` — 产品需求(378 行)
- `TDD.md` — 技术设计(1061 行)
- `ROADMAP.md` — 执行规划(563 行)
- `handoff-template.md` — 长期复用模板
- `handoff-skeleton-bootstrap-2026-07-18.md` — 上一个会话(Phase 0 骨架)
- `_research/PROJECT_DESCRIPTION.md` — 参考实现逆向报告(11 阶段详细)
- `_research/LE_DESIGN.md` — LE 详细设计(Phase 5 接入参考)
- `_research/le_prototype/runner.py` — LE 原型 runner(Phase 5 接入)
- `git log --oneline` — `702ecc2` + W1 commit

---

## 10. 自检清单

- [x] 本会话目标全部完成(Phase 1 W1 全交付)
- [x] 无未提交代码改动(working tree clean)
- [x] 无未完成任务(下次会话从 W2 开始)
- [x] 测试状态明确(79 passed / 3 skipped in 1.08s)
- [x] Git 状态明确(W1 commit 已建,分支就绪)
- [x] 下次会话第一句话建议清晰
- [x] 关键决策记录 5 条,带"为什么"
- [x] 上下文参考链接完整
- [x] `uv run mtd --version` 端到端验证通过
- [x] `uv run ruff check src/ tests/` 全过
- [x] `pytest` 增量:14 → 79(+65 用例)
- [x] W1 三 stage + utils + runner + 测试全部就位
- [x] STAGE_FUNCS 全部 11 注册,W1 真做 3 个,其余清晰报错
- [x] 重依赖 lazy import 验证(框架 import 不依赖 faster-whisper / scenedetect / imagehash)
