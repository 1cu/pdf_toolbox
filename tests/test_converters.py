from pathlib import Path


from pdf_toolbox.docx import pdf_to_docx
from pdf_toolbox.rasterize import pdf_to_images
from pdf_toolbox.repair import repair_pdf
from pdf_toolbox.unlock import unlock_pdf


def test_pdf_to_images_png(sample_pdf, tmp_path):
    outputs = pdf_to_images(
        sample_pdf, dpi=72, image_format="PNG", out_dir=str(tmp_path)
    )
    assert len(outputs) == 3
    assert all(Path(p).exists() for p in outputs)


def test_pdf_to_images_jpeg(sample_pdf, tmp_path):
    outputs = pdf_to_images(
        sample_pdf, dpi=72, image_format="JPEG", out_dir=str(tmp_path)
    )
    assert len(outputs) == 3
    assert all(Path(p).exists() for p in outputs)


def test_pdf_to_images_tiff(sample_pdf, tmp_path):
    outputs = pdf_to_images(
        sample_pdf, dpi=72, image_format="TIFF", out_dir=str(tmp_path)
    )
    assert len(outputs) == 3
    assert all(Path(p).exists() for p in outputs)


def test_pdf_to_images_default_outdir(sample_pdf):
    outputs = pdf_to_images(sample_pdf, dpi=72)
    assert all(Path(p).parent == Path(sample_pdf).parent for p in outputs)


def test_pdf_to_docx(sample_pdf, tmp_path):
    out = pdf_to_docx(sample_pdf, out_dir=str(tmp_path))
    assert Path(out).exists()


def test_repair_pdf(sample_pdf, tmp_path):
    out = repair_pdf(sample_pdf, out_dir=str(tmp_path))
    assert Path(out).exists()


def test_unlock_pdf(sample_pdf, tmp_path):
    out = unlock_pdf(sample_pdf, out_dir=str(tmp_path))
    assert Path(out).exists()
