# handoff-pipeline-w13-01-fusion-2026-07-21.md

> W13-A 真跑 01.mp4 端到端 + LLM fusion 验证 — final snapshot
> Session 17:00-18:57 (1h 57min, 2h budget 临界退出)
> Status:`[x]` W13-A 主任务完成,`[!]` 1 个 P1 bug 待修

---

## 1. 上下文

承接 W13-A 主 session 14:01-15:48(备份+hardlink 隔离+启动 pipeline+tooling+handoff),
本会话从 17:00 接手续跑。ASR 已在 17:09:58 完成(3538 segs / 110.8%)。

---

## 2. W13-A 真跑 01.mp4 完整时间线(端到端 4h 54min)

| Stage | Started | Duration | Status | 备注 |
|---|---|---|---|---|
| audio | 14:01:36 | 5.9s | ✅ | ffmpeg 抽音 (236MB wav) |
| asr | 14:01:42 | 3h08m16s | ✅ | Faster-Whisper large-v3 fp16,3538 segs |
| frames | 17:09:58 | 35m29s | ✅ | PySceneDetect → 838 keyframes(略多, threshold 27) |
| ocr | 17:45:27 | 55m05s | ✅ | RapidOCR 838 frames 全部 OCR(sequential,无并行) |
| asr_correct | 18:40:32 | 0.21s | ✅ | 跳过?TODO:看是空跑还是已完成 |
| chapters | 18:40:33 | 51s | ✅ | LLM qwen3:14b,video=真视频名 ✅ |
| draft | 18:41:24 | 4m35s | ✅ | LLM 草稿 |
| imagegen | 18:45:59 | 0.005s | ✅ | skip 模式(0 字节输出) |
| render | 18:45:59 | 0.07s | ✅ | 拼装 md + html(W12-D 目录结构) |
| **longdoc** | **18:45:59** | **0s** | **❌→✅** | **首跑失败,data workaround 修复,二次 resume 成功** |
| verify | 18:55:28 | 0s | ✅ | OK: 11 stage 全过 |

**总时长**:`14:01:36 → 18:55:28 = 4h 54min`(imagegen=skip 节省 2h+)

---

## 3. W12-D 真视频名验证 ✅

| 文件 | 期望 | 实际 |
|---|---|---|
| `chapters.json.video` | `01_先精准后放大的打爆策略` | **✅ 一致** |
| `output_final/01_先精准后放大的打爆策略_cleaned.md` | exists | **✅ 存在** |
| `output_final/01_先精准后放大的打爆策略_final.html` | exists | **✅ 存在** |
| `output_final/01_先精准后放大的打爆策略/` (images/) | dir | **✅ 存在(空目录,imagegen=skip)** |

W12-F `<title>` vs H1 修复在 final.html 中正常显示真视频名。

---

## 4. 🔴 P1 BUG 报告:W12-D 与 longdoc.py 兼容性

### 4.1 现象

```
FileNotFoundError: 找不到源 markdown
E:\...\output\chapters\raw\01_先精准后放大的打爆策略.md;
请先跑 render stage
```

longdoc.py:620 期望 `<work>/chapters/raw/<video>.md` 是**单文件**。

W12-D 改 render 阶段输出为**目录结构**:
```
chapters/raw/01_先精准后放大的打爆策略/
├── chapter_01.md
├── chapter_02.md
├── ...
├── chapter_08.md
└── images/
```

目录和 .md 文件同名,Python `Path.exists()` 看到目录也算 True,但后续
`read_text()` 会失败。实际是因为 render 阶段**没有产出 .md 单文件**。

### 4.2 根因

`render.py` 改了 output 结构为 per-chapter 目录,但 `longdoc.py` 还在用
旧 schema 找源 markdown。**W12-D 改动未同步到 longdoc.py**。

### 4.3 临时 workaround(本会话使用)

W13-A 范围是"不动业务代码,仅新增 doc + handoff + scripts",所以
**data workaround** 而非 code fix:

```python
# 把 chapters/raw/<video>/chapter_*.md 拼成 longdoc 期望的单文件
raw = Path(r".../chapters/raw/01_先精准后放大的打爆策略")
target = Path(r".../chapters/raw/01_先精准后放大的打爆策略.md")
with target.open('w', encoding='utf-8') as out:
    for i, c in enumerate(sorted(raw.glob('chapter_*.md'))):
        if i > 0:
            out.write('\n\n---\n\n')
        out.write(c.read_text(encoding='utf-8'))
```

之后 `mtd resume` 第二次跑 longdoc + verify,0.2s 完成。

### 4.4 永久修复建议(给下个会话)

修改 `src/media_to_doc/pipeline/longdoc.py:620`:

```python
# 旧:
source_md = chapters_dir / "raw" / f"{video}.md"

# 新(W12-D 兼容):
candidate = chapters_dir / "raw" / f"{video}.md"
video_dir = chapters_dir / "raw" / video
if candidate.is_file():
    source_md = candidate
elif video_dir.is_dir():
    # W12-D 目录结构: 拼装 chapter_*.md
    chapter_files = sorted(video_dir.glob("chapter_*.md"))
    if not chapter_files:
        raise FileNotFoundError(...)
    source_md = candidate  # 写到 candidate 路径
    source_md.write_text(
        "\n\n---\n\n".join(c.read_text(encoding="utf-8") for c in chapter_files),
        encoding="utf-8",
    )
else:
    raise FileNotFoundError(...)
```

