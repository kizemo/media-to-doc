"""Stage 10 — ``longdoc``:长文档深度净化 + 最终 HTML 渲染。

输入:
- ``<drafts_dir>/<stem>.md``:由 :mod:`render` 阶段产出的拼装讲义 markdown
  (含 TOC + 各章节块 + 关键帧引用 + AI 配图)

输出:
- ``<drafts_dir>/<stem>_cleaned.md``:深度净化后的 markdown(去时间戳 / 去空行 /
  可选 LLM 重写)
- ``<drafts_dir>/<stem>_final.html``:最终交付的 HTML(TOC + 锚点 + 内嵌 CSS +
  print stylesheet + dark mode)

逻辑:
1. **分块**:按 ``chunk_size``(默认 15000 CJK 字符)在段落边界切分 md
2. **净化**:对每块调 LLM 提示模板"5 类保留 / 4 类清理" / 4 级标题
   - provider = ``"skip"`` → 不调 LLM,只跑规则清理
3. **合并**:拼接回 ``<stem>_cleaned.md``
4. **HTML 渲染**:BeautifulSoup 解析 markdown→ HTML,内嵌 CSS + TOC 锚点 +
   暗色模式 + 打印样式

依赖(``[longdoc]`` extras):
- :mod:`beautifulsoup4` — 解析 HTML 校验结构
- :mod:`lxml` — BeautifulSoup 后端
- :mod:`markdown` + jinja2(已在核心 deps,W3 上移)
- LLM provider(由 :func:`process_long_doc` 调用方传入;``skip`` 时不需要)

参考:long-doc-processor skill(SKILL.md + references/phase-1-purification.md +
     references/phase-3-render-html.md),适配 11 阶段流水线约束。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..config import WorkflowConfig

if TYPE_CHECKING:
  from ..llm.base import BaseLLMProvider

# ─────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────

DEFAULT_CHUNK_SIZE = 15000  # CJK 字符数
DEFAULT_MIN_CHUNK_SIZE = 2000  # 避免最后一块太小

# 章节草稿文件命名模式
_CLEANED_SUFFIX = "_cleaned.md"
_FINAL_SUFFIX = "_final.html"

# LLM 净化 prompt
_SYSTEM_PROMPT = (
  "你是一名资深中文课程编辑,把讲师讲义 markdown 改写为精炼、结构化的最终讲义。"
  "要求:\n"
  "1. 保留 5 类核心资产:概念定义 / 实战案例 / 数据指标 / 逻辑推理 / 表格列表\n"
  "2. 删除 4 类噪声:纪律语 / 引导语 / 寒暄 / 纯口语填充词\n"
  "3. 使用 4 级标题:# 一级 / ## 二级 / ### 三级 / #### 四级\n"
  "4. 严禁编造原文没有的事实;严禁减少独立信息单元\n"
  "5. 输入是 markdown,输出仍是 markdown(只输出正文,不要解释)"
)

_USER_PROMPT_TEMPLATE = """\
## 任务

把下面这份讲师讲义片段改写为最终讲义。

## 改写要求

- 保留 5 类核心:概念定义、实战案例、数据指标、逻辑推理、表格列表
- 删除 4 类噪声:
  - 纪律语("请大家把手机调静音"等)
  - 引导语("我们看一下"等纯铺垫,无信息量)
  - 寒暄("大家好我是小王"等自我介绍)
  - 口语填充词(嗯、啊、然后呢、那么、其实呢等)
- 4 级标题层级清晰;H1 一份文档只用 1 个(主标题)
- 信息完整:严禁删减事实、数据、案例
- 不杜撰:不在原文没有的细节
- 保留图片引用 `![Image](<stem>/images/...)` 完整不动

## 输入

