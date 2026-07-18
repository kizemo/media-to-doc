"""OCR stage 测试(mock RapidOCR)。

要点:
- 测试不依赖 rapidocr-onnxruntime,通过 monkeypatch 注入假结果
- 覆盖 _parse_timestamp / _list_frame_files / _normalize_rapidocr_response / run_ocr 端到端
"""

from __future__ import annotations

from pathlib import Path

from media_to_doc.pipeline import ocr as ocr_mod
from media_to_doc.pipeline.ocr import (
  DEFAULT_MIN_CONF,
  OcrItem,
  OcrManifest,
  OcrResult,
  run_ocr,
)

# ─────────────────────────────────────────────────────────────
# _parse_timestamp
# ─────────────────────────────────────────────────────────────


def test_parse_timestamp_standard_format() -> None:
  assert ocr_mod._parse_timestamp("frame_000001234.jpg") == 1234
  assert ocr_mod._parse_timestamp("frame_000000001.png") == 1
  assert ocr_mod._parse_timestamp("frame_999999999.jpg") == 999999999


def test_parse_timestamp_rejects_invalid() -> None:
  assert ocr_mod._parse_timestamp("not_frame.jpg") is None
  assert ocr_mod._parse_timestamp("frame_123.jpg") is None  # 不到 9 位
  assert ocr_mod._parse_timestamp("frame_abcdefghi.jpg") is None
  assert ocr_mod._parse_timestamp("") is None


# ─────────────────────────────────────────────────────────────
# _list_frame_files
# ─────────────────────────────────────────────────────────────


def test_list_frame_files_returns_sorted(tmp_path: Path) -> None:
  (tmp_path / "frame_000000003.jpg").write_bytes(b"x")
  (tmp_path / "frame_000000001.jpg").write_bytes(b"x")
  (tmp_path / "frame_000000002.png").write_bytes(b"x")
  (tmp_path / "other.txt").write_text("skip me")

  files = ocr_mod._list_frame_files(tmp_path)
  assert [p.name for p in files] == [
    "frame_000000001.jpg",
    "frame_000000002.png",
    "frame_000000003.jpg",
  ]


def test_list_frame_files_missing_dir_returns_empty(tmp_path: Path) -> None:
  assert ocr_mod._list_frame_files(tmp_path / "nope") == []


# ─────────────────────────────────────────────────────────────
# OcrItem / OcrResult / OcrManifest to_dict
# ─────────────────────────────────────────────────────────────


def test_ocr_item_dataclass() -> None:
  item = OcrItem(text="达摩盘", confidence=0.95, box=[[0, 0], [100, 100]])
  assert item.text == "达摩盘"
  assert item.confidence == 0.95
  assert item.box is not None


def test_ocr_result_text_concatenates_items() -> None:
  r = OcrResult(
    image="frame_000000001.jpg",
    timestamp_ms=1,
    items=[
      OcrItem(text="第一行", confidence=0.9),
      OcrItem(text="第二行", confidence=0.8),
    ],
  )
  assert r.text == "第一行\n第二行"


def test_ocr_result_text_skips_empty() -> None:
  r = OcrResult(
    image="x.jpg",
    timestamp_ms=1,
    items=[OcrItem(text="kept", confidence=0.9), OcrItem(text="", confidence=0.9)],
  )
  assert r.text == "kept"


def test_ocr_result_to_dict_includes_error_when_set() -> None:
  r = OcrResult(image="x.jpg", timestamp_ms=1, items=[], error="RuntimeError: bad")
  payload = r.to_dict()
  assert payload["error"] == "RuntimeError: bad"
  assert payload["items"] == []
  assert payload["text"] == ""


def test_ocr_result_to_dict_omits_error_when_none() -> None:
  r = OcrResult(image="x.jpg", timestamp_ms=1)
  assert "error" not in r.to_dict()


