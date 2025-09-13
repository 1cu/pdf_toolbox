import math
import warnings
from pathlib import Path

import pytest
from PIL import Image

from pdf_toolbox.images import DPI_PRESETS, pdf_to_images


def test_pdf_to_images_returns_paths(sample_pdf, tmp_path):
    outputs = pdf_to_images(sample_pdf, dpi="Low (72 dpi)", out_dir=str(tmp_path))
    assert len(outputs) == 3
    for output_path in outputs:
        assert Path(output_path).exists()
        assert isinstance(output_path, str)


def test_pdf_to_images_requires_width_height(sample_pdf, tmp_path):
    with pytest.raises(ValueError, match="width and height must be provided together"):
        pdf_to_images(sample_pdf, width=100, out_dir=str(tmp_path))


def test_pdf_to_images_svg(sample_pdf, tmp_path):
    outputs = pdf_to_images(
        sample_pdf, image_format="SVG", dpi="Low (72 dpi)", out_dir=str(tmp_path)
    )
    assert len(outputs) == 3
    for output_path in outputs:
        assert output_path.endswith(".svg")
        assert Path(output_path).exists()


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
    for output_path in outputs:
        assert Path(output_path).exists()


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


def test_pdf_to_images_dimensions(sample_pdf, tmp_path):
    outputs = pdf_to_images(
        sample_pdf,
        width=413,
        height=585,
        image_format="PNG",
        out_dir=str(tmp_path),
    )
    assert len(outputs) == 3
    img = Image.open(outputs[0])
    assert img.size == (414, 585)


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
    for output_path in outputs:
        path_obj = Path(output_path)
        assert path_obj.exists()
        assert path_obj.suffix.lower() == ".png"


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
    base_img = Image.open(base)
    limited_img = Image.open(limited)
    assert limited_size <= limit_mb * 1024 * 1024
    assert limited_size < base_size
    assert limited_img.size == base_img.size


def test_pdf_to_images_numeric_quality(tmp_path):
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

    out = pdf_to_images(
        str(pdf_path), image_format="JPEG", quality=80, out_dir=str(tmp_path)
    )[0]
    assert Path(out).exists()


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


@pytest.mark.parametrize("fmt", ["PNG"])
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
    limit_mb = 0.01
    with pytest.warns(UserWarning, match="scaled down"):
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


def test_pdf_to_images_png_max_size_too_small_raises(tmp_path):
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
            image_format="PNG",
            out_dir=str(tmp_path),
            max_size_mb=1e-6,
        )


@pytest.mark.parametrize("fmt", ["PNG"])
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
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        limited = pdf_to_images(
            str(pdf_path),
            image_format=fmt,
            out_dir=str(limited_dir),
            max_size_mb=limit_mb,
        )[0]
    assert not records
    limited_size = Path(limited).stat().st_size
    limited_img = Image.open(limited)
    assert limited_size <= limit_mb * 1024 * 1024
    assert limited_size <= base_size
    assert limited_img.size == base_img.size


def test_pdf_to_images_tiff_max_size(tmp_path):
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

    base = pdf_to_images(str(pdf_path), image_format="TIFF", out_dir=str(tmp_path))[0]
    base_size = Path(base).stat().st_size
    limit_mb = base_size * 2 / (1024 * 1024)
    limited = pdf_to_images(
        str(pdf_path),
        image_format="TIFF",
        out_dir=str(tmp_path),
        max_size_mb=limit_mb,
    )[0]
    limited_size = Path(limited).stat().st_size
    assert limited_size <= limit_mb * 1024 * 1024
