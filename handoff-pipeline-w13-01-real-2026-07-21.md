# handoff-pipeline-w13-01-real-2026-07-21.md

> W13-A 真跑 01.mp4 端到端 + LLM fusion 验证 — session snapshot
> Started 2026-07-21T14:01(本会话 14:01-16:01 活跃,2h 预算)
> 状态:进行中(`[~]` in task.md)

---

## 1. 上下文

**用户反馈(2026-07-21 第一轮)**:"01.mp4 没处理过"。W10-A / W11-C / W12-C 都只跑过 03.mp4,
01.mp4 一直没参与端到端测试。本次会话决定:

- 真跑 01.mp4(506MB / ~111min)完整 11 阶段 → 验证 W12-F 真视频名修复 + W12-D 真视频名派生 + W12-E LLM fusion
- 备份旧 output/output_final,避免覆盖 W12-C 03 的产物
- 跑完用 01 + 03 双视频合并,fusion LLM 决策全局章节结构

---

## 2. 环境

| 项 | 值 |
|---|---|
| 工作目录 | `F:\soft\00selfmade\media-to-doc`(release/v1.0 分支) |
| git | 538f217 origin/main 同步,本会话无 commit |
| Python | 3.13 (uv-managed) |
| 项目版本 | media-to-doc 1.x (install via PyPI / dev install via uv) |
| 依赖 | `uv sync --all-extras` 已完成(W5) |
| Ollama | localhost:11434 / qwen3:14b 在线(0.02s ping) |
| 网络 | HF_ENDPOINT=https://hf-mirror.com + HF_HUB_DISABLE_XET=1 + unset proxy |

---

## 3. 操作步骤

### 3.1 备份旧产物

```bash
cd "E:/resource/2026-01-27_年度复训/"
[ -d output ] && mv output output-backup-2026-07-21
[ -d output_final ] && mv output_final output_final-backup-2026-07-21
```

✅ 已执行 14:00 — output-backup-2026-07-21/ + output_final-backup-2026-07-21/ 创建
   (output-w12c + output-w11c 保留供 fusion 用)

### 3.2 Hardlink 单文件 inbox

```bash
mkdir -p _w13a_inbox
uv run python -c "import os; src=r'E:\...\01_先精准后放大的打爆策略 .mp4'; dst=r'E:\...\_w13a_inbox\01_先精准后放大的打爆策略 .mp4'; os.link(src, dst)"
```

✅ 已执行 14:00 — `_w13a_inbox/01_先精准后放大的打爆策略 .mp4` hardlink 创建

### 3.3 启动 pipeline (14:01:36)

```bash
cd "F:/soft/00selfmade/media-to-doc"
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY
export HF_ENDPOINT=https://hf-mirror.com HF_HUB_DISABLE_XET=1
nohup uv run mtd run "E:/resource/2026-01-27_年度复训/_w13a_inbox" \
  --no-isolate --imagegen skip --longdoc-llm ollama \
  > /tmp/w13a_run.log 2>&1 &
echo $! > /tmp/w13a_run.pid
```

✅ PID 2627 bash 包装 / PID 2629 uv / PID 23492 python.exe (2.5GB RAM)
   audio.wav 5.9s 落盘,ASR 启动

### 3.4 Polling (14:15 启动)

```bash
nohup uv run --project . python scripts/_w13a_poll_loop.py > /tmp/w13a_poll.log 2>&1 &
```

✅ PID 5087 bash / PID 5090 uv — 5min sleep 周期,asr 完成后自动退出
   阈值:282 segments + 镜像 last_end ~6000s

### 3.5 (待)Fusion 测试

```bash
# 等 pipeline 完成后
mkdir -p "E:/resource/2026-01-27_年度复训/_w13a_fusion"
cp "E:/resource/2026-01-27_年度复训/_w13a_inbox/output_final/01_先精准后放大的打爆策略_cleaned.md" \
   "E:/resource/2026-01-27_年度复训/_w13a_fusion/01_cleaned.md"
cp "E:/resource/2026-01-27_年度复训/output-w12c/chapters/raw/output_cleaned.md" \
   "E:/resource/2026-01-27_年度复训/_w13a_fusion/03_cleaned.md"

cd "E:/resource/2026-01-27_年度复训/"
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY
uv run --project "F:/soft/00selfmade/media-to-doc" \
  mtd merge _w13a_fusion --fusion ollama --name "年度复训综合"
```

