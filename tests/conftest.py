import json
import fitz
from PIL import Image
import pytest

import pdf_toolbox.utils as utils


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
