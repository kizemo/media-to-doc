# media-to-doc 项目级学习库 — LEARNINGS

> **目的**:积累项目开发过程中沉淀的最佳实践(best_practice),供未来会话/开发者复用。
> **格式**:每条 LP-YYYYMMDD-NNN 条目,包含 标题 / 上下文 / 做法 / 启示 四部分。
> **写入**:Claude 在每个里程碑 commit 时主动追加;也可人工编辑。
> **关联**:`../_research/le_prototype/`(LE 原型)、`../PRD.md` §4.1.G、`../TDD.md` §4.5。
> **W9 实装**(首批 LP 条目):W1-W8 关键 best_practice 沉淀。

---

## 模板

```markdown
### LP-YYYYMMDD-NNN — <标题>

**上下文**: <何时何地遇到的问题 / 学到的经验>
**做法**: <具体如何解决 / 实践>
**启示**: <对未来开发者的建议 / 通用原则>
**相关文件**: <src/.../file.py:line>、<docs/...>
**作者**: <Claude 自动 / 用户 / 协作者>
```

---

## 条目

### LP-20260718-001 — 11 stage 函数签名统一 `(work: Path, config: WorkflowConfig)`

**上下文**:W1 把 11 stage 从占位转成实装,每个 stage 都需要拿到 work 目录 + config,
签名不统一会让 runner `_invoke_stage` 写大量 `if/else` 分发。

**做法**:
- 全部 stage 函数签名:`(work: Path, config: WorkflowConfig) -> <StageResult>`
- runner 用统一 `_invoke_stage(stage, func, ctx)` 包装,ctx 注入 `inbox / state / logger`
- chapters / draft / longdoc 三个 LLM 阶段走 wrapper(`_chapters_wrapper` 等)从 config 派生 LLM provider

**启示**:流水线 stage 签名统一 = runner 极简,新增 stage 只需在 `STAGE_FUNCS` 注册一行。

**相关文件**:`src/media_to_doc/pipeline/runner.py:50-90`(STAGE_FUNCS / _chapters_wrapper),
`src/media_to_doc/pipeline/runner.py:287-407`(_invoke_stage 三分支)
**作者**:Claude W1

---

### LP-20260718-002 — LLM provider 用 ABC + lazy import,缺库时给清晰 ImportError

**上下文**:W2 接 3 个 LLM provider(ollama / anthropic / openai_compat),用户可能没装全部 SDK。

**做法**:
- 基类 `BaseLLMProvider`(`llm/base.py`)用 `abc.ABC`,子类只实现 `_chat_impl`
- 实际 SDK(ollama / anthropic / openai)在子类 `__init__` 内 lazy import
- 缺库时 `raise ImportError("请 pip install media-to-doc[llm_anthropic]")`
- `llm/__init__.py` 顶层只暴露基类 + 工厂函数,3 个具体 provider 通过 `_register_defaults()` 延迟注册

**启示**:ABC 强约束接口 + lazy import 强隔离重依赖,测试时可只装 ollama。

**相关文件**:`src/media_to_doc/llm/base.py`、`src/media_to_doc/llm/anthropic.py`、`src/media_to_doc/llm/ollama.py`
**作者**:Claude W2

---

### LP-20260718-003 — chapters JSON 解析做宽松适配(围栏 / 前缀文字 / `[` 到 `]` 切片)