{chunk}
"""

# 规则清理(LLM skip 模式下用)
# 匹配 ``[xxx - xxx]`` 或 ``[xxx - xxx]s`` 等时间戳行(包括行首空白)
_TIMESTAMP_LINE_RE = re.compile(r"^\s*\[[^\]\n]*\d[^\]\n]*\].*?$", re.MULTILINE)
# 3+ 连续空行 → 2 空行
_MULTI_BLANK_RE = re.compile(r"\n{3,}")
# 独立行的 ``---``(水平线)— 保留,但确保前后有空行
# 开头/末尾多余空行
_TRIM_LINES_RE = re.compile(r"^[ \t]*\n+")  # 行首纯空白行
_TRIM_TRAIL_RE = re.compile(r"\n[ \t]+$")  # 行尾纯空白

# slugify(与 render.py 一致)
_SLUG_RE = re.compile(r"[^a-zA-Z0-9\u4e00-\u9fff\-_]+")


# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


@dataclass
class PurificationStats:
  """净化统计(机器可读,不入 HTML)。"""

  chunks_total: int = 0
  chars_input: int = 0
  chars_output: int = 0
  retention_rate: float = 1.0
  rules_applied: list[str] = field(default_factory=list)
  lines_stripped: int = 0

  def to_dict(self) -> dict[str, object]:
    return {
      "chunks_total": self.chunks_total,
      "chars_input": self.chars_input,
      "chars_output": self.chars_output,
      "retention_rate": round(self.retention_rate, 4),
      "rules_applied": list(self.rules_applied),
      "lines_stripped": self.lines_stripped,
    }


@dataclass
class LongDocResult:
  """``process_long_doc`` 整体结果。"""

  video: str = ""
  course_title: str = ""
  source_md: Path | None = None
  cleaned_md: Path | None = None
  final_html: Path | None = None
  provider: str = ""
  model: str = ""
  stats: PurificationStats = field(default_factory=PurificationStats)

  def to_dict(self) -> dict[str, object]:
    return {
      "video": self.video,
      "course_title": self.course_title,
      "source_md": str(self.source_md) if self.source_md else "",
      "cleaned_md": str(self.cleaned_md) if self.cleaned_md else "",
      "final_html": str(self.final_html) if self.final_html else "",
      "provider": self.provider,
      "model": self.model,
      "stats": self.stats.to_dict(),
    }

  def save_manifest(self, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
      json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
      encoding="utf-8",
    )


# ─────────────────────────────────────────────────────────────
# 工具
# ─────────────────────────────────────────────────────────────


def _slugify(text: str) -> str:
  """生成 HTML 锚点兼容的 slug:小写 + 非字面字符替 ``-``。"""
  s = text.strip().lower()
  s = _SLUG_RE.sub("-", s)
  s = s.strip("-")
  return s or "section"


def _count_cjk(text: str) -> int:
  """统计 CJK 字符数(粗略:中文字符 + 日韩文字符)。

  实际分块时同时考虑 CJK 和 ASCII 的总字节,但 15000 的阈值按字符计
  (与 long-doc-processor skill 一致)。
  """
  cjk_re = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
  return len(cjk_re.findall(text))


def _split_into_chunks(
  text: str,
  chunk_size: int = DEFAULT_CHUNK_SIZE,
  min_chunk_size: int = DEFAULT_MIN_CHUNK_SIZE,
) -> list[str]:
  """按段落边界切分,每块不超过 ``chunk_size`` 字符(CJK 优先)。

  - 优先在 ``\\n\\n`` 切
  - 段落 > chunk_size → 强行按 ``\\n`` 切
  - 段落 > 2*chunk_size → 强行按字符切
  - 末块若 < min_chunk_size → 合并到前一块
  """
  if not text:
    return []
  if len(text) <= chunk_size:
    return [text]

  paragraphs = text.split("\n\n")
  chunks: list[str] = []
  current: list[str] = []
  current_len = 0

  for para in paragraphs:
    para_len = len(para)
    if para_len > chunk_size:
      # 段落本身就太长:先 flush current,再强行按字符切
      if current:
        chunks.append("\n\n".join(current))
        current = []
        current_len = 0
      # 强行切分:按 chunk_size 切,保留空行结构
      for i in range(0, para_len, chunk_size):
        chunks.append(para[i : i + chunk_size])
      continue
    if current_len + para_len + 2 > chunk_size:
      # 当前块已满,先 flush
      if current:
        last_chunk = "\n\n".join(current)
        # 末块太小:合并
        if (
          chunks
          and len(last_chunk) < min_chunk_size
          and len(chunks[-1]) + len(last_chunk) + 2 <= chunk_size * 2
        ):
          chunks[-1] = chunks[-1] + "\n\n" + last_chunk
        else:
          chunks.append(last_chunk)
      current = [para]
      current_len = para_len
    else:
      current.append(para)
      current_len += para_len + 2

  # 收尾
  if current:
    last_chunk = "\n\n".join(current)
    if (
      chunks
      and len(last_chunk) < min_chunk_size
      and len(chunks[-1]) + len(last_chunk) + 2 <= chunk_size * 2
    ):
      chunks[-1] = chunks[-1] + "\n\n" + last_chunk
    else:
      chunks.append(last_chunk)

  return chunks


# ─────────────────────────────────────────────────────────────
# 规则清理(LLM skip 模式)
# ─────────────────────────────────────────────────────────────


def _rule_clean_text(text: str) -> tuple[str, PurificationStats]:
  """对单块文本做规则清理(去时间戳 / 去连续空行 / 去前后空白)。

  返回 (cleaned, stats)。
  """
  rules: list[str] = []
  lines_stripped = 0
  before_len = len(text)

  # 1. 去时间戳行
  new_text, n = _TIMESTAMP_LINE_RE.subn("", text)
  if n > 0:
    rules.append("strip_timestamp_lines")
    lines_stripped += n

  # 2. 连续空行 → 最多 2
  new_text, n = _MULTI_BLANK_RE.subn("\n\n", new_text)
  if n > 0:
    rules.append("collapse_blank_lines")

  # 3. 去行尾空白 + 文档首尾空行
  new_text = new_text.strip() + "\n"

  if not rules:
    rules.append("noop")

  after_len = len(new_text)
  stats = PurificationStats(
    chunks_total=1,
    chars_input=before_len,
    chars_output=after_len,
    retention_rate=after_len / before_len if before_len else 1.0,
    rules_applied=rules,
    lines_stripped=lines_stripped,
  )
  return new_text, stats


# ─────────────────────────────────────────────────────────────
# LLM 净化(单块)
# ─────────────────────────────────────────────────────────────


def _purify_chunk_with_llm(
  chunk: str,
  provider: BaseLLMProvider,
) -> str:
  """对单块调 LLM 净化,返回净化后的文本。"""
  prompt = _USER_PROMPT_TEMPLATE.format(chunk=chunk)
  response = provider.chat(_SYSTEM_PROMPT + "\n\n" + prompt)
  return response.text.strip() + "\n"


# ─────────────────────────────────────────────────────────────
# markdown → HTML + TOC 锚点
# ─────────────────────────────────────────────────────────────


_HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
:root {{ color-scheme: light dark; }}
* {{ box-sizing: border-box; }}
body {{
  font-family: -apple-system, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
  max-width: 920px; margin: 2rem auto; padding: 0 1.5rem;
  line-height: 1.7; color: #1a1a1a; background: #fafafa;
}}
@media (prefers-color-scheme: dark) {{
  body {{ background: #1a1a1a; color: #e0e0e0; }}
}}
h1, h2, h3, h4 {{ line-height: 1.3; scroll-margin-top: 1.5rem; }}
h1 {{ font-size: 2rem; border-bottom: 2px solid #4a90e2; padding-bottom: 0.3rem; }}
h2 {{ font-size: 1.5rem; margin-top: 2.5rem; color: #2a6496; border-bottom: 1px solid #d0e0f0; padding-bottom: 0.2rem; }}
h3 {{ font-size: 1.2rem; color: #3a749c; margin-top: 1.8rem; }}
h4 {{ font-size: 1.05rem; color: #4a8ab0; margin-top: 1.2rem; }}
nav.toc {{
  background: #f0f7ff; border: 1px solid #d0e0f0; border-radius: 8px;
  padding: 1rem 1.5rem; margin: 1.5rem 0 2rem 0;
}}
@media (prefers-color-scheme: dark) {{
  nav.toc {{ background: #1f2a37; border-color: #2a3a4a; }}
}}
nav.toc h2 {{ margin-top: 0; font-size: 1rem; color: inherit; border: none; }}
nav.toc ol {{ padding-left: 1.4rem; margin: 0.4rem 0 0 0; }}
nav.toc ol ol {{ padding-left: 1.2rem; font-size: 0.92em; }}
nav.toc a {{ text-decoration: none; }}
nav.toc a:hover {{ text-decoration: underline; }}
code, pre {{
  background: #f5f5f5; padding: 0.1rem 0.3rem; border-radius: 3px;
  font-family: "Cascadia Code", "Consolas", "Menlo", monospace;
  font-size: 0.92em;
}}
pre {{ padding: 0.8rem 1rem; overflow-x: auto; line-height: 1.5; }}
@media (prefers-color-scheme: dark) {{
  code, pre {{ background: #2a2a2a; }}
}}
img {{ max-width: 100%; height: auto; border-radius: 4px;
       box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin: 1rem 0; }}
blockquote {{
  border-left: 4px solid #4a90e2; margin: 1rem 0;
  padding: 0.5rem 1rem; background: #f8f8f8;
}}
@media (prefers-color-scheme: dark) {{
  blockquote {{ background: #252525; }}
}}
hr {{ border: 0; border-top: 1px solid #ddd; margin: 2rem 0; }}
table {{ border-collapse: collapse; margin: 1rem 0; }}
th, td {{ border: 1px solid #d0d0d0; padding: 0.4rem 0.8rem; }}
@media (prefers-color-scheme: dark) {{
  th, td {{ border-color: #444; }}
}}
footer {{
  margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #ddd;
  font-size: 0.85rem; color: #888; text-align: center;
}}
@media print {{
  body {{ background: white; color: black; max-width: none; margin: 0; padding: 1rem; }}
  nav.toc {{ background: #f5f5f5; border: 1px solid #ccc; page-break-after: always; }}
  h1, h2, h3, h4 {{ color: black; page-break-after: avoid; }}
  pre, blockquote {{ page-break-inside: avoid; }}
  img {{ max-width: 80%; page-break-inside: avoid; }}
  footer {{ display: none; }}
}}
/* v1.0.1:tasklist 不可点击(只读 checkbox)+ mermaid 块留白 */
input[type="checkbox"][disabled] {{ margin-right: 0.35em; cursor: not-allowed; }}
pre.mermaid {{ text-align: center; background: #ffffff; }}
@media (prefers-color-scheme: dark) {{
  pre.mermaid {{ background: #1a1a1a; }}
}}
</style>
<!-- v1.0.1:GFM ```mermaid 围栏 → 浏览器端渲染 -->
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
  if (typeof mermaid !== "undefined") {{
    mermaid.initialize({{
      startOnLoad: true,
      securityLevel: "loose",
      theme: document.body && window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark" : "default"
    }});
  }}
</script>
</head>
<body>
{toc_html}
{body_html}
<footer>
  Generated by media-to-doc · {generated_at}
</footer>
</body>
</html>
"""


