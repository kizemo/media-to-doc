"""Stage 6 — ``chapters``:LLM 章节切分(新 schema)。

输入:
- ``work/asr/transcript.jsonl``:ASR 段落(逐字稿)
- ``work/frames/keyframes.json``:关键帧时间戳
- ``work/asr/asr_corrections.json``(可选):OCR 候选修正

输出:
- ``work/chapters/chapters.json``:全文章节列表
- ``work/chapters/chapter_NN.md``:每个章节一份草稿

LLM 章节 schema(PRD §4.1 新版本):
  - ``title``:章节标题(15-25 字)
  - ``summary``:章节摘要(50-100 字)
  - ``start_seconds``:起始时间(秒)
  - ``end_seconds``:结束时间(秒)
  - ``key_points``:关键要点列表(3-5 条)
  - ``image_refs``:引用关键帧时间戳列表
  - ``illustrations``:AI 配图标注列表(``[[GEN: prompt]]`` 占位)

依赖:
- LLM provider(由 :func:`split_chapters` 调用方传入;lazy import 在 :mod:`llm`)

参考:TDD §5 数据流第 6 步 + PROJECT_DESCRIPTION §3.2 chapters 行 +
     TDD §4.1.3 chapter 接口。
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

DEFAULT_MIN_CHAPTER_SECONDS = 60.0
DEFAULT_MAX_CHAPTER_SECONDS = 600.0  # 10 分钟
DEFAULT_TOP_KEYFRAMES = 12

# 章节草稿文件名格式化(``chapter_01.md``)
_CHAPTER_FILENAME = "chapter_{idx:02d}.md"


# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


@dataclass
class Chapter:
  """单个章节。"""

  idx: int  # 1-based
  title: str
  summary: str
  start_seconds: float
  end_seconds: float
  key_points: list[str] = field(default_factory=list)
  image_refs: list[float] = field(default_factory=list)
  illustrations: list[str] = field(default_factory=list)

  @property
  def duration_seconds(self) -> float:
    return max(0.0, float(self.end_seconds) - float(self.start_seconds))

  def to_dict(self) -> dict[str, object]:
    return {
      "idx": self.idx,
      "title": self.title,
      "summary": self.summary,
      "start_seconds": float(self.start_seconds),
      "end_seconds": float(self.end_seconds),
      "duration_seconds": self.duration_seconds,
      "key_points": list(self.key_points),
      "image_refs": [float(t) for t in self.image_refs],
      "illustrations": list(self.illustrations),
    }


@dataclass
class ChaptersReport:
  """整体章节切分结果(对应 ``chapters.json``)。"""

  video: str = ""
  provider: str = ""
  model: str = ""
  chapters: list[Chapter] = field(default_factory=list)

  def to_dict(self) -> dict[str, object]:
    return {
      "video": self.video,
      "provider": self.provider,
      "model": self.model,
      "count": len(self.chapters),
      "chapters": [c.to_dict() for c in self.chapters],
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


def _load_transcript(work: Path) -> str:
  """把 transcript.jsonl 拼成 ``[start-ends] text`` 列表(限制总长)。"""
  from .asr import read_transcript_jsonl

  transcript_path = work / "asr" / "transcript.jsonl"
  if not transcript_path.exists():
    raise FileNotFoundError(
      f"找不到 {transcript_path};请先跑 transcribe() stage"
    )
  segments = read_transcript_jsonl(transcript_path)
  lines: list[str] = []
  for seg in segments:
    lines.append(
      f"[{seg.start:7.2f}s - {seg.end:7.2f}s] {seg.text}"
    )
  return "\n".join(lines)


def _load_keyframe_timestamps(work: Path, top: int) -> list[float]:
  """从 ``keyframes.json`` 取关键帧时间戳(秒,降序限制 top)。"""
  manifest = work / "frames" / "keyframes.json"
  if not manifest.exists():
    return []
  data = json.loads(manifest.read_text(encoding="utf-8"))
  frames = data.get("frames", [])
  timestamps = sorted(
    (float(f["timestamp_ms"]) / 1000.0 for f in frames if "timestamp_ms" in f),
  )
  # 限制数量(避免 prompt 过长)
  if len(timestamps) > top:
    # 等距采样 top 个
    step = max(1, len(timestamps) // top)
    timestamps = timestamps[::step][:top]
  return timestamps


def _load_corrections(work: Path) -> str:
  """从 ``asr_corrections.json`` 提取 top 候选修正(去重 + 限数)。"""
  path = work / "asr" / "asr_corrections.json"
  if not path.exists():
    return ""
  data = json.loads(path.read_text(encoding="utf-8"))
  seen: set[str] = set()
  out: list[str] = []
  for corr in data.get("corrections", []):
    for cand in corr.get("candidates", []):
      text = cand.get("text", "")
      if text and text not in seen:
        seen.add(text)
        out.append(text)
        if len(out) >= 50:
          return "\n".join(f"- {t}" for t in out)
  return "\n".join(f"- {t}" for t in out)


# ─────────────────────────────────────────────────────────────
# Prompt 模板
# ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
  "你是一名专业的课程编辑,擅长把培训视频的逐字稿整理为结构化讲义。"
  "请严格按用户给定的 JSON schema 输出,不要包含任何额外文字或 markdown 标记。"
)

_USER_PROMPT_TEMPLATE = """\
## 任务

