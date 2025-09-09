import pytest

from pdf_toolbox.pptx import (
    pptx_to_jpegs_via_powerpoint,
    pptx_to_pngs_via_powerpoint,
    pptx_to_tiffs_via_powerpoint,
)


def test_pptx_to_images_requires_win32(tmp_path):
    dummy = tmp_path / "sample.pptx"
    dummy.write_bytes(b"")
    with pytest.raises(ModuleNotFoundError):
        pptx_to_jpegs_via_powerpoint(str(dummy))
    with pytest.raises(ModuleNotFoundError):
        pptx_to_pngs_via_powerpoint(str(dummy))
    with pytest.raises(ModuleNotFoundError):
        pptx_to_tiffs_via_powerpoint(str(dummy))
