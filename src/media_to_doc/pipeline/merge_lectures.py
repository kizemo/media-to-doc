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

  # 拼装 markdown
  parts: list[str] = []
  parts.append(f"# {merged_name}")
  parts.append("")
  parts.append(f"> 本讲义由 media-to-doc merge_lectures 合并 {len(lectures)} 个视频讲义。")
  parts.append("")
  parts.append("## 目录")
  parts.append("")
  for _i, (_path, stem) in enumerate(lectures, start=1):
    display = strip_leading_index(stem) or stem
    parts.append(f"- {display}")
  parts.append("")
  parts.append("---")
  parts.append("")

  total_copied = 0
  source_paths: list[Path] = []
  for i, (md_path, stem) in enumerate(lectures, start=1):
    text = md_path.read_text(encoding="utf-8")
    # 图片路径重写
    text = _rewrite_image_refs_to_merged(text, original_stem=stem, merged_name=merged_name)
    # 章节降一级 + 加 part 标题
    text = _wrap_chapters(text, part_num=i, part_title=strip_leading_index(stem))
    parts.append(text.rstrip())
    parts.append("")
    parts.append("---")
    parts.append("")
    source_paths.append(md_path)
    # 复制图片
    total_copied += _copy_video_images(output_final_dir, stem, merged_name)

  merged_text = "\n".join(parts).rstrip() + "\n"
  merged_md = output_final_dir / f"{merged_name}_cleaned.md"
  merged_md.write_text(merged_text, encoding="utf-8")

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
  "merge_lectures",
  "strip_leading_index",
  "discover_lecture_files",
]
