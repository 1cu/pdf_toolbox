import sys

import pytest

from pdf_toolbox.pptx import _pptx_to_images_via_powerpoint, pptx_to_images


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "TIFF", "SVG"])
@pytest.mark.skipif(sys.platform == "win32", reason="requires non-Windows")
def test_pptx_to_images_requires_win32(tmp_path, fmt):
    dummy = tmp_path / "sample.pptx"
    dummy.write_bytes(b"")
    with pytest.raises(RuntimeError):
        pptx_to_images(str(dummy), image_format=fmt)


def test_pptx_to_images_invalid_format():
    with pytest.raises(ValueError):
        _pptx_to_images_via_powerpoint("dummy.pptx", image_format="BMP")