把下面的培训视频逐字稿切成 N 个章节(每章 90 秒 ~ 8 分钟),
为每个章节输出符合 schema 的 JSON 对象。

## 章节 schema

每个章节对象包含以下字段(均为必填):
- `title`:章节标题(15-25 字,简洁有力)
- `summary`:章节摘要(50-100 字,描述本章核心内容)
- `start_seconds`:起始时间(秒,数字,与逐字稿中的时间戳一致)
- `end_seconds`:结束时间(秒,数字,大于 start_seconds)
- `key_points`:关键要点列表(3-5 条字符串)
- `image_refs`:引用关键帧时间戳列表(数字,秒,只引用下面的关键帧时间点)
- `illustrations`:AI 配图标注列表(0-3 条字符串,每条形如"绘制一张图展示...")

## 输出格式

严格的 JSON 数组,无 markdown 代码块标记。例如:
[
  {{"title":"示例章节","summary":"本章介绍...","start_seconds":0.0,"end_seconds":120.5,
   "key_points":["要点 1","要点 2"],"image_refs":[10.5,60.2],
   "illustrations":["绘制一张图展示产品架构"]}}
]

## 逐字稿(带时间戳)

{transcript}

## 关键帧时间点(秒,可引用)

{keyframes}

## OCR 候选修正(可能的人名 / 专有名词)