def _extract_headings(md_text: str) -> list[tuple[int, str, str]]:
  """从 markdown 文本提取标题,返回 ``(level, title, slug)`` 列表。

  跳过代码块围栏内的 ``#`` 行(粗略:含 ````` `` 的行视为代码块边界)。
  """
  results: list[tuple[int, str, str]] = []
  in_code = False
  for line in md_text.split("\n"):
    stripped = line.lstrip()
    if stripped.startswith("```") or stripped.startswith("~~~"):
      in_code = not in_code
      continue
    if in_code:
      continue
    m = re.match(r"^(#{1,4})\s+(.+?)\s*#*\s*$", line)
    if m:
      level = len(m.group(1))
      title = m.group(2).strip()
      # 复用 slug,带计数避免冲突
      slug = _slugify(title)
      results.append((level, title, slug))
  return results


def _build_toc_html(headings: list[tuple[int, str, str]]) -> str:
  """生成 ``<nav class="toc"><h2>目录</h2><ol>...</ol></nav>`` HTML 字符串。

  只列 H1/H2;H3+ 折叠为子列表(简单两级结构,深层级不展开)。
  """
  if not headings:
    return ""
  # 仅保留 H1/H2 作为 TOC 入口
  items = [(lvl, t, s) for lvl, t, s in headings if lvl <= 2]
  if not items:
    return ""
  lines: list[str] = ['<nav class="toc">', "<h2>目录</h2>", "<ol>"]
  for lvl, title, slug in items:
    if lvl == 1:
      lines.append(f'  <li><a href="#{slug}">{_html_escape(title)}</a></li>')
    else:  # lvl == 2
      lines.append(f'    <li><a href="#{slug}">{_html_escape(title)}</a></li>')
  lines.append("</ol>")
  lines.append("</nav>")
  return "\n".join(lines)


