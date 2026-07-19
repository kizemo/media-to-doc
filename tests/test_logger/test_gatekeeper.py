"""``media_to_doc.logger.gatekeeper`` 单元测试(W8 + W11-A)。

覆盖:
- 4 项机器可验证检查:chapters 存在 + H1>=1 + H2>=3 + output_final.html + image_refs
- 适配新产物布局(W3 render + W4 longdoc):<work>/chapters/raw/<stem>.md +
  <work>/chapters/raw/<stem>_final.html
- 兼容旧布局(W4 原型):<work>/chapters/raw/<stem>/<stem>.md + <work>/output_final.html
- W11-A 真端到端一致性:gatekeeper 与 verify 对同一份数据给出一致结论
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

  def test_resolve_lecture_new_layout_no_file(
    self, tmp_path: Path,
  ) -> None:
    """chapters.json 含 video + 新布局文件不存在 → 返回新布局诊断路径。

    W11-A 修复后:无文件时返回新布局路径(W3+ 默认),
    而非旧布局 <stem>/<stem>.md(W4 原型)。
    """
    work = tmp_path / "work"
    (work / "chapters").mkdir(parents=True)
    (work / "chapters" / "chapters.json").write_text(
      json.dumps({"video": "course1"}),
      encoding="utf-8",
    )
    resolved = _resolve_lecture_path(work)
    assert resolved == work / "chapters" / "raw" / "course1.md"

  def test_resolve_lecture_new_layout_file_exists(
    self, tmp_path: Path,
  ) -> None:
    """新布局文件 <work>/chapters/raw/<stem>.md 存在 → 返回该路径(W3+ 默认)。"""
    work = tmp_path / "work"
    (work / "chapters" / "raw").mkdir(parents=True)
    (work / "chapters" / "chapters.json").write_text(
      json.dumps({"video": "course1"}),
      encoding="utf-8",
    )
    target = work / "chapters" / "raw" / "course1.md"
    target.write_text("# Title\n", encoding="utf-8")
    resolved = _resolve_lecture_path(work)
    assert resolved == target

  def test_resolve_lecture_old_layout_fallback(
    self, tmp_path: Path,
  ) -> None:
    """新布局不存在 + 旧布局存在 → 返回旧布局路径(W4 兼容)。"""
    work = tmp_path / "work"
    old_layout_dir = work / "chapters" / "raw" / "course1"
    old_layout_dir.mkdir(parents=True)
    (work / "chapters" / "chapters.json").write_text(
      json.dumps({"video": "course1"}),
      encoding="utf-8",
    )
    target = old_layout_dir / "course1.md"
    target.write_text("# Title\n", encoding="utf-8")
    resolved = _resolve_lecture_path(work)
    assert resolved == target

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

  def test_resolve_final_html_new_layout_exists(
    self, tmp_path: Path,
  ) -> None:
    """新布局 <work>/chapters/raw/<stem>_final.html 存在 → 返回该路径。"""
    work = tmp_path / "work"
    (work / "chapters" / "raw").mkdir(parents=True)
    (work / "chapters" / "chapters.json").write_text(
      json.dumps({"video": "course1"}),
      encoding="utf-8",
    )
    target = work / "chapters" / "raw" / "course1_final.html"
    target.write_text("x" * 2000, encoding="utf-8")
    resolved = _resolve_final_html(work)
    assert resolved == target

  def test_resolve_final_html_old_layout_fallback(
    self, tmp_path: Path,
  ) -> None:
    """新布局不存在 + 旧布局 <work>/output_final.html 存在 → 返回旧路径。"""
    work = tmp_path / "work"
    (work / "chapters" / "raw").mkdir(parents=True)
    (work / "chapters" / "chapters.json").write_text(
      json.dumps({"video": "course1"}),
      encoding="utf-8",
    )
    target = work / "output_final.html"
    target.write_text("x" * 2000, encoding="utf-8")
    resolved = _resolve_final_html(work)
    assert resolved == target

  def test_resolve_final_html_no_chapters_json(self, tmp_path: Path) -> None:
    """chapters.json 不存在时 → 默认 fallback 为旧布局 <work>/output_final.html。"""
    work = tmp_path / "work"
    assert _resolve_final_html(work) == work / "output_final.html"

  def test_resolve_final_html_chapters_json_no_video(
    self, tmp_path: Path,
  ) -> None:
    """chapters.json 缺 video 字段 → 新布局默认 stem='output'。"""
    work = tmp_path / "work"
    (work / "chapters").mkdir(parents=True)
    (work / "chapters" / "chapters.json").write_text("{}", encoding="utf-8")
    resolved = _resolve_final_html(work)
    assert resolved == work / "chapters" / "raw" / "output_final.html"


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


# ─────────────────────────────────────────────────────────────
# W11-A:新布局(W3+ render + W4 longdoc)+ W10-A 端到端场景
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def work_dir_new_layout(tmp_path: Path) -> Path:
  """W3+ 新布局 fixture(chapters/raw/<stem>.md + _final.html,与 W10-A 一致)。"""
  work = tmp_path / "work"
  (work / "chapters" / "raw" / "output").mkdir(parents=True)
  (work / "chapters" / "chapters.json").write_text(
    json.dumps({"video": "output"}),
    encoding="utf-8",
    # chapters.json 在 W10-A 实际含 chapters 列表,这里简化
  )
  # W3 render 产物:chapters/raw/<stem>.md + .html
  (work / "chapters" / "raw" / "output.md").write_text(
    "# 课程讲义\n\n"
    "Intro lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\n\n"
    "## Chapter 1\n\nLorem ipsum dolor sit amet, consectetur adipiscing elit, "
    "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\n\n"
    "## Chapter 2\n\nSed ut perspiciatis unde omnis iste natus error sit "
    "voluptatem accusantium doloremque laudantium, totam rem aperiam.\n\n"
    "## Chapter 3\n\nNemo enim ipsam voluptatem quia voluptas sit aspernatur "
    "aut odit aut fugit, sed quia consequuntur magni dolores.\n",
    encoding="utf-8",
  )
  # W4 longdoc 产物:chapters/raw/<stem>_cleaned.md + _final.html
  (work / "chapters" / "raw" / "output_cleaned.md").write_text(
    "# cleaned\n\nbody content",
    encoding="utf-8",
  )
  (work / "chapters" / "raw" / "output_final.html").write_text(
    "<html>" + "x" * 5000 + "</html>",
    encoding="utf-8",
  )
  return work


class TestGatekeeperNewLayout:
  """W11-A:gatekeeper 必须能识别 W3+ 新布局,与 verify 一致。"""

  def test_new_layout_all_pass(self, work_dir_new_layout: Path) -> None:
    """W3+ 新布局产物 → ok=True(W10-A 真实场景)。"""
    result = gatekeeper_check(work_dir_new_layout)
    assert result.ok, f"issues: {result.issues}"
    assert "lecture_md_exists" in result.checks_passed
    assert "lecture_md_nonempty" in result.checks_passed
    assert "lecture_chapter_count" in result.checks_passed
    assert "final_html_exists" in result.checks_passed

  def test_new_layout_missing_final_html(
    self, work_dir_new_layout: Path,
  ) -> None:
    """新布局下 _final.html 缺失 → ok=False。"""
    (work_dir_new_layout / "chapters" / "raw" / "output_final.html").unlink()
    result = gatekeeper_check(work_dir_new_layout)
    assert not result.ok
    assert any("output_final.html" in i for i in result.issues)
    assert "final_html_exists" in result.checks_failed

  def test_new_layout_image_refs_stem_images(
    self, work_dir_new_layout: Path,
  ) -> None:
    """W3 render 默认:image 在 <lecture_dir>/<stem>/images/ 子目录(W10-A 实际)。

    验证 gatekeeper image_refs 候选路径第 4 项
    ``<lecture_dir>/<stem>/images/<basename>`` 能找到图片。
    """
    img_dir = (
      work_dir_new_layout / "chapters" / "raw" / "output" / "images"
    )
    img_dir.mkdir(parents=True)
    (img_dir / "gen_xxx.png").write_bytes(b"\x89PNG\r\n")
    lecture_md = work_dir_new_layout / "chapters" / "raw" / "output.md"
    content = lecture_md.read_text(encoding="utf-8")
    # md-link 引用形式(等价于 W3 render 拼装后的 ![(...)](output/images/gen_xxx.png))
    lecture_md.write_text(
      content + "\n\n![Image](output/images/gen_xxx.png)\n",
      encoding="utf-8",
    )
    result = gatekeeper_check(work_dir_new_layout)
    assert result.ok, f"issues: {result.issues}"
    assert any("image_refs_valid" in c for c in result.checks_passed)


# ─────────────────────────────────────────────────────────────
# W11-A:gatekeeper vs verify 一致性 — 防回归
# ─────────────────────────────────────────────────────────────


class TestGatekeeperVerifyConsistency:
  """W11-A 防回归:同一份产物布局,gatekeeper 与 verify 必须给出一致结论。

  关键不变量:gatekeeper_passed == verify_pipeline overall_passed。
  W10-A 真跑发现 gatekeeper FAIL 但 verify PASS 是历史 bug 模式,任何
  layout 变化时这个测试若失败就说明又分叉了。
  """

  def _setup_w10a_layout(self, work: Path, stem: str = "course1") -> None:
    """复刻 W10-A 真跑产物布局(新布局 + 完整产物)。

    布局:
      <work>/chapters/raw/<stem>/            ← drafts_dir(目录)
        chapter_01..N.md                     ← draft per-chapter
      <work>/chapters/raw/<stem>.md          ← W3 render 拼装 markdown
      <work>/chapters/raw/<stem>_cleaned.md  ← W4 longdoc 净化后
      <work>/chapters/raw/<stem>_final.html  ← W4 longdoc 最终 HTML
      <work>/chapters/chapters.json          ← video='<stem>',chapters=[]
    """
    chapters_dir = work / "chapters"
    drafts_dir = chapters_dir / "raw" / stem
    drafts_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.joinpath("chapters.json").write_text(
      json.dumps({"video": stem, "chapters": []}),
      encoding="utf-8",
    )
    # render 拼装 markdown(新布局,drafts_dir.parent / <stem>.md)
    md_parts = [f"# {stem} 主标题", ""]
    md_parts.append(
      "Intro lorem ipsum dolor sit amet, consectetur adipiscing elit. "
      "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
      "Ut enim ad minim veniam, quis nostrud exercitation ullamco."
    )
    for i in range(1, 5):
      md_parts.extend([f"## Chapter {i}", "", f"Chapter {i} body content."])
    (chapters_dir / "raw" / f"{stem}.md").write_text(
      "\n".join(md_parts) + "\n", encoding="utf-8",
    )
    # longdoc 产物(新布局)— final HTML 必须含 <title> + H1 满足 verify html_structure
    (chapters_dir / "raw" / f"{stem}_cleaned.md").write_text(
      f"# {stem} 主标题\n\nbody content", encoding="utf-8",
    )
    final_html_body = "x" * 2000  # > 1000 bytes 满足 gatekeeper final_html 大小
    (chapters_dir / "raw" / f"{stem}_final.html").write_text(
      f"<!doctype html><html><head><title>{stem}</title></head>"
      f"<body><h1>{stem} 主标题</h1><p>{final_html_body}</p></body></html>",
      encoding="utf-8",
    )

  def test_consistent_on_new_layout_full_products(self, tmp_path: Path) -> None:
    """新布局 + 完整产物 → gatekeeper PASS 与 verify PASS 一致(W10-A 场景)。"""
    work = tmp_path / "work"
    self._setup_w10a_layout(work, stem="course1")

    from media_to_doc.pipeline.verify import verify_pipeline

    gk = gatekeeper_check(work)
    vr = verify_pipeline(work)
    assert gk.ok == vr.overall_passed, (
      f"分叉!gatekeeper.ok={gk.ok} vs verify.overall_passed={vr.overall_passed}; "
      f"gk_issues={gk.issues}, verify_failures={vr.failures}"
    )
    assert gk.ok, "W10-A 布局 + 完整产物应 PASS(gatekeeper + verify)"

  def test_consistent_when_missing_final_html(self, tmp_path: Path) -> None:
    """final html 缺失 → gatekeeper FAIL 与 verify FAIL 一致。"""
    work = tmp_path / "work"
    self._setup_w10a_layout(work, stem="course1")
    # 删 final html
    (work / "chapters" / "raw" / "course1_final.html").unlink()

    from media_to_doc.pipeline.verify import verify_pipeline

    gk = gatekeeper_check(work)
    vr = verify_pipeline(work)
    assert gk.ok == vr.overall_passed, (
      f"分叉!gk.ok={gk.ok} vs vr.overall_passed={vr.overall_passed}; "
      f"gk_issues={gk.issues}, verify_failures={vr.failures}"
    )
    assert not gk.ok, "缺 final html 应 FAIL(gatekeeper + verify)"
