from pathlib import Path

import pytest
from pptx import Presentation

from pdf_toolbox.pdf_pptx import pptx_to_images


def test_pptx_to_images_invalid_format(tmp_path):
    pptx_path = tmp_path / "dummy.pptx"
    Presentation().save(pptx_path)
    with pytest.raises(ValueError):
        pptx_to_images(str(pptx_path), image_format="BMP")


@pytest.mark.parametrize("fmt", ["PNG", "WEBP", "SVG"])
def test_pptx_to_images_converts(tmp_path, fmt):
    pptx_path = tmp_path / "sample.pptx"
    prs = Presentation()
    prs.slides.add_slide(prs.slide_layouts[5])
    prs.save(pptx_path)

    out_dir = tmp_path / "out"
    images = pptx_to_images(
        str(pptx_path), image_format=fmt, slides="1", out_dir=str(out_dir)
    )
    assert len(images) == 1
    out_path = Path(images[0])
    assert out_path.is_file()
    assert out_path.suffix == f".{fmt.lower()}"
