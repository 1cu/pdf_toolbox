from pathlib import Path

import pytest

import fitz
from pdf_toolbox.actions import pdf_images as images_mod
from pdf_toolbox.actions.pdf_images import pdf_to_images
from pdf_toolbox.actions.unlock import unlock_pdf


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
    with pytest.raises(ValueError, match="Invalid password"):
        unlock_pdf(str(locked), password="wrong", out_dir=str(tmp_path))


def test_render_doc_pages_converts_colorspace(monkeypatch, sample_pdf):
    class DummyPix:
        def __init__(self, n: int, alpha: int = 0):
            self.colorspace = type("CS", (), {"n": n})()
            self.alpha = alpha
            self.width = 1
            self.height = 1
            self.samples = b"\x00\x00\x00"

    class DummyPage:
        def get_pixmap(self, matrix, alpha: bool = False):
            _ = matrix
            assert alpha is False
            return DummyPix(4)

    def fake_load_page(_doc, _index):
        return DummyPage()

    def fake_pixmap(arg1, _arg2):
        assert arg1 is images_mod.fitz.csRGB
        return DummyPix(3)

    monkeypatch.setattr(images_mod.fitz.Document, "load_page", fake_load_page)
    monkeypatch.setattr(images_mod.fitz, "Pixmap", fake_pixmap)
    with images_mod.open_pdf(sample_pdf) as doc:
        outputs = images_mod._render_doc_pages(sample_pdf, doc, [1], 72, "PNG", 95)
    assert outputs


def test_render_doc_pages_strips_alpha(monkeypatch, sample_pdf):
    class DummyPix:
        def __init__(self, alpha: int):
            self.colorspace = type("CS", (), {"n": 3})()
            self.alpha = alpha
            self.width = 1
            self.height = 1
            self.samples = b"\x00\x00\x00"

    class DummyPage:
        def get_pixmap(self, matrix, alpha: bool = False):
            _ = matrix
            assert alpha is False
            return DummyPix(1)

    def fake_load_page(_doc, _index):
        return DummyPage()

    def fake_pixmap(_arg1, arg2):
        assert arg2 == 0
        return DummyPix(0)

    monkeypatch.setattr(images_mod.fitz.Document, "load_page", fake_load_page)
    monkeypatch.setattr(images_mod.fitz, "Pixmap", fake_pixmap)
    with images_mod.open_pdf(sample_pdf) as doc:
        outputs = images_mod._render_doc_pages(sample_pdf, doc, [1], 72, "PNG", 95)
    assert outputs
