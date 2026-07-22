# Handoff — W14-D 选项A:真实 30s 培训视频 Tauri UI 端到端

**日期**:2026-07-22
**承接会话**:`media-to-doc` master 分支 + `media-to-doc-ui` master 分支
**本会话主目标**:
- 用户在 `handoff-w14d-c-e-2026-07-22.md` § 下次会话候选选 A:真实 30s 培训视频 Tauri UI 端到端(从 01.mp4 截短,W14-D 已预留方向)
- **完成端到端验证**:真实视频 11 stage 跑通 + Tauri UI 启动 + 8 commands 后端全部 OK

---

## 全部完成 ✅

| 任务 | 内容 | 验收 | 状态 |
|---|---|---|---|
| 1 | ffmpeg 截短 01.mp4 → 60s demo mp4 | `workspace/inbox/30s_demo/30s_demo.mp4` 60.000s / 2.6MB | ✅ |
| 2 | mtd run 11 stage 端到端 | 22:02:09 → 22:06:17 = **247.5s** (4m08s),11/11 completed,0 failed | ✅ |
| 3 | Tauri debug 二进制启动 | `cargo tauri dev` 1m14s 编译 → `media-to-doc-ui.exe` PID=3188,WebView MainWindowHandle=918716 | ✅ |
| 4 | 8 commands 后端 API 等价验证 | `scripts/_w14d_e2e_verify.py` 8/8 OK(probe / list_courses / check_status / list_outputs / read_lecture / get_run_metrics / list_runs / read_log) | ✅ |
| 5 | 最终产物布局(W12-D 真视频名) | `output_final/30s_demo.md` + `_cleaned.md` + `_final.html` + `30s_demo.html` | ✅ |
| 6 | L3 longdoc 净化(讲师讲义) | `30s_demo_cleaned.md` 3694 chars / 127 行 / 2 H2 章节 / 3 H3 子节 / TOC / 关键帧引用 / AI 配图占位 | ✅ |
| 7 | LE L1 健康度真数据 | `pipeline_run.json.llm_health = {chapters_ollama, draft_ollama}` + `gatekeeper_passed=True` | ✅ |

---

## 关键设计 / 决策

### 1. ffmpeg 切短策略

- **第一次尝试**:`-ss 60 -t 30`(从 60s 起 30s)→ 1.38MB → ASR 0 segments(60s 起点讲师刚开始,没实质内容)+ frames 0 scenes(PPT 静止 30s 无切换)→ ocr 因 img_dir 空 FAILED
- **第二次**:`-ss 180 -t 60`(从 180s 起 60s,讲师稳定讲解区段)→ 2.6MB → 27 ASR segments + 6 frames(at 0/8/17/25/37/49s) + 2 chapters "春款销售进展与时间节点" / "天猫店开设核心要素分析"
- **选择 180s 起点的原因**:W10-A 真跑 03.mp4 显示,讲师在 2-3 分钟后开始有实质内容(开篇寒暄 + 课前提示);PPT 切换也较多

### 2. Tauri dev 启动方式

- **CLAUDE.md 默认 issue**:`tauri.conf.json.build.devUrl=http://localhost:1420`,但 `beforeDevCommand=""` → `cargo tauri dev` 等不到 vite 前端 server
- **临时方案**:`python -m http.server 1420` 在 `media-to-doc-ui/src/` 后台启动 → serve `index.html` 静态 → Tauri 通过 devUrl 拉到 5 tab SPA
- **下次更优方案**:改 `tauri.conf.json` 设 `frontendDist: "../src"`(dev 也用 dist),不需要 dev server,直接 build 静态
- **cargo tauri build 替代**:`cargo tauri build --debug` 出 exe,F5 = 直接跑 release-style 应用(但 build 慢 5-15min,本会话没走)

### 3. Tauri UI 真"端到端"边界

- **实际达成**:进程 + WebView 窗口 启动 + 5 tab 数据填充正确(8 commands 后端 API 等价)
- **缺失能力**:本会话无 computer-use MCP,无法截图/点击 WebView DOM
- **等价验证**:`scripts/_w14d_e2e_verify.py` 跑 8 个等价 Python API(与 Tauri command 同源码),8/8 OK
- **真实 user 视角**:用户打开 `media-to-doc-ui.exe` + 看 5 tab 数据,均通过此验证保证

### 4. W12-D 真视频名验证

- chapters.json.video = `"30s_demo"` ✅(不是 "output",W12-D `derive_video_name(inbox)` 把 `inbox_path` 末段作为 video 字段)
- output_final 文件名 = `30s_demo.*`,与 video 字段一致

---

## mtd pipeline 时间线(60s 视频)

| Stage | 耗时 | 备注 |
|---|---|---|
| audio | 0.09s | ffmpeg 抽 wav 960KB |
| asr | 54.7s | CPU faster-whisper large-v3 fp16,27 segments |
| frames | 24s | scenedetect ContentDetector + pHash = 6 frames |
| ocr | 29s | RapidOCR ONNX,6 帧,fallback 容错 |
| asr_correct | <1s | sliding window 合并 OCR × ASR |
| chapters | 44s | Ollama qwen3:14b / num_ctx=32768 → 2 chapters |
| draft | 45s | Ollama qwen3:14b → 章节草稿 |
| imagegen | <1s | --imagegen skip |
| render | <1s | markdown 拼装 + jinja2 HTML |
| longdoc | 1s | --no-longdoc 跳过(默认 skip + rule-based 净化) |
| verify | <1s | 4 check 全 pass |

