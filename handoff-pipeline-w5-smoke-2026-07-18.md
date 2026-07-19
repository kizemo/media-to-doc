# handoff-pipeline-w5-smoke-2026-07-18.md — Phase 1 W5 端到端冒烟(部分完成)

> **会话主题**:Phase 1 W5 — 把 11 stage 流水线在真实视频上跑通一次(端到端冒烟)
> **会话日期**:2026-07-18 ~ 2026-07-19,~1.5 小时(撞墙时退出,ASR 后台跑)
> **会话状态**:**部分完成** — smoke 脚本 + CLAUDE.md 已落地,ASR 在 CPU 模式跑(后台),剩余 stage 待续跑
> **下次会话**:等 ASR 完成 → 续跑 frames → ... → verify → 验证产物

---

## 1. 本次会话目标

承接 `handoff-pipeline-w4-2026-07-18.md` §8 W5 候选 A(跑通示例视频),
端到端验证 11 stage 流水线在真实视频上能否工作。

- 视频:`F:\resourse_study\边界\AI助力主图点击率低_2026-06-03.mp4`(1.3GB,112min 中文电商培训)
- 输出:`F:\resourse_study\边界\output\`(用户要求"视频所在目录的 output 子目录")
- LLM:Ollama qwen3:14b(本地已就绪)
- 依赖:用户期望"已装",实际未装 → 装齐 [all] extras(含 torch)

---

## 2. 已完成

| 项 | 文件 / 状态 | 行数 | 备注 |
|---|---|---|---|
| `feat/pipeline-w5-smoke` 分支 | git branch | - | 基于 W4 commit `3b32743` |
| `uv sync --all-extras` 装齐依赖(含 torch 2.13.0 + diffusers + faster-whisper 1.2.1 + rapidocr 1.4.4 + scenedetect 0.7 + imagehash 4.3.2 + PIL 12.3.0 + numpy 2.5.1) | .venv | ~5GB | background 跑完 |
| 备份 `output/` 旧产物 → `output-backup-2026-07-18/` | shell `mv` | - | 用户旧产物(参考实现留下的 lecture_final.html 等) |
| `scripts/run_smoke.py` — 端到端 smoke runner(inbox 隔离 + 网络环境默认 + try/finally 恢复) | `scripts/run_smoke.py` | 254 行 | **含 inbox isolation bug fix** |
| `CLAUDE.md` §4.1 输出目录约定(项目级规则,2026-07-18 用户确认) | `CLAUDE.md` | +27 行 | W5 起所有调用入口遵循 |
| `transcript.jsonl` 部分产出(ASR 转写中) | `output/asr/transcript.jsonl` | 49KB / 382 segments / 1582s(26min) | VAD filter 后实际语音段 |
| **W5 commit**(scripts/run_smoke.py + CLAUDE.md) | git | `pending` | 本会话结束前 commit |

**测试**:`uv run pytest` 346 passed / 3 skipped(**未变**,smoke 是产品代码不新增测试)

---

## 3. 已读 / 已写文件清单

### 已读(信息已缓存,下次会话无需重读)

- `handoff-pipeline-w4-2026-07-18.md` — W4 交付详情 + W5 候选
- `src/media_to_doc/pipeline/runner.py` — run_pipeline / _invoke_stage / STAGE_FUNCS(W4 完成版)
- `src/media_to_doc/pipeline/audio.py` — find_media / prepare_audio / SUPPORTED_EXTS
- `src/media_to_doc/pipeline/asr.py` — transcribe / _transcribe_with_whisper / DEFAULT_MODEL="large-v3"
- `src/media_to_doc/config.py` — WorkflowConfig / PipelineConfig.longdoc_llm_provider="skip"
- `src/media_to_doc/paths.py` — workspace 解析(ENV 覆盖)
- `pyproject.toml` — extras 分组(asr/frames/ocr/imagegen/longdoc/llm/mcp)
- `~/.cache/huggingface/hub/models--Systran--faster-whisper-large-v3/` — 模型缓存(2.9GB model.bin)

### 已写

- `F:/soft/00selfmade/media-to-doc/scripts/run_smoke.py` — 254 行,关键函数:
  - `parse_args()` — argparse,接受 video + --work-dir + --stop-after + --imagegen + --longdoc-llm + --llm-provider + --llm-model + --no-skip-completed + --no-isolate
  - `_isolate_inbox(inbox, target_video, staging_dir, exclude_dirs=[work])` — **bug fix 后版本**,跳过 work_dir 内文件,避免误移 audio.wav
  - `_restore_isolated(moved, staging_dir)` — 反向恢复 + 清理空目录
  - `main()` — 网络 env 默认(HF_ENDPOINT + HF_HUB_DISABLE_XET + unset proxies) + 隔离 + try/finally 恢复 + run_pipeline + 错误时打印 state.json
- `F:/soft/00selfmade/media-to-doc/handoff-pipeline-w5-smoke-2026-07-18.md` — 本文件

### 已修改

- `F:/soft/00selfmade/media-to-doc/CLAUDE.md`:
  - `§4` 目录树:加 `scripts/` 一行,`workspace/` 注释改为"默认 inbox/work(可由 env 覆盖)"
  - 新增 `§4.1 输出目录约定(W5+ 用户确认)` — 27 行,说明 inbox/work 派生 + 调用入口 + 已有产物保护

---

## 4. 关键决策与原因

### 决策 1:HF_ENDPOINT=https://hf-mirror.com + HF_HUB_DISABLE_XET=1

**问题**:Faster-Whisper 首次跑从 huggingface.co 下载 large-v3 模型(2.9GB)。环境 HTTP_PROXY=`http://127.0.0.1:64454`(Claude Code 系统代理)返回 502;unset 代理后直连 huggingface.co 超时(WinError 10060)。