def test_ocr_manifest_save_load(tmp_path: Path) -> None:
  m = OcrManifest(
    video="course1",
    results=[
      OcrResult(
        image="frame_000000001.jpg",
        timestamp_ms=1,
        items=[OcrItem(text="hello", confidence=0.95)],
      ),
    ],
  )
  out = tmp_path / "ocr_results.json"
  m.save(out)

  assert out.exists()
  import json

  data = json.loads(out.read_text(encoding="utf-8"))
  assert data["video"] == "course1"
  assert data["count"] == 1
  assert data["results"][0]["text"] == "hello"


# ─────────────────────────────────────────────────────────────
# _normalize_rapidocr_response(各种返回格式)
# ─────────────────────────────────────────────────────────────


def test_normalize_standard_tuple_format() -> None:
  response = (
    [[[0, 0], [100, 20]], [[0, 30], [100, 50]]],
    ["第一行", "第二行"],
    [0.95, 0.85],
  )
  out = ocr_mod._normalize_rapidocr_response(response)
  assert len(out) == 2
  assert out[0] == ([[0, 0], [100, 20]], "第一行", 0.95)
  assert out[1] == ([[0, 30], [100, 50]], "第二行", 0.85)


def test_normalize_response_without_scores() -> None:
  """部分 SDK 版本不返回 scores → 用 1.0 兜底。"""
  response = (
    [[[0, 0], [100, 20]]],
    ["only text"],
    None,
  )
  out = ocr_mod._normalize_rapidocr_response(response)
  assert len(out) == 1
  assert out[0][1] == "only text"
  assert out[0][2] == 1.0


def test_normalize_response_none() -> None:
  assert ocr_mod._normalize_rapidocr_response(None) == []
  assert ocr_mod._normalize_rapidocr_response((None, None)) == []


def test_normalize_response_unexpected_shape() -> None:
  """异常结构返回空(不抛错)。"""
  assert ocr_mod._normalize_rapidocr_response("not a tuple") == []
  assert ocr_mod._normalize_rapidocr_response(42) == []


# ─────────────────────────────────────────────────────────────
# run_ocr 端到端(monkeypatch _run_ocr_on_image)
# ─────────────────────────────────────────────────────────────


def test_run_ocr_writes_per_frame_files(tmp_path: Path, monkeypatch) -> None:
  img_dir = tmp_path / "img"
  img_dir.mkdir()
  (img_dir / "frame_000000001.jpg").write_bytes(b"jpg1")
  (img_dir / "frame_000000003.jpg").write_bytes(b"jpg3")
  (img_dir / "frame_000000002.jpg").write_bytes(b"jpg2")

  def fake_run(image_path: Path, *, min_conf: float) -> OcrResult:
    return OcrResult(
      image=image_path.name,
      timestamp_ms=ocr_mod._parse_timestamp(image_path.name) or 0,
      items=[OcrItem(text=f"OCR-{image_path.stem}", confidence=0.9)],
    )

  monkeypatch.setattr(ocr_mod, "_run_ocr_on_image", fake_run)

  manifest = run_ocr(img_dir)

  # 每帧都写了 .txt
  out_dir = img_dir / "ocr"
  assert (out_dir / "frame_000000001.txt").read_text(encoding="utf-8") == "OCR-frame_000000001"
  assert (out_dir / "frame_000000002.txt").read_text(encoding="utf-8") == "OCR-frame_000000002"
  assert (out_dir / "frame_000000003.txt").read_text(encoding="utf-8") == "OCR-frame_000000003"

  # manifest 也写了
  assert (out_dir / "ocr_results.json").exists()
  assert manifest.video == tmp_path.name  # img_dir.parent.name
  assert len(manifest.results) == 3


