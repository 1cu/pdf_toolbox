import pytest

from pdf_toolbox.pptx import pptx_to_images_via_powerpoint


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "TIFF"])
def test_pptx_to_images_requires_win32(tmp_path, fmt):
    dummy = tmp_path / "sample.pptx"
    dummy.write_bytes(b"")
    with pytest.raises(RuntimeError):
        pptx_to_images_via_powerpoint(str(dummy), image_format=fmt)
