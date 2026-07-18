# media-to-doc — Product Requirements Document (PRD)

> 版本:v1.0(初版) · 日期:2026-07-17 · 状态:待评审
>
> 本文档定义 `media-to-doc` 作为开源项目的**产品边界、用户场景、功能清单、验收标准**。
> 技术实现细节见 `TDD.md`,执行节奏见 `ROADMAP.md`。

---

## 0. 文档元信息

| 项 | 值 |
|---|---|
| 项目代号 | media-to-doc |
| 文档版本 | v1.0 |
| 创建日期 | 2026-07-17 |
| 状态 | Draft — 待技术评审 + 用户验收 |
| 作者 | Claude(reference session `2cf14f87-...`) |
| 关联文档 | `TDD.md`、`ROADMAP.md`、`CLAUDE.md`、`_research/PROJECT_DESCRIPTION.md` |

修订历史:

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v1.0 | 2026-07-17 | 初版,基于 `local-ai-workflow` 8 次 commit 经验 + 新增 4 项要求 | Claude |

---

## 1. 一句话定位

**media-to-doc** 是一款 Windows 开源桌面工具,把本地音视频(培训录像、讲座录音、
内部课程、运营课、电商课、客服培训)和图片,**一键转化为带 AI 配图、可独立分发的
Markdown + HTML 讲义**,内置 LLM/SDXL 推理栈与向导式安装器,面向 Claude / Codex 用户
和需要长期沉淀培训内容的个人/小团队。

---

## 2. 业务背景与目标

### 2.1 业务背景

- 培训内容沉淀难:公司/团队内部每周产生大量培训视频和录音,目前靠人工整理,
  效率低且不标准化
- LLM 工作流工具碎片化:Faster-Whisper、SDXL、PySceneDetect 等单点工具成熟,
  但缺乏端到端流水线
- 部署门槛高:同类项目要求用户懂 Python/uv/CUDA,非技术用户无法独立使用
- 跨工具集成弱:培训内容产出后,无法直接喂给 Claude Desktop / Codex 等 AI 助手

### 2.2 产品目标

| 维度 | 目标 | 度量 |
|---|---|---|
| **降低使用门槛** | 非技术用户 5 分钟内完成首次安装 + 跑通一条流水线 | 安装向导完成 → `mtd run` 全程 < 5 分钟 |
| **端到端可用** | 一条命令产出 md/html,无需手工串联多个工具 | 单条 `mtd run <inbox>` 输出 ≥ 1 个完整讲义 |
| **AI 助手原生集成** | 安装即用 MCP server,Claude Desktop / Codex / Claude Code 直接调用 | MCP 配置 ≤ 3 步,工具数量 ≥ 6 |
| **本地优先** | 默认完全离线工作,云端 LLM 仅作可选 | Ollama + SDXL 全本地默认 |
| **跨平台产物** | 产物可整盘复制到任何电脑/上传网盘/丢知识库 | 产物目录无绝对路径依赖 |
| **自我进化** | 跑得越多,质量越好(LE 闭环) | 错误模式自动晋升 LLM 知识库 |

### 2.3 非目标(明确不做)

- ❌ 不做云端 SaaS 服务(本项目是开源本地工具)
- ❌ 不做 macOS / Linux 桌面客户端(Windows 优先,macOS/Linux CLI 仍可)
- ❌ 不做实时字幕 / 实时翻译(只做离线批量)
- ❌ 不做视频剪辑 / 转码(只消费现有 mp4/mp3)
- ❌ 不做企业内部账户系统 / 多用户协作
- ❌ 不做 LLM 模型本身的训练 / 微调

---

## 3. 用户与场景

### 3.1 目标用户画像

| 用户类型 | 占比 | 场景 | 关键诉求 |
|---|---|---|---|
| **企业培训负责人** | 40% | 月处理 5-20 个培训视频 | 标准化、可批量、产物可发给同事 |
| **知识管理个人/咨询顾问** | 30% | 处理自己录的课/讲座 | 长期沉淀、可检索、可丢知识库 |
| **技术决策者 / DevOps** | 20% | 评估工具,内部推广 | 开源、可审计、可定制、可集成 |
| **AI 工具爱好者** | 10% | 折腾 LLM/SDXL 工作流 | 可玩、可扩展、模型可选 |

