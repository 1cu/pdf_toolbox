from pathlib import Path

from pdf_toolbox._fitz import fitz
import pytest
from pdf_toolbox.optimize import QUALITY_SETTINGS, optimize_pdf


def test_pdf_quality_passed_to_doc_save(tmp_path, monkeypatch):
    input_pdf = tmp_path / "input.pdf"
    with fitz.open() as doc:
        doc.new_page()
        doc.save(input_pdf)

    saved = {}
    original_save = fitz.Document.save

    def wrapped_save(self, filename, *args, **kwargs):
        saved.update(kwargs)
        return original_save(self, filename, *args, **kwargs)

    monkeypatch.setattr(fitz.Document, "save", wrapped_save)
    optimize_pdf(str(input_pdf), quality="screen")

    pdf_quality = QUALITY_SETTINGS["screen"]["pdf_quality"]
    expected = max(0, min(9, (100 - pdf_quality) // 10))
    assert saved.get("compression_effort") == expected


def test_invalid_quality_raises(sample_pdf):
    with pytest.raises(ValueError):
        optimize_pdf(sample_pdf, quality="unknown")


def test_compress_images(pdf_with_image, tmp_path):
    out, _ = optimize_pdf(pdf_with_image, compress_images=True, out_dir=str(tmp_path))
    assert Path(out).exists()


def test_remove_output_on_small_reduction(sample_pdf, tmp_path, monkeypatch):
    monkeypatch.setitem(QUALITY_SETTINGS["default"], "min_reduction", 1.0)
    out, reduction = optimize_pdf(sample_pdf, keep=False, out_dir=str(tmp_path))
    assert out is None
    assert reduction < 1.0