_HTML_ESCAPE_RE = re.compile(r"[&<>'\"']")


def _html_escape(text: str) -> str:
  """极简 HTML escape(用于 TOC 文本)。"""
  return (
    text.replace("&", "&amp;")
    .replace("<", "&lt;")
    .replace(">", "&gt;")
    .replace('"', "&quot;")
  )


def _assign_unique_slugs(
  headings: list[tuple[int, str, str]],
) -> list[tuple[int, str, str, str]]:
  """为重名 slug 加 ``-N`` 后缀,返回 ``(level, title, slug, anchor)``。"""
  counts: dict[str, int] = {}
  out: list[tuple[int, str, str, str]] = []
  for level, title, slug in headings:
    n = counts.get(slug, 0)
    counts[slug] = n + 1
    anchor = slug if n == 0 else f"{slug}-{n}"
    out.append((level, title, slug, anchor))
  return out


# ─────────────────────────────────────────────────────────────
# v1.0.1:后处理 — mermaid 围栏 / GFM tasklist
# ─────────────────────────────────────────────────────────────


_TASKLIST_RE = re.compile(r"^\s*\[([ xX])\]\s*(.*)$", re.DOTALL)


def _post_process_html(soup: Any) -> None:
  """就地修改 soup,处理 markdown → HTML 后的两类残留。

  1. ``mermaid`` 围栏:markdown 库输出 ``<pre><code class="language-mermaid">xxx</code></pre>``,
     把 ``<code>`` 内容移到 ``<pre>`` 自身 + ``<pre class="mermaid">``,
     让浏览器端 mermaid.js 自动渲染。
  2. GFM tasklist:markdown 库默认输出 ``<li>[ ] xxx</li>`` / ``<li>[x] xxx</li>``
     (有序列表 ``1. [ ] xxx`` 同样落到 ``<li>`` 内),把开头的 ``[ ]`` / ``[x]``
     替换为 ``<input type="checkbox" disabled>`` (checked 视原状态)。
  """
  from bs4 import BeautifulSoup, NavigableString

  # 1. mermaid 围栏
  for pre in list(soup.find_all("pre")):
    code = pre.find("code")
    if code is None:
      continue
    classes = code.get("class") or []
    classes_list = classes.split() if isinstance(classes, str) else list(classes)
    is_mermaid = any(c in ("mermaid", "language-mermaid") for c in classes_list)
    if not is_mermaid:
      continue
    inner = code.get_text()
    code.decompose()
    pre.clear()
    pre["class"] = "mermaid"
    pre.append(NavigableString(inner))

  # 2. GFM tasklist checkbox
  for li in soup.find_all("li"):
    raw = li.decode_contents()
    m = _TASKLIST_RE.match(raw)
    if not m:
      continue
    checked = m.group(1).lower() == "x"
    rest = m.group(2)
    li.clear()
    # checkbox 必须作为 tag 插入(NavigableString 会被 escape)
    checkbox_html = (
      f'<input type="checkbox" disabled{" checked" if checked else ""}>'
    )
    cb_fragment = BeautifulSoup(checkbox_html, "html.parser")
    cb_tag = cb_fragment.find("input")
    if cb_tag is not None:
      li.append(cb_tag.extract())
    li.append(NavigableString(" "))
    # rest 可能含 innerHTML(链接等),parse 后逐 child append
    rest_fragment = BeautifulSoup(rest, "html.parser")
    for child in list(rest_fragment.contents):
      if hasattr(child, "name") and child.name is not None:
        li.append(child.extract())
      else:
        li.append(NavigableString(str(child)))