### 3.2 核心场景剧本

#### 场景 A:首次安装(目标 5 分钟内)

```
1. 下载 mtd-setup-1.0.0.exe(80-150MB)
2. 双击运行,NSIS 向导引导:
   a. 选安装路径
   b. 自动检测系统:
      - GPU 类型(NVIDIA/AMD/无)
      - 显存(GB)
      - 磁盘剩余(GB)
      - 网络(是否能下载模型)
   c. 推荐部署级别:
      - 完整(本地 Ollama + qwen3:14b + SDXL Base + Refiner,需 ~30GB 磁盘 + RTX 3090)
      - 标准(本地 Ollama + qwen3:14b,云端 SDXL 或 skip,需 ~15GB 磁盘)
      - 轻量(全部云端 API,需 1GB 磁盘,任意 GPU)
   d. 勾选部署级别 → 自动下载所需模型
   e. 设置开机自启 / 系统托盘(可选)
3. 安装完成 → 桌面出现 "media-to-doc" 快捷方式 + 控制台命令 mtd
```

#### 场景 B:处理一条培训视频

```
1. 用户把 mp4 拖到 "media-to-doc 客户端" 窗口,或:
   - 桌面右键 mp4 → "用 media-to-doc 处理"
   - CLI: mtd run "D:/培训/2026-07-15 课程.mp4"
   - 控制台点击 "添加任务"
2. 客户端显示进度条:audio → asr → frames → ocr → chapters → draft → imagegen → render → longdoc → verify
3. 完成后自动弹出浏览器预览最终 HTML 讲义
4. 产物位置:
   D:/培训/2026-07-15 课程/
   ├── raw/<视频同名>.md / .html
   ├── raw/<视频同名>_cleaned.md
   ├── raw/<视频同名>_final.html    ← 推荐分发
   ├── img/frame_*.jpg
   └── work/(中间产物,可清理)
```

#### 场景 C:在 Claude Desktop 里调用

```
1. 客户端 "集成" 页 → 显示 Claude Desktop 配置 JSON
2. 用户复制到 claude_desktop_config.json
3. 重启 Claude Desktop
4. 对话框输入:"处理 D:/培训/2026-07-15/ 的视频,完成后告诉我产物位置"
5. Claude 自动调 MCP tools:
   - list_courses 确认视频
   - run_pipeline 启动处理
   - check_status 查进度
   - read_lecture 读最终 HTML
   - 总结报告
```

#### 场景 D:断点续跑

```
1. 中途电脑关机 / 进程被 kill
2. 重启客户端 → 自动扫描 workspace/work/ 下未完成的课程
3. 显示 "5 个课程中断,点击续跑" → 一键 resume
4. CLI: mtd resume <work-dir>
```

### 3.3 边界场景与异常处理

| 异常 | 处理 |
|---|---|
| GPU 显存不够(SDXL 至少 8GB,qwen3:14b 至少 10GB) | 客户端弹窗提示,自动降级到云端或 skip |
| Ollama 11434 端口被占用 | 自动切换到备用端口,启动失败时提示用户检查 |
| 模型下载中断 | 断点续传,记录 hash,完成后校验 |
| 视频文件损坏 | 单文件失败不影响其他,标记 ERROR |
| 长视频(>3 小时)拆批 | 自动按 30 分钟切片,逐片处理,最后合并 |
| 网络断开 | 离线模式(纯本地 LLM/SDXL)继续工作 |

---

## 4. 功能清单

### 4.1 必须有(P0,首发版本 v1.0)

#### A. 核心流水线(11 阶段,与参考实现一致)

