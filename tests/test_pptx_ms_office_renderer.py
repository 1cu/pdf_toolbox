import os
import sys
from pathlib import Path

import pytest
from pptx import Presentation

from pdf_toolbox.renderers.ms_office import PptxMsOfficeRenderer

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("win") or not os.getenv("PDF_TOOLBOX_TEST_MS_OFFICE"),
    reason="MS Office Integration nur auf Windows mit PDF_TOOLBOX_TEST_MS_OFFICE=1",
)


def _make_pptx(tmp: Path, slides: int = 1) -> Path:
    prs = Presentation()
    for i in range(slides):
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        box = slide.shapes.add_textbox(100, 100, 300, 50)
        box.text_frame.text = f"Slide {i + 1}"
    file = tmp / "demo.pptx"
    prs.save(str(file))
    return file


def test_to_pdf(tmp_path: Path) -> None:
    src = _make_pptx(tmp_path, slides=3)
    out = tmp_path / "out.pdf"
    got = PptxMsOfficeRenderer().to_pdf(str(src), str(out), range_spec="1-2")
    assert Path(got).exists()


def test_to_images(tmp_path: Path) -> None:
    src = _make_pptx(tmp_path, slides=2)
    out = tmp_path / "img"
    got = PptxMsOfficeRenderer().to_images(
        str(src),
        out_dir=str(out),
        img_format="png",
        width=1920,
        height=1080,
    )
    files = list(Path(got).glob("*.png"))
    assert files, "Kein Bild exportiert"
    assert len(files) == 2
