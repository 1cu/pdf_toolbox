import json
import fitz
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


@pytest.fixture(autouse=True)
def author_config(tmp_path, monkeypatch):
    config = tmp_path / "pdf_toolbox_config.json"
    config.write_text(json.dumps({"author": "Tester", "email": "tester@example.com"}))
    monkeypatch.setattr(utils, "CONFIG_FILE", config)
    yield
