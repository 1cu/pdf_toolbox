import io
import sys
from pathlib import Path

import fitz
from PIL import Image

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from pdf_toolbox.rasterize import pdf_to_images


def _make_pdf_with_image(tmp_path, image: Image.Image, name: str) -> str:
    doc = fitz.open()
    width, height = image.size
    page = doc.new_page(width=width, height=height)
    rect = fitz.Rect(0, 0, width, height)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    page.insert_image(rect, stream=buf.getvalue())
    pdf_path = tmp_path / name
    doc.save(pdf_path)
    doc.close()
    return str(pdf_path)


import pytest


@pytest.mark.parametrize("fmt", ["PNG", "TIFF"])
def test_pdf_to_images_grayscale(tmp_path, fmt):
    img = Image.new("L", (10, 10), 128)
    pdf_path = _make_pdf_with_image(tmp_path, img, "gray.pdf")
    images = pdf_to_images(pdf_path, dpi=72, image_format=fmt, as_pil=True)
    assert len(images) == 1
    out = images[0]
    assert out.mode in {"L", "RGB"}
    pix = out.getpixel((0, 0))
    if isinstance(pix, tuple):
        assert pix == (128, 128, 128)
    else:
        assert pix == 128


@pytest.mark.parametrize("fmt", ["PNG", "TIFF"])
def test_pdf_to_images_transparent(tmp_path, fmt):
    img = Image.new("RGBA", (10, 10), (255, 0, 0, 128))
    pdf_path = _make_pdf_with_image(tmp_path, img, "transparent.pdf")
    images = pdf_to_images(pdf_path, dpi=72, image_format=fmt, as_pil=True)
    assert len(images) == 1
    out = images[0]
    assert out.mode == "RGBA"
    assert out.getpixel((0, 0)) == (255, 0, 0, 128)
