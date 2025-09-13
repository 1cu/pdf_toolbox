from pathlib import Path

import fitz  # type: ignore
import pytest

from pdf_toolbox.docx import pdf_to_docx
from pdf_toolbox.images import pdf_to_images
from pdf_toolbox.repair import repair_pdf
from pdf_toolbox.unlock import unlock_pdf


def test_pdf_to_images_png(sample_pdf, tmp_path):
    outputs = pdf_to_images(
        sample_pdf, dpi=72, image_format="PNG", out_dir=str(tmp_path)
    )
    assert len(outputs) == 3
    assert all(Path(output_path).exists() for output_path in outputs)


def test_pdf_to_images_jpeg(sample_pdf, tmp_path):
    outputs = pdf_to_images(
        sample_pdf, dpi="Low (72 dpi)", image_format="JPEG", out_dir=str(tmp_path)
    )
    assert len(outputs) == 3
    assert all(Path(output_path).exists() for output_path in outputs)


def test_pdf_to_images_tiff(sample_pdf, tmp_path):
    outputs = pdf_to_images(
        sample_pdf, dpi="Low (72 dpi)", image_format="TIFF", out_dir=str(tmp_path)
    )
    assert len(outputs) == 3
    assert all(Path(output_path).exists() for output_path in outputs)


def test_pdf_to_images_default_outdir(sample_pdf):
    outputs = pdf_to_images(sample_pdf, dpi="Low (72 dpi)")
    assert all(
        Path(output_path).parent == Path(sample_pdf).parent for output_path in outputs
    )


def test_pdf_to_docx(pdf_with_image, tmp_path):
    output = pdf_to_docx(pdf_with_image, out_dir=str(tmp_path))
    assert Path(output).exists()


def test_repair_pdf(sample_pdf, tmp_path):
    output = repair_pdf(sample_pdf, out_dir=str(tmp_path))
    assert Path(output).exists()


def test_unlock_pdf(sample_pdf, tmp_path):
    output = unlock_pdf(sample_pdf, out_dir=str(tmp_path))
    assert Path(output).exists()


def test_unlock_pdf_invalid_password(sample_pdf, tmp_path):
    locked = tmp_path / "locked.pdf"
    with fitz.open(sample_pdf) as doc:
        doc.save(
            locked,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw="secret",
            user_pw="secret",
        )
    with pytest.raises(ValueError):
        unlock_pdf(str(locked), password="wrong", out_dir=str(tmp_path))