**上下文**:W2 chapters 阶段用 LLM 输出章节列表,LLM 输出经常不规范(带 ```json 围栏 / 前缀文字 / 解释行)。

**做法**:`chapters.py:_parse_chapters_response` 三重容错:

1. 先 strip markdown 围栏(```json ... ```)
2. 正则找第一个 `[` 到最后一个 `]` 切片
3. 解析失败时用 json.JSONDecoder.raw_decode 从 `[` 开始逐字符尝试

**启示**:LLM 输出永远不要相信,用最宽松的解析策略 + 友好错误信息。

**相关文件**:`src/media_to_doc/pipeline/chapters.py`(W2 实装)
**作者**:Claude W2

---

### LP-20260718-004 — imagegen ABC + Protocol 双轨(产品代码 ABC,测试 duck-typed)

**上下文**:W3 imagegen 阶段要支持 2 种 provider(local_sdxl / skip)+ 未来插件扩展。

**做法**:
- 产品代码用 `abc.ABC` 强制 `generate(prompt) -> Path` 接口
- 测试用 `typing.Protocol` duck-typed mock(无需继承 ABC),让测试 fixture 更轻量
- `SkipProvider.generate()` 直接返回 None,render 阶段检测到 None 时退化警告文字

**启示**:ABC 用于运行时多态,Protocol 用于测试替身 — 双轨互不干扰。

**相关文件**:`src/media_to_doc/pipeline/imagegen.py`(W3)
**作者**:Claude W3

---

### LP-20260718-005 — render 阶段缺失图自动退化为警告文字

**上下文**:W3 render 时 chapters.json 引用 `gen_001.png` 等图,但 imagegen skip 时图不存在。

**做法**:`render.py` 拼装 HTML 时:

1. 先扫 `images/` 子目录,把存在的图存进 `_existing_images: set[str]`
2. 渲染时若引用图不在 set,输出 `<p><em>[图片缺失: gen_001.png]</em></p>` 而非坏链接
3. verify 阶段检查 image_refs 与实际文件一致

**启示**:缺失外部资源永远不要 raise,降级显示比中断流水线更有价值。

**相关文件**:`src/media_to_doc/pipeline/render.py:150-220`(W3)
**作者**:Claude W3

---

### LP-20260718-006 — draft 默认输出到 `<work>/chapters/raw/<stem>/`,后续可注入 inbox

**上下文**:W3 draft 阶段产物应放哪里?work 中间产物 vs inbox 最终产物?

**做法**:
- 默认:`<work>/chapters/raw/<stem>/chapter_NN.md`(中间产物,可清空重跑)
- runner 接受 `output_dir` 参数,W5 smoke 跑通时把它注入到 `inbox/raw/<stem>/`
- `render` 阶段从 `_resolve_drafts_dir(work)` 派生路径,与 default 一致

**启示**:中间产物与最终产物物理隔离,方便 resume / 重跑 / 归档。

**相关文件**:`src/media_to_doc/pipeline/runner.py:407-419`(_resolve_drafts_dir)、`src/media_to_doc/pipeline/draft.py`
**作者**:Claude W3

---

### LP-20260718-007 — Ollama `num_ctx` 默认 65536,长 transcript 调 LLM 必备

**上下文**:W5 smoke 跑真实课程(50816 tokens transcript)时 Ollama 报"exceeds context size"。

**根因**:Ollama `num_ctx` 默认 4096,Qwen3-14B 原生 32k(可 RoPE 扩展到 65k)。

**做法**:`LLMConfig.num_ctx = 65536`(默认),`OllamaProvider` 创建时显式传 `num_ctx`。
chapters 阶段 prompt 也做 30000 chars 截断(留 system prompt + 输出空间)。

**启示**:本地 LLM 调长 prompt 时,context window 是隐性瓶颈,必须显式声明。

**相关文件**:`src/media_to_doc/config.py:43`、`src/media_to_doc/llm/ollama.py`
**作者**:Claude W5

---

### LP-20260718-008 — longdoc 默认 `provider="skip"`,规则清理兜底

**上下文**:W4 longdoc 阶段要不要默认调 LLM?

**决策**:**默认 skip,只跑规则清理**(去时间戳 / 合并空行)。LLM 净化是可选项。

**做法**:
- `PipelineConfig.longdoc_llm_provider = "skip"`(默认)
- `process_long_doc` 检测 `provider=None` 时走纯规则分支
- CI 离线环境(无 GPU)可全跑通过,真用时再 `--longdoc-llm anthropic`

**启示**:默认行为应该是最保守 / 最兼容的(零 GPU 依赖),高级功能用 opt-in flag 开启。

**相关文件**:`src/media_to_doc/config.py:80`、`src/media_to_doc/pipeline/longdoc.py`
**作者**:Claude W4

---

### LP-20260719-009 — Gatekeeper image_refs 候选路径 3 重试(md-link / wiki-link / images 子目录)

**上下文**:W8 gatekeeper 检查 lecture.md 引用的图片是否存在。原型只查 basename,W3-W5 后
产物布局变了(图可能在 `images/` 子目录,引用可能是 wiki-link `![[foo.png]]` 或 md-link `![alt](images/foo.png)`)。

**做法**:对每个 image_ref,候选路径 = 3 个:

```python
candidates = [
  lecture_dir / ref,                # 原路径
  lecture_dir / basename,           # 同目录(wiki-link)
  lecture_dir / "images" / basename,  # images 子目录(W3 render 默认)
]
```

任一存在即 OK,3 个都不存在才报 missing。

**启示**:产物布局会演化,文件存在性检查永远做候选路径重试,不要假设单一布局。

**相关文件**:`src/media_to_doc/logger/gatekeeper.py`(W8)
**作者**:Claude W8

---

### LP-20260719-010 — PipelineLogger 三层 try/except 异常隔离,LE 失败不破坏 run_pipeline

**上下文**:W8 LE 接入 runner 末尾:`gatekeeper_check` / `logger.finalize` / `post_pipeline_hook`
任何一项失败(磁盘满 / 权限不够),都不应破坏 `run_pipeline` 的 return 值。

**做法**:`run_pipeline` 末尾三层 try/except,每个 catch 后只 `print(..., file=sys.stderr)`:

```python
try:
  ...  # 主流水线
finally:
  try: gatekeeper = gatekeeper_check(work)
  except Exception as exc: print(f"[le] gatekeeper failed: {exc}", file=sys.stderr)
  try: pipeline_run = logger.finalize(...)
  except Exception as exc: print(f"[le] logger.finalize failed: {exc}", file=sys.stderr)
  try: post_pipeline_hook(work)
  except Exception as exc: print(f"[le] post_pipeline_hook failed: {exc}", file=sys.stderr)
```

**启示**:LE 是辅助 / 沉淀层,不是调度真相。state.json(主真相)始终先 save,LE 失败可观察但不致命。

**相关文件**:`src/media_to_doc/pipeline/runner.py:540-585`(W8)
**作者**:Claude W8

---

### LP-20260719-011 — `assess_llm_health.total_runs` 只计成功解析的 run_file

**上下文**:W8 health 评估跨 run 的 LLM 失败率。原 `assess_llm_health` 把损坏的 JSON run_file 也计入 `total_runs`,污染统计。

**做法**:引入 `parsed_runs` 单独计数,只在 `json.loads` 成功时 +1;`total_runs` 字段 = 成功解析数。
损坏文件只 warn,不计入分母。

**启示**:跨 run 聚合统计要严格区分"目录数" vs "有效数据数",分母必须可信。

**相关文件**:`src/media_to_doc/logger/learnings.py:129-198`(W8)
**作者**:Claude W8

---

### LP-20260719-012 — PEP 562 `__getattr__` 实现 lazy import,重依赖按需加载

**上下文**:W9 让 `from media_to_doc import run_pipeline` 跨项目可用,但 `import media_to_doc` 不应触发
faster-whisper / diffusers / anthropic 等重依赖。

**做法**:
- `__init__.py` 用 PEP 562 模块级 `__getattr__(name)`,从 `_LAZY_EXPORTS: dict[str, str]` 查目标模块路径
- 用户访问 `media_to_doc.run_pipeline` 时才 `importlib.import_module("media_to_doc.pipeline.runner")`
- 首次访问后缓存到 `globals()[name]`,后续访问走正常属性查找
- `__dir__()` 列出所有公开符号,IDE 自动补全可用

**启示**:Python 3.7+ 的 PEP 562 是包顶层 re-export 的最佳实践,比 `import *` 更可控。

**相关文件**:`src/media_to_doc/__init__.py`(W9)、`tests/test_init.py`(26 用例)
**作者**:Claude W9

---

### LP-20260719-013 — 测试不要真跑 11 stage,monkeypatch 是已验证模式

**上下文**:11 stage 涉及 ffmpeg / faster-whisper / SDXL,CI 环境无法真跑。

**做法**:
- `tests/test_pipeline/test_runner.py` 用 monkeypatch 把 `STAGE_FUNCS[stage]` 替换为 mock 函数
- mock 函数只写产物文件,不真调重依赖
- 验证:`state.stages[stage].status == "completed"` + 文件存在
- 同样模式适用 `test_llm/*`(mock provider)、`test_imagegen/*`(Protocol duck-typed)

**启示**:单测 / 集成测中,重依赖全部 mock。E2E 测单独跑(本项目 `scripts/run_smoke.py`)。

**相关文件**:`tests/test_pipeline/test_runner.py`(W4-W8 共用模式)
**作者**:Claude W1-W8

---

### LP-20260719-014 — stdout 留给 JSON,所有日志走 stderr

**上下文**:CLI 的 `--json` 输出与 MCP 的 stdio JSON-RPC 都依赖 stdout 纯净。调试 log 走 stdout 会破坏输出。

**做法**:
- CLI:`sys.stdout.write(json.dumps(...))`,不用 `console.print`(Rich 把 `[...]` 当 markup)
- MCP server:handler 内 `print(..., file=sys.stderr)`,stdout 留给 JSON-RPC 帧
- logger 配置:Python `logging` 默认走 stderr

**启示**:stdout = 数据契约,stderr = 人类观察。混用就是埋雷。

**相关文件**:`src/media_to_doc/cli.py`(eprint helper)、`src/media_to_doc/mcp_server.py`(_log helper)
**作者**:Claude W6 + W7

---

## 沉淀规则

- 每条 LP 条目必须有 **上下文 / 做法 / 启示** 三段,缺一不收
- "启示"段必须可复用(其它项目也适用),不能只描述本项目特定 case
- W+ 数字 = W1/W2/.../W9 的开发会话标识,新增条目按 `LP-YYYYMMDD-NNN` 自增编号
- 重复出现的 ERRORS.md Pattern-Key 由 LE L4 进化层自动晋升到本文件(参见 `.learnings/ERRORS.md`)