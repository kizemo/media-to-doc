"""longdoc W12-D 兼容测试 — 3 级 fallback 找源 markdown。

W12-D 把 render 阶段最终讲义 ``<video>.md`` 从 ``<work>/chapters/raw/`` 迁到
``<work>.parent / "output_final"``。本测试套件覆盖 W12-D 兼容逻辑的三个分支:

1. **W12-D 真相位置**:``<final_dir>/<video>.md``(render 已拼装好的讲义)
2. **W3-W11 旧布局**:``<work>/chapters/raw/<video>.md``
3. **W12-D 中间产物应急**:``<work>/chapters/raw/<video>/chapter_*.md`` 拼装

要点:
- 优先 1,回退 2,再回退 3
- 全部失败抛 FileNotFoundError,错误信息列出 3 个尝试路径
- 旧测试 fixture(_seed_rendered_md 写 chapters/raw/<stem>.md)仍能工作
"""

from __future__ import annotations

from pathlib import Path

import pytest

from media_to_doc.pipeline.chapters import Chapter, ChaptersReport
from media_to_doc.pipeline.longdoc import (
  _resolve_source_md,
  process_long_doc,
)

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


def _seed_chapters(work: Path, video: str = "course-x") -> None:
  """写 ``<work>/chapters/chapters.json``(模拟 chapters 阶段产物)。"""
  chapters_dir = work / "chapters"
  chapters_dir.mkdir(parents=True, exist_ok=True)
  r = ChaptersReport(
    video=video,
    provider="fake",
    model="fm",
    chapters=[Chapter(idx=1, title="第一章", summary="简介",
                      start_seconds=0.0, end_seconds=60.0)],
  )
  r.save(chapters_dir / "chapters.json")


def _seed_final_md(
  final_dir: Path, stem: str, body: str
) -> Path:
  """模拟 render 阶段 W12-D 产物布局:``<final_dir>/<stem>.md``。"""
  final_dir.mkdir(parents=True, exist_ok=True)
  md_path = final_dir / f"{stem}.md"
  md_path.write_text(body, encoding="utf-8")
  return md_path


def _seed_legacy_md(work: Path, stem: str, body: str) -> Path:
  """模拟 W3-W11 旧布局:``<work>/chapters/raw/<stem>.md``。"""
  raw_dir = work / "chapters" / "raw"
  raw_dir.mkdir(parents=True, exist_ok=True)
  md_path = raw_dir / f"{stem}.md"
  md_path.write_text(body, encoding="utf-8")
  return md_path


def _seed_chapter_files(
  work: Path, stem: str, chapters: list[str]
) -> Path:
  """模拟 draft 阶段产物:``<work>/chapters/raw/<stem>/chapter_NN.md``。"""
  video_dir = work / "chapters" / "raw" / stem
  video_dir.mkdir(parents=True, exist_ok=True)
  for i, body in enumerate(chapters, start=1):
    (video_dir / f"chapter_{i:02d}.md").write_text(body, encoding="utf-8")
  return video_dir


def _default_final_dir(work: Path) -> Path:
  """W12-D 默认 final_dir:``<work>.parent / "output_final"``。"""
  return work.parent / "output_final"


# ─────────────────────────────────────────────────────────────
# 1. W12-D 真相位置优先
# ─────────────────────────────────────────────────────────────


def test_resolve_source_md_prefers_w12d_final_dir(tmp_path: Path) -> None:
  """final_dir/<video>.md 存在 → 优先返回它,不读 legacy / chapter 拼装。"""
  work = tmp_path / "work"
  work.mkdir()
  final_dir = _default_final_dir(work)
  _seed_final_md(
    final_dir, "lesson-01", "# W12-D 真讲义\n\n正文\n"
  )
  # 即便 legacy 也存在,也不该用它
  _seed_legacy_md(work, "lesson-01", "# legacy\n\n不应被读\n")
  # 即便 chapter files 也存在,也不该拼装
  _seed_chapter_files(work, "lesson-01", ["# 不应拼装\n"])

  resolved = _resolve_source_md(
    work=work, video="lesson-01", final_dir=final_dir
  )
  assert resolved == final_dir / "lesson-01.md"
  assert resolved.read_text(encoding="utf-8").startswith("# W12-D 真讲义")


def test_resolve_source_md_w12d_layout_does_not_assemble_chapters(
  tmp_path: Path,
) -> None:
  """W12-D 真相位置优先 → chapter files 不被读到,raw/<video>.md 不生成。"""
  work = tmp_path / "work"
  work.mkdir()
  final_dir = _default_final_dir(work)
  _seed_final_md(final_dir, "l1", "# 真讲义\n\n")
  _seed_chapter_files(work, "l1", ["# chapter 1\n"])

  _resolve_source_md(work=work, video="l1", final_dir=final_dir)

  # chapters/raw/l1.md 不应被生成(没拼装)
  legacy = work / "chapters" / "raw" / "l1.md"
  assert not legacy.exists()