# ─────────────────────────────────────────────────────────────
# 公开 API
# ─────────────────────────────────────────────────────────────


def process_long_doc(
  work: Path,
  provider: BaseLLMProvider | None,
  config: WorkflowConfig | None = None,
  *,
  source_md: Path | None = None,
  output_dir: Path | None = None,
  output_stem: str | None = None,
  final_dir: Path | None = None,
  chunk_size: int = DEFAULT_CHUNK_SIZE,
  write_html: bool = True,
) -> LongDocResult:
  """Stage 10:深度净化 render 阶段产出的 markdown + 渲染最终 HTML。

  W12-D 新规:最终 ``<stem>_cleaned.md`` + ``<stem>_final.html`` 写到
  ``final_dir``(默认 ``<work>.parent / "output_final"``),与中间产物分离。

  Parameters
  ----------
  work : Path
    work 根目录(中间产物根)
  provider : BaseLLMProvider | None
    LLM provider 实例;为 ``None`` 或属性 ``name == "skip"`` 时跳过 LLM
    净化(仅做规则清理)
  config : WorkflowConfig | None
    配置(预留,当前未读字段)
  source_md : Path | None
    源 markdown(默认 ``<work>/chapters/raw/<video_stem>.md``)
  output_dir : Path | None
    **保留参数**——向后兼容。优先级低于 ``final_dir``。
  output_stem : Path | None
    输出文件 stem(默认 = 派生:``chapters.json video`` 或 ``source_md.stem``)
  final_dir : Path | None
    W12-D 新增:最终产物目录(默认 ``<work>.parent / "output_final"``)。
  chunk_size : int
    分块大小(CJK 字符数,默认 15000)
  write_html : bool
    是否同时写最终 HTML(默认 True)

  Returns
  -------
  LongDocResult
    含源/净化/最终产物路径 + provider/model + 统计

  Raises
  ------
  FileNotFoundError
    源 markdown 不存在
  """
  _ = config
  # 1. 定位源文件
  if source_md is None:
    # 默认: ``<work>/chapters/raw/<video_stem>.md``(与 render 一致)
    chapters_dir = work / "chapters"
    if (chapters_dir / "chapters.json").exists():
      chapters_json = json.loads(
        (chapters_dir / "chapters.json").read_text(encoding="utf-8")
      )
      video = (chapters_json.get("video") or "").strip() or "output"
    else:
      video = "output"
    source_md = chapters_dir / "raw" / f"{video}.md"
  if not source_md.exists():
    raise FileNotFoundError(
      f"找不到源 markdown {source_md};请先跑 render stage"
    )

  # W12-D:输出目录优先级 = final_dir > output_dir > <work>.parent / "output_final"
  if output_stem is None:
    # 优先用 chapters.json video 字段(真视频名),fallback 到 source_md.stem
    chapters_dir = work / "chapters"
    if (chapters_dir / "chapters.json").exists():
      chapters_json = json.loads(
        (chapters_dir / "chapters.json").read_text(encoding="utf-8")
      )
      output_stem = (chapters_json.get("video") or "").strip() or source_md.stem
    else:
      output_stem = source_md.stem

  target_dir: Path
  if final_dir is not None:
    target_dir = final_dir
  elif output_dir is not None:
    target_dir = output_dir
  else:
    target_dir = work.parent / "output_final"
  target_dir.mkdir(parents=True, exist_ok=True)

  text = source_md.read_text(encoding="utf-8")
  if not text.strip():
    raise ValueError(f"源 markdown {source_md} 为空")

  # 2. 决定净化模式
  provider_name = getattr(provider, "name", "skip") or "skip"
  use_llm = provider is not None and provider_name != "skip"

  # 3. 分块 + 净化
  chunks = _split_into_chunks(text, chunk_size=chunk_size)
  cleaned_chunks: list[str] = []
  total_rules: list[str] = []
  total_lines_stripped = 0
  chars_input = len(text)
  provider_label = provider_name
  model_label = ""

  if use_llm:
    assert provider is not None  # for type checker
    for chunk in chunks:
      cleaned = _purify_chunk_with_llm(chunk, provider)
      cleaned_chunks.append(cleaned)
      model_label = getattr(provider, "model", "") or model_label
  else:
    for chunk in chunks:
      cleaned, stats = _rule_clean_text(chunk)
      cleaned_chunks.append(cleaned)
      total_rules.extend(stats.rules_applied)
      total_lines_stripped += stats.lines_stripped

  cleaned_text = "\n\n".join(c.rstrip() for c in cleaned_chunks).rstrip() + "\n"
  cleaned_path = target_dir / f"{output_stem}{_CLEANED_SUFFIX}"
  cleaned_path.write_text(cleaned_text, encoding="utf-8")

  # 4. 渲染最终 HTML
  final_path: Path | None = None
  if write_html:
    final_path = render_final_html(
      cleaned_md=cleaned_path,
      html_path=target_dir / f"{output_stem}{_FINAL_SUFFIX}",
    )
  else:
    final_path = target_dir / f"{output_stem}{_FINAL_SUFFIX}"

  # 5. 统计
  chars_output = len(cleaned_text)
  retention = chars_output / chars_input if chars_input else 1.0
  if use_llm:
    rules_applied = ["llm_purify"] if chunks else ["noop"]
  else:
    # 去重
    rules_applied = list(dict.fromkeys(total_rules)) or ["noop"]
  stats = PurificationStats(
    chunks_total=len(chunks),
    chars_input=chars_input,
    chars_output=chars_output,
    retention_rate=retention,
    rules_applied=rules_applied,
    lines_stripped=total_lines_stripped,
  )

  return LongDocResult(
    video=output_stem,
    course_title=output_stem,
    source_md=source_md,
    cleaned_md=cleaned_path,
    final_html=final_path if final_path.exists() else None,
    provider=provider_label,
    model=model_label,
    stats=stats,
  )