| 阶段 | 实现 | 输入 | 输出 |
|---|---|---|---|
| audio | ffmpeg 抽音 | mp4 | wav |
| asr | Faster-Whisper large-v3 + CUDA fp16 | wav | transcript.jsonl |
| frames | PySceneDetect + pHash | mp4 | frame_*.jpg |
| ocr | RapidOCR | jpg | frame_*.txt |
| asr_correct | OCR×ASR 8s 校对 | 两者 | corrections.json |
| chapters | LLM(默认 Ollama Qwen3-14B) | transcript | chapter_*.md |
| draft | LLM 模板生成 | chapter | draft |
| imagegen | SDXL Base + Refiner | draft | gen_*.png |
| render | jinja2 + markdown | chapters | .md + .html |
| longdoc | 借鉴 long-doc-processor | raw.md | _cleaned.md + _final.html |
| verify | gatekeeper + 校验 | 全产物 | verify.json |

#### B. 安装与配置

- [ ] NSIS 安装器(`mtd-setup-1.0.0.exe`)
- [ ] 系统检测(GPU/显存/磁盘/网络/CPU)
- [ ] 部署级别推荐(完整/标准/轻量)
- [ ] 模型下载管理(进度条/暂停/恢复/校验)
- [ ] 安装后首次启动配置向导
- [ ] Ollama 自动安装与启动(NVIDIA GPU 检测到时)
- [ ] 配置文件路径:`%APPDATA%\media-to-doc\config.yaml`
- [ ] 日志路径:`%LOCALAPPDATA%\media-to-doc\logs\`

#### C. 客户端 UI(Tauri + React)

- [ ] **首页 Dashboard**:近期任务、快速开始、模型状态
- [ ] **任务页**:新增任务、批量管理、进度查看、续跑
- [ ] **设置页**:LLM provider、imagegen provider、系统检测结果、模型下载管理
- [ ] **集成页**:Claude Desktop / Codex 配置 JSON 一键复制、CLI 用法
- [ ] **讲义预览页**:HTML 预览 + 编辑 + 导出
- [ ] **学习库页**:`.learnings/LEARNINGS.md` / `ERRORS.md` 可视化
- [ ] **系统托盘**:右键菜单快速操作

#### D. CLI(`mtd` 命令)

- [ ] `mtd run <inbox>` — 完整流水线
- [ ] `mtd resume <work>` — 续跑
- [ ] `mtd status <work>` — 进度
- [ ] `mtd list` — 列出 inbox 课程
- [ ] `mtd doctor` — 系统诊断
- [ ] `mtd config` — 配置管理(get/set/edit)
- [ ] `mtd model` — 模型管理(download/list/delete)
- [ ] `mtd mcp` — 启动 MCP server(stdio)
- [ ] `mtd version` / `mtd --help`

#### E. MCP Server(`mtd mcp` 启动)

6 个工具:

- `list_courses(workspace_root)`
- `run_pipeline(inbox_dir, workspace_root)`
- `resume_pipeline(work_dir)`
- `check_status(work_dir)`
- `list_outputs(inbox_dir)`
- `read_lecture(inbox_dir, version, fmt)` — `raw/cleaned/final`

#### F. LLM Provider 可插拔

| Provider | 默认 | 配置 |
|---|---|---|
| ollama | ✅ | 自动检测本地 Ollama + qwen3:14b |
| anthropic | - | `ANTHROPIC_API_KEY` + `LLM_PROVIDER=anthropic` |
| openai_compatible | - | MiniMax/DeepSeek/智谱/Moonshot/混元/OpenRouter/DashScope |
| 自定义(用户输入) | - | URL + Key + Model 自动拉取模型列表 |

#### G. 自我进化(Loop Engineering)

> **设计依据**:`_research/LE_KEYPOINTS.md`(基于 aiec.fun 两篇文章)
> **落地设计**:`_research/LE_DESIGN.md`
> **L1+L2 原型**:`_research/le_prototype/`(23 测试全过,Phase 5 时迁移)

- **L1 执行层**:每 stage 写 `workspace/work/<course>/memory/YYYY-MM-DD.md`
- **L2 审核层**:gatekeeper 4 项机器可验证检查(lecture.md / 章节数 / final.html / image_refs)
- **L3 沉淀层**:`pipeline_run.json` 全 stage 记录 + quality 聚合
- **L4 进化层**:`post_pipeline_hook` 扫描 ERRORS,Pattern-Key ≥ 3 晋升 `.learnings/ERRORS.md`(幂等)
- **L5 编排层**:CLI / MCP / Tauri UI 三层触达
- **健康度**:`assess_llm_health` 抽最近 20 run LLM 失败率(>20% → switch_provider,>10% → reduce_chunk)

**LE 反模式**(本项目避免):
- ❌ L1 没跑通就上 L4
- ❌ Generator/Checker 同模型
- ❌ "感觉差不多"作为通过标准
- ❌ 跳过 gatekeeper 直接 verify
- ❌ 人工不读结果

**LE 度量 KPI**:
- stage completion rate ≥ 99%
- gatekeeper pass rate ≥ 95%
- pattern_key repeat rate < 5%
- LLM failure rate < 10%

### 4.2 应该有(P1,v1.1-1.2)

- [ ] **多 LLM provider 并行**:同一课程用 Ollama + Claude 交叉验证章节切分质量
- [ ] **自动重试 + 自愈**:失败 stage 最多重试 2 次,自动调整 prompt
- [ ] **批量任务队列**:一次性添加 10+ 视频,顺序处理,共享模型缓存
- [ ] **Obsidian 风格 md 模板**:`![[]]` 内嵌、`> [!quote]` callout、frontmatter tags
- [ ] **导出 PDF**:基于 _final.html,可选 weasyprint 或 wkhtmltopdf
- [ ] **讲义版本管理**:同一视频多次跑,产物按 timestamp 保留
- [ ] **导出 EPUB**:为电子书阅读器优化
- [ ] **多语言 UI**:英文/简中/繁中

### 4.3 可以有(P2,v2.0+)

- [ ] **macOS / Linux 桌面客户端**(NSIS 改用对应平台工具)
- [ ] **云同步配置**:登录账号同步 config.yaml
- [ ] **协作分享**:产物可一键上传到 S3 / WebDAV / 网盘
- [ ] **自定义 pipeline**:用户拖拽式编排 stage
- [ ] **Webhook 集成**:跑完通知 Slack / 钉钉 / 企业微信
- [ ] **插件系统**:第三方 stage 注入

---

## 5. 验收标准

### 5.1 v1.0 验收清单(发布门槛)

| 维度 | 标准 | 度量方法 |
|---|---|---|
| **安装** | 全新 Windows 11 + RTX 3090 机器,5 分钟内完成安装 + 模型部署 | 计时 |
| **首次运行** | 从桌面双击 mtd 快捷方式,3 次点击跑通一条流水线 | 用户测试 |
| **核心功能** | 11 阶段全部跑通,产出 md/html | `mtd doctor` 全过 |
| **测试覆盖** | pytest ≥ 110 用例,全过 | `uv run pytest` |
| **集成** | Claude Desktop + Codex + Claude Code 三个环境均能 MCP 调用 | 文档演示 |
| **本地优先** | 断网后所有功能仍可用 | 飞行模式测试 |
| **跨平台产物** | 把产物目录整盘复制到另一台 Windows / Mac / Linux,讲义图片仍正常显示 | 复制测试 |
| **Loop Engineering** | L1+L2 全部 hook 落地,人工跑 5 次后看到 `.learnings/ERRORS.md` 自动累积 | 实证 |

### 5.2 非功能需求

| 维度 | 标准 |
|---|---|
| **性能** | 1.5 小时普通话培训视频,10 分钟内出逐字稿;30 分钟内出最终 HTML |
| **可靠性** | 单 stage 失败不影响整体;断点续跑 100% 成功 |
| **可观测** | 每个 stage 实时进度 + 失败 traceback + LLM 调用 token 计数 |
| **可维护** | 关键模块 ≤ 500 行;函数 ≤ 100 行;复杂度可解释 |
| **国际化** | UI 中英文切换;产物 md/html 支持 CJK |
| **隐私** | 默认完全本地,不上传任何数据;云端 API 调用需用户显式勾选 |
| **可审计** | MIT 协议;依赖锁版本(uv.lock);签名 release |

---

## 6. 风险与缓解

| 风险 | 影响 | 概率 | 缓解 |
|---|---|---|---|
| **NSIS 安装器在 Win11 S Mode 受限** | 部分企业用户装不上 | 中 | 文档提供 winget / 手动安装步骤 |
| **Tauri + Rust 工具链 Windows 编译慢** | CI 30+ 分钟 | 中 | 用 GitHub Actions windows-latest + 缓存 |
| **SDXL Refiner 6GB 下载失败** | 部分用户首次体验卡住 | 高 | 断点续传 + 跳过 Refiner 模式 + 云端降级 |
| **Ollama 与 NVIDIA 驱动版本不兼容** | 安装后 GPU 不可用 | 中 | 安装时检测驱动版本,提示升级 |
| **开源社区贡献冷启动** | Issue / PR 不足 | 中 | 完善的 CONTRIBUTING.md + good-first-issue 标签 |
| **Claude Desktop / Codex MCP 协议变更** | 集成失效 | 低 | 关注 Anthropic/OpenAI 公告,快速跟进 |
| **盗版 / 商标抢注** | 品牌受损 | 低 | 注册 media-to-doc 域名 + GitHub org 名占位 |
| **法律风险(音视频版权)** | 用户上传侵权内容 | 低 | LICENSE + README + ToS 明确"用户自负" |

---

## 7. 商业模式与社区

- **开源免费**:核心代码 MIT 协议,所有 P0/P1 功能免费
- **商业衍生**:可基于本项目做 SaaS、咨询服务、定制开发,无需授权费
- **社区**:
  - GitHub Discussions(问答)
  - Discord / 飞书群(实时)
  - 月度社区会议(roadmap 同步)
- **贡献激励**:
  - Contributors 列入 `AUTHORS.md`
  - 活跃贡献者可获 committer 权限
  - 年度社区奖(media-to-doc Award)

---

## 8. 度量与迭代

### 8.1 关键指标(KPIs)

| 指标 | 目标(v1.0 发布 3 个月内) | 度量 |
|---|---|---|
| GitHub Stars | 500+ | GitHub API |
| 周下载量(PyPI) | 200+ | pypistats |
| 周活跃安装数 | 100+ | 安装遥测(可选,opt-in) |
| Issue 关闭率 | ≥ 80% | GitHub API |
| 文档完整度 | 100% API / 100% CLI | 文档测试 |
| L1→L2 触发率 | ≥ 30% pipeline_run 触发 ERROR 晋升 | 遥测 |

### 8.2 反馈循环

- 用户提 Issue → triage 标签 → 排期 → PR → release
- 每月发布次版本(v1.1, v1.2)
- 每季度发布主版本(v2.0)
- `pipeline_run.json` 跨用户聚合(可选,opt-in),用于质量基准对比

---

## 9. PRD 评审清单

- [ ] 用户 / 场景覆盖完整
- [ ] 功能清单 P0/P1/P2 分级清晰
- [ ] 验收标准可测量
- [ ] 风险与缓解完整
- [ ] 非功能需求完整
- [ ] 关联 TDD / ROADMAP 链接
- [ ] 关联 `CLAUDE.md` 项目规则
- [ ] 与参考实现 `local-ai-workflow` 经验一致

---

## 10. 附录

### A. 术语表

| 术语 | 含义 |
|---|---|
| **ASR** | Automatic Speech Recognition,语音识别 |
| **OCR** | Optical Character Recognition,光学字符识别 |
| **SDXL** | Stable Diffusion XL,文生图模型 |
| **Refiner** | SDXL 的细节精修模型 |
| **MCP** | Model Context Protocol,Anthropic 提出的 AI 工具协议 |
| **CLI** | Command Line Interface |
| **PyPI** | Python Package Index |
| **NSIS** | Nullsoft Scriptable Install System,Windows 安装器 |
| **LE** | Loop Engineering,自我驱动/检查/进化的工程方法 |
| **pHash** | perceptual Hash,图像感知哈希 |

### B. 参考文档

- `_research/PROJECT_DESCRIPTION.md` — 参考实现完整逆向报告
- `_research/real_user_msgs.txt` — 14 个用户原始需求
- `C:\Users\Duanyi\.claude\projects\E-------01----\2cf14f87-...jsonl` — 参考会话原文
- `C:\Users\Duanyi\.claude\skills\long-doc-processor\` — long-doc-processor skill
