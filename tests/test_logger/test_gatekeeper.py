"""``media_to_doc.logger.gatekeeper`` 单元测试(W8)。

覆盖:
- 4 项机器可验证检查:chapters 存在 + H1>=1 + H2>=3 + output_final.html + image_refs
- 适配新产物布局:<work>/chapters/raw/<stem>.md(W3 render) + <work>/output_final.html(longdoc)
- edge cases:空产物 / 缺章节数 / 缺 html / 缺图引用 / 空图引用不算失败
- pattern-key 不在 gatekeeper 接口里(在 learnings 那边测)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from media_to_doc.logger.gatekeeper import (
  _resolve_final_html,
  _resolve_lecture_path,
  gatekeeper_check,
)

# ─────────────────────────────────────────────────────────────
# 内部 helper
# ─────────────────────────────────────────────────────────────


class TestResolvePaths:
  def test_resolve_lecture_no_chapters_json(self, tmp_path: Path) -> None:
    """chapters.json 不存在 → 返回 None。"""
    work = tmp_path / "work"
    work.mkdir()
    assert _resolve_lecture_path(work) is None

  def test_resolve_lecture_with_chapters_json(self, tmp_path: Path) -> None:
    """chapters.json 含 video 字段 → 派生 <work>/chapters/raw/<stem>/<stem>.md。"""
    work = tmp_path / "work"
    (work / "chapters").mkdir(parents=True)
    (work / "chapters" / "chapters.json").write_text(
      json.dumps({"video": "course1"}),
      encoding="utf-8",
    )
    resolved = _resolve_lecture_path(work)
    assert resolved == work / "chapters" / "raw" / "course1" / "course1.md"

  def test_resolve_lecture_default_stem(self, tmp_path: Path) -> None:
    """chapters.json 缺 video 字段 → 默认 stem='output'。"""
    work = tmp_path / "work"
    (work / "chapters").mkdir(parents=True)
    (work / "chapters" / "chapters.json").write_text("{}", encoding="utf-8")
    resolved = _resolve_lecture_path(work)
    assert resolved is not None
    assert resolved.name == "output.md"

  def test_resolve_lecture_empty_video(self, tmp_path: Path) -> None:
    """chapters.json video='' → 默认 stem='output'(空白 strip)。"""
    work = tmp_path / "work"
    (work / "chapters").mkdir(parents=True)
    (work / "chapters" / "chapters.json").write_text(
      json.dumps({"video": "   "}),
      encoding="utf-8",
    )
    resolved = _resolve_lecture_path(work)
    assert resolved is not None
    assert resolved.name == "output.md"

  def test_resolve_final_html(self, tmp_path: Path) -> None:
    """final_html 路径 = <work>/output_final.html(不依赖 chapters.json)。"""
    work = tmp_path / "work"
    assert _resolve_final_html(work) == work / "output_final.html"


# ─────────────────────────────────────────────────────────────
# gatekeeper_check — 4 项机器可验证
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def work_dir_with_lecture(tmp_path: Path) -> Path:
  """创建合规的产物布局(11 章 + final_html + 0 图)。"""
  work = tmp_path / "work"
  (work / "chapters").mkdir(parents=True)
  (work / "chapters" / "chapters.json").write_text(
    json.dumps({"video": "course1"}),
    encoding="utf-8",
  )
  lecture_dir = work / "chapters" / "raw" / "course1"
  lecture_dir.mkdir(parents=True)
  (lecture_dir / "course1.md").write_text(
    "# Title\n\n"
    "Intro lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\n\n"
    "## Chapter 1\n\nLorem ipsum dolor sit amet, consectetur adipiscing elit, "
    "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
    "Ut enim ad minim veniam, quis nostrud exercitation.\n\n"
    "## Chapter 2\n\nSed ut perspiciatis unde omnis iste natus error sit "
    "voluptatem accusantium doloremque laudantium, totam rem aperiam.\n\n"
    "## Chapter 3\n\nNemo enim ipsam voluptatem quia voluptas sit aspernatur "
    "aut odit aut fugit, sed quia consequuntur magni dolores.\n\n"
    "## Chapter 4\n\nNeque porro quisquam est, qui dolorem ipsum quia dolor "
    "sit amet, consectetur, adipisci velit.\n",
    encoding="utf-8",
  )
  (work / "output_final.html").write_text("x" * 2000, encoding="utf-8")
  return work


class TestGatekeeperAllPass:
  def test_all_pass(self, work_dir_with_lecture: Path) -> None:
    """合规产物 → ok=True,无 issues,4 项检查全 pass。"""
    result = gatekeeper_check(work_dir_with_lecture)
    assert result.ok, f"issues: {result.issues}"
    assert result.issues == []
    assert "lecture_md_exists" in result.checks_passed
    assert "lecture_md_nonempty" in result.checks_passed
    assert "lecture_chapter_count" in result.checks_passed
    assert "final_html_exists" in result.checks_passed


class TestGatekeeperFailures:
  def test_missing_chapters_json(
    self, tmp_path: Path,
  ) -> None:
    """chapters.json 不存在 → lecture_md 派生失败 → ok=False。"""
    work = tmp_path / "work"
    work.mkdir()
    result = gatekeeper_check(work)
    assert not result.ok
    assert any("lecture.md not found" in i for i in result.issues)
    assert "lecture_md_exists" in result.checks_failed

  def test_too_few_chapters(
    self, work_dir_with_lecture: Path,
  ) -> None:
    """章节数 < H1>=1 + H2>=3 → ok=False。"""
    lecture_md = work_dir_with_lecture / "chapters" / "raw" / "course1" / "course1.md"
    # 内容 > 100 字符 + 只有 1 个 H2(避免命中 lecture_md_too_small)
    lecture_md.write_text(
      "# Title\n\n"
      "Intro lorem ipsum dolor sit amet, consectetur adipiscing elit, "
      "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\n\n"
      "## Chapter 1\n\nOnly one chapter. Lorem ipsum dolor sit amet, "
      "consectetur adipiscing elit, sed do eiusmod tempor incididunt.\n",
      encoding="utf-8",
    )
    result = gatekeeper_check(work_dir_with_lecture)
    assert not result.ok
    assert any("chapter count too low" in i for i in result.issues)
    assert "lecture_chapter_count" in result.checks_failed

  def test_missing_final_html(
    self, work_dir_with_lecture: Path,
  ) -> None:
    """output_final.html 不存在或太小 → ok=False。"""
    (work_dir_with_lecture / "output_final.html").unlink()
    result = gatekeeper_check(work_dir_with_lecture)
    assert not result.ok
    assert any("output_final.html" in i for i in result.issues)
    assert "final_html_exists" in result.checks_failed

  def test_too_small_final_html(
    self, work_dir_with_lecture: Path,
  ) -> None:
    """output_final.html < 1000 bytes → ok=False。"""
    (work_dir_with_lecture / "output_final.html").write_text(
      "<html></html>", encoding="utf-8"
    )
    result = gatekeeper_check(work_dir_with_lecture)
    assert not result.ok
    assert "final_html_exists" in result.checks_failed

  def test_missing_image_refs(
    self, work_dir_with_lecture: Path,
  ) -> None:
    """lecture.md 引用不存在的图片 → ok=False。"""
    lecture_md = work_dir_with_lecture / "chapters" / "raw" / "course1" / "course1.md"
    content = lecture_md.read_text(encoding="utf-8")
    # 在末尾追加一个不存在的图片引用
    lecture_md.write_text(
      content + "\n\n![missing](nonexistent.png)\n",
      encoding="utf-8",
    )
    result = gatekeeper_check(work_dir_with_lecture)
    assert not result.ok
    assert any("image_refs missing" in i for i in result.issues)
    assert "image_refs_valid" in result.checks_failed

  def test_existing_image_refs_pass(
    self, work_dir_with_lecture: Path,
  ) -> None:
    """lecture.md 引用真实存在的图片 → image_refs_valid pass。"""
    lecture_dir = work_dir_with_lecture / "chapters" / "raw" / "course1"
    img_dir = lecture_dir / "images"
    img_dir.mkdir()
    (img_dir / "chapter1.png").write_bytes(b"\x89PNG\r\n")
    lecture_md = lecture_dir / "course1.md"
    content = lecture_md.read_text(encoding="utf-8")
    lecture_md.write_text(
      content + "\n\n![caption](images/chapter1.png)\n",
      encoding="utf-8",
    )
    result = gatekeeper_check(work_dir_with_lecture)
    assert result.ok, f"issues: {result.issues}"
    assert any("image_refs_valid" in c for c in result.checks_passed)

  def test_no_image_refs_not_a_failure(
    self, work_dir_with_lecture: Path,
  ) -> None:
    """lecture.md 无图片引用 → 算 pass(image_refs_valid_no_images)。"""
    # 默认无图引用
    result = gatekeeper_check(work_dir_with_lecture)
    assert result.ok
    assert "image_refs_valid_no_images" in result.checks_passed

  def test_wiki_link_image_refs(
    self, work_dir_with_lecture: Path,
  ) -> None:
    """wiki-link ![[image.png]] 语法也能被识别。"""
    lecture_dir = work_dir_with_lecture / "chapters" / "raw" / "course1"
    img_dir = lecture_dir / "images"
    img_dir.mkdir()
    (img_dir / "chapter2.png").write_bytes(b"\x89PNG\r\n")
    lecture_md = lecture_dir / "course1.md"
    content = lecture_md.read_text(encoding="utf-8")
    lecture_md.write_text(
      content + "\n\n![[chapter2.png]]\n",
      encoding="utf-8",
    )
    result = gatekeeper_check(work_dir_with_lecture)
    assert result.ok, f"issues: {result.issues}"
    assert any("image_refs_valid" in c for c in result.checks_passed)

  def test_checks_passed_and_failed_lists(
    self, work_dir_with_lecture: Path,
  ) -> None:
    """GatekeeperResult.checks_passed / checks_failed 是非互斥集合。"""
    # 把 final_html 删了 → final_html_exists 在 failed,其他在 passed
    (work_dir_with_lecture / "output_final.html").unlink()
    result = gatekeeper_check(work_dir_with_lecture)
    assert "lecture_md_exists" in result.checks_passed
    assert "final_html_exists" in result.checks_failed
