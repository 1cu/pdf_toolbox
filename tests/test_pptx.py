import sys
from pathlib import Path
import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="requires Windows and PowerPoint")

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from pdf_toolbox.pptx import pptx_to_jpegs_via_powerpoint


def test_pptx_to_jpegs_via_powerpoint_placeholder():
    assert callable(pptx_to_jpegs_via_powerpoint)