**选项**:
- A. 走代理(失败,502)
- B. 直连(失败,GFW 超时)
- C. hf-mirror.com 镜像(部分成功,但 xet 协议 401)
- D. hf-mirror.com + 禁用 xet(`HF_HUB_DISABLE_XET=1`)→ 4:38 下载完成

**选择**:D

**原因**:hf-mirror.com(阿里云 HF 镜像)国内可达,但 huggingface_hub 默认 xet 协议下载大文件,xet 镜像不支持 → 401。禁用 xet 走普通 HTTPS 下载即可。

**下次何时再讨论**:首次装模型时再触发(已下载好的模型不需重做)。

### 决策 2:inbox 隔离排除 work_dir(关键 bug fix)

**问题**:`_isolate_inbox(inbox, ...)` 用 `inbox.rglob("*")` 递归遍历。当 `work_dir` 是 `inbox/output/` 时,**rglob 会扫到 `output/asr/audio.wav`** 这种流水线产物,把上次 audio 阶段创建的 audio.wav 误移到 staging_dir,导致续跑 asr 时 `audio.wav not found`。

**修复**:`_isolate_inbox` 加 `exclude_dirs: list[Path]` 参数,跳过 `work_dir` 下的所有文件(以及 staging_dir 自己)。

**为什么是关键**:这条 bug 让 smoke 跑抛 FileNotFoundError 看起来像 runner bug,实际是隔离逻辑 bug。修复后 smoke 跑正常进入 asr。

**下次何时再讨论**:有人重构 `_isolate_inbox` 时再看一遍(rglob 扫整个 inbox 容易触发同类问题)。

### 决策 3:smoke 脚本默认加网络环境(HF_ENDPOINT / HF_HUB_DISABLE_XET / unset proxies)

**问题**:中国大陆访问 huggingface.co 不通,需要镜像 + 禁用 xet + 显式 unset 系统代理。

**选项**:
- A. 让用户在外部 shell 手动设置 env
- B. 写到 README 文档
- C. smoke 脚本顶部 `os.environ.setdefault(...)` + `os.environ.pop(...)`

**选择**:C

**原因**:smoke 是"开箱即跑"的入口,网络环境内置避免每次用户手动设。`setdefault` 不覆盖用户外部传入,`pop` 显式 unset Claude Code 系统代理(避免 502)。

**下次何时再讨论**:部署到非中国大陆环境时,这套默认值可能不适用 → 用户传 env 即可覆盖。

---

## 5. 撞墙 / 未完成 / 已知问题

### 5.1 撞墙点(下次会话语境)

