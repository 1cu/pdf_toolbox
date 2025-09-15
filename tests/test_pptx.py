"""Tests for PPTX actions."""

from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path

import pytest
from PIL import Image
from pptx import Presentation
from pptx.util import Inches

from pdf_toolbox.actions.pptx import (
    extract_pptx_images,
    pptx_properties,
    pptx_to_images,
    pptx_to_pdf,
    reorder_pptx,
)
from pdf_toolbox.renderers.pptx import BasePptxRenderer, get_pptx_renderer


@pytest.fixture
def pptx_with_images(tmp_path) -> str:
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    img1 = Image.new("RGB", (10, 10), color=(255, 0, 0))
    img1_path = tmp_path / "img1.png"
    img1.save(img1_path)
    slide.shapes.add_picture(str(img1_path), Inches(1), Inches(1))
    img2 = Image.new("RGB", (10, 10), color=(0, 255, 0))
    img2_path = tmp_path / "img2.jpeg"
    img2.save(img2_path)
    slide.shapes.add_picture(str(img2_path), Inches(2), Inches(1))
    path = tmp_path / "images.pptx"
    prs.save(path)
    return str(path)


@pytest.fixture
def simple_pptx(tmp_path) -> str:
    prs = Presentation()
    for idx in range(5):
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = f"Slide {idx + 1}"
    path = tmp_path / "simple.pptx"
    prs.save(path)
    return str(path)


def test_extract_pptx_images(pptx_with_images, tmp_path):
    target = tmp_path / "out"
    out_dir = extract_pptx_images(pptx_with_images, out_dir=str(target))
    files = sorted(Path(out_dir).iterdir())
    exts = {p.suffix for p in files}
    assert exts == {".png", ".jpg"}


def test_extract_pptx_images_default_dir(pptx_with_images):
    out_dir = extract_pptx_images(pptx_with_images)
    assert Path(out_dir).exists()


def test_pptx_properties(tmp_path):
    prs = Presentation()
    prs.core_properties.author = "Tester"
    prs.core_properties.title = "Demo"
    path = tmp_path / "props.pptx"
    prs.save(path)
    json_path = pptx_properties(str(path))
    data = json.loads(Path(json_path).read_text())
    assert data["author"] == "Tester"
    assert data["title"] == "Demo"


def test_reorder_pptx(simple_pptx, tmp_path):
    out = reorder_pptx(simple_pptx, "3,1,2,5,4", output_path=str(tmp_path / "out.pptx"))
    prs = Presentation(out)
    titles = [s.shapes.title.text for s in prs.slides]
    assert titles == ["Slide 3", "Slide 1", "Slide 2", "Slide 5", "Slide 4"]


def test_reorder_pptx_default_path(simple_pptx):
    out = reorder_pptx(simple_pptx, "2,1")
    assert Path(out).exists()


def test_reorder_pptx_range_and_invalid(simple_pptx):
    out = reorder_pptx(simple_pptx, "1-2")
    assert Path(out).exists()
    out_all = reorder_pptx(simple_pptx, "")
    assert Path(out_all).exists()
    out_gap = reorder_pptx(simple_pptx, "1,,2")
    assert Path(out_gap).exists()
    with pytest.raises(ValueError, match="out of range"):
        reorder_pptx(simple_pptx, "0")
    with pytest.raises(ValueError, match="invalid range"):
        reorder_pptx(simple_pptx, "3-2")


def test_rendering_actions_raise(simple_pptx):
    with pytest.raises(NotImplementedError, match="Rendering PPTX"):
        pptx_to_images(simple_pptx)
    with pytest.raises(NotImplementedError, match="Rendering PPTX"):
        pptx_to_pdf(simple_pptx)


def test_renderer_env(monkeypatch):
    class DummyRenderer(BasePptxRenderer):
        def to_images(
            self,
            _input_pptx: str,
            out_dir: str | None = None,
            max_size_mb: float | None = None,
            img_format: str = "jpeg",
            width: int | None = None,
            height: int | None = None,
        ) -> str:
            del out_dir, max_size_mb, img_format, width, height
            return "ok"

        def to_pdf(
            self,
            _input_pptx: str,
            output_path: str | None = None,
            notes: bool = False,
            handout: bool = False,
            range_spec: str | None = None,
        ) -> str:
            del output_path, notes, handout, range_spec
            return "ok.pdf"

    class EP:
        name = "dummy"

        def load(self):
            return DummyRenderer

    monkeypatch.setenv("PDF_TOOLBOX_PPTX_RENDERER", "dummy")
    monkeypatch.setattr(
        importlib.metadata,
        "entry_points",
        lambda group: [EP()] if group == "pdf_toolbox.pptx_renderers" else [],
    )
    renderer = get_pptx_renderer()
    assert isinstance(renderer, DummyRenderer)
    assert pptx_to_images(simple_pptx) == "ok"
    assert pptx_to_pdf(simple_pptx) == "ok.pdf"
