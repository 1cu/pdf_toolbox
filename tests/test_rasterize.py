import math
import warnings
from pathlib import Path

import pytest
from PIL import Image

from pdf_toolbox.rasterize import DPI_PRESETS, pdf_to_images


def test_pdf_to_images_returns_paths(sample_pdf, tmp_path):
    outputs = pdf_to_images(sample_pdf, dpi="Low (72 dpi)", out_dir=str(tmp_path))
    assert len(outputs) == 3
    for out in outputs:
        assert Path(out).exists()
        assert isinstance(out, str)


def test_pdf_to_images_svg(sample_pdf, tmp_path):
    outputs = pdf_to_images(
        sample_pdf, image_format="SVG", dpi="Low (72 dpi)", out_dir=str(tmp_path)
    )
    assert len(outputs) == 3
    for out in outputs:
        assert out.endswith(".svg")
        assert Path(out).exists()


def test_pdf_to_images_invalid_page(sample_pdf):
    with pytest.raises(ValueError, match="page 5 out of range"):
        pdf_to_images(sample_pdf, pages="5")


def test_pdf_to_images_missing_file(tmp_path):
    missing = tmp_path / "missing.pdf"
    with pytest.raises(RuntimeError, match="Could not open PDF file"):
        pdf_to_images(str(missing))


def test_pdf_to_images_unsupported_format(sample_pdf):
    with pytest.raises(ValueError, match="Unsupported image format"):
        pdf_to_images(sample_pdf, image_format="BMP")


def test_pdf_to_images_unknown_dpi(sample_pdf):
    with pytest.raises(ValueError, match="Unknown DPI preset"):
        pdf_to_images(sample_pdf, dpi="bogus")


def test_pdf_to_images_selected_pages(sample_pdf, tmp_path):
    outputs = pdf_to_images(
        sample_pdf,
        pages="1,2",
        dpi="Low (72 dpi)",
        out_dir=str(tmp_path),
    )
    assert len(outputs) == 2
    for out in outputs:
        assert Path(out).exists()


def test_pdf_to_images_invalid_page_type(sample_pdf):
    with pytest.raises(ValueError, match="Invalid page specification"):
        pdf_to_images(sample_pdf, pages="x")


@pytest.mark.parametrize(
    "dpi_label",
    ["Low (72 dpi)", "Medium (150 dpi)", "High (300 dpi)"],
)
def test_pdf_to_images_dpi_resolution(sample_pdf, tmp_path, dpi_label):
    low_dir = tmp_path / "low"
    high_dir = tmp_path / "high"
    base_path = pdf_to_images(sample_pdf, dpi="Low (72 dpi)", out_dir=str(low_dir))[0]
    base_size = Image.open(base_path).size
    outputs = pdf_to_images(sample_pdf, dpi=dpi_label, out_dir=str(high_dir))
    assert len(outputs) == 3
    img = Image.open(outputs[0])
    dpi = DPI_PRESETS[dpi_label]
    expected = (
        math.ceil(base_size[0] * dpi / 72),
        math.ceil(base_size[1] * dpi / 72),
    )
    assert img.size == expected


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

    out_dir = tmp_path / "out"
    outputs = pdf_to_images(str(pdf_path), dpi=dpi_label, out_dir=str(out_dir))
    dpi = DPI_PRESETS[dpi_label]
    expected = (math.ceil(10 * dpi / 72), math.ceil(10 * dpi / 72))
    img = Image.open(outputs[0])
    assert img.size == expected


def test_pdf_to_images_high_dpi_with_max_size(tmp_path):
    import sys

    import fitz

    sys.set_int_max_str_digits(4300)
    doc = fitz.open()
    page = doc.new_page()
    rect = page.rect
    pdf_path = tmp_path / "doc.pdf"
    doc.save(pdf_path)
    doc.close()

    outputs = pdf_to_images(
        str(pdf_path),
        dpi="Very High (600 dpi)",
        image_format="PNG",
        max_size_mb=30,
        out_dir=str(tmp_path),
    )

    assert len(outputs) == 1
    out_path = Path(outputs[0])
    assert out_path.exists()
    img = Image.open(out_path)
    assert out_path.stat().st_size <= 30 * 1024 * 1024
    expected_w = math.ceil(rect.width * 600 / 72)
    expected_h = math.ceil(rect.height * 600 / 72)
    assert img.width == expected_w
    assert img.height == expected_h
    assert sys.get_int_max_str_digits() == 4300


