"""多视频讲义合并(W12-D 新增)。

按用户新规第 3 条:多视频处理后,合并根据多视频输出的文档,整合序号。
文件名使用第一个视频的名称(去除序号)。

输入
----
``<output_final_dir>/<video1>_cleaned.md / .html`` +
``<video2>_cleaned.md / .html`` + ...

输出
----
``<output_final_dir>/<merged_name>_cleaned.md / .html`` +
``<output_final_dir>/<merged_name>/images/<original_stem>_<file>``

合并规则
--------

1. **文件名**:用第一个视频 stem,去除序号前缀(如 ``01_xxx`` → ``xxx``)
2. **章节序号**:全局重排。``## 一、`` → ``## 第一部分``(第一个视频),
   后续视频章节用 ``## 第二部分`` / ``## 第三部分`` 包裹
3. **图片路径**:每个原 md 的 ``<stem>/images/<file>`` 重写到
   ``<merged_name>/images/<original_stem>_<file>``
4. **HTML**:用 :func:`longdoc.render_final_html` 渲染最终 HTML

合并 ``_cleaned.md``(讲师 9/9 ⭐ LLM 净化版),如果不存在则 fallback 到 ``.md``。
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# 章节序号提取:`01_xxx` / `01-xxx` / `01 xxx` → ``(1, "xxx")``
_LEADING_INDEX_RE = re.compile(r"^\s*(\d+)[_\-\s]+(.*)$")
# 章节标题序号:`## 一、` `## 1.` `## 第一章` → ``(1, "原标题")``
_CN_NUM = {
  "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
  "八": 8, "九": 9, "十": 10,
}


@dataclass
class MergeResult:
  """合并结果摘要。"""

  output_dir: Path
  merged_name: str
  source_files: list[Path] = field(default_factory=list)
  merged_md: Path | None = None
  merged_html: Path | None = None
  copied_images: int = 0

  def to_dict(self) -> dict[str, object]:
    return {
      "output_dir": str(self.output_dir),
      "merged_name": self.merged_name,
      "source_files": [str(p) for p in self.source_files],
      "merged_md": str(self.merged_md) if self.merged_md else "",
      "merged_html": str(self.merged_html) if self.merged_html else "",
      "copied_images": self.copied_images,
    }

  def save_manifest(self, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
      json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
      encoding="utf-8",
    )


# ─────────────────────────────────────────────────────────────
# 工具:文件名解析 + 序号提取
# ─────────────────────────────────────────────────────────────


def strip_leading_index(stem: str) -> str:
  """去除 stem 开头的序号前缀。

  ``"01_先精准后放大"`` → ``"先精准后放大"``
  ``"02-拉新"`` → ``"拉新"``
  ``"03 全站爆款"`` → ``"全站爆款"``
  ``"全站爆款流程"`` → ``"全站爆款流程"``(无前缀)
  """
  m = _LEADING_INDEX_RE.match(stem)
  if m:
    return m.group(2).strip()
  return stem.strip()


def discover_lecture_files(
  output_final_dir: Path,
  prefer_cleaned: bool = True,
) -> list[tuple[Path, str]]:
  """扫 ``<output_final_dir>/`` 下的讲义文件,返回 ``(path, stem)`` 列表。

  优先 ``<stem>_cleaned.md``(LLM 净化版),fallback 到 ``<stem>.md``。
  跳过合并产物(以 ``_merged`` 结尾的文件)。
  按文件名自然排序(让用户预期的顺序稳定)。

  Parameters
  ----------
  output_final_dir : Path
    最终产物目录(默认 ``<video>.parent / output_final/``)
  prefer_cleaned : bool
    优先选 ``_cleaned.md``(讲师版),fallback 到 ``.md``(逐字稿版)。

  Returns
  -------
  list[tuple[Path, str]]
    ``[(md_path, stem), ...]`` 排序后的列表
  """
  if not output_final_dir.exists():
    raise FileNotFoundError(f"output_final_dir 不存在:{output_final_dir}")

  found: dict[str, Path] = {}  # stem → path
  for p in sorted(output_final_dir.glob("*.md")):
    raw_stem = p.stem
    base_stem = raw_stem
    if raw_stem.endswith("_cleaned"):
      base_stem = raw_stem[: -len("_cleaned")]
    # 跳过合并产物(避免自我合并)
    if base_stem.endswith("_merged"):
      continue
    # 同目录下 _cleaned.md 与 .md 视为同一讲义(用 base_stem 去重)
    if prefer_cleaned or base_stem not in found:
      found[base_stem] = p

  # 自然排序:数字部分按数值比较,避免 "10_xxx" < "1_xxx"
  def _natural_key(stem: str) -> list[tuple[int, str | int]]:
    parts = re.split(r"(\d+)", stem)
    return [(0, int(p)) if p.isdigit() else (1, p) for p in parts if p]

  return [(path, stem) for stem, path in sorted(found.items(), key=lambda kv: _natural_key(kv[0]))]


# ─────────────────────────────────────────────────────────────
# 合并主流程
# ─────────────────────────────────────────────────────────────


@dataclass
class ChapterSummary:
  """单章节简化版:用于 LLM fusion prompt,避免上下文超限。"""

  video: str
  chapter: str
  summary: str

  def to_dict(self) -> dict[str, str]:
    return {"video": self.video, "chapter": self.chapter, "summary": self.summary}


@dataclass
class FusionSource:
  """fusion_plan.sources 一项:指明某个融合章节包含哪(几)个原章节。"""

  video: str
  chapter: str
  include: str = "all"  # "all" | "first_n:<n>" | "summary"

  def to_dict(self) -> dict[str, str]:
    return {"video": self.video, "chapter": self.chapter, "include": self.include}


@dataclass
class FusionChapter:
  """fusion_plan.chapters 一项:融合后的全局章节。"""

  title: str
  sources: list[FusionSource] = field(default_factory=list)

  def to_dict(self) -> dict[str, object]:
    return {
      "title": self.title,
      "sources": [s.to_dict() for s in self.sources],
    }


@dataclass
class FusionPlan:
  """LLM 返回的融合规划(全局章节结构)。"""

  chapters: list[FusionChapter] = field(default_factory=list)

  def to_dict(self) -> dict[str, object]:
    return {"chapters": [c.to_dict() for c in self.chapters]}


# ─────────────────────────────────────────────────────────────
# 简化版生成(避免上下文超限)
# ─────────────────────────────────────────────────────────────


def chapters_summary(
  md_text: str,
  max_summary_chars: int = 800,
  video_name: str = "",
) -> list[ChapterSummary]:
  """从 md 文本提取章节简化版,用于 fusion prompt。

  跳过代码块围栏(`` ``` ``/`` ~~~ ``),按 H2 切分章节;
  每个章节摘要 = H2 标题 + 前 max_summary_chars 字符的正文。

  Parameters
  ----------
  md_text : str
    cleaned.md 全文
  max_summary_chars : int
    每章摘要最大字符数(默认 800,经验值)
  video_name : str
    视频名(给 summary 标归属,空时从 H1 提取)

  Returns
  -------
  list[ChapterSummary]
    ``[(video, chapter, summary), ...]`` 按文档顺序
  """
  if not video_name:
    # 从 H1 提取
    for line in md_text.split("\n"):
      if line.startswith("# ") and not line.startswith("## "):
        video_name = line[2:].strip()
        break
  video_name = video_name or "untitled"

  out: list[ChapterSummary] = []
  lines = md_text.split("\n")
  in_code = False
  current_chapter: str | None = None
  current_lines: list[str] = []

  def _flush(chapter: str | None, body: list[str]) -> None:
    if chapter is None:
      return
    text = "\n".join(body).strip()
    if len(text) > max_summary_chars:
      text = text[:max_summary_chars].rstrip() + "…"
    out.append(
      ChapterSummary(
        video=video_name,
        chapter=chapter,
        summary=text,
      )
    )

  for line in lines:
    stripped = line.lstrip()
    if stripped.startswith("```") or stripped.startswith("~~~"):
      in_code = not in_code
      if current_chapter is not None:
        current_lines.append(line)
      continue
    if in_code:
      if current_chapter is not None:
        current_lines.append(line)
      continue
    # H2 切分
    if line.startswith("## ") and not line.startswith("### "):
      _flush(current_chapter, current_lines)
      current_chapter = line[3:].strip()
      current_lines = []
      continue
    if current_chapter is not None:
      current_lines.append(line)

  _flush(current_chapter, current_lines)
  return out


# ─────────────────────────────────────────────────────────────
# Fusion prompt + LLM 解析
# ─────────────────────────────────────────────────────────────


_FUSION_SYSTEM_PROMPT = (
  "你是资深讲义编辑,擅长把多段独立讲义融合为一份连贯的全局讲义。"
  "任务:把下列多个视频的章节列表融合为统一的全局章节结构。"
  "规则:\n"
  "1. **内容驱动**:章节命名与切分应基于内容逻辑,不要简单按视频分块。\n"
  "   跨视频连续内容(如同主题的不同方面)应合并为同一全局章节。\n"
  "2. **粒度合理**:全局章节数 = max(视频章节数 / 2, 4),既不冗余也不碎。\n"
  "3. **来源透明**:每个全局章节必须列出包含哪些源章节,精确匹配用户输入的章节标题。\n"
  "4. **include 控制**:\n"
  "   - 'all' = 引用该源章节全文(默认,适合主体内容)\n"
  "   - 'first_n:2' = 引用前 2 段(适合只取关键观点的辅助章节)\n"
  "   - 'summary' = 仅作引用提及,不搬正文(适合重复或收尾章节)\n"
  "5. **顺序合理**:全局章节按讲义叙事逻辑排序(开场 → 主体 → 收尾),而非视频出现顺序。\n"
  "6. **严格 JSON 输出**:不写解释,只输出 JSON 对象。"
)

_FUSION_USER_PROMPT = """## 任务

把以下 {n_videos} 个视频讲义的章节融合为一份统一的全局章节结构。
合并产物将作为讲义分发给读者,需要逻辑连贯、命名统一。

## 视频与章节列表

{video_summaries}

## 输出格式

严格的 JSON 对象,无 markdown 代码块标记:

{{
  "chapters": [
    {{
      "title": "融合章节 1 标题",
      "sources": [
        {{"video": "<video_name>", "chapter": "<原章节标题>", "include": "all"}},
        {{"video": "<video_name>", "chapter": "<原章节标题>", "include": "first_n:2"}}
      ]
    }},
    ...
  ]
}}
"""


def _build_fusion_prompt(
  summaries_by_video: dict[str, list[ChapterSummary]],
) -> str:
  """构造 fusion 用户 prompt(把所有视频的简化版拼起来)。"""
  blocks: list[str] = []
  for video, summaries in summaries_by_video.items():
    blocks.append(f"\n### 视频:{video}\n")
    for i, s in enumerate(summaries, start=1):
      blocks.append(
        f"- **章节 {i}:{s.chapter}**\n"
        f"  {s.summary or '(无摘要)'}\n"
      )
  return _FUSION_USER_PROMPT.format(
    n_videos=len(summaries_by_video),
    video_summaries="\n".join(blocks),
  )


def _parse_fusion_plan(raw: str) -> FusionPlan:
  """从 LLM 输出解析 fusion plan(JSON 容错,支持 ```json 围栏)。"""
  text = raw.strip()
  fence_re = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
  m = fence_re.search(text)
  if m:
    text = m.group(1).strip()
  # 找首个 { 到末个 } 之间
  start = text.find("{")
  end = text.rfind("}")
  if start != -1 and end != -1 and end > start:
    text = text[start : end + 1]
  data = json.loads(text)
  chapters: list[FusionChapter] = []
  for ch_data in data.get("chapters", []):
    sources: list[FusionSource] = []
    for src in ch_data.get("sources", []):
      sources.append(
        FusionSource(
          video=str(src.get("video", "")).strip(),
          chapter=str(src.get("chapter", "")).strip(),
          include=str(src.get("include", "all")).strip() or "all",
        )
      )
    if sources:  # 跳过空 sources 的章节
      chapters.append(
        FusionChapter(
          title=str(ch_data.get("title", "未命名章节")).strip(),
          sources=sources,
        )
      )
  return FusionPlan(chapters=chapters)


# ─────────────────────────────────────────────────────────────
# Fusion plan 应用:重写合并 md
# ─────────────────────────────────────────────────────────────


def _split_md_by_chapters(
  md_text: str,
) -> list[tuple[str, str]]:
  """把 md 切分为 ``[(chapter_title, body), ...]`` 列表。

  跳过代码块围栏内的 ``## `` 误判;包含 H1(整视频标题)在最前,
  chapter 为空表示它是 H1 段。
  """
  lines = md_text.split("\n")
  out: list[tuple[str, str]] = []
  in_code = False
  h1: str | None = None
  current_chapter: str | None = ""
  current_body: list[str] = []

  def _flush(chapter: str | None, body: list[str]) -> None:
    out.append((chapter or "", "\n".join(body).rstrip()))

  for line in lines:
    stripped = line.lstrip()
    if stripped.startswith("```") or stripped.startswith("~~~"):
      in_code = not in_code
      if current_chapter is not None:
        current_body.append(line)
      continue
    if in_code:
      if current_chapter is not None:
        current_body.append(line)
      continue
    if line.startswith("# ") and not line.startswith("## "):
      # 第一个 H1:不当作 chapter
      if h1 is None:
        h1 = line[2:].strip()
        continue
      # 后续 H1 出现:当作 chapter 边界
      _flush(current_chapter, current_body)
      current_chapter = f"<<H1:{line[2:].strip()}>>"
      current_body = []
      continue
    if line.startswith("## ") and not line.startswith("### "):
      _flush(current_chapter, current_body)
      current_chapter = line[3:].strip()
      current_body = []
      continue
    if current_chapter is not None:
      current_body.append(line)

  _flush(current_chapter, current_body)
  return out


def _fuzzy_match_chapter(
  query: str,
  candidates: list[str],
) -> str | None:
  """fuzzy 匹配 query 到 candidates 中最相似的字符串。相似度阈值 0.6。"""
  if not query or not candidates:
    return None
  from difflib import SequenceMatcher

  best: tuple[str, float] | None = None
  for cand in candidates:
    score = SequenceMatcher(None, query, cand).ratio()
    if best is None or score > best[1]:
      best = (cand, score)
  if best is None or best[1] < 0.6:
    return None
  return best[0]


def _truncate_chapter_body(body: str, include: str) -> str:
  """按 include 指令截取章节正文。"""
  if include == "all" or not include:
    return body
  if include == "summary":
    return ""
  m = re.match(r"^first_n:(\d+)$", include)
  if m:
    n = int(m.group(1))
    # 按 \n\n 切段,取前 n 段
    parts = re.split(r"\n\n+", body.strip())
    return "\n\n".join(parts[:n])
  return body  # 未知 include → 兜底用全文


def apply_fusion_plan(
  plan: FusionPlan,
  source_mds: dict[str, str],
  merged_name: str,
) -> str:
  """按 fusion_plan 重组合并 md。

  Parameters
  ----------
  plan : FusionPlan
    LLM 返回的融合规划
  source_mds : dict[str, str]
    ``{video_stem: md_text, ...}`` 所有源讲义
  merged_name : str
    合并产物名(用于 H1 + TOC)

  Returns
  -------
  str
    拼装好的合并 md 全文
  """
  # 预解析每个源讲义:(video, [(chapter, body), ...])
  parsed: dict[str, list[tuple[str, str]]] = {}
  for video, md_text in source_mds.items():
    parsed[video] = _split_md_by_chapters(md_text)

  # 拼装
  parts: list[str] = []
  parts.append(f"# {merged_name}")
  parts.append("")
  parts.append(
    f"> 本讲义由 media-to-doc merge_lectures(LLM 融合)合并"
    f" {len(source_mds)} 个视频讲义。"
  )
  parts.append("")
  parts.append("## 目录")
  parts.append("")
  for ch in plan.chapters:
    parts.append(f"- {ch.title}")
  parts.append("")
  parts.append("---")
  parts.append("")

  # 跟踪哪些源章节被引用(用于 manifest 统计)
  for ch in plan.chapters:
    parts.append(f"## {ch.title}")
    parts.append("")
    for src in ch.sources:
      md_text = source_mds.get(src.video)
      if md_text is None:
        # video 找不到,降级为只显示标题
        parts.append(
          f"> 引用自 `{src.video}` / 章节 `{src.chapter}`(源视频不在本批合并)"
        )
        parts.append("")
        continue
      chapters = parsed.get(src.video, [])
      # 用 fuzzy 匹配找原章节
      titles = [t for t, _ in chapters if t and not t.startswith("<<H1:")]
      matched = _fuzzy_match_chapter(src.chapter, titles)
      if matched is None:
        parts.append(
          f"> 引用自 `{src.video}` / 章节 `{src.chapter}`(源未找到,fallback)"
        )
        parts.append("")
        continue
      body = next(b for t, b in chapters if t == matched)
      body = _truncate_chapter_body(body, src.include)
      if body:
        # 图片路径重写
        body = _rewrite_image_refs_to_merged(
          body, original_stem=src.video, merged_name=merged_name,
        )
        parts.append(body.rstrip())
        parts.append("")
      else:
        # include="summary" 等空正文:仍写引用提示,让读者知道引自哪里
        parts.append(
          f"> (汇总自 `{src.video}` / 章节 `{src.chapter}`,include=`{src.include}`)"
        )
        parts.append("")
    parts.append("---")
    parts.append("")

  return "\n".join(parts).rstrip() + "\n"


# ─────────────────────────────────────────────────────────────
# 合并主流程
# ─────────────────────────────────────────────────────────────


def _copy_video_images(
  output_final_dir: Path,
  video_stem: str,
  merged_name: str,
) -> int:
  """把 ``<output_final_dir>/<video_stem>/images/`` 复制到
  ``<output_final_dir>/<merged_name>/images/<video_stem>_*.png``。

  返回复制的图片数(0 表示没有图片目录)。
  """
  src_images = output_final_dir / video_stem / "images"
  if not src_images.exists():
    return 0
  dest_images = output_final_dir / merged_name / "images"
  dest_images.mkdir(parents=True, exist_ok=True)
  copied = 0
  for img in src_images.glob("*.png"):
    dest = dest_images / f"{video_stem}_{img.name}"
    shutil.copy2(img, dest)
    copied += 1
  return copied


def _rewrite_image_refs_in_md(md_text: str, video_stem: str) -> str:
  """把 md 中的 ``<stem>/images/<file>`` 改写为 ``<merged>/images/<video_stem>_<file>``。

  只针对 ``<stem>/images/`` 前缀的引用(wikilink + md-link 两种语法)。

  注意:此函数在 _rewrite_image_refs_to_merged 调用前对单段 md 做,实际归并时
  知道 video_stem 后用 _rewrite_image_refs_to_merged 一次性替换。
  """
  # 当前函数保留用于测试 / 调试。归并主流程用 _rewrite_image_refs_to_merged
  raise NotImplementedError(
    "请用 _rewrite_image_refs_to_merged(stem, merged_name, md_text)"
  )


def _rewrite_image_refs_to_merged(
  md_text: str,
  original_stem: str,
  merged_name: str,
) -> str:
  """把 md 中的 ``<original_stem>/images/<file>`` → ``<merged_name>/images/<original_stem>_<file>``。

  支持两种语法:
  - 标准 md:``![alt](<stem>/images/foo.png)`` / ``![alt](stem/images/foo.png)``
  - wiki-link:``![[foo.png]]``(不常见于 render 后产物,但兼容)

  不修改外部 URL 图片。
  """
  # md-link 标准语法:`![alt](<stem>/images/foo.png)` 或 `![alt](stem/images/foo.png)`
  md_link_re = re.compile(
    r"!\[([^\]]*)\]\((" + re.escape(original_stem) + r"/images/[^)]+)\)"
  )
  md_text = md_link_re.sub(
    lambda m: f"![{m.group(1)}]({merged_name}/images/{original_stem}_"
    + m.group(2).split("/")[-1] + ")",
    md_text,
  )
  # wiki-link:render 阶段已重写,这里兼容兜底
  wiki_re = re.compile(r"!\[\[(" + re.escape(original_stem) + r"/images/[^]]+)\]\]")
  md_text = wiki_re.sub(
    lambda m: f"![[{merged_name}/images/{original_stem}_"
    + m.group(2).split("/")[-1] + "]]",
    md_text,
  )
  return md_text


def _wrap_chapters(
  md_text: str,
  part_num: int,
  part_title: str,
) -> str:
  """把单视频的 md 包成 ``## 第N部分:xxxx`` 段。

  - 把 H1 标题改成 H2 ``## 第N部分:xxxx``
  - 把每个 H2 章节改成 H3 ``### <原章节>``
  - 其他 H3+ 顺延一级
  """
  if part_num == 1:
    title_prefix = "第一部分"
  elif part_num == 2:
    title_prefix = "第二部分"
  elif part_num == 3:
    title_prefix = "第三部分"
  elif part_num == 4:
    title_prefix = "第四部分"
  elif part_num == 5:
    title_prefix = "第五部分"
  else:
    title_prefix = f"第{part_num}部分"

  out: list[str] = []
  in_code = False
  for line in md_text.split("\n"):
    stripped = line.lstrip()
    if stripped.startswith("```") or stripped.startswith("~~~"):
      in_code = not in_code
      out.append(line)
      continue
    if in_code:
      out.append(line)
      continue
    # H1 → H2
    if line.startswith("# ") and not line.startswith("## "):
      title = line[2:].strip()
      out.append(f"## {title_prefix}:{title}")
      continue
    # H2 → H3
    if line.startswith("## ") and not line.startswith("### "):
      out.append("#" + line)  # 加一个 # → H3
      continue
    # H3 → H4
    if line.startswith("### ") and not line.startswith("#### "):
      out.append("#" + line)
      continue
    # H4 → H5
    if line.startswith("#### ") and not line.startswith("##### "):
      out.append("#" + line)
      continue
    out.append(line)
  return "\n".join(out)


def merge_lectures(
  output_final_dir: Path,
  merged_name: str | None = None,
  *,
  no_html: bool = False,
  prefer_cleaned: bool = True,
  fusion_provider: Any | None = None,
  fusion_model: str = "",
  fallback_on_error: bool = True,
) -> MergeResult:
  """合并多视频讲义主入口。

  Parameters
  ----------
  output_final_dir : Path
    最终产物目录(默认 ``<video>.parent / output_final/``)
  merged_name : str | None
    合并产物文件名(去 ``.md`` 后缀)。默认 = 第一个视频 stem 去除序号
  no_html : bool
    是否跳过 HTML 渲染(默认 False)
  prefer_cleaned : bool
    优先选 ``_cleaned.md`` 净化版,fallback 到 ``.md``(默认 True)

  Returns
  -------
  MergeResult
    合并结果摘要(含 merged_md / merged_html / copied_images)

  Raises
  ------
  FileNotFoundError
    output_final_dir 不存在或没有可合并的讲义
  ValueError
    只找到 1 个讲义(无需合并,直接返回提示)
  """
  output_final_dir = output_final_dir.resolve()
  lectures = discover_lecture_files(output_final_dir, prefer_cleaned=prefer_cleaned)
  if not lectures:
    raise FileNotFoundError(
      f"在 {output_final_dir} 没有找到讲义文件(.md / _cleaned.md)"
    )
  if len(lectures) == 1:
    raise ValueError(
      f"只找到 1 个讲义 {lectures[0][0].name},无需合并。"
      "至少需要 2 个视频的讲义才能合并。"
    )

  # 决定 merged_name:第一个 stem 去序号
  first_stem = lectures[0][1]
  if merged_name is None:
    merged_name = strip_leading_index(first_stem)
    # 若去重后为空,用 "merged"
    if not merged_name:
      merged_name = "merged"

  # 准备输出目录
  output_final_dir.mkdir(parents=True, exist_ok=True)
  merged_images_dir = output_final_dir / merged_name / "images"
  if merged_images_dir.exists():
    shutil.rmtree(merged_images_dir)
  merged_images_dir.mkdir(parents=True, exist_ok=True)

  # 收集 source_files(共享给两种合并模式)
  source_paths: list[Path] = [md_path for md_path, _ in lectures]

  # 决定合并模式:LLM fusion(若 provider 提供) vs 硬切(向后兼容)
  use_fusion = fusion_provider is not None
  total_copied = 0  # 共享给两种模式,images 复制独立做
  merged_text: str
  if use_fusion:
    # ─── 路径 B:LLM 融合 ─────────────────────────────
    # 1) 收集每个讲义(简化版 + 全文)
    summaries_by_video: dict[str, list[ChapterSummary]] = {}
    source_texts: dict[str, str] = {}
    for md_path, stem in lectures:
      text = md_path.read_text(encoding="utf-8")
      display = strip_leading_index(stem) or stem
      source_texts[stem] = text
      summaries_by_video[stem] = chapters_summary(
        text, max_summary_chars=800, video_name=display,
      )
    # 2) 构造 prompt + 调 LLM
    user_prompt = _build_fusion_prompt(summaries_by_video)
    system_prompt = _FUSION_SYSTEM_PROMPT
    plan: FusionPlan | None = None
    try:
      response = fusion_provider.chat(system_prompt + "\n\n" + user_prompt)
      plan = _parse_fusion_plan(response.text)
    except Exception as exc:
      if not fallback_on_error:
        raise
      import sys

      print(
        f"[merge_lectures] LLM fusion 失败({type(exc).__name__}: {exc}),"
        " 降级到硬切模式",
        file=sys.stderr,
      )
      use_fusion = False
    if use_fusion and plan is not None and plan.chapters:
      merged_text = apply_fusion_plan(plan, source_texts, merged_name)
    else:
      use_fusion = False  # LLM 返回空 plan,降级硬切

  if not use_fusion:
    # ─── 路径 A:硬切(向后兼容,默认) ──────────────
    parts: list[str] = []
    parts.append(f"# {merged_name}")
    parts.append("")
    parts.append(
      f"> 本讲义由 media-to-doc merge_lectures 合并 {len(lectures)} 个视频讲义。"
    )
    parts.append("")
    parts.append("## 目录")
    parts.append("")
    for _i, (_path, stem) in enumerate(lectures, start=1):
      display = strip_leading_index(stem) or stem
      parts.append(f"- {display}")
    parts.append("")
    parts.append("---")
    parts.append("")

    for i, (md_path, stem) in enumerate(lectures, start=1):
      text = md_path.read_text(encoding="utf-8")
      text = _rewrite_image_refs_to_merged(
        text, original_stem=stem, merged_name=merged_name,
      )
      text = _wrap_chapters(
        text, part_num=i, part_title=strip_leading_index(stem),
      )
      parts.append(text.rstrip())
      parts.append("")
      parts.append("---")
      parts.append("")
    merged_text = "\n".join(parts).rstrip() + "\n"

  merged_md = output_final_dir / f"{merged_name}_cleaned.md"
  merged_md.write_text(merged_text, encoding="utf-8")

  # 复制图片(共享两种合并模式)
  for _md_path, stem in lectures:
    total_copied += _copy_video_images(output_final_dir, stem, merged_name)

  # 渲染 HTML(用 longdoc.render_final_html 复用 v1.0.1 mermaid + tasklist 修复)
  merged_html: Path | None = None
  if not no_html:
    from .longdoc import render_final_html

    merged_html = render_final_html(merged_md, title=merged_name)

  result = MergeResult(
    output_dir=output_final_dir,
    merged_name=merged_name,
    source_files=source_paths,
    merged_md=merged_md,
    merged_html=merged_html,
    copied_images=total_copied,
  )
  result.save_manifest(output_final_dir / f"{merged_name}_merge_manifest.json")
  return result


__all__ = [
  "MergeResult",
  "ChapterSummary",
  "FusionPlan",
  "merge_lectures",
  "strip_leading_index",
  "discover_lecture_files",
  "chapters_summary",
  "apply_fusion_plan",
  "_build_fusion_prompt",
]
