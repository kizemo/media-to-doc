"""Stage 7 — ``draft``:LLM 章节草稿生成。

输入:
- ``work/chapters/chapters.json``:章节切分(由 :mod:`chapters` 阶段产出)
- ``work/asr/transcript.jsonl``:ASR 逐字稿
- ``work/asr/asr_corrections.json``(可选):OCR × ASR 候选修正

输出:
- ``raw/<视频同名>/chapter_NN.md``:每章节一份草稿 markdown
- ``work/drafts/drafts.json``:整体 manifest(provider/model/字数统计)

逻辑:
1. 从 chapters.json 读 Chapter 列表(含 title / summary / key_points / image_refs / illustrations)
2. 对每章节,从 transcript.jsonl 切片 ``[start_seconds, end_seconds]`` 段的文字
3. 调 LLM 按 prompt("系统 = 中文讲义编辑","用户 = 标题+摘要+要点+切片+修正")
   输出纯 markdown 讲义正文
4. 写 ``raw/<stem>/chapter_NN.md``(N 从 1 开始)
5. 返回 :class:`DraftsReport`(含章节数 / provider / 总字数 / 输出目录)

依赖:
- :class:`BaseLLMProvider`(由调用方传入;runner 用 ``_draft_wrapper`` 从 config 派生)
- :mod:`chapters` 的 :class:`Chapter` / :class:`ChaptersReport` 数据复用

参考:TDD §5 数据流第 7 步 + PROJECT_DESCRIPTION §3.2 draft 行。
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ..config import WorkflowConfig
from .asr import TranscriptSegment, read_transcript_jsonl
from .chapters import Chapter, ChaptersReport

if TYPE_CHECKING:
  from ..llm.base import BaseLLMProvider


# ─────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────

# 默认输出子目录(从 work 派生 inbox 与 stem;适用于 ``mtd run`` 布局)
_DEFAULT_RAW_SUBDIR = "raw"

# 单 prompt 最大 transcript 字符数(防止单章节超长截断)
_DEFAULT_TRANSCRIPT_CHAR_CAP = 12000

# 单 prompt 输出最大字符数(防 LLM 输出失控)
DEFAULT_MAX_OUTPUT_CHARS = 16000

# 章节草稿文件命名:``chapter_NN.md``
_DRAFT_FILENAME = "chapter_{idx:02d}.md"


# ─────────────────────────────────────────────────────────────
# Prompt 模板
# ─────────────────────────────────────────────────────────────


_SYSTEM_PROMPT = (
  "你是一名资深课程编辑,把培训视频逐字稿改写为结构化的中文讲义。"
  "讲义要遵循给定章节的标题 / 摘要 / 关键要点 / 配图标注,"
  "语言流畅、信息完整;严禁编造逐字稿中没有的细节。"
  "如果出现 AI 配图标注,以 ``[[GEN: 描述]]`` 一行占位,描述不超过 30 字。"
)

_USER_PROMPT_TEMPLATE = """\
## 任务

把以下培训视频章节,改写为一份**结构化中文讲义**章节。

## 章节标题
{title}

## 章节摘要(50-100 字)
{summary}

## 关键要点(必须覆盖,3-5 条)
{key_points}

## 该章节的逐字稿片段

下面 ``[start-ends] text`` 格式的时间戳与文字:

{transcript}

## OCR 候选修正(可选,可能的人名/专有名词)

{corrections}

## 输出要求