def render_final_html(
  cleaned_md: Path,
  html_path: Path | None = None,
  *,
  title: str | None = None,
) -> Path:
  """把 ``<stem>_cleaned.md`` 渲染为 ``<stem>_final.html``(内嵌 CSS + TOC 锚点)。

  Parameters
  ----------
  cleaned_md : Path
    净化后的 markdown 路径
  html_path : Path | None
    输出 HTML 路径(默认 ``<cleaned_md_stem>``.html 与 cleaned 同目录)
  title : str | None
    HTML ``<title>``(默认 = ``cleaned_md.stem`` 去掉 ``_cleaned`` 后缀)

  Returns
  -------
  Path
    实际写入的 html 路径

  Raises
  ------
  FileNotFoundError
    cleaned_md 不存在
  """
  if not cleaned_md.exists():
    raise FileNotFoundError(f"找不到 {cleaned_md}")
  md_text = cleaned_md.read_text(encoding="utf-8")

  if title is None:
    stem = cleaned_md.stem
    title = stem[: -len("_cleaned")] if stem.endswith("_cleaned") else stem

  # 提取标题并赋予唯一 slug
  headings = _extract_headings(md_text)
  unique = _assign_unique_slugs(headings)

  # 把 H1/H2/H3 标题插入 anchor id
  body_html = _md_body_with_anchors(md_text, unique)

  # toc HTML
  toc_html = _build_toc_html([(lvl, t, a) for lvl, t, s, a in unique])

  import datetime as _dt

  full_html = _HTML_TEMPLATE.format(
    title=_html_escape(title),
    toc_html=toc_html,
    body_html=body_html,
    generated_at=_dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
  )

  target = html_path or cleaned_md.with_name(f"{cleaned_md.stem}{_FINAL_SUFFIX}")
  target = target.with_suffix(".html") if target.suffix != ".html" else target
  target.write_text(full_html, encoding="utf-8")
  return target