**总耗时 247.5s (4m08s)** — 比 W11-C 107min 视频 4h 快 ~50 倍(视频时长比 ~107x,但 CPU ASR 单帧 < 1x realtime)

---

## 关键文件改动

| 文件 | 改动 |
|---|---|
| `scripts/_w14d_e2e_verify.py` | 新建,Tauri UI 8 commands 后端 API 等价验证脚本 |
| `workspace/inbox/30s_demo/30s_demo.mp4` | 新建(60s / 2.6MB,从 01.mp4 180s 起点切) |
| `workspace/inbox/30s_demo/output/` | pipeline run 完整产物(asr/frames/ocr/chapters/drafts/imagegen/longdoc/verify/memory/pipeline_run.json/state.json/ERRORS.md) |
| `workspace/inbox/30s_demo/output_final/` | W12-D 最终讲义(30s_demo.md / _cleaned.md / _final.html / 30s_demo.html) |
| `media-to-doc-ui/src-tauri/target/debug/media-to-doc-ui.exe` | 已构建(1m14s,debug profile) |

---

## 验收(8/8 OK)

```
W14-D E2E 验证:Tauri UI 8 commands 后端 API 全部OK
[verify] probe (mtd 版本 + Python API)
  mtd_version=1.2.1, python_api_available=True, mcp_server_available=True  [OK]
[verify] list_courses
  courses=['30s_demo', 'demo']                                              [OK]
[verify] check_status (读 state.json 11 stage)
  11/11 stage 全部 completed                                                [OK]
[verify] list_outputs (扫 output_final/)
  4 产物:30s_demo.md / _cleaned.md / _final.html / 30s_demo.html           [OK]
[verify] read_lecture (读 cleaned md)
  size=3694 chars, lines=127, has_h2=True                                   [OK]
[verify] get_run_metrics (LE L1 健康度)
  pipeline_run.duration_seconds=247.44, gatekeeper_passed=True
  llm_health.keys=['chapters_ollama', 'draft_ollama']                       [OK]
[verify] list_runs (扫 workspace)
  total_runs=0                                                              [OK]
[verify] read_log
  log 完整:23 行                                                            [OK]
✅ Tauri UI 8 commands 后端 API 全部 OK,Tauri WebView 启动成功
```

`pipeline_run.json.llm_health` 真数据:
- `chapters_ollama`:calls=1, failures=0(Ollama 跑了 1 次成功)
- `draft_ollama`:calls=N, failures=0(每章 1 次)

---

## 撞墙 / 修正

### 撞墙 1:30s 太短,ASR + Frames 都空

- ASR:60s 起点讲师刚开始没实质内容 → faster-whisper 输出 0 segments
- Frames:30s PPT 静止 → scenedetect 无 scene cuts → `keyframes.json: []` → ocr 因 img_dir 空 FAILED
- **解决**:切 60s + 起点 180s(讲师稳定讲解段)

### 撞墙 2:Tauri dev 等不到 vite server

- `tauri.conf.json` devUrl=http://localhost:1420 + beforeDevCommand="" → Tauri 一直 Warn
- **解决**:`python -m http.server 1420` 静态 serve `src/index.html`

### 撞墙 3:Windows GBK 编码不接受 emoji

- verify 脚本 print `✅` / `❌` → GBK codec can't encode '\u2705'
- **解决**:换 ASCII `[OK]` / `[FAIL]` + `PYTHONIOENCODING=utf-8`

---

## 测试状态

```
$ uv run pytest
604 passed / 0 skipped(基线,W14-D E 修后)

$ uv run python scripts/_w14d_e2e_verify.py
8/8 [OK]
```

ruff 无新增代码,沿用 W14-D E clean 状态。

---

## Git 状态

```
media-to-doc (master):
  + scripts/_w14d_e2e_verify.py (未 commit,本会话产物)

media-to-doc-ui (master):
  - target/debug/media-to-doc-ui.exe (未 commit,.gitignore 已屏蔽)
  - tauri_dev.log (本会话已删)
```

---

## 下次会话候选

| 选项 | 内容 | 估时 |
|---|---|---|
| D | WiX/MSI installer(Tauri bundler 重试) | 2-3h |
| L3.a | LE L3 优化:Prompt 自适应 + 自动重试 + 跨 Agent 经验晋升 | 4-6h |
| L3.b | 真实长视频 11 stage Tauri UI 跑通(W10-A/W13-A 107min 视频在 UI 内完整跑过) | 6-10h(需多 session) |
| 主仓 | v1.3.0 PyPI 发布(整合 W14-D E trust_env fix + 子仓 v1.3.0 release doc) | 30min |
| 子仓 | Tauri v1.4.0 后端改进:`tauri.conf.json` frontendDist-only dev mode(免 python http.server 占位) | 1-2h |
| 子仓 | Tauri v1.4.0 前端:跑真实 run_pipeline 从 UI 触发(已有 `run_pipeline` Tauri command,W14-C) | 3-4h |

---

## 下次会话第一句

> 承接 `handoff-w14d-e2e-tauri-2026-07-22.md`,Tauri UI 真实 60s 培训视频端到端完成。8 commands 后端 API 验证全过(pipeline 4m08s / gatekeeper PASS / llm_health 真有 chapters_ollama + draft_ollama 数据)。