- **格式**:Markdown 二级标题 ``##`` 是章节标题(已写),三级标题 ``###`` 起分段
- **线索保留**:每个关键要点用一个三级标题展开
- **风格**:叙事性中文,忠实于逐字稿;不杜撰事实;不输出代码块围栏
- **AI 配图标注**:如适合,在合理位置插入 ``[[GEN: 一句话描述图内容]]`` 占位,**0-3 处**
- **字数**:1500-3500 字
- 输出**只含章节正文**(不要重新写标题/摘要/要点列表/JSON)。
"""


# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


@dataclass
class ChapterDraft:
  """单章节草稿结果。"""

  idx: int  # 1-based
  chapter_title: str
  output_path: Path
  body: str
  char_count: int
  illustration_count: int = 0

  def to_dict(self) -> dict[str, object]:
    return {
      "idx": self.idx,
      "chapter_title": self.chapter_title,
      "output_path": str(self.output_path),
      "char_count": self.char_count,
      "illustration_count": self.illustration_count,
    }


@dataclass
class DraftsReport:
  """整体草稿生成结果(对应 ``drafts.json``)。"""

  video: str = ""
  course_title: str = ""
  provider: str = ""
  model: str = ""
  output_dir: str = ""
  drafts: list[ChapterDraft] = field(default_factory=list)

  @property
  def total_chars(self) -> int:
    return sum(d.char_count for d in self.drafts)

  def to_dict(self) -> dict[str, object]:
    return {
      "video": self.video,
      "course_title": self.course_title,
      "provider": self.provider,
      "model": self.model,
      "output_dir": self.output_dir,
      "count": len(self.drafts),
      "total_chars": self.total_chars,
      "drafts": [d.to_dict() for d in self.drafts],
    }

  def save(self, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
      json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
      encoding="utf-8",
    )


# ─────────────────────────────────────────────────────────────
# 输入准备
# ─────────────────────────────────────────────────────────────


_GEN_TAG_RE = re.compile(r"\[\[GEN:[^\]]*\]\]")


def _count_illustrations(text: str) -> int:
  """统计 ``[[GEN: ...]]`` 占位标签数量。"""
  return len(_GEN_TAG_RE.findall(text))


def _slice_transcript_for_chapter(
  segments: Iterable[TranscriptSegment],
  start_seconds: float,
  end_seconds: float,
  *,
  char_cap: int = _DEFAULT_TRANSCRIPT_CHAR_CAP,
) -> str:
  """把 transcript 切片到 [start_seconds, end_seconds](首尾包含)。返回 ``[start-ends] text`` 列表。"""
  seg_list = list(segments)  # 容许迭代器且方便统计总数
  lines: list[str] = []
  total = 0
  for seg in seg_list:
    if seg.end < start_seconds or seg.start > end_seconds:
      continue
    line = f"[{seg.start:7.2f}s - {seg.end:7.2f}s] {seg.text}"
    if total + len(line) > char_cap:
      lines.append(line[: max(0, char_cap - total)])
      lines.append(f"... (后续片段省略,共 {len(seg_list)} 段已截断)")
      break
    lines.append(line)
    total += len(line)
  return "\n".join(lines) if lines else "(该章节无对应逐字稿)"


def _load_corrections_for_chapter(work: Path, start: float, end: float) -> str:
  """从 asr_corrections.json 取 [start, end] 时间窗内的去重候选修正。"""
  path = work / "asr" / "asr_corrections.json"
  if not path.exists():
    return ""
  try:
    data = json.loads(path.read_text(encoding="utf-8"))
  except json.JSONDecodeError:
    return ""
  seen: set[str] = set()
  out: list[str] = []
  for corr in data.get("corrections", []):
    seg_start = float(corr.get("segment_start", 0.0))
    seg_end = float(corr.get("segment_end", 0.0))
    # 与章节时间范围有重叠即可
    if seg_end < start or seg_start > end:
      continue
    for cand in corr.get("candidates", []):
      text = cand.get("text", "")
      if text and text not in seen:
        seen.add(text)
        out.append(text)
        if len(out) >= 25:
          return "\n".join(f"- {t}" for t in out)
  return "\n".join(f"- {t}" for t in out)


# ─────────────────────────────────────────────────────────────
# LLM 输出清理
# ─────────────────────────────────────────────────────────────


# 围栏 + 后续免责声明的剥离
_FENCE_RE = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.DOTALL)
_HR_LINE_RE = re.compile(r"^[\s>\-*]*---+\s*$", re.MULTILINE)


def _strip_wrapping(raw: str) -> str:
  """剥离 LLM 输出最外层可能存在的 markdown 代码块围栏。"""
  text = raw.strip()
  m = _FENCE_RE.search(text)
  if m:
    return m.group(1).strip()
  return text


def _normalize_body(body: str, *, max_chars: int = DEFAULT_MAX_OUTPUT_CHARS) -> str:
  """规范化讲义正文:去围栏 / 去尾巴 / 限长。"""
  text = _strip_wrapping(body)
  text = _HR_LINE_RE.sub("", text)
  if len(text) > max_chars:
    text = text[:max_chars].rsplit("\n", 1)[0] + "\n\n(章节过长,后续省略)\n"
  return text.rstrip() + "\n"


# ─────────────────────────────────────────────────────────────
# 输出路径派生
# ─────────────────────────────────────────────────────────────


def _derive_course_title(chapters_report: ChaptersReport) -> str:
  """从 chapters.json 派生课程标题(找不到则用空串,由调用方决定默认)。"""
  return chapters_report.video or ""


def _resolve_output_dir(
  chapters_dir: Path,
  course_title: str,
) -> Path:
  """``raw/<course_title>/`` —— ``course_title`` 为空则用 ``raw/output``。"""
  stem = course_title.strip() or "output"
  return chapters_dir / _DEFAULT_RAW_SUBDIR / stem


def _load_chapters_report(path: Path) -> ChaptersReport:
  """从 chapters.json 反序列化(:class:`ChaptersReport` 没有 ``load`` 类方法)。"""
  data = json.loads(path.read_text(encoding="utf-8"))
  chapters: list[Chapter] = []
  for raw in data.get("chapters", []):
    payload = {k: v for k, v in raw.items() if k != "duration_seconds"}
    chapters.append(Chapter(**payload))
  return ChaptersReport(
    video=data.get("video", ""),
    provider=data.get("provider", ""),
    model=data.get("model", ""),
    chapters=chapters,
  )


# ─────────────────────────────────────────────────────────────
# 公开 API
# ─────────────────────────────────────────────────────────────


def generate_drafts(
  work: Path,
  provider: BaseLLMProvider,
  config: WorkflowConfig | None = None,
  *,
  chapters_dir: Path | None = None,
  output_dir: Path | None = None,
  max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS,
) -> DraftsReport:
  """Stage 7:为每章节生成讲义草稿 markdown。

  Parameters
  ----------
  work : Path
    work 根目录
  provider : BaseLLMProvider
    LLM provider 实例(由 runner 从 config 派生;测试可注入 mock)
  config : WorkflowConfig | None
    配置(预留,当前未读字段)
  chapters_dir : Path | None
    chapters 目录(默认 ``<work>/chapters``)
  output_dir : Path | None
    草稿输出根目录(默认 ``<work>/chapters/raw/<course_title>``)
    注意:这里为简化,默认与 ``chapters/`` 同级的 ``raw/<stem>`` 是**章节目录旁**
    真实生产链在 ``inbox/<课程>/raw/<视频同名>/``,runner 应当传入 inbox 根
  max_output_chars : int
    单章节输出最大字符数(防 LLM 输出失控)

  Returns
  -------
  DraftsReport
    整体结果(已写盘:每章 chapter_NN.md + work/drafts/drafts.json)

  Raises
  ------
  FileNotFoundError
    缺 chapters.json 或 transcript.jsonl
  ValueError
    chapters 列表为空
  """
  _ = config
  c_dir = chapters_dir or (work / "chapters")
  if not (c_dir / "chapters.json").exists():
    raise FileNotFoundError(
      f"找不到 {c_dir / 'chapters.json'};请先跑 chapters stage"
    )
  chapters_report = _load_chapters_report(c_dir / "chapters.json")
  if not chapters_report.chapters:
    raise ValueError("chapters.json 章节列表为空,无法生成草稿")

  # 加载 transcript
  transcript_path = work / "asr" / "transcript.jsonl"
  if not transcript_path.exists():
    raise FileNotFoundError(
      f"找不到 {transcript_path};请先跑 asr stage"
    )
  segments = read_transcript_jsonl(transcript_path)

  course_title = _derive_course_title(chapters_report)
  if output_dir is None:
    output_dir = _resolve_output_dir(c_dir, course_title)
  output_dir.mkdir(parents=True, exist_ok=True)

  # 顺序处理每章节(LLM 同步阻塞)
  drafts: list[ChapterDraft] = []
  last_response = None
  for ch in chapters_report.chapters:
    chapter_transcript = _slice_transcript_for_chapter(
      segments,
      ch.start_seconds,
      ch.end_seconds,
    )
    corrections = _load_corrections_for_chapter(
      work,
      ch.start_seconds,
      ch.end_seconds,
    )
    key_points_str = (
      "\n".join(f"- {p}" for p in ch.key_points) if ch.key_points else "(无)"
    )
    user_prompt = _USER_PROMPT_TEMPLATE.format(
      title=ch.title,
      summary=ch.summary or "(无摘要)",
      key_points=key_points_str,
      transcript=chapter_transcript,
      corrections=corrections or "(无候选修正)",
    )
    response = provider.chat(_SYSTEM_PROMPT + "\n\n" + user_prompt)
    last_response = response
    body = _normalize_body(response.text, max_chars=max_output_chars)

    md_path = output_dir / _DRAFT_FILENAME.format(idx=ch.idx)
    md_path.write_text(_render_draft_markdown(ch, body), encoding="utf-8")

    drafts.append(
      ChapterDraft(
        idx=ch.idx,
        chapter_title=ch.title,
        output_path=md_path,
        body=body,
        char_count=len(body),
        illustration_count=_count_illustrations(body),
      )
    )

  # 写整体 manifest 到 ``work/drafts/drafts.json``
  manifest_path = work / "drafts" / "drafts.json"
  report = DraftsReport(
    video=chapters_report.video,
    course_title=course_title,
    provider=getattr(last_response, "provider", "") if last_response else "",
    model=getattr(last_response, "model", "") if last_response else "",
    output_dir=str(output_dir),
    drafts=drafts,
  )
  report.save(manifest_path)
  return report


def _render_draft_markdown(ch, body: str) -> str:
  """单章节草稿文件 = 标题 + 摘要块 + 三级标题正文 + 引用关键帧列表 + AI 配图标注。"""
  out: list[str] = []
  out.append(f"# {ch.title}")
  out.append("")
  if ch.summary:
    out.append(f"> **摘要**:{ch.summary}")
    out.append("")
  if ch.key_points:
    out.append("**关键要点**:")
    for p in ch.key_points:
      out.append(f"- {p}")
    out.append("")
  if ch.image_refs:
    out.append("**引用关键帧**:")
    for ts in ch.image_refs:
      out.append(f"- {ts:.2f}s → `frame_{int(ts * 1000):09d}.jpg`")
    out.append("")
  out.append("---")
  out.append("")
  out.append(body.rstrip())
  out.append("")
  return "\n".join(out)


__all__ = [
  "DEFAULT_MAX_OUTPUT_CHARS",
  "ChapterDraft",
  "DraftsReport",
  "generate_drafts",
]