{corrections}
"""


# ─────────────────────────────────────────────────────────────
# JSON 容错解析
# ─────────────────────────────────────────────────────────────


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _parse_chapters_json(raw: str) -> list[dict[str, Any]]:
  """从 LLM 输出中解析章节 JSON 数组(容错处理 ```json ... ``` 围栏)。"""
  text = raw.strip()

  # 1. 直接尝试
  try:
    data = json.loads(text)
    if isinstance(data, list):
      return [dict(item) for item in data]
  except json.JSONDecodeError:
    pass

  # 2. 尝试从 ```json ... ``` 中提取
  match = _JSON_FENCE_RE.search(text)
  if match:
    try:
      data = json.loads(match.group(1).strip())
      if isinstance(data, list):
        return [dict(item) for item in data]
    except json.JSONDecodeError:
      pass

  # 3. 尝试找第一个 [ ... ] 块
  start = text.find("[")
  end = text.rfind("]")
  if start != -1 and end != -1 and end > start:
    try:
      data = json.loads(text[start : end + 1])
      if isinstance(data, list):
        return [dict(item) for item in data]
    except json.JSONDecodeError:
      pass

  raise ValueError(
    f"无法从 LLM 输出解析 JSON 数组(长度 {len(raw)}):{raw[:200]}..."
  )


# ─────────────────────────────────────────────────────────────
# LLM 输出 → Chapter
# ─────────────────────────────────────────────────────────────


def _coerce_chapter(idx: int, raw: dict[str, Any]) -> Chapter:
  """把 LLM 输出的 dict 规范化为 Chapter(缺字段给空,类型错误给默认值)。"""
  title = str(raw.get("title", "")).strip() or f"章节 {idx}"
  summary = str(raw.get("summary", "")).strip()

  def _f(value: object, default: float = 0.0) -> float:
    try:
      return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
      return default

  start = _f(raw.get("start_seconds"), 0.0)
  end = _f(raw.get("end_seconds"), start + 60.0)
  if end <= start:
    end = start + max(DEFAULT_MIN_CHAPTER_SECONDS, 60.0)

  key_points_raw = raw.get("key_points") or []
  if not isinstance(key_points_raw, list):
    key_points_raw = []
  key_points = [str(x).strip() for x in key_points_raw if str(x).strip()]

  image_refs_raw = raw.get("image_refs") or []
  if not isinstance(image_refs_raw, list):
    image_refs_raw = []
  image_refs = []
  for t in image_refs_raw:
    try:
      image_refs.append(float(t))
    except (TypeError, ValueError):
      continue

  illustrations_raw = raw.get("illustrations") or []
  if not isinstance(illustrations_raw, list):
    illustrations_raw = []
  illustrations = [str(x).strip() for x in illustrations_raw if str(x).strip()]

  return Chapter(
    idx=idx,
    title=title,
    summary=summary,
    start_seconds=start,
    end_seconds=end,
    key_points=key_points,
    image_refs=image_refs,
    illustrations=illustrations,
  )


# ─────────────────────────────────────────────────────────────
# 章节草稿 markdown 渲染
# ─────────────────────────────────────────────────────────────


def _render_chapter_markdown(chapter: Chapter) -> str:
  """生成单章节 markdown(供 :mod:`render` 阶段拼接)。"""
  lines: list[str] = []
  lines.append(f"## {chapter.title}")
  lines.append("")
  if chapter.summary:
    lines.append(f"**摘要**:{chapter.summary}")
    lines.append("")
  if chapter.key_points:
    lines.append("**关键要点**:")
    for point in chapter.key_points:
      lines.append(f"- {point}")
    lines.append("")
  if chapter.image_refs:
    lines.append("**引用关键帧**:")
    for ts in chapter.image_refs:
      lines.append(f"- {ts:.2f}s → `frame_{int(ts * 1000):09d}.jpg`")
    lines.append("")
  if chapter.illustrations:
    lines.append("**AI 配图标注**:")
    for prompt in chapter.illustrations:
      lines.append(f"- [[GEN: {prompt}]]")
    lines.append("")
  return "\n".join(lines).rstrip() + "\n"


# ─────────────────────────────────────────────────────────────
# 公开 API
# ─────────────────────────────────────────────────────────────


def split_chapters(
  work: Path,
  provider: BaseLLMProvider,
  config: WorkflowConfig | None = None,
  *,
  output_dir: Path | None = None,
) -> ChaptersReport:
  """Stage 6:用 LLM 把全文切分为章节。

  Parameters
  ----------
  work : Path
    work 根目录
  provider : BaseLLMProvider
    已初始化的 LLM provider 实例(由调用方从 :mod:`llm` 工厂创建)
  config : WorkflowConfig | None
    配置(预留,当前未用)
  output_dir : Path | None
    章节输出目录,默认 ``<work>/chapters/``

  Returns
  -------
  ChaptersReport
    整体结果(已写盘:``chapters.json`` + ``chapter_NN.md``)
  """
  _ = config  # 保留参数;W3+ 接 chapters.* 字段

  out_dir = output_dir or (work / "chapters")
  out_dir.mkdir(parents=True, exist_ok=True)

  # 1. 准备 prompt 输入
  transcript = _load_transcript(work)
  keyframes = _load_keyframe_timestamps(work, DEFAULT_TOP_KEYFRAMES)
  corrections = _load_corrections(work)

  user_prompt = _USER_PROMPT_TEMPLATE.format(
    transcript=transcript,
    keyframes=", ".join(f"{t:.2f}" for t in keyframes) or "(无关键帧)",
    corrections=corrections or "(无候选修正)",
  )

  # 2. LLM 调用
  response = provider.chat(_SYSTEM_PROMPT + "\n\n" + user_prompt)
  raw_chapters = _parse_chapters_json(response.text)

  # 3. 规范化 + 写文件
  chapters: list[Chapter] = []
  for i, raw in enumerate(raw_chapters, start=1):
    chapter = _coerce_chapter(i, raw)
    chapters.append(chapter)
    md_path = out_dir / _CHAPTER_FILENAME.format(idx=i)
    md_path.write_text(_render_chapter_markdown(chapter), encoding="utf-8")

  # 4. 整体 manifest
  report = ChaptersReport(
    video=work.name or "",
    provider=response.provider,
    model=response.model,
    chapters=chapters,
  )
  report.save(out_dir / "chapters.json")
  return report


__all__ = [
  "Chapter",
  "ChaptersReport",
  "DEFAULT_MIN_CHAPTER_SECONDS",
  "DEFAULT_MAX_CHAPTER_SECONDS",
  "split_chapters",
]
