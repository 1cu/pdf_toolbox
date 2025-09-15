import io
from pathlib import Path
from threading import Event

import fitz  # type: ignore  # pdf-toolbox: PyMuPDF lacks type hints | issue:-
import pytest
from PIL import Image

from pdf_toolbox.actions.optimise import batch_optimise_pdfs, optimise_pdf


def test_optimise_pdf_cancellation_cleans_up(tmp_path):
    # Create simple PDF
    pdf_path = tmp_path / "in.pdf"
    document = fitz.open()
    document.new_page()
    document.save(pdf_path)
    document.close()

    cancel = Event()
    cancel.set()
    with pytest.raises(RuntimeError):
        optimise_pdf(str(pdf_path), cancel=cancel, out_dir=str(tmp_path))


def test_compress_images_grayscale(tmp_path):
    # Prepare grayscale image embedded in PDF
    img = Image.new("L", (20, 20), color=128)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    pdf_path = tmp_path / "g.pdf"
    document = fitz.open()
    page = document.new_page()
    rect = fitz.Rect(0, 0, 20, 20)
    page.insert_image(rect, stream=img_bytes)
    document.save(pdf_path)
    document.close()
    with pdf_path.open("ab") as fh:
        fh.write(b"% pad" + b"0" * 1000)

    output, _ = optimise_pdf(str(pdf_path), compress_images=True, out_dir=str(tmp_path))
    assert Path(output).exists()


def test_optimise_with_progress_threshold_and_cancel(tmp_path, monkeypatch):
    pdf_path = tmp_path / "in.pdf"
    document = fitz.open()
    document.new_page()
    document.save(pdf_path)
    document.close()

    # Exercise keep=False branch in progress variant
    monkeypatch.setattr(
        "pdf_toolbox.actions.optimise.QUALITY_SETTINGS",
        {"default": {"pdf_quality": 80, "image_quality": 75, "min_reduction": 1.0}},
    )
    output, _reduction = optimise_pdf(str(pdf_path), keep=False, out_dir=str(tmp_path))
    assert output is None

    # Now trigger cancellation early
    cancel = Event()
    cancel.set()
    with pytest.raises(RuntimeError):
        optimise_pdf(str(pdf_path), cancel=cancel, out_dir=str(tmp_path))


def test_batch_optimise_invalid_dir():
    with pytest.raises(FileNotFoundError):
        batch_optimise_pdfs("/path/does/not/exist/xyz")
