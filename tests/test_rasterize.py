import pytest
from PIL import Image

from pdf_toolbox.rasterize import pdf_to_images


def test_pdf_to_images_returns_pil(sample_pdf):
    images = pdf_to_images(sample_pdf, as_pil=True, dpi=72)
    assert len(images) == 3
    assert all(isinstance(img, Image.Image) for img in images)


def test_pdf_to_images_invalid_page(sample_pdf):
    with pytest.raises(ValueError, match="start_page 5 out of range"):
        pdf_to_images(sample_pdf, start_page=5)


def test_pdf_to_images_missing_file(tmp_path):
    missing = tmp_path / "missing.pdf"
    with pytest.raises(ValueError, match="Could not open PDF file"):
        pdf_to_images(str(missing))


def test_pdf_to_images_unsupported_format(sample_pdf):
    with pytest.raises(ValueError, match="Unsupported image format"):
        pdf_to_images(sample_pdf, image_format="BMP")


def test_pdf_to_images_str_page_numbers(sample_pdf):
    images = pdf_to_images(
        sample_pdf, start_page="1", end_page="2", as_pil=True, dpi=72
    )
    assert len(images) == 2


def test_pdf_to_images_invalid_page_type(sample_pdf):
    with pytest.raises(ValueError, match="start_page must be an integer"):
        pdf_to_images(sample_pdf, start_page="x")
