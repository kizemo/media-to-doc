# handoff-pipeline-w10-real-LE-verify-2026-07-19.md — W10-A 真实端到端 LLM 健康度验收

> **会话主题**:W10-A 跑真实 107 分钟培训视频端到端,验证 W10-C 修复后 `pipeline_run.json.llm_health` 真正聚合 + `get_run_metrics` MCP 工具返回真实数据
> **会话日期**:2026-07-19,~4 小时(mtd run 实际 3h57m + setup + polling)
> **会话状态**:**W10-A 主目标达成** ✅ / **顺带发现 1 个 bug**(gatekeeper vs verify 不一致)— 待 W11+ 修

---

## 1. 本次会话目标

承接 `handoff-pipeline-w10-llm-health-2026-07-19.md`(W10-C),跑真实端到端验证:
- ✓ W10-C `llm_health` 聚合逻辑在 1.3GB / 107 min 真实视频上能工作
- ✓ `get_run_metrics`(MCP 工具等价 Python API)返回真数据
- ✓ pipeline_run.json 真含 `chapters_ollama` / `draft_ollama` 等 LLM 调用统计

---

## 2. 视频 / 输出设定

| 项 | 值 |
|---|---|
| 源视频 | `E:\resource\2026-01-27_年度复训\03_全站爆款流程-稳定消耗最重要 .mp4`(395 MB / 6422 s / h264 + aac) |
| 同目录其他视频 | `01_...打爆策略.mp4`(506 MB)/ `02_...潜客规模.mp4`(522 MB)— **未触碰** |
| W10-A 单视频 inbox | `E:\...\\_w10a_inbox\`(NTFS hardlink 0 字节开销) |
| Work / 输出 | `E:\resource\2026-01-27_年度复训\output\`(用户指定,符合 CLAUDE.md §4.1) |
| CLI | `mtd run ... --no-isolate --stop-after verify --imagegen skip`(longdoc 默认 skip) |
| Env | `HF_ENDPOINT=https://hf-mirror.com` + `HF_HUB_DISABLE_XET=1` + unproxy(W5 已知 fix) |

---

## 3. Pipeline Run 实测

**总时长**:14255.94 秒 = **3 小时 57 分**(start 19:41:26 / finish 23:39:02)。

| Stage | Started | Finished | Duration | Status |
|---|---|---|---|---|
| audio | 19:41:26 | 19:41:28 | 2.2s | ✓ completed |
| **asr** | 19:41:28 | **22:26:10** | **9881.9s = 2h45m** | ✓ completed |
| frames | 22:26:10 | 22:51:18 | 1507.8s = 25m | ✓ completed |
| ocr | 22:51:18 | 23:35:09 | 2631.2s = 44m | ✓ completed |
| asr_correct | 23:35:09 | 23:35:09 | 0.2s | ✓ completed |
| chapters | 23:35:09 | 23:35:56 | 46.7s | ✓ completed |
| draft | 23:35:56 | 23:39:02 | 185.8s = 3m | ✓ completed |
| imagegen | 23:39:02 | 23:39:02 | 0.0s | ✓ skipped |
| render | 23:39:02 | 23:39:02 | 0.1s | ✓ completed |
| longdoc | 23:39:02 | 23:39:02 | 0.1s | ✓ skipped |
| verify | 23:39:02 | 23:39:02 | 0.0s | ✓ completed |

**11/11 完成,0 failed**(质量:完成率 1.0)。

- ASR 产物:`transcript.jsonl` = 255368 bytes / 2723 segments(W5 同类 ~1.5h CPU → 这次 2h45m,因视频更长)
- 关键帧:`keyframes.json` = 663 帧
- OCR 产物:`output/ocr/frame_*.txt` = 663 帧文本
- 章节:`output/chapters/raw/output/chapter_01.md ... chapter_06.md`(6 章)
- 草稿:`output/drafts/drafts.json`

---

## 4. **W10-A 主目标达成** ✅

### 4.1 `pipeline_run.json.llm_health` 真数据

```python
{
  "chapters_ollama": {"calls": 1,  "failures": 0},
  "draft_ollama":    {"calls": 6,  "failures": 0}
}
```

✅ W8 时空字典 → W10-C 后真有数据。

说明:
- **`chapters_ollama`:1 calls** = qwen3:14b 一次 prompt 把完整 107min transcript 切章节
- **`draft_ollama`:6 calls** = 每章一次 prompt 共 6 章 → 6 次 LLM 调用
- **0 failures** = qwen3:14b 在 num_ctx=65536 + 32K RoPE 扩展下全程不报错(LP-007 W5 已验证)
- **longdoc_ollama 不存在** = longdoc 默认 skip,W10-C 设计行为(只有真用 LLM 的 stage 才注册 provider,见 handoff W10-C 决策 6)

### 4.2 `get_run_metrics` Python API 等价 MCP 工具,返回真数据

```python
from media_to_doc import get_run_metrics  # PEP 562 lazy import
m = get_run_metrics("E:/.../output")
m["pipeline_run"]["llm_health"]  # → 同上字典 ✅
```

