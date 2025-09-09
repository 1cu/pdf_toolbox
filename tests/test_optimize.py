import fitz
from pdf_toolbox.optimize import optimize_pdf, QUALITY_SETTINGS


def test_pdf_quality_passed_to_doc_save(tmp_path, monkeypatch):
    input_pdf = tmp_path / "input.pdf"
    with fitz.open() as doc:
        doc.new_page()
        doc.save(input_pdf)

    saved = {}
    original_save = fitz.Document.save

    def wrapped_save(self, filename, *args, **kwargs):
        saved.update(kwargs)
        return original_save(self, filename, *args, **kwargs)

    monkeypatch.setattr(fitz.Document, "save", wrapped_save)
    optimize_pdf(str(input_pdf), quality="screen")

    pdf_quality = QUALITY_SETTINGS["screen"]["pdf_quality"]
    expected = max(0, min(9, (100 - pdf_quality) // 10))
    assert saved.get("compression_effort") == expected