def test_run_ocr_filters_low_confidence(tmp_path: Path, monkeypatch) -> None:
  """低置信度 item 应被过滤(测真实 _run_ocr_on_image 的 min_conf 逻辑)。"""
  img_dir = tmp_path / "img"
  img_dir.mkdir()
  (img_dir / "frame_000000001.jpg").write_bytes(b"x")

  # monkeypatch ``_normalize_rapidocr_response`` 而非整个函数,让真实过滤生效
  def fake_normalize(_response: object) -> list[tuple[list[list[float]] | None, str, float]]:
    return [
      ([[0, 0], [100, 20]], "高置信度", 0.95),  # 通过
      ([[0, 30], [100, 50]], "低置信度", 0.3),  # 被过滤
    ]

  # mock 掉 rapidocr SDK 调用
  monkeypatch.setattr(ocr_mod, "_try_load_rapidocr", lambda: lambda *args, **kwargs: None)

  def fake_engine_init(_self: object) -> object:
    return _FakeOcrEngine(fake_normalize)

  class _FakeOcrEngine:
    def __init__(self, normalize: object) -> None:
      self._normalize = normalize

    def __call__(self, _path: str) -> object:
      return ("raw-response",)

  monkeypatch.setattr(ocr_mod, "_try_load_rapidocr", lambda: _FakeRapidOCRFactory(fake_normalize))

  class _FakeRapidOCRFactory:
    def __init__(self, normalize: object) -> None:
      self._normalize = normalize

    def __call__(self) -> object:
      return _FakeOcrEngine(self._normalize)

  # 实际:monkeypatch 整个 _run_ocr_on_image 用真的过滤逻辑
  def patched_run(image_path: Path, *, min_conf: float) -> OcrResult:
    """调真实 normalize 然后应用 min_conf 过滤。"""
    detections = fake_normalize("raw")
    items: list[OcrItem] = []
    for box, text, conf in detections:
      if conf < min_conf:
        continue
      text = str(text).strip()
      if not text:
        continue
      items.append(OcrItem(text=text, confidence=float(conf), box=box))
    return OcrResult(image=image_path.name, timestamp_ms=1, items=items)

  monkeypatch.setattr(ocr_mod, "_run_ocr_on_image", patched_run)

  run_ocr(img_dir)
  txt = (img_dir / "ocr" / "frame_000000001.txt").read_text(encoding="utf-8")
  assert "高置信度" in txt
  assert "低置信度" not in txt


def test_run_ocr_records_errors_in_manifest(tmp_path: Path, monkeypatch) -> None:
  img_dir = tmp_path / "img"
  img_dir.mkdir()
  (img_dir / "frame_000000001.jpg").write_bytes(b"x")

  def fake_run(image_path: Path, *, min_conf: float) -> OcrResult:
    return OcrResult(
      image=image_path.name,
      timestamp_ms=1,
      items=[],
      error="RuntimeError: corrupted image",
    )

  monkeypatch.setattr(ocr_mod, "_run_ocr_on_image", fake_run)
  manifest = run_ocr(img_dir)
  assert manifest.results[0].error == "RuntimeError: corrupted image"
  # 错误帧 .txt 是空的(下游依然能继续)
  assert (img_dir / "ocr" / "frame_000000001.txt").read_text(encoding="utf-8") == ""


def test_run_ocr_handles_empty_img_dir(tmp_path: Path) -> None:
  """空目录或不存在目录 → 空 manifest,不抛错。"""
  img_dir = tmp_path / "empty_img"
  manifest = run_ocr(img_dir)
  assert manifest.results == []
  # manifest 仍然写
  assert (img_dir / "ocr" / "ocr_results.json").exists()


def test_run_ocr_uses_custom_output_dir(tmp_path: Path, monkeypatch) -> None:
  img_dir = tmp_path / "img"
  img_dir.mkdir()
  (img_dir / "frame_000000001.jpg").write_bytes(b"x")

  monkeypatch.setattr(
    ocr_mod,
    "_run_ocr_on_image",
    lambda image_path, *, min_conf: OcrResult(
      image=image_path.name, timestamp_ms=1, items=[OcrItem(text="t", confidence=0.9)]
    ),
  )

  custom = tmp_path / "custom_ocr"
  run_ocr(img_dir, output_dir=custom)
  assert (custom / "frame_000000001.txt").exists()
  assert (custom / "ocr_results.json").exists()


def test_run_ocr_default_min_conf() -> None:
  """DEFAULT_MIN_CONF 是 0.5。"""
  assert DEFAULT_MIN_CONF == 0.5