# ─────────────────────────────────────────────────────────────
# 2. W3-W11 旧布局回退
# ─────────────────────────────────────────────────────────────


def test_resolve_source_md_falls_back_to_legacy_layout(tmp_path: Path) -> None:
  """final_dir 不存在 + legacy 存在 → 用 legacy。"""
  work = tmp_path / "work"
  work.mkdir()
  final_dir = _default_final_dir(work)
  # final_dir 不创建任何东西(没有 <video>.md)
  legacy = _seed_legacy_md(work, "old-course", "# legacy 真讲义\n\n")

  resolved = _resolve_source_md(
    work=work, video="old-course", final_dir=final_dir
  )
  assert resolved == legacy


def test_resolve_source_md_legacy_only_no_w12d_dir(tmp_path: Path) -> None:
  """final_dir 完全不存在 → fallback 到 legacy。"""
  work = tmp_path / "work"
  work.mkdir()
  # final_dir 路径不创建
  legacy = _seed_legacy_md(work, "legacy-1", "# legacy\n")

  resolved = _resolve_source_md(
    work=work, video="legacy-1", final_dir=_default_final_dir(work)
  )
  assert resolved == legacy


# ─────────────────────────────────────────────────────────────
# 3. W12-D 中间产物应急拼装
# ─────────────────────────────────────────────────────────────


def test_resolve_source_md_assembles_chapter_files(tmp_path: Path) -> None:
  """final_dir 没有 + legacy 没有 + chapter_NN.md 存在 → 拼装到 legacy 路径。"""
  work = tmp_path / "work"
  work.mkdir()
  final_dir = _default_final_dir(work)
  _seed_chapter_files(
    work, "chap",
    ["# 第一章\n\nc1 body\n", "# 第二章\n\nc2 body\n"],
  )

  resolved = _resolve_source_md(
    work=work, video="chap", final_dir=final_dir
  )

  # 应写到 chapters/raw/<video>.md(legacy 路径),下次直接命中 layer 2
  expected = work / "chapters" / "raw" / "chap.md"
  assert resolved == expected
  assert expected.exists()
  text = expected.read_text(encoding="utf-8")
  assert "# 第一章" in text
  assert "# 第二章" in text
  # 章节分隔符
  assert "---" in text


def test_resolve_source_md_assembles_chapter_files_sorted(tmp_path: Path) -> None:
  """chapter_NN.md 按文件名排序拼装(01 在前,10 在最后,而不是字母序)。"""
  work = tmp_path / "work"
  work.mkdir()
  video_dir = _seed_chapter_files(
    work, "sortme",
    [
      "# 第 10 章\n\n10 body\n",  # 故意写乱顺序
      "# 第 2 章\n\n2 body\n",
      "# 第 1 章\n\n1 body\n",
    ],
  )
  # 实际写到磁盘时用 chapter_NN.md 命名 → 我们重命名为模拟字母序
  # (glob 排序基于文件名,需要确保顺序是 01 → 02 → 10)
  files = sorted(video_dir.glob("chapter_*.md"))
  # 重写:第 1 章 → chapter_01, 第 2 章 → chapter_02, 第 10 章 → chapter_10
  (video_dir / "chapter_01.md").write_text("# 第 1 章\n\n1 body\n", encoding="utf-8")
  (video_dir / "chapter_02.md").write_text("# 第 2 章\n\n2 body\n", encoding="utf-8")
  (video_dir / "chapter_10.md").write_text("# 第 10 章\n\n10 body\n", encoding="utf-8")
  # 删原始 chapter_NN.md(如果有)
  for f in files:
    if f.name not in {"chapter_01.md", "chapter_02.md", "chapter_10.md"}:
      f.unlink()

  resolved = _resolve_source_md(
    work=work, video="sortme", final_dir=_default_final_dir(work)
  )
  text = resolved.read_text(encoding="utf-8")
  # 1 章应在 2 章前,2 章在 10 章前(glob 默认字母序 = 数值序)
  pos_1 = text.find("# 第 1 章")
  pos_2 = text.find("# 第 2 章")
  pos_10 = text.find("# 第 10 章")
  assert 0 <= pos_1 < pos_2 < pos_10


# ─────────────────────────────────────────────────────────────
# 4. 全部失败抛 FileNotFoundError
# ─────────────────────────────────────────────────────────────