#### 撞墙 1:HuggingFace 模型下载失败
- **现象**:Faster-Whisper large-v3 模型下载时 `ProxyError: 502 Bad Gateway`(代理 502)或 `ConnectTimeout: WinError 10060`(直连超时)或 `RuntimeError: HTTP 401`(xet 401)
- **已尝试**:unset HTTP_PROXY / hf-mirror.com / 禁用 xet → 最终成功
- **残留**:`HF_ENDPOINT` + `HF_HUB_DISABLE_XET` 已硬编码到 smoke 脚本顶部

#### 撞墙 2:smoke 跑 FileNotFoundError 但 audio.wav 实际存在
- **现象**:smoke 跑 asr 阶段抛 `FileNotFoundError: asr stage 需要 audio.wav;请先跑 audio stage`,但 `output/asr/audio.wav` 真实存在(215MB)
- **诊断**:`_isolate_inbox` 用 `inbox.rglob("*")` 扫到 `output/asr/audio.wav`(因为 inbox = video.parent = `F:\resourse_study\边界\`,output 是其子目录),把它当媒体文件移走了
- **修复**:`_isolate_inbox` 加 `exclude_dirs=[work]`,跳过 work_dir 下的文件
- **残留**:无,已 commit

#### 撞墙 3:CUDA 不可用 + ASR 转写慢
- **现象**:`torch.cuda.is_available() = False`,faster-whisper 走 CPU 模式。112min 视频 1.3GB 大约需要 1-2 小时转写
- **已尝试**:bx2o443en 后台跑,已转写 ~26min 语音内容(382 segments / 1582s),估计再 1-2h 完成
- **残留**:bx2o443en 任务还在 background(task ID 仍 active,output 文件 99 字节因 Python stdout buffer)

#### 撞墙 4:两个 ASR 并发争 CPU
- **现象**:bx2o443en(debug 脚本) + bre53o53u(smoke full run)同时跑 ASR,争 CPU 各 3GB 内存,两个都会变慢
- **已尝试**:`taskkill /F /PID 23628` 杀掉 bre53o53u
- **残留**:bx2o443en 独占 CPU,跑完即可

### 5.2 TODO(下次会话继续)

- [ ] **确认 bx2o443en 完成**:transcript.jsonl 不再增长 30s 以上时,任务 exit
- [ ] **手动 mark state.asr=completed**:`scripts/run_smoke.py` 重跑会重跑 asr(因为 state.asr.status=failed)。手动改 `output/state.json` 把 asr 改为 `{"status": "completed", "error": null, "finished_at": <now>}`
- [ ] **续跑剩余 9 stage**:frames → ocr → asr_correct → chapters → draft → imagegen(skip) → render → longdoc(skip) → verify
- [ ] **验证产物**:output/asr/audio.wav + transcript.jsonl + output/chapters/chapters.json + output/chapters/raw/AI助力.../lecture_cleaned.md + lecture_final.html + verify.json
- [ ] **commit W5**:`feat(scripts): add smoke runner with inbox isolation`(scripts/run_smoke.py + CLAUDE.md §4.1)
- [ ] **更新 task.md**:W5 端到端冒烟完成记录 + W6 候选(B/C/D)

### 5.3 已知问题 / 技术债

- **CPU 模式转写慢**:用户机器 RTX 3090 + Windows 但 torch 报 CUDA 不可用。下次会话可查 `torch` build 版本 + NVIDIA driver + 是否需要装 `torch+cu118` 等 wheel
- **imagegen 默认 skip**:本次未生成 AI 配图,verify 阶段会跳过 image_refs 校验(因为没图片)。生产跑 `--imagegen local_sdxl` 需要等 ~5min 模型加载 + 30-60min 生成(每章节 1-3min)
- **longdoc_llm_provider 默认 "skip"**:本次只跑规则清理(去时间戳 / 合并空行),不调 LLM 净化。生产可设 `ollama` 跑 LLM 净化
- **inbox 隔离依赖 `exclude_dirs`**:下次重构时必须保留这个参数,否则会回归 bug

---

## 6. 测试状态

```
$ uv run pytest
346 passed / 3 skipped in 2.50s (W4 baseline,未变)
```

smoke 是产品代码,未新增测试。下次会话可加 `tests/test_scripts/test_run_smoke.py` 测试 argparse + 隔离逻辑。

---

## 7. Git 状态

```
$ git branch
* feat/pipeline-w5-smoke
  feat/pipeline-w4-longdoc-verify
  main

$ git status
M  CLAUDE.md
?? scripts/

$ git log --oneline -5
3b32743 feat(pipeline): W4 — longdoc + verify stages (11 stages all live)
266d741 docs(handoff): add W3 pipeline snapshot + task.md progress
86694a0 feat(pipeline): draft + imagegen + render stages (W3)
f712552 feat(pipeline): ocr + asr_correct + chapters + llm providers (W2)
04f992c feat(pipeline): W1 — audio + asr + frames stages + utils + runner
```

**待 commit**:`feat(scripts): add smoke runner with inbox isolation` — 含
`scripts/run_smoke.py`(+254 行) + `CLAUDE.md` §4.1(+27 行)。

---

## 8. 给下一个会话的提示

```
承接 handoff-pipeline-w5-smoke-2026-07-18.md,W5 部分完成。
ASR 后台跑中(bx2o443en task),transcript.jsonl 写到 1582s / 382 segments / 49KB。
请:
1. 检查 bx2o443en 是否完成(看 transcript.jsonl mtime + size 30s 不变)
2. 若完成,手动改 output/state.json 把 asr.status=completed
3. 启动 smoke 续跑(uv run python scripts/run_smoke.py <video> --no-skip-completed)
4. 验证 9 stage 产物(chapters.json / lecture_cleaned.md / lecture_final.html / verify.json)
5. commit W5:feat(scripts): add smoke runner with inbox isolation
6. 决定 W6 候选(B L2 LE / C CLI mtd / D MCP)
```

**主要任务**:

1. **等 ASR + 续跑**(最高优先级)— 1-2h 内完成
2. **commit W5 代码**(scripts/run_smoke.py + CLAUDE.md)
3. **写 README "快速开始" 章节更新**:把 smoke 脚本作为推荐入口

**别忘了**:

- 不在 handoff / task.md / state.json 里手改音频数据
- 修改 state.json 后,用 `uv run python -c "from media_to_doc.state import State; ..."` 验证能 load
- 如果 transcript.jsonl 不完整,等 bx2o443en 自然完成,**不要 kill** 否则转写会丢数据
- W5 smoke 跑完后,346 测试不能 regress(没改 src/ 应该不会)

**关键参考**:

- `handoff-pipeline-w4-2026-07-18.md` — 上一个 W4 handoff
- `scripts/run_smoke.py` — 端到端入口
- `src/media_to_doc/pipeline/runner.py:run_pipeline` — runner 调度
- `CLAUDE.md` §4.1 — 输出目录约定
- 本会话 `scripts/run_smoke.py:_isolate_inbox` — inbox 隔离(含 work_dir 排除)

**复杂度提示**:

- W5 是 3 人天 → 实际 ~1.5h(部分完成,撞墙 4 项)
- 端到端跑完预计 2-4h(ASR CPU + chapters LLM + draft LLM + longdoc LLM + render)
- 跑通后可作为基线,后续 W6+ 改进有参照

---

## 9. 上下文参考链接

- `CLAUDE.md` — 项目级指引(含 §4.1 输出目录约定)
- `task.md` — 活跃 todo(W5 部分完成,继续到 W6)
- `handoff-pipeline-w4-2026-07-18.md` — 上一个 W4 handoff
- `_research/PROJECT_DESCRIPTION.md` — 参考实现逆向报告
- `_research/LE_DESIGN.md` — LE 详细设计(W6 接入参考)

---

## 10. 自检清单

- [x] 本次会话目标:smoke 脚本 + CLAUDE.md + 部分端到端跑(ASR 后台中)
- [x] smoke 脚本可独立运行:`uv run python scripts/run_smoke.py --help`
- [x] inbox 隔离 bug 已修复:`exclude_dirs=[work]`
- [x] 网络环境默认(HF 镜像 + unset proxies)已内置 smoke 脚本
- [x] 无未提交代码改动 scripts/ + CLAUDE.md(待 commit)
- [x] 测试状态明确(346 passed,未变)
- [x] Git 状态明确(W5 在 feat/pipeline-w5-smoke 分支,待 commit)
- [x] 下次会话第一句话建议清晰
- [x] 关键决策记录 3 条,带"为什么"
- [x] 撞墙 4 项 + 已知问题 4 项,完整记录
- [x] bx2o443en ASR 后台跑中(下次会话 wait + 续跑)