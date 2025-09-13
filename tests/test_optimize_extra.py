import io
from pathlib import Path
from threading import Event

import fitz  # type: ignore
import pytest
from PIL import Image

from pdf_toolbox.optimize import batch_optimize_pdfs, optimize_pdf


def test_optimize_pdf_cancellation_cleans_up(tmp_path):
    # Create simple PDF
    p = tmp_path / "in.pdf"
    d = fitz.open()
    d.new_page()
    d.save(p)
    d.close()

    cancel = Event()
    cancel.set()
    with pytest.raises(RuntimeError):
        optimize_pdf(str(p), cancel=cancel, out_dir=str(tmp_path))


def test_compress_images_grayscale(tmp_path):
    # Prepare grayscale image embedded in PDF
    img = Image.new("L", (20, 20), color=128)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    p = tmp_path / "g.pdf"
    d = fitz.open()
    page = d.new_page()
    rect = fitz.Rect(0, 0, 20, 20)
    page.insert_image(rect, stream=img_bytes)
    d.save(p)
    d.close()

    out, _ = optimize_pdf(str(p), compress_images=True, out_dir=str(tmp_path))
    assert Path(out).exists()


def test_optimize_with_progress_threshold_and_cancel(tmp_path, monkeypatch):
    p = tmp_path / "in.pdf"
    d = fitz.open()
    d.new_page()
    d.save(p)
    d.close()

    # Exercise keep=False branch in progress variant
    monkeypatch.setattr(
        "pdf_toolbox.optimize.QUALITY_SETTINGS",
        {"default": {"pdf_quality": 80, "image_quality": 75, "min_reduction": 1.0}},
    )
    out, reduction = optimize_pdf(str(p), keep=False, out_dir=str(tmp_path))
    assert out is None

    # Now trigger cancellation early
    cancel = Event()
    cancel.set()
    with pytest.raises(RuntimeError):
        optimize_pdf(str(p), cancel=cancel, out_dir=str(tmp_path))


def test_batch_optimize_invalid_dir():
    with pytest.raises(FileNotFoundError):
        batch_optimize_pdfs("/path/does/not/exist/xyz")
