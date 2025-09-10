from pathlib import Path
import math

import pytest
from PIL import Image

from pdf_toolbox.rasterize import DPI_PRESETS, pdf_to_images


def test_pdf_to_images_returns_pil(sample_pdf):
    images = pdf_to_images(sample_pdf, as_pil=True, dpi="Low (72 dpi)")
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
        sample_pdf,
        start_page="1",
        end_page="2",
        as_pil=True,
        dpi="Low (72 dpi)",
    )
    assert len(images) == 2


def test_pdf_to_images_invalid_page_type(sample_pdf):
    with pytest.raises(ValueError, match="start_page must be an integer"):
        pdf_to_images(sample_pdf, start_page="x")


@pytest.mark.parametrize(
    "dpi_label",
    ["Low (72 dpi)", "Medium (150 dpi)", "High (300 dpi)"],
)
def test_pdf_to_images_dpi_resolution(sample_pdf, dpi_label):
    base = pdf_to_images(sample_pdf, as_pil=True, dpi="Low (72 dpi)")[0].size
    images = pdf_to_images(sample_pdf, as_pil=True, dpi=dpi_label)
    assert len(images) == 3
    dpi = DPI_PRESETS[dpi_label]
    expected = (
        math.ceil(base[0] * dpi / 72),
        math.ceil(base[1] * dpi / 72),
    )
    assert images[0].size == expected


@pytest.mark.parametrize(
    "dpi_label",
    ["Very High (600 dpi)", "Ultra (1200 dpi)"],
)
def test_pdf_to_images_high_dpi(tmp_path, dpi_label):
    # create a tiny PDF to keep memory usage low even at very high DPI
    import fitz

    doc = fitz.open()
    doc.new_page(width=10, height=10)
    pdf_path = tmp_path / "tiny.pdf"
    doc.save(pdf_path)
    doc.close()

    images = pdf_to_images(str(pdf_path), as_pil=True, dpi=dpi_label)
    dpi = DPI_PRESETS[dpi_label]
    expected = (math.ceil(10 * dpi / 72), math.ceil(10 * dpi / 72))
    assert images[0].size == expected


def test_pdf_to_images_custom_dpi(sample_pdf):
    base = pdf_to_images(sample_pdf, as_pil=True, dpi=72)[0].size
    images = pdf_to_images(sample_pdf, as_pil=True, dpi=200)
    expected = (
        math.ceil(base[0] * 200 / 72),
        math.ceil(base[1] * 200 / 72),
    )
    assert images[0].size == expected


def test_pdf_to_images_invalid_page_range(sample_pdf):
    with pytest.raises(
        ValueError, match="end_page must be greater than or equal to start_page"
    ):
        pdf_to_images(sample_pdf, start_page=3, end_page=2)


def test_pdf_to_images_creates_files(sample_pdf, tmp_path):
    outputs = pdf_to_images(sample_pdf, out_dir=str(tmp_path), dpi="Low (72 dpi)")
    assert len(outputs) == 3
    for out in outputs:
        p = Path(out)
        assert p.exists()
        assert p.suffix.lower() == ".png"
