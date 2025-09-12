from pathlib import Path

import pytest
from pptx import Presentation

from pdf_toolbox.pptx import pptx_to_images


@pytest.fixture
def sample_pptx(tmp_path):
    prs = Presentation()
    blank = prs.slide_layouts[6]
    prs.slides.add_slide(blank)
    prs.slides.add_slide(blank)
    path = tmp_path / "sample.pptx"
    prs.save(path)
    return str(path)


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "TIFF", "SVG"])
def test_pptx_to_images_creates_files(sample_pptx, tmp_path, fmt):
    outputs = pptx_to_images(sample_pptx, image_format=fmt, out_dir=str(tmp_path))
    assert len(outputs) == 2
    for out in outputs:
        assert out.endswith(f".{fmt.lower()}")
        assert Path(out).exists()


def test_pptx_to_images_invalid_format(sample_pptx):
    with pytest.raises(ValueError, match="Unsupported image format"):
        pptx_to_images(sample_pptx, image_format="BMP")
