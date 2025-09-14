from pathlib import Path

import fitz  # type: ignore
import pytest

from pdf_toolbox.builtin.optimise import QUALITY_SETTINGS, optimise_pdf


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
    optimise_pdf(str(input_pdf), quality="screen")

    pdf_quality = QUALITY_SETTINGS["screen"]["pdf_quality"]
    expected = max(0, min(9, (100 - pdf_quality) // 10))
    assert saved.get("compression_effort") == expected


def test_invalid_quality_raises(sample_pdf):
    with pytest.raises(ValueError, match="unknown quality"):
        optimise_pdf(sample_pdf, quality="unknown")


def test_compress_images(pdf_with_image, tmp_path):
    output, _ = optimise_pdf(
        pdf_with_image, compress_images=True, out_dir=str(tmp_path)
    )
    assert Path(output).exists()


def test_remove_output_on_small_reduction(sample_pdf, tmp_path, monkeypatch):
    monkeypatch.setitem(QUALITY_SETTINGS["default"], "min_reduction", 1.0)
    out, reduction = optimise_pdf(sample_pdf, keep=False, out_dir=str(tmp_path))
    assert out is None
    assert reduction < 1.0


def test_optimise_pdf_internal_path(tmp_path):
    import fitz  # type: ignore

    pdf_path = tmp_path / "in.pdf"
    document = fitz.open()
    document.new_page()
    document.save(pdf_path)
    document.close()
    output, reduction = optimise_pdf(str(pdf_path))
    assert output is not None
    assert reduction <= 1


def test_logs_size_increase(sample_pdf, tmp_path, monkeypatch):
    import logging

    from pdf_toolbox.utils import logger
    from pdf_toolbox.utils import save_pdf as original_save_pdf

    def bigger_save(doc, out_path, *, note=None, **kwargs):
        original_save_pdf(doc, out_path, note=note, **kwargs)
        with Path(out_path).open("ab") as fh:
            fh.write(b"extra")

    monkeypatch.setattr("pdf_toolbox.builtin.optimise.save_pdf", bigger_save)

    class ListHandler(logging.Handler):
        def __init__(self) -> None:  # pragma: no cover - simple container
            super().__init__()
            self.messages: list[str] = []

        def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - simple
            self.messages.append(record.getMessage())

    list_handler = ListHandler()
    logger.addHandler(list_handler)
    try:
        optimise_pdf(sample_pdf, out_dir=str(tmp_path))
    finally:
        logger.removeHandler(list_handler)
    assert any("size increased by" in msg for msg in list_handler.messages)
