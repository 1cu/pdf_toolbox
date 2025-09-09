from pathlib import Path

from pdf_toolbox.docx import pdf_to_docx
from pdf_toolbox.jpeg import pdf_to_jpegs
from pdf_toolbox.png import pdf_to_pngs
from pdf_toolbox.rasterize import pdf_to_images
from pdf_toolbox.repair import repair_pdf
from pdf_toolbox.tiff import pdf_to_tiff
from pdf_toolbox.unlock import unlock_pdf


def test_pdf_to_images(sample_pdf, tmp_path):
    outputs = pdf_to_images(sample_pdf, dpi=72, out_dir=str(tmp_path))
    assert len(outputs) == 3
    assert all(Path(p).exists() for p in outputs)


def test_pdf_to_tiff(sample_pdf, tmp_path):
    out = pdf_to_tiff(sample_pdf, dpi=72, out_dir=str(tmp_path))
    assert Path(out).exists()


def test_pdf_to_pngs(sample_pdf, tmp_path):
    outputs = pdf_to_pngs(sample_pdf, dpi=72, out_dir=str(tmp_path))
    assert len(outputs) == 3
    assert all(Path(p).exists() for p in outputs)


def test_pdf_to_jpegs(sample_pdf, tmp_path):
    outputs = pdf_to_jpegs(sample_pdf, dpi=72, out_dir=str(tmp_path))
    assert len(outputs) == 3
    assert all(Path(p).exists() for p in outputs)


def test_pdf_to_docx(sample_pdf, tmp_path):
    out = pdf_to_docx(sample_pdf, out_dir=str(tmp_path))
    assert Path(out).exists()


def test_repair_pdf(sample_pdf, tmp_path):
    out = repair_pdf(sample_pdf, out_dir=str(tmp_path))
    assert Path(out).exists()


def test_unlock_pdf(sample_pdf, tmp_path):
    out = unlock_pdf(sample_pdf, out_dir=str(tmp_path))
    assert Path(out).exists()