### 3.6 验收

- chapters.json `video` 字段 = "01_先精准后放大的打爆策略"
- output_final/01_先精准后放大的打爆策略_cleaned.md + final.html 存在
- pipeline_run.json llm_health 含 chapters_ollama + draft_ollama + longdoc_ollama
- verify + gatekeeper 一致 PASS
- 融合:`_w13a_fusion/年度复训综合_cleaned.md` 7+ 章节 + include 字段分布

### 3.7 清理 + commit

```bash
rm -rf "E:/resource/2026-01-27_年度复训/_w13a_inbox" \
       "E:/resource/2026-01-27_年度复训/_w13a_fusion"

cd "F:/soft/00selfmade/media-to-doc"
uv run pytest && uv run ruff check
# 任意阶段的 commit(被前面 step block 时可独立 commit)
git add -A
git commit -m "feat(pipeline): W13-A — real 01.mp4 end-to-end + LLM fusion validate"
```

---

## 4. 关键决策记录

### 4.1 Pipeline 配置
- **imagegen=skip**:用户明确要求节省 SDXL 2h+,这样 11 stage 中跳过 imagegen,只剩 asr/frames/ocr/asr_correct/chapters/draft/render/longdoc/verify 9 真跑
- **longdoc-llm ollama**:1 次 LLM call 真净化(同 W11-C 复跑成功经验)
- **--no-isolate**:inbox = _w13a_inbox(用 hardlink 隔离),work = _w13a_inbox/output,final = _w13a_inbox/output_final

### 4.2 hardlink 而非 rename/copy 优势
- 不动用户原 .mp4
- 跑完 `rm -rf _w13a_inbox` 自动 release link count,源文件 link count 2→1
- 0 字节开销

### 4.3 W12-D derive_video_name 验证点
- `state.course` = "output" (work.name 派生,**正常**,state 标识用)
- `chapters.json.video` = 真视频名 (derive_video_name,W12-D 期望)
- 最终产物文件名 = 真视频名(01_先精准后放大的打爆策略_cleaned.md)

---

## 5. 撞墙 / 修复记录

- `_w10a_poll.py` / `_w13a_poll_loop.py` 路径写错(`output/` 在 inbox 同级而非 _w13a_inbox/output/)→ 改到 `_w13a_inbox/output/state.json`
- pipeline /tmp/w13a_run.log 有 UnicodeDecodeError(`gbk` 解码 ffmpeg stderr)→ 已知非致命,继续观察

---

## 6. 当前进度(check at session exit)

| Stage | 时间戳 | 段数 / 大小 |
|---|---|---|
| audio | 14:01:36-14:01:42 (5.9s) | audio.wav 236MB |
| asr | 14:01:42+ (running) | 14:08 = 8KB / 82 segs / 302s |
| frames | pending | - |
| ocr | pending | - |
| asr_correct | pending | - |
| chapters | pending | - |
| draft | pending | - |
| imagegen | skip | - |
| render | pending | - |
| longdoc | pending | - |
| verify | pending | - |

(状态会随 pipeline 推进更新;详细看 `_w13a_poll.log`)

---

## 7. 下个会话第一句话

承接 W13-A 真跑 01.mp4 端到端 + LLM fusion 验证,见
`F:\soft\00selfmade\media-to-doc\handoff-pipeline-w13-01-real-2026-07-21.md`

快速步骤:
1. `cat /tmp/w13a_poll.log` — 看 ASR 是否完成 / 停在何处
2. `tasklist | grep -i python` — 看 PID 23492 是否还活
3. 如 asr=completed → 继续 3.5 fusion 步骤
4. 如 asr 仍 running 且超时 → 检查 last_end,session 超 90min 卡 50%+ 时 taskkill 接受 85% transcript
5. pipeline 完整完成 → 跑 3.6 验收 + 3.7 清理 + commit