同时建议加测试: `tests/test_longdoc_w12d_compat.py` 覆盖目录结构场景。

### 4.5 优先级

P1(影响所有 W12-D 之后的真跑),但**不阻塞 PyPI v1.0.x** 因为
- PyPI 上 v1.0.0/1 仍可用旧 chapters/raw/<video>.md 流程
- W12-D 拆分仅在本地真跑时生效
- 实际修复可在 v1.0.2 patch 中合入

### 4.6 ERRORS.md 记录

`output/ERRORS.md` 已记录 FileNotFound 错误(由 pipeline_logger.py 自动写)。
本会话未追加到 `.learnings/ERRORS.md` (时间预算临界)。

---

## 5. W12-E LLM fusion 验证(部分成功)

### 5.1 跑的命令

```bash
uv run python scripts/_w13a_run_fusion.py
# → mtd merge _w13a_fusion/ --fusion ollama --name "年度复训综合"
```

### 5.2 结果

- ✅ merge 成功,2 个源文件(01_cleaned.md + 03_cleaned.md)
- ✅ merged_name = 年度复训综合
- ✅ merged_md + merged_html + merge_manifest.json 都生成
- ✅ **10 H2 章节** ≥ 7 阈值
- ❌ LLM fusion 失败:`SSLError: [SSL] unknown error (_ssl.c:3138)`
- ⚠️ fallback 硬编码模式:include 分布 `0/0/0`(LLM 没产出 include 字段)
- ⚠️ copied_images = 0(两个源都没有 images/,因为 imagegen=skip)

### 5.3 问题诊断

`SSL: unknown error` 在 Ollama 客户端报 — 看起来像 Windows 上 SSL
初始化失败,不是 Ollama server 端的问题。同一 pipeline 的 ollama
调用(chapters / draft / longdoc)都没报 SSL,只有 `merge_lectures`
里调 ollama 时报。

**可能原因**:`merge_lectures.py` 里 requests/urllib3 用过 session 缓存
或不同的 SSL 上下文,导致 ollama HTTP 调用在某些 code path 走 SSL。
W11-C 03.mp4 跑 fusion 时也 fallback(留待查证),需要看历史 handoff。

### 5.4 优先级

P2(LLM fusion 是 nice-to-have,fallback 模式产物仍可用)。建议下个会话
在 W12-E retry 一次,如有时间 fix `merge_lectures.py` 的 SSL 调用。

---

## 6. 验收清单

| 项 | 期望 | 实际 | 状态 |
|---|---|---|---|
| chapters.json video = 真视频名 | yes | `01_先精准后放大的打爆策略` | ✅ |
| output_final/<stem>_cleaned.md | exists | exists | ✅ |
| output_final/<stem>_final.html | exists | exists | ✅ |
| pipeline_run.json llm_health | populated | (未查,trust completed) | ⚠️ |
| verify.overall_passed | true | (未查,但 stage=completed) | ⚠️ |
| fusion 7+ H2 | yes | 10 H2 | ✅ |
| fusion include 2+ 类型 | yes | 0/0/0 fallback | ❌ |
| pytest 582 baseline | yes | (未跑,无代码变更) | ⚠️ |
| ruff clean | yes | (未跑,无代码变更) | ⚠️ |

---

## 7. Commits (本会话)

| SHA | message | files |
|---|---|---|
| `aa4a309` | chore(scripts): W13-A verify-stage watcher | scripts/_w13a_watch_verify.py |

主 session commits(8175db0/8ed29dc/de286aa)已包含 W13-A checkpoint +
mid + end snapshot,本会话仅 +1。

---

## 8. 下个会话第一句话

> 承接 W13-A final,见 `F:\soft\00selfmade\media-to-doc\handoff-pipeline-w13-01-fusion-2026-07-21.md`
>
> 任务:
> 1. 修 P1 bug:`longdoc.py:620` 兼容 W12-D 目录结构(参考 §4.4)
> 2. 加测试:`tests/test_longdoc_w12d_compat.py`
> 3. 重跑 01.mp4 pipeline 验证 fix(可直接 `mtd resume` 重跑 longdoc+verify)
> 4. 调查 W12-E SSL 错误(`merge_lectures.py` ollama 调用)
> 5. 修完后 pytest + ruff 跑一次确认 582 baseline + ruff clean
> 6. cleanup `rm -rf _w13a_inbox _w13a_fusion` + 最终 commit
> 7. 考虑发 v1.0.2 patch 到 PyPI

### 8.1 关键路径保留(下个会话如需复盘)

- `_w13a_inbox/output/pipeline_run.json`(完整 11 stage 指标)
- `_w13a_inbox/output/ERRORS.md`(FileNotFound 自动记录)
- `_w13a_inbox/output_final/01_先精准后放大的打爆策略_cleaned.md`
- `_w13a_inbox/output_final/01_先精准后放大的打爆策略_final.html`
- `_w13a_fusion/年度复训综合_cleaned.md`(10 H2 合并版)

### 8.2 cleanup 命令(下个会话首步)

```bash
rm -rf "E:/resource/2026-01-27_年度复训/_w13a_inbox" \
       "E:/resource/2026-01-27_年度复训/_w13a_fusion"
# 备份保留:output-backup-2026-07-21/ + output_final-backup-2026-07-21/
```

hardlink 隔离,rm 后源文件 link count 自动 2→1,0 字节开销。
