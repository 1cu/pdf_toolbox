from pathlib import Path

import pytest
from pptx import Presentation

from pdf_toolbox import pdf_pptx
from pdf_toolbox.pdf_pptx import pptx_to_images


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "TIFF", "SVG", "WEBP"])
def test_pptx_to_images_requires_aspose(tmp_path, fmt, monkeypatch):
    pptx_path = tmp_path / "dummy.pptx"
    Presentation().save(pptx_path)
    monkeypatch.setattr(pdf_pptx, "aspose_slides", None)
    with pytest.raises(RuntimeError):
        pptx_to_images(str(pptx_path), image_format=fmt)


def test_pptx_to_images_invalid_format(tmp_path):
    pptx_path = tmp_path / "dummy.pptx"
    Presentation().save(pptx_path)
    with pytest.raises(ValueError):
        pptx_to_images(str(pptx_path), image_format="BMP")


@pytest.mark.parametrize("fmt", ["PNG", "WEBP", "SVG"])
def test_pptx_to_images_converts(tmp_path, monkeypatch, sample_pdf, fmt):
    pptx_path = tmp_path / "sample.pptx"
    prs = Presentation()
    prs.slides.add_slide(prs.slide_layouts[5])
    prs.save(pptx_path)

    class FakePresentation:
        def __init__(self, path: str) -> None:
            self.path = path

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def save(self, out_path: str, fmt) -> None:
            Path(out_path).write_bytes(Path(sample_pdf).read_bytes())

    class FakeSaveFormat:
        PDF = object()

    monkeypatch.setattr(
        pdf_pptx, "aspose_slides", type("mod", (), {"Presentation": FakePresentation})
    )
    monkeypatch.setattr(pdf_pptx, "SaveFormat", FakeSaveFormat)

    out_dir = tmp_path / "out"
    images = pptx_to_images(
        str(pptx_path), image_format=fmt, slides="1", out_dir=str(out_dir)
    )
    assert len(images) == 1
    out_path = Path(images[0])
    assert out_path.is_file()
    assert out_path.suffix == f".{fmt.lower()}"