def test_resolve_source_md_all_missing_raises(tmp_path: Path) -> None:
  """3 层全失败 → 抛 FileNotFoundError,错误信息列 3 路径。"""
  work = tmp_path / "work"
  work.mkdir()
  final_dir = _default_final_dir(work)
  # 全部不创建

  with pytest.raises(FileNotFoundError) as exc_info:
    _resolve_source_md(work=work, video="missing", final_dir=final_dir)

  msg = str(exc_info.value)
  assert "W12-D 兼容 3 级 fallback 全失败" in msg
  # 错误信息应列出 3 个尝试路径,便于排查
  assert "final_dir" in msg
  assert "legacy" in msg
  assert "dir-glob" in msg
  # 应提示先跑 render
  assert "render stage" in msg


def test_resolve_source_md_empty_chapter_dir_raises(tmp_path: Path) -> None:
  """chapters/raw/<video>/ 存在但里面没 chapter_*.md → 当作全失败。"""
  work = tmp_path / "work"
  work.mkdir()
  # 只建空目录
  (work / "chapters" / "raw" / "empty" / "images").mkdir(parents=True)

  with pytest.raises(FileNotFoundError):
    _resolve_source_md(
      work=work, video="empty", final_dir=_default_final_dir(work)
    )


# ─────────────────────────────────────────────────────────────
# 5. 端到端 process_long_doc 集成
# ─────────────────────────────────────────────────────────────


def test_process_long_doc_reads_w12d_final_md(tmp_path: Path) -> None:
  """端到端:process_long_doc 默认从 final_dir/<video>.md 读(W12-D)。"""
  work = tmp_path / "work"
  work.mkdir()
  _seed_chapters(work, video="w12d-1")
  final_dir = _default_final_dir(work)
  body = (
    "# W12D 真讲义\n\n"
    "正文段一\n\n"
    "[0.50s - 1.20s] 时间戳应被剥离\n\n"
    "正文段二\n"
  )
  _seed_final_md(final_dir, "w12d-1", body)
  # 同时存在 legacy 文件,验证优先读 final_dir
  _seed_legacy_md(work, "w12d-1", "# 应被忽略\n")

  result = process_long_doc(work, None)  # skip LLM

  assert result.source_md == final_dir / "w12d-1.md"
  cleaned = result.cleaned_md.read_text(encoding="utf-8")
  assert "时间戳应被剥离" not in cleaned
  assert "W12D 真讲义" in cleaned  # 真讲义标题
  assert "应被忽略" not in cleaned  # 没读 legacy


def test_process_long_doc_falls_back_to_legacy(tmp_path: Path) -> None:
  """端到端:final_dir 无 → fallback 到 legacy 旧布局。"""
  work = tmp_path / "work"
  work.mkdir()
  _seed_chapters(work, video="legacy-2")
  _seed_legacy_md(work, "legacy-2", "# Legacy 讲义\n\nlegacy 正文\n")

  result = process_long_doc(work, None)

  assert result.source_md == work / "chapters" / "raw" / "legacy-2.md"
  assert "Legacy 讲义" in result.cleaned_md.read_text(encoding="utf-8")


def test_process_long_doc_assembles_chapters(tmp_path: Path) -> None:
  """端到端:final_dir 无 + legacy 无 → 拼装 chapter_NN.md。"""
  work = tmp_path / "work"
  work.mkdir()
  _seed_chapters(work, video="chap-3")
  _seed_chapter_files(
    work, "chap-3",
    ["# Chapter A\n\nA body\n", "# Chapter B\n\nB body\n"],
  )

  result = process_long_doc(work, None)

  cleaned = result.cleaned_md.read_text(encoding="utf-8")
  assert "Chapter A" in cleaned
  assert "Chapter B" in cleaned
  # 拼装文件应被写到 legacy 路径(便于下次直接命中)
  legacy = work / "chapters" / "raw" / "chap-3.md"
  assert legacy.exists()


def test_process_long_doc_missing_all_layers_raises(tmp_path: Path) -> None:
  """端到端:3 层全失败 → 抛 FileNotFoundError。"""
  work = tmp_path / "work"
  work.mkdir()
  _seed_chapters(work, video="none")

  with pytest.raises(FileNotFoundError, match="W12-D 兼容 3 级 fallback"):
    process_long_doc(work, None)


# ─────────────────────────────────────────────────────────────
# 6. 向后兼容:旧测试 fixture(_seed_rendered_md → chapters/raw/<stem>.md)仍 work
# ─────────────────────────────────────────────────────────────


def test_process_long_doc_legacy_only_works_via_compat(tmp_path: Path) -> None:
  """W3-W11 旧产物布局 → 通过 layer 2 fallback 仍能跑通(兼容)。"""
  work = tmp_path
  _seed_chapters(work, video="legacy-bridge")
  _seed_legacy_md(work, "legacy-bridge", "# 旧布局\n\n正文\n")

  result = process_long_doc(work, None)
  assert result.cleaned_md is not None and result.cleaned_md.exists()
  assert "旧布局" in result.cleaned_md.read_text(encoding="utf-8")