def test_pdf_to_images_png_30mb_limit_no_digit_error(tmp_path):
    import sys

    import fitz

    sys.set_int_max_str_digits(1000)
    doc = fitz.open()
    page = doc.new_page()
    rect = page.rect
    pdf_path = tmp_path / "doc.pdf"
    doc.save(pdf_path)
    doc.close()

    outputs = pdf_to_images(
        str(pdf_path),
        dpi="Very High (600 dpi)",
        image_format="PNG",
        max_size_mb=30,
        out_dir=str(tmp_path / "out"),
    )

    out_path = Path(outputs[0])
    assert out_path.exists()
    img = Image.open(out_path)
    expected_w = math.ceil(rect.width * 600 / 72)
    expected_h = math.ceil(rect.height * 600 / 72)
    assert img.width == expected_w
    assert img.height == expected_h
    assert out_path.stat().st_size <= 30 * 1024 * 1024
    assert sys.get_int_max_str_digits() == 1000


def test_pdf_to_images_custom_dpi(sample_pdf, tmp_path):
    low_dir = tmp_path / "low"
    high_dir = tmp_path / "high"
    base_path = pdf_to_images(sample_pdf, dpi=72, out_dir=str(low_dir))[0]
    base_size = Image.open(base_path).size
    outputs = pdf_to_images(sample_pdf, dpi=200, out_dir=str(high_dir))
    img = Image.open(outputs[0])
    expected = (
        math.ceil(base_size[0] * 200 / 72),
        math.ceil(base_size[1] * 200 / 72),
    )
    assert img.size == expected


@pytest.mark.parametrize("fmt", ["JPEG", "WEBP"])
def test_pdf_to_images_lossy_quality_preset(sample_pdf, tmp_path, fmt):
    images = pdf_to_images(
        sample_pdf,
        image_format=fmt,
        quality="Medium (85)",
        dpi="Low (72 dpi)",
        out_dir=str(tmp_path),
    )
    assert len(images) == 3


@pytest.mark.parametrize("fmt", ["JPEG", "WEBP"])
def test_pdf_to_images_lossy_quality_custom(sample_pdf, tmp_path, fmt):
    images = pdf_to_images(
        sample_pdf,
        image_format=fmt,
        quality=80,
        dpi="Low (72 dpi)",
        out_dir=str(tmp_path),
    )
    assert len(images) == 3


@pytest.mark.parametrize("fmt", ["JPEG", "WEBP"])
def test_pdf_to_images_unknown_quality(sample_pdf, fmt):
    with pytest.raises(ValueError, match="Unknown quality preset"):
        pdf_to_images(
            sample_pdf,
            image_format=fmt,
            quality="Ultra",
        )


def test_pdf_to_images_invalid_page_range(sample_pdf):
    with pytest.raises(ValueError, match="end must be greater than or equal to start"):
        pdf_to_images(sample_pdf, pages="3-2")


def test_pdf_to_images_creates_files(sample_pdf, tmp_path):
    outputs = pdf_to_images(sample_pdf, out_dir=str(tmp_path), dpi="Low (72 dpi)")
    assert len(outputs) == 3
    for out in outputs:
        p = Path(out)
        assert p.exists()
        assert p.suffix.lower() == ".png"


@pytest.mark.parametrize("fmt", ["JPEG", "WEBP"])
def test_pdf_to_images_max_size_reduces_quality(tmp_path, fmt):
    import os

    import fitz

    width = height = 100
    img_path = tmp_path / "noise.png"
    Image.frombytes("RGB", (width, height), os.urandom(width * height * 3)).save(
        img_path
    )
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    rect = fitz.Rect(0, 0, width, height)
    page.insert_image(rect, filename=str(img_path))
    pdf_path = tmp_path / "noise.pdf"
    doc.save(pdf_path)
    doc.close()

    high_dir = tmp_path / "high"
    limited_dir = tmp_path / "limited"
    base = pdf_to_images(str(pdf_path), image_format=fmt, out_dir=str(high_dir))[0]
    base_size = Path(base).stat().st_size
    limit_mb = base_size * 0.8 / (1024 * 1024)
    limited = pdf_to_images(
        str(pdf_path),
        image_format=fmt,
        out_dir=str(limited_dir),
        max_size_mb=limit_mb,
    )[0]
    limited_size = Path(limited).stat().st_size
    assert limited_size <= limit_mb * 1024 * 1024
    assert limited_size < base_size


@pytest.mark.parametrize("fmt", ["JPEG", "WEBP"])
def test_pdf_to_images_max_size_binary_search(tmp_path, fmt, monkeypatch):
    import io

    import fitz

    def fake_save(self, fp, *, quality=None, **kwargs):
        data = b"x" * (quality * 1000)
        if isinstance(fp, io.BytesIO):
            fp.write(data)
        else:
            with open(fp, "wb") as f:
                f.write(data)

    monkeypatch.setattr(Image.Image, "save", fake_save)

    doc = fitz.open()
    doc.new_page()
    pdf_path = tmp_path / "doc.pdf"
    doc.save(pdf_path)
    doc.close()

    limit_mb = (90_000 - 1) / (1024 * 1024)
    limited = pdf_to_images(
        str(pdf_path),
        image_format=fmt,
        quality=95,
        max_size_mb=limit_mb,
        out_dir=str(tmp_path / "out"),
    )[0]
    limited_size = Path(limited).stat().st_size
    assert 85_000 < limited_size < 95_000


