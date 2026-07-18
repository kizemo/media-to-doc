"""Stage 4 — ``ocr``:对关键帧做 RapidOCR 推理。

输入:``inbox/<课程>/img/frame_<ts_ms>.jpg``(由 :mod:`frames` 抽取)
输出:
- ``inbox/<课程>/ocr/frame_<ts_ms>.txt``:每帧的纯文本(多行,中文保留)
- ``work/ocr/ocr_results.json``:整体 manifest(含置信度)

依赖:
- ``rapidocr-onnxruntime>=1.4.0``(lazy import,只装 ``media_to_doc[ocr]`` extras 才可用)
- 测试通过 monkeypatch :func:`_run_ocr_on_image` 注入假数据,无需真依赖

参考:TDD §5 数据流第 4 步 + PROJECT_DESCRIPTION §3.2 ocr 行。
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..config import PipelineConfig, WorkflowConfig

# ─────────────────────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────────────────────

# RapidOCR 默认参数(可在 PipelineConfig 中调)
DEFAULT_MIN_CONF = 0.5

# 文件名解析:``frame_<ts_ms:09d>.<ext>``
_FRAME_PATTERN = re.compile(r"^frame_(\d{9})\.[a-zA-Z0-9]+$")


# ─────────────────────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────────────────────


@dataclass
class OcrItem:
  """单帧的 OCR 识别项(一段文字 + 置信度)。"""

  text: str
  confidence: float
  # 包围盒(可选,RapidOCR 返回的 4 角坐标 [[x1,y1],...])
  box: list[list[float]] | None = None


@dataclass
class OcrResult:
  """单帧 OCR 结果(对应 ``frame_<ts_ms>.txt``)。"""

  image: str  # 文件名,如 ``frame_000001234.jpg``
  timestamp_ms: int
  items: list[OcrItem] = field(default_factory=list)
  error: str | None = None  # 推理失败时的错误信息(留 None=成功)

  @property
  def text(self) -> str:
    """所有 item.text 拼成纯文本(行分隔)。"""
    return "\n".join(item.text for item in self.items if item.text)

  def to_dict(self) -> dict[str, object]:
    payload: dict[str, object] = {
      "image": self.image,
      "timestamp_ms": self.timestamp_ms,
      "items": [asdict(it) for it in self.items],
      "text": self.text,
    }
    if self.error is not None:
      payload["error"] = self.error
    return payload


@dataclass
class OcrManifest:
  """整体 OCR manifest(对应 ``ocr_results.json``)。"""

  video: str = ""
  results: list[OcrResult] = field(default_factory=list)

  def to_dict(self) -> dict[str, object]:
    return {
      "video": self.video,
      "count": len(self.results),
      "results": [r.to_dict() for r in self.results],
    }

  def save(self, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
      json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
      encoding="utf-8",
    )


# ─────────────────────────────────────────────────────────────
# RapidOCR 懒加载 + 单帧推理(可 mock)
# ─────────────────────────────────────────────────────────────


def _try_load_rapidocr():
  """尝试加载 rapidocr,失败抛 ``ImportError``(信息明确)。"""
  try:
    from rapidocr_onnxruntime import RapidOCR  # type: ignore[import-untyped]
  except ImportError as exc:
    raise ImportError(
      "run_ocr() 需要 rapidocr-onnxruntime。安装方式:"
      "uv add 'media_to_doc[ocr]' 或 uv add rapidocr-onnxruntime"
    ) from exc
  return RapidOCR


def _run_ocr_on_image(image_path: Path, *, min_conf: float) -> OcrResult:
  """对单帧做 OCR,返回结构化结果(测试时 monkeypatch 此函数)。

  RapidOCR 返回格式:
    ``(results, elapse)`` 其中 ``results`` 是 ``[[box, text, conf], ...]``
  不同版本可能直接返回 ``(boxes, texts, scores)`` 或 ``None``。
  本函数做宽松适配:任意可索引对象都尝试解包。
  """
  ts_ms = _parse_timestamp(image_path.name) or 0

  try:
    RapidOCR = _try_load_rapidocr()  # noqa: N806
    engine = RapidOCR()
    response = engine(str(image_path))
  except ImportError:
    raise
  except Exception as exc:
    # 推断失败(图片损坏 / 模型加载失败)→ 返回空 result + error 信息
    return OcrResult(
      image=image_path.name,
      timestamp_ms=ts_ms,
      items=[],
      error=f"{type(exc).__name__}: {exc}",
    )

  # 解析 RapidOCR 返回
  detections = _normalize_rapidocr_response(response)
  items: list[OcrItem] = []
  for det in detections:
    box, text, conf = det
    if conf < min_conf:
      continue
    text = str(text).strip()
    if not text:
      continue
    items.append(OcrItem(text=text, confidence=float(conf), box=box))

  return OcrResult(image=image_path.name, timestamp_ms=ts_ms, items=items)


def _normalize_rapidocr_response(response: object) -> list[tuple[list[list[float]] | None, str, float]]:
  """把 RapidOCR 返回值规范化为 ``[(box, text, conf), ...]`` 列表。"""
  boxes = texts = scores = None
  try:
    if isinstance(response, tuple):
      if len(response) >= 1 and response[0] is not None:
        first = response[0]
        if isinstance(first, list) and first and isinstance(first[0], (list, tuple)):
          boxes = first
      if len(response) >= 2 and response[1] is not None:
        texts = response[1]
      if len(response) >= 3 and response[2] is not None:
        scores = response[2]
  except Exception:
    return []

  if boxes is None or texts is None:
    return []

  out: list[tuple[list[list[float]] | None, str, float]] = []
  for idx, text in enumerate(texts):
    box: list[list[float]] | None = boxes[idx] if idx < len(boxes) else None
    score = float(scores[idx]) if scores is not None and idx < len(scores) else 1.0
    out.append((box, str(text), score))
  return out


# ─────────────────────────────────────────────────────────────
# 文件名解析 + 帧文件枚举
# ─────────────────────────────────────────────────────────────


def _parse_timestamp(filename: str) -> int | None:
  """从 ``frame_<ts_ms>.<ext>`` 解析毫秒时间戳。"""
  match = _FRAME_PATTERN.match(filename)
  if not match:
    return None
  return int(match.group(1))


def _list_frame_files(img_dir: Path) -> list[Path]:
  """列出 ``img_dir`` 下所有关键帧文件(按时间戳排序)。"""
  if not img_dir.exists():
    return []
  files = [p for p in img_dir.iterdir() if p.is_file() and _FRAME_PATTERN.match(p.name)]
  files.sort(key=lambda p: (_parse_timestamp(p.name) or 0, p.name))
  return files


def _write_text(path: Path, content: str) -> None:
  """写单帧 OCR 文本(空内容也写空文件,方便下游检测)。"""
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(content, encoding="utf-8")


# ─────────────────────────────────────────────────────────────
# 公开 API
# ─────────────────────────────────────────────────────────────


def run_ocr(
  img_dir: Path,
  config: WorkflowConfig | None = None,
  *,
  output_dir: Path | None = None,
  manifest_path: Path | None = None,
) -> OcrManifest:
  """Stage 4:对 ``img_dir`` 下所有关键帧做 OCR。

  Parameters
  ----------
  img_dir : Path
    关键帧目录(默认 ``inbox/<课程>/img/``)
  config : WorkflowConfig | None
    配置(用 ``pipeline.default_ocr_threshold`` 调置信度阈值)
  output_dir : Path | None
    OCR 文本输出目录,默认 ``<img_dir>/ocr/``
  manifest_path : Path | None
    manifest json 路径,默认 ``<output_dir>/ocr_results.json``

  Returns
  -------
  OcrManifest
    整体结果(已写盘)
  """
  pipeline_cfg: PipelineConfig = (config or WorkflowConfig()).pipeline
  min_conf = float(pipeline_cfg.default_ocr_threshold)

  out_dir = output_dir or (img_dir / "ocr")
  out_dir.mkdir(parents=True, exist_ok=True)
  manifest = manifest_path or (out_dir / "ocr_results.json")

  frame_files = _list_frame_files(img_dir)
  results: list[OcrResult] = []
  for frame in frame_files:
    ocr = _run_ocr_on_image(frame, min_conf=min_conf)
    txt_path = out_dir / f"{frame.stem}.txt"
    _write_text(txt_path, ocr.text)
    results.append(ocr)

  video = img_dir.parent.name or ""
  m = OcrManifest(video=video, results=results)
  m.save(manifest)
  return m


__all__ = [
  "OcrItem",
  "OcrResult",
  "OcrManifest",
  "DEFAULT_MIN_CONF",
  "run_ocr",
]