def _md_body_with_anchors(
  md_text: str,
  unique_headings: list[tuple[int, str, str, str]],
) -> str:
  """markdown 库转换 + 把每个标题的 id 替换为我们的 anchor。

  - 先用 markdown 库转 HTML
  - 用 BeautifulSoup 找 ``h1/h2/h3/h4`` 的 id
  - 按出现顺序匹配 unique_headings,替换 id
  """
  import markdown as _md
  from markdown.extensions.toc import TocExtension

  md = _md.Markdown(
    extensions=[
      "fenced_code",
      "tables",
      TocExtension(toc_depth="2-4"),
    ],
    output_format="html",
  )
  html = md.convert(md_text)

  # lazy import
  try:
    from bs4 import BeautifulSoup  # type: ignore[import-not-found]
  except ImportError as exc:
    raise ImportError(
      "render_final_html 需要 beautifulsoup4;请 `uv add media_to_doc[longdoc]`"
    ) from exc

  soup = BeautifulSoup(html, "lxml")
  tag_to_level = {"h1": 1, "h2": 2, "h3": 3, "h4": 4}
  heading_iter = iter(unique_headings)
  for tag in soup.find_all(list(tag_to_level.keys())):
    try:
      _, _title, _slug, anchor = next(heading_iter)
    except StopIteration:
      break
    tag["id"] = anchor

  # v1.0.1:后处理 mermaid 围栏 + GFM tasklist checkbox
  _post_process_html(soup)

  return str(soup)


__all__ = [
  "DEFAULT_CHUNK_SIZE",
  "LongDocResult",
  "PurificationStats",
  "process_long_doc",
  "render_final_html",
]
