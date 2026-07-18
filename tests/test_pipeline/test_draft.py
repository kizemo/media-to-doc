"""draft stage 测试。

要点:
- mock LLM provider,验证 prompt 构造 / 文件写入 / 切片逻辑
- 覆盖工具函数:illustration 计数 / transcript 切片 / corrections 过滤 / 围栏剥离
- 全流程:generate_drafts() 端到端 mock 输出
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from media_to_doc.pipeline import draft as dr_mod
from media_to_doc.pipeline.asr import TranscriptSegment, write_transcript_jsonl
from media_to_doc.pipeline.chapters import Chapter, ChaptersReport
from media_to_doc.pipeline.draft import (
  DEFAULT_MAX_OUTPUT_CHARS,
  ChapterDraft,
  DraftsReport,
  generate_drafts,
)

# ─────────────────────────────────────────────────────────────
# 假 LLM provider
# ─────────────────────────────────────────────────────────────


class _FakeChatResponse:
  def __init__(self, text: str, provider: str = "fake", model: str = "fake-model") -> None:
    self.text = text
    self.provider = provider
    self.model = model
    self.duration_seconds = 0.1


class _FakeProvider:
  """最小 LLM provider mock(满足 duck-typing)。"""

  def __init__(self, replies: list[str] | str) -> None:
    self._replies = [replies] if isinstance(replies, str) else list(replies)
    self._call_count = 0
    self.last_prompt = ""
    self._calls: list[str] = []

  @property
  def name(self) -> str:
    return "fake"

  def list_models(self) -> list[str]:
    return ["fake-model"]

  def chat(self, prompt: str, **_kwargs: object) -> _FakeChatResponse:
    self._call_count += 1
    self.last_prompt = prompt
    self._calls.append(prompt)
    if not self._replies:
      raise RuntimeError("no more fake replies")
    text = self._replies.pop(0)
    return _FakeChatResponse(text=text)


def _seed_chapters(work: Path, chapters: list[Chapter]) -> None:
  cdir = work / "chapters"
  cdir.mkdir(parents=True, exist_ok=True)
  report = ChaptersReport(video="course-x", provider="fake", model="fm", chapters=chapters)
  report.save(cdir / "chapters.json")


def _seed_transcript(work: Path, segments: list[TranscriptSegment]) -> None:
  adir = work / "asr"
  adir.mkdir(parents=True, exist_ok=True)
  write_transcript_jsonl(iter(segments), adir / "transcript.jsonl")


def _seed_corrections(work: Path, corrections: list[dict]) -> None:
  path = work / "asr" / "asr_corrections.json"
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(
    json.dumps({"video": "course-x", "corrections": corrections}, ensure_ascii=False, indent=2),
    encoding="utf-8",
  )


def _make_chapter(idx: int, start: float, end: float, title: str = "T") -> Chapter:
  return Chapter(
    idx=idx,
    title=f"{title} {idx}",
    summary=f"摘要 {idx}",
    start_seconds=start,
    end_seconds=end,
    key_points=[f"要点 {idx}.1", f"要点 {idx}.2"],
    image_refs=[start + 1.0],
    illustrations=[f"配图 {idx}"],
  )


# ─────────────────────────────────────────────────────────────
# 工具函数:illustration 计数
# ─────────────────────────────────────────────────────────────


def test_count_illustrations_basic() -> None:
  text = "前置[[GEN: 流程图]]中段[[GEN: 表格]]结尾"
  assert dr_mod._count_illustrations(text) == 2


def test_count_illustrations_zero() -> None:
  assert dr_mod._count_illustrations("纯文本无标记") == 0


def test_count_illustrations_handles_complex_bracket() -> None:
  # 不平衡的 ] 与 ] 不参与新标签
  text = "[[GEN: 嵌套 [嵌套] 描述]]内容[[GEN: 第二个]]"
  assert dr_mod._count_illustrations(text) >= 1


# ─────────────────────────────────────────────────────────────
# 工具函数:transcript 切片
# ─────────────────────────────────────────────────────────────


def test_slice_transcript_for_chapter_basic() -> None:
  segs = [
    TranscriptSegment(start=0.0, end=2.0, text="A"),
    TranscriptSegment(start=10.0, end=12.0, text="B"),
    TranscriptSegment(start=20.0, end=22.0, text="C"),
  ]
  out = dr_mod._slice_transcript_for_chapter(iter(segs), 5.0, 15.0)
  assert "B" in out
  assert "A" not in out and "C" not in out


def test_slice_transcript_for_chapter_inclusive_endpoints() -> None:
  segs = [
    TranscriptSegment(start=5.0, end=10.0, text="边界左"),
    TranscriptSegment(start=15.0, end=20.0, text="边界右"),
  ]
  out = dr_mod._slice_transcript_for_chapter(iter(segs), 5.0, 20.0)
  assert "边界左" in out
  assert "边界右" in out


def test_slice_transcript_for_chapter_empty() -> None:
  out = dr_mod._slice_transcript_for_chapter(iter([]), 0.0, 100.0)
  assert out == "(该章节无对应逐字稿)"


def test_slice_transcript_for_chapter_cap_truncates() -> None:
  segs = [
    TranscriptSegment(start=float(i), end=float(i + 1), text="X" * 50)
    for i in range(50)
  ]
  out = dr_mod._slice_transcript_for_chapter(segs, 0.0, 50.0, char_cap=300)
  # 300 字符上限 + 截断注释
  assert len(out) < 500
  assert "省略" in out


# ─────────────────────────────────────────────────────────────
# 工具函数:corrections 过滤
# ─────────────────────────────────────────────────────────────


def test_load_corrections_for_chapter_filters_out_of_range(tmp_path: Path) -> None:
  work = tmp_path
  _seed_corrections(
    work,
    [
      {
        "segment_idx": 0,
        "segment_start": 0.0,
        "segment_end": 5.0,
        "segment_text": "原文本",
        "ocr_window_text": "达摩盘",
        "candidates": [{"text": "达摩盘", "frequency": 1, "score": 1.0}],
      },
      {
        "segment_idx": 1,
        "segment_start": 100.0,
        "segment_end": 105.0,
        "segment_text": "另一段",
        "ocr_window_text": "完全无关",
        "candidates": [{"text": "完全无关", "frequency": 1, "score": 1.0}],
      },
    ],
  )
  out = dr_mod._load_corrections_for_chapter(work, 0.0, 10.0)
  assert "达摩盘" in out
  assert "完全无关" not in out


def test_load_corrections_for_chapter_no_file(tmp_path: Path) -> None:
  assert dr_mod._load_corrections_for_chapter(tmp_path, 0.0, 10.0) == ""


def test_load_corrections_for_chapter_dedup(tmp_path: Path) -> None:
  work = tmp_path
  _seed_corrections(
    work,
    [
      {
        "segment_idx": 0,
        "segment_start": 0.0,
        "segment_end": 5.0,
        "segment_text": "",
        "ocr_window_text": "",
        "candidates": [
          {"text": "同一", "frequency": 1, "score": 1.0},
          {"text": "同一", "frequency": 1, "score": 1.0},
          {"text": "不同", "frequency": 1, "score": 1.0},
        ],
      }
    ],
  )
  out = dr_mod._load_corrections_for_chapter(work, 0.0, 5.0)
  assert out.count("同一") == 1
  assert out.count("不同") == 1


# ─────────────────────────────────────────────────────────────
# 工具函数:正文规范化
# ─────────────────────────────────────────────────────────────


def test_strip_wrapping_with_fence() -> None:
  raw = "前缀\n```markdown\n正文\n```\n后缀"
  out = dr_mod._strip_wrapping(raw)
  assert out == "正文"


def test_strip_wrapping_without_fence() -> None:
  assert dr_mod._strip_wrapping("纯文本") == "纯文本"


def test_normalize_body_strips_horizontal_rule() -> None:
  body = "段落 A\n\n---\n\n段落 B"
  out = dr_mod._normalize_body(body)
  assert "---" not in out
  assert "段落 A" in out and "段落 B" in out


def test_normalize_body_truncates_and_adds_note() -> None:
  body = "A" * (DEFAULT_MAX_OUTPUT_CHARS + 5000)
  out = dr_mod._normalize_body(body, max_chars=200)
  assert len(out) < 500
  assert "后续省略" in out


# ─────────────────────────────────────────────────────────────
# 工具函数:输出路径派生
# ─────────────────────────────────────────────────────────────


def test_resolve_output_dir_with_title() -> None:
  out = dr_mod._resolve_output_dir(Path("/chapters"), "我的课")
  # Windows 风格:Path 反斜杠
  assert str(out).endswith("raw\\我的课") or str(out).endswith("raw/我的课")


def test_resolve_output_dir_empty_title_falls_back() -> None:
  out = dr_mod._resolve_output_dir(Path("/chapters"), "")
  assert str(out).endswith("raw\\output") or str(out).endswith("raw/output")


# ─────────────────────────────────────────────────────────────
# 工具函数:文件渲染
# ─────────────────────────────────────────────────────────────


def test_render_draft_markdown_includes_title_and_body() -> None:
  ch = _make_chapter(1, 0.0, 10.0)
  body = "### 关键段一\n要点展开\n\n[[GEN: 流程图]]"
  out = dr_mod._render_draft_markdown(ch, body)
  assert out.startswith(f"# {ch.title}")
  assert "摘要" in out
  assert "关键要点" in out
  assert "引用关键帧" in out
  assert "### 关键段一" in out
  assert "[[GEN: 流程图]]" in out


# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


def test_chapter_draft_to_dict_includes_illustration_count(tmp_path: Path) -> None:
  d = ChapterDraft(
    idx=3,
    chapter_title="T3",
    output_path=tmp_path / "x.md",
    body="[[GEN: A]]和[[GEN: B]]",
    char_count=20,
    illustration_count=2,
  )
  payload = d.to_dict()
  assert payload["idx"] == 3
  assert payload["illustration_count"] == 2


def test_drafts_report_total_chars(tmp_path: Path) -> None:
  r = DraftsReport(
    video="x",
    course_title="course",
    provider="fake",
    model="fm",
    output_dir=str(tmp_path),
    drafts=[
      ChapterDraft(idx=1, chapter_title="A", output_path=tmp_path / "a", body="12345", char_count=5),
      ChapterDraft(idx=2, chapter_title="B", output_path=tmp_path / "b", body="123456789", char_count=9),
    ],
  )
  assert r.total_chars == 14


def test_drafts_report_save_round_trip(tmp_path: Path) -> None:
  r = DraftsReport(
    video="x",
    course_title="course",
    provider="fake",
    model="fm",
    output_dir="out",
    drafts=[
      ChapterDraft(idx=1, chapter_title="A", output_path=tmp_path / "a", body="x", char_count=1)
    ],
  )
  path = tmp_path / "drafts.json"
  r.save(path)
  data = json.loads(path.read_text(encoding="utf-8"))
  assert data["count"] == 1
  assert data["total_chars"] == 1


# ─────────────────────────────────────────────────────────────
# generate_drafts 端到端
# ─────────────────────────────────────────────────────────────


def test_generate_drafts_writes_files_and_manifest(tmp_path: Path) -> None:
  work = tmp_path
  _seed_chapters(
    work,
    [
      _make_chapter(1, 0.0, 10.0),
      _make_chapter(2, 10.0, 25.0),
    ],
  )
  _seed_transcript(
    work,
    [
      TranscriptSegment(start=0.0, end=5.0, text="第一段文字"),
      TranscriptSegment(start=10.0, end=15.0, text="第二段文字"),
      TranscriptSegment(start=20.0, end=25.0, text="第三段文字"),
    ],
  )
  _seed_corrections(
    work,
    [
      {
        "segment_idx": 0,
        "segment_start": 0.0,
        "segment_end": 5.0,
        "segment_text": "",
        "ocr_window_text": "",
        "candidates": [{"text": "达摩盘", "frequency": 1, "score": 1.0}],
      }
    ],
  )

  provider = _FakeProvider(
    replies=[
      "### 1.1 第一段\n要点展开 [[GEN: 流程图]]",
      "### 2.1 第二段\n要点展开",
    ]
  )

  generate_drafts(work, provider)

  # chapter_NN.md 写到默认 raw/course-x/chapter_01.md 等
  raw_dir = work / "chapters" / "raw" / "course-x"
  assert (raw_dir / "chapter_01.md").exists()
  assert (raw_dir / "chapter_02.md").exists()

  # 工作目录 manifest
  assert (work / "drafts" / "drafts.json").exists()

  # provider 字段正确
  data = json.loads((work / "drafts" / "drafts.json").read_text(encoding="utf-8"))
  assert data["count"] == 2
  assert data["provider"] == "fake"
  assert data["drafts"][0]["illustration_count"] >= 1

  # 第二章 LLM 收到的 prompt 含切片(应含"第二段文字")
  second_prompt = provider._calls[1]
  assert "第二段文字" in second_prompt or "第二段" in second_prompt


def test_generate_drafts_raises_when_no_chapters_json(tmp_path: Path) -> None:
  provider = _FakeProvider(replies=[""])
  with pytest.raises(FileNotFoundError, match="chapters.json"):
    generate_drafts(tmp_path, provider)


def test_generate_drafts_raises_when_empty_chapters(tmp_path: Path) -> None:
  work = tmp_path
  _seed_chapters(work, [])
  _seed_transcript(work, [])
  with pytest.raises(ValueError, match="章节列表为空"):
    generate_drafts(work, _FakeProvider(replies=[""]))


def test_generate_drafts_raises_when_no_transcript(tmp_path: Path) -> None:
  work = tmp_path
  _seed_chapters(work, [_make_chapter(1, 0.0, 10.0)])
  # 不写 transcript
  with pytest.raises(FileNotFoundError, match="transcript.jsonl"):
    generate_drafts(work, _FakeProvider(replies=[""]))


def test_generate_drafts_uses_custom_output_dir(tmp_path: Path) -> None:
  work = tmp_path
  _seed_chapters(work, [_make_chapter(1, 0.0, 5.0)])
  _seed_transcript(work, [TranscriptSegment(start=0.0, end=5.0, text="A")])

  custom_out = tmp_path / "my-output"
  provider = _FakeProvider(replies=["纯正文"])
  generate_drafts(work, provider, output_dir=custom_out)
  assert (custom_out / "chapter_01.md").exists()


def test_generate_drafts_uses_custom_chapters_dir(tmp_path: Path) -> None:
  work = tmp_path
  other_chapters = tmp_path / "other-chapters"
  other_chapters.mkdir()
  report = ChaptersReport(
    video="course-x",
    provider="fake",
    model="fm",
    chapters=[_make_chapter(1, 0.0, 5.0)],
  )
  report.save(other_chapters / "chapters.json")
  _seed_transcript(work, [TranscriptSegment(start=0.0, end=5.0, text="A")])

  provider = _FakeProvider(replies=["纯正文"])
  generate_drafts(work, provider, chapters_dir=other_chapters)
  # 默认 output_dir = chapters_dir / raw / course-x
  assert (other_chapters / "raw" / "course-x" / "chapter_01.md").exists()