`get_run_metrics` 调用 `<work>/pipeline_run.json` 读 llm_health,与 MCP `get_run_metrics` 工具等价。

### 4.3 端到端 11 stage 全部完成

```
✓ audio    ✓ asr    ✓ frames    ✓ ocr    ✓ asr_correct
✓ chapters ✓ draft  ✓ imagegen  ✓ render ✓ longdoc   ✓ verify
```

`get_run_metrics` 返回的 `state.is_complete=true` / 11 stage 全部 completed。

---

## 5. 顺带发现:Gatekeeper vs Verify **不一致** Bug ⚠️

### 5.1 现象

- `verify/verify.json.overall_passed = **true**`(verify stage 写的)
- `pipeline_run.json.gatekeeper_passed = **false**`(runner finally 写的)

**同一份数据,两个相反结论**。这是真 bug,不是 random。

### 5.2 根本原因

`gatekeeper_check` (LE L2 in `src/media_to_doc/logger/gatekeeper.py`) 检查 4 项:
1. `<work>/chapters/raw/<stem>/<stem>.md` 存在 — **不存在**(只有 chapter_01...06.md,无合并 .md)
2. lecture.md 有 H1≥1 + H2≥3 — **不适用**
3. `<work>/output_final.html` 存在且 > 1000 bytes — **不存在**(longdoc 跳过了,render 没写)
4. image_refs 真实存在 — 没图片所以 **passed**(warn 而已)

→ check 1 + check 3 **FAILED** → Gatekeeper FAIL。

而 `verify_pipeline` (separate `src/media_to_doc/pipeline/verify.py`) 检查项更宽,在 longdoc skip 场景下得出 `overall_passed=true`。

### 5.3 解决方案(待 W11+ 修)

`gatekeeper_check` 假设了**完整 render+longdoc 流水线**。当 longdoc skip 时:
- 没有 `output_final.html` — gatekeeper check 3 应放宽,允许"final html skipped"
- 没有合并的 `<stem>.md` — gatekeeper check 1 应允许"per-chapter drafts"作为合法 lecture

或者:让 gatekeeper 与 verify 共享检查逻辑,避免分叉。

### 5.4 不影响 W10-A 主结论

llm_health 与 gatekeeper 完全独立 — gatekeeper 失败不影响 W10-A 主目标,但记录在案。

---

## 6. 关键执行细节(给后续真跑参考)

### 6.1 Hardlink 单文件 inbox

`E:\...\年度复训\` 含 3 个 .mp4,CLI `find_media` 按字母排序选 `01_...`,而非用户指定的 `03_...`。

**解决**:用 Python `os.link(src, dst)` 创建 NTFS hardlink 到同目录的 `_w10a_inbox\` 子目录。
- 0 字节额外占用(inode 复用)
- 同目录下独立目录,`find_media` 只看到 03
- 跑完 `rm -rf _w10a_inbox` 即撤,原文件 link count 从 2 → 1 不动数据

**比 rename 方案更干净**:不修改用户原文件名 / mtime。

### 6.2 W5 网络 Env 必备(中国大陆用户)

`HTTP_PROXY=http://127.0.0.1:53471`(公司 / VPN proxy)会阻挡 HF download → 502 Bad Gateway。

**强制三件套**:

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
    HF_ENDPOINT=https://hf-mirror.com \
    HF_HUB_DISABLE_XET=1 \
    uv run mtd run ...