@pytest.mark.parametrize("fmt", ["JPEG", "WEBP"])
def test_pdf_to_images_max_size_too_small_raises(tmp_path, fmt):
    import os

    import fitz

    width = height = 100
    img_path = tmp_path / "noise.png"
    Image.frombytes("RGB", (width, height), os.urandom(width * height * 3)).save(
        img_path
    )
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    rect = fitz.Rect(0, 0, width, height)
    page.insert_image(rect, filename=str(img_path))
    pdf_path = tmp_path / "noise.pdf"
    doc.save(pdf_path)
    doc.close()

    with pytest.raises(RuntimeError, match="Could not reduce image below max_size_mb"):
        pdf_to_images(
            str(pdf_path),
            image_format=fmt,
            out_dir=str(tmp_path),
            max_size_mb=1e-6,
        )


@pytest.mark.parametrize("fmt", ["JPEG", "WEBP"])
def test_pdf_to_images_max_size_under_limit_keeps_quality(tmp_path, fmt):
    import os

    import fitz

    width = height = 100
    img_path = tmp_path / "noise.png"
    Image.frombytes("RGB", (width, height), os.urandom(width * height * 3)).save(
        img_path
    )
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    rect = fitz.Rect(0, 0, width, height)
    page.insert_image(rect, filename=str(img_path))
    pdf_path = tmp_path / "noise.pdf"
    doc.save(pdf_path)
    doc.close()

    base = pdf_to_images(str(pdf_path), image_format=fmt, out_dir=str(tmp_path))[0]
    base_size = Path(base).stat().st_size
    zoom = 300 / 72
    width_px = math.ceil(width * zoom)
    height_px = math.ceil(height * zoom)
    uncompressed = width_px * height_px * 3
    limit_mb = uncompressed * 2 / (1024 * 1024)
    limited = pdf_to_images(
        str(pdf_path),
        image_format=fmt,
        out_dir=str(tmp_path / "limited"),
        max_size_mb=limit_mb,
    )[0]
    limited_size = Path(limited).stat().st_size
    assert limited_size == base_size


@pytest.mark.parametrize("fmt", ["PNG", "TIFF"])
def test_pdf_to_images_max_size_lossless_scales_down(tmp_path, fmt):
    import os

    import fitz

    width = height = 500
    img_path = tmp_path / "noise.png"
    Image.frombytes("RGB", (width, height), os.urandom(width * height * 3)).save(
        img_path
    )
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    rect = fitz.Rect(0, 0, width, height)
    page.insert_image(rect, filename=str(img_path))
    pdf_path = tmp_path / "noise.pdf"
    doc.save(pdf_path)
    doc.close()

    high_dir = tmp_path / "high"
    limited_dir = tmp_path / "limited"
    base = pdf_to_images(str(pdf_path), image_format=fmt, out_dir=str(high_dir))[0]
    base_size = Path(base).stat().st_size
    base_img = Image.open(base)
    limit_mb = 0.001
    with pytest.warns(UserWarning, match="downscale"):
        limited = pdf_to_images(
            str(pdf_path),
            image_format=fmt,
            out_dir=str(limited_dir),
            max_size_mb=limit_mb,
        )[0]
    limited_size = Path(limited).stat().st_size
    limited_img = Image.open(limited)
    assert limited_size <= limit_mb * 1024 * 1024
    assert limited_size < base_size
    assert (
        limited_img.size[0] < base_img.size[0]
        and limited_img.size[1] < base_img.size[1]
    )


@pytest.mark.parametrize("fmt", ["PNG", "TIFF"])
def test_pdf_to_images_max_size_lossless_no_warning_when_under_limit(tmp_path, fmt):
    import os

    import fitz

    width = height = 500
    img_path = tmp_path / "noise.png"
    Image.frombytes("RGB", (width, height), os.urandom(width * height * 3)).save(
        img_path
    )
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    rect = fitz.Rect(0, 0, width, height)
    page.insert_image(rect, filename=str(img_path))
    pdf_path = tmp_path / "noise.pdf"
    doc.save(pdf_path)
    doc.close()

    base_dir = tmp_path / "base"
    limited_dir = tmp_path / "limited"
    base = pdf_to_images(str(pdf_path), image_format=fmt, out_dir=str(base_dir))[0]
    base_size = Path(base).stat().st_size
    base_img = Image.open(base)
    limit_mb = base_size * 2 / (1024 * 1024)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        limited = pdf_to_images(
            str(pdf_path),
            image_format=fmt,
            out_dir=str(limited_dir),
            max_size_mb=limit_mb,
        )[0]
    assert not w
    limited_size = Path(limited).stat().st_size
    limited_img = Image.open(limited)
    assert limited_size <= limit_mb * 1024 * 1024
    assert limited_size <= base_size
    assert limited_img.size == base_img.size
