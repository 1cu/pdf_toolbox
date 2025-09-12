import json
import sys
import types

import fitz  # type: ignore
import pytest
from PIL import Image

from pdf_toolbox import utils

# Provide a lightweight stub for aspose.slides if the real library is absent.
try:  # pragma: no cover - testing stub
    import aspose.slides  # type: ignore  # noqa: F401
except Exception:  # pragma: no cover
    slides_mod = types.ModuleType("aspose.slides")

    class Presentation:
        """Stub presentation used for tests."""

        def __init__(self, _path: str) -> None:  # pragma: no cover - stub
            """Store the given path."""
            self.path = _path

        def __enter__(self):  # pragma: no cover - stub  # noqa: D105
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - stub
            """Support context manager protocol."""
            return

        def save(self, out_path: str, fmt) -> None:  # pragma: no cover - stub
            """Write a minimal PDF to ``out_path``."""
            doc = fitz.open()
            doc.new_page()
            doc.save(out_path)
            doc.close()

    slides_mod.Presentation = Presentation  # type: ignore[attr-defined]
    export_mod = types.ModuleType("aspose.slides.export")

    class SaveFormat:  # pragma: no cover - stub
        """Stub container for save format constants."""

        PDF = object()

    export_mod.SaveFormat = SaveFormat  # type: ignore[attr-defined]
    aspose_pkg = types.ModuleType("aspose")
    aspose_pkg.slides = slides_mod  # type: ignore[attr-defined]
    sys.modules["aspose"] = aspose_pkg
    sys.modules["aspose.slides"] = slides_mod
    sys.modules["aspose.slides.export"] = export_mod


@pytest.fixture
def sample_pdf(tmp_path):
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    pdf_path = tmp_path / "sample.pdf"
    doc.save(pdf_path)
    doc.close()
    return str(pdf_path)


@pytest.fixture
def pdf_with_image(tmp_path):
    img_path = tmp_path / "img.png"
    Image.new("RGB", (10, 10), color=(255, 0, 0)).save(img_path)
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(0, 0, 10, 10)
    page.insert_image(rect, filename=str(img_path))
    pdf_path = tmp_path / "with_image.pdf"
    doc.save(pdf_path)
    doc.close()
    return str(pdf_path)


@pytest.fixture(autouse=True)
def author_config(tmp_path, monkeypatch):
    config = tmp_path / "pdf_toolbox_config.json"
    config.write_text(json.dumps({"author": "Tester", "email": "tester@example.com"}))
    monkeypatch.setattr(utils, "CONFIG_FILE", config)
    yield