```

实测:`qwen3:14b`(已经本地拉过) + `faster-whisper-large-v3`(cache 完整)两模型都用镜像源。

### 6.3 长视频预计时长(107 min 培训课)

| 阶段 | 时长 |
|---|---|
| audio | < 5s |
| asr (faster-whisper large-v3, CPU fp16) | **~2h45min** |
| frames (PySceneDetect + pHash) | **~25 min** |
| ocr (RapidOCR,663 帧) | **~44 min** |
| asr_correct | < 5s |
| chapters (LLM 1 call, qwen3:14b) | ~1 min |
| draft (LLM 6 calls, qwen3:14b) | ~3 min |
| imagegen (skip) | 0s |
| render | < 1s |
| longdoc (skip) | < 1s |
| verify | < 1s |
| **总时长** | **~3h57min** |

比 W5 估算"1-2h"长 → 实际:107min 培训视频 + 中文语音 + CPU 模式 ASR ≈ 3-4h。

### 6.4 stdout 缓冲 vs state.json 真相

`tee` 配合 `uv run mtd run` 时 stdout 严重缓冲,只在 stage 切换或结束时 flush。
**监控用 `state.json` (按 stage 真存) + `memory/<today>.md` (LE L1 即时记忆)** — 这是 LE W8 已建立的事实真相流。

新增 poll 脚本:`scripts/_w10a_poll.py`(Windows path 反斜杠 `\r` 等触发 Python 严格 JSON parser 报错,需 fix 函数)。

---

## 7. 工具脚本(供后续真跑 / W11 测试)

新增到 `scripts/`(待 commit):

- **`_w10a_poll.py`**:轮询当前 11 stage 状态 + transcript.jsonl 进度。Windows path fix 内嵌。
- **`_w10a_check.py`**:跑完后,读 verify.json + imagegen.json + 看产物布局。
- **`_w10a_verify.py`**:调 `get_run_metrics` Python API + 断言 llm_health 真有数据 + 列 11 stage 状态。

下次 W11 / 真跑可以复用。

---

## 8. 输出物清单(用户视角)

用户指定的输出目录 `E:\resource\2026-01-27_年度复训\output\`:

```
output/
├── run-stdout.log                   # 504KB tee 缓冲的全过程输出
├── state.json                       # 11 stage 状态(W4 state machine 真相)
├── pipeline_run.json                # LE 沉淀(llm_health 在这里 ✅)
├── ERRORS.md                        # 空(全程 0 error)
├── memory/
│   └── 2026-07-19.md                # LE L1 即时记忆
├── asr/
│   ├── audio.wav                    # 205 MB ffmpeg 抽音
│   └── transcript.jsonl             # 2723 segments / 107min 中文转写
├── frames/keyframes.json            # 663 关键帧
├── ocr/frame_*.txt × 663            # RapidOCR 文本
├── chapters/chapters.json           # 6 章节 JSON
├── chapters/raw/output/             # 6 个 chapter_NN.md 草稿
├── drafts/drafts.json               # draft manifest
├── imagegen/imagegen.json           # skip 模式(27 prompts 跳过)
└── verify/verify.json               # overall_passed=true(与 gatekeeper 矛盾 ⚠️)
```

**总大小**:audio.wav 205 MB + 663 个 OCR txt(几百 KB)+ 6 chapter md(~36KB)+ JSON ~10KB ≈ **~210MB**。

可分发性:`output/` 用相对路径,跨机器整盘复制无路径依赖(W3 render 设计原则)。

---

## 9. 清理状态

| 资源 | 状态 |
|---|---|
| 原 mp4 03_(395MB) | ✅ 完好,link count 2→1 后等于 1,不破坏 inode |
| 原 mp4 01, 02 | ✅ 完全未触碰 |
| `_w10a_inbox/` hardlink 目录 | ✅ `rm -rf` 删除,0 字节开销撤除 |
| `output/` 用户产物 | ✅ 保留在 `E:\resource\2026-01-27_年度复训\output\` |

---

## 10. 给下一个会话的提示

**W10-A 主目标完全达成**,3 个候选可继续:

### 选项 1:**修 Gatekeeper vs Verify 不一致 bug**(W11-?)

- `gatekeeper_check` 应在 `longdoc_llm_provider == "skip"` 时跳过 `output_final.html` 检查
- 应允许 `<stem>.md` 不存在(只用 chapter_NN.md)或要求 render 真写合并 .md
- 同步 gatekeeper + verify 两套检查逻辑,避免分叉

### 选项 2:**W10-B v1.0 release prep**

- CHANGELOG.md(Known pattern:W0-W10 关键 commit)
- `docs/installation.md`(各 OS / CUDA / CPU / Ollama 步骤)
- `uv build` dry-run + `gh release create v1.0.0 --draft`
- `pyproject.toml` `[project.urls]` 加 repo / docs
- **建议先修 Gatekeeper 再 release**(release quality 干净)

### 选项 3:**长视频 + 真 LLM 文档质量验收**

- 当前 output 只有 chapter markdown,无 `<stem>.md` 合并 + 无 final HTML
- 若要分发给讲师看,需让 render 真写合并 + longdoc active 净化 + final HTML
- 这需要先把 Gatekeeper 修了才能 PASS

**个人推荐顺序**:修 Gatekeeper (W11-bugfix) → release W10-B → 真实分发验收 W11-doc。

---

## 11. 复杂度提示

- **W10-A 实际耗时 ~4 小时**(含 3h57min pipeline + 中途 fix HF env + 多轮 polling)
- 比 W5 预期 1.5-2.5h 长 → 107 min 中文培训视频 CPU ASR 实测 2h45min(单核 fast-whisper large-v3),比预期长
- 单 session 撞 2h 活跃线的话需要新开会话续跑 — 用户明确说"撞 600s 上限也请继续",所以本次跨线完成
- 下次类似规模真跑,推荐开后台 + 用户授权 4-5h 不打断

---

## 12. 自检清单

- [x] W10-A 主目标:`pipeline_run.json.llm_health` 真有 chapters_ollama/draft_ollama 数据 ✅
- [x] `get_run_metrics` Python API 等价 MCP 工具,返回正确 ✅
- [x] 11/11 stage 全部完成,0 failed ✅
- [x] HF env fix 正确传播(W5 三件套)✅
- [x] NTFS hardlink 创建成功 + 跑完撤除,原 mp4 完好 ✅
- [x] 用户指定输出目录路径(`E:\...\output\`)保留 ✅
- [x] 顺带发现 1 个 follow-up bug:Gatekeeper vs Verify 不一致 → 记录在 §5
- [x] 所有 poll / check 脚本加入 `scripts/_w10a_*.py`,可复用 ✅
- [ ] Gatekeeper bug 修复(留 W11+)
- [ ] W10-B release prep(留 W11+)
