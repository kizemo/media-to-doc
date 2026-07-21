# Release Notes — v1.1.0

> **Minor release** — multi-video layout + merge(W12-D)。
>
> 按用户 2026-07-21 拍板的新规落地。

---

## 🎯 用户新规 3 条

1. **中间 vs 最终产物分离**:中间产物(ASR/frames/OCR/chapters/drafts/state) →
   `<video>.parent / output/`;最终 md/html → `<video>.parent / output_final/`
2. **真视频名**:chapters.video + 最终文件名 = 真视频文件名(去后缀、去末尾空格)
3. **多视频合并**:新增 `merge_lectures`,文件名 = 第一个视频名(去除序号),章节重排,图片路径重写

---

## ✨ 主要改动

### 1. 中间 vs 最终产物分离

```text
output/                       ← 中间产物(11 stage 调度)
├── chapters/
│   ├── chapters.json
│   └── raw/<video>/chapter_NN.md
├── state.json
└── ... (其他 stage 产物)

output_final/                 ← 最终产物(自包含、可整盘分发)
├── <真视频名>.md             ← 拼装讲义 markdown
├── <真视频名>.html           ← 渲染 HTML(含 v1.0.1 mermaid + tasklist 修复)
└── <真视频名>/
    └── images/               ← AI 配图(从 drafts_dir/images/ 复制)
```

### 2. 真视频名派生

`chapters.derive_video_name(inbox, target_video)` — 从 inbox + target_video 派生
真视频文件名(去后缀、去末尾空格)。W10-A 跑出的 `output.md` 降级问题修复。

### 3. 多视频合并

```bash
# CLI
mtd merge <output_final_dir> [--name "培训综合"] [--no-html]

# MCP 工具
merge_lectures(output_final_dir, merged_name, no_html)

# Python API
from media_to_doc import merge_lectures
result = merge_lectures(Path("output_final"), merged_name="培训综合")
```

合并规则:
- 文件名 = 第一个视频 stem 去除序号(`01_xxx` → `xxx`)
- 章节全局重排(`## 第一部分` / `## 第二部分` ...)+ H2 降级为 H3
- 图片路径重写到 `<merged>/images/<original_stem>_<file>`(避免多视频同名冲突)
- 自然排序(数字按数值比较)
- `_cleaned.md` 优先,`_merged` 后缀跳过自合

### 4. 兼容性策略

**默认新规 + 旧产物只读兼容**(gatekeeper / verify 优先 `output_final/`,
回退 `output/chapters/raw/`)。无需迁移脚本。

---

## 📊 验证

- **559 pytest 用例 / 0 跳过**(1.0.1 539 → 1.1.0 559,+20 merge_lectures 测试)
- **ruff**:All checks passed
- **PyPI**:https://pypi.org/project/media_to_doc/(latest_version: 1.1.0)

---

## 📦 Install

```bash
uv pip install --upgrade media_to_doc==1.1.0
```

或从 GitHub Release 下载 wheel:

```
https://github.com/kizemo/media-to-doc/releases/download/v1.1.0/media_to_doc-1.1.0-py3-none-any.whl
```

---

## 🔄 Migration from 1.0.x

新规默认开启,无需迁移脚本:

- **新跑**:`mtd run <inbox>` 自动用 `output_final/` 新布局
- **旧产物**:`gatekeeper / verify` 同时支持新旧路径回退读取,但新跑不会再写旧位置
- **手动迁移**(可选):`cp output/chapters/raw/output.md output_final/<真视频名>.md`

---

## 📝 Full Changelog

见 [CHANGELOG.md](https://github.com/kizemo/media-to-doc/blob/main/CHANGELOG.md#110---2026-07-21)。