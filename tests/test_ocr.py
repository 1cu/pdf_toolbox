from __future__ import annotations
import io
import sys
from pathlib import Path

import pytest
import fitz
from PIL import Image, ImageDraw, ImageFont

from pdf_toolbox.actions import ocr


def _make_pdf_with_images(tmp_path: Path, pages: int = 2, *, include_image_on_last: bool = True) -> Path:
    doc = fitz.open()
    for index in range(pages):
        page = doc.new_page()
        if include_image_on_last or index < pages - 1:
            image = Image.new("RGB", (200, 80), color="white")
            draw = ImageDraw.Draw(image)
            draw.text((10, 30), f"Page {index + 1}", fill="black", font=ImageFont.load_default())
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            rect = fitz.Rect(50, 50, 250, 170)
            page.insert_image(rect, stream=buf.getvalue())
    pdf_path = tmp_path / "handwritten.pdf"
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def test_extract_handwritten_notes_exports_markdown_and_text(tmp_path, monkeypatch):
    pdf_path = _make_pdf_with_images(tmp_path)
    calls: list[str] = []

    def fake_ocr(image, *, lang: str, tesseract_cmd: str | None = None) -> str:  # type: ignore[override]
        calls.append(image.mode)
        return f"recognized-{len(calls)} ({lang})"

    monkeypatch.setattr(ocr, "_ensure_ocr_language_available", lambda lang, cmd: None)
    monkeypatch.setattr(ocr, "_run_ocr", fake_ocr)

    result = ocr.extract_handwritten_notes(
        str(pdf_path),
        output_txt="notes.txt",
        preprocess=True,
        lang="deu",
        out_dir=str(tmp_path),
    )

    expected_md = tmp_path / "handwritten_ocr.md"
    expected_txt = tmp_path / "notes.txt"

    assert result.markdown_path == str(expected_md)
    assert result.text_path == str(expected_txt)
    assert result.page_text == ["recognized-1 (deu)", "recognized-2 (deu)"]
    assert all(mode == "L" for mode in calls)

    markdown = expected_md.read_text(encoding="utf-8")
    assert "# OCR Ergebnisse für handwritten.pdf" in markdown
    assert "## Seite 1" in markdown and "## Seite 2" in markdown
    assert "recognized-1" in markdown and "recognized-2" in markdown

    text_export = expected_txt.read_text(encoding="utf-8")
    assert "Seite 1" in text_export and "recognized-1" in text_export
    assert text_export.endswith("\n")


def test_extract_handwritten_notes_handles_empty_pages(tmp_path, monkeypatch):
    pdf_path = _make_pdf_with_images(tmp_path, pages=2, include_image_on_last=False)

    def fake_ocr(image, *, lang: str, tesseract_cmd: str | None = None) -> str:  # type: ignore[override]
        return f"image-text-{lang}"

    monkeypatch.setattr(ocr, "_ensure_ocr_language_available", lambda lang, cmd: None)
    monkeypatch.setattr(ocr, "_run_ocr", fake_ocr)

    result = ocr.extract_handwritten_notes(
        str(pdf_path),
        preprocess=False,
        out_dir=str(tmp_path),
    )

    expected_md = tmp_path / "handwritten_ocr.md"
    markdown = expected_md.read_text(encoding="utf-8")

    assert result.markdown_path == str(expected_md)
    assert result.text_path is None
    assert result.page_text == ["image-text-deu", ""]
    assert "## Seite 1" in markdown
    assert "image-text-deu" in markdown
    assert "_Kein Text erkannt._" in markdown


def test_run_ocr_uses_pytesseract(monkeypatch):
    calls: list[tuple[str, str]] = []

    class DummyTesseract:
        @staticmethod
        def image_to_string(image: Image.Image, *, lang: str) -> str:  # type: ignore[override]
            calls.append((image.mode, lang))
            return "dummy"

    monkeypatch.setitem(sys.modules, "pytesseract", DummyTesseract())

    text = ocr._run_ocr(Image.new("RGB", (10, 10)), lang="deu")

    assert text == "dummy"
    assert calls == [("RGB", "deu")]


def test_extract_handwritten_notes_requires_installed_language(tmp_path, monkeypatch):
    pdf_path = _make_pdf_with_images(tmp_path)

    class DummyTesseract:
        TesseractNotFoundError = RuntimeError
        TesseractError = RuntimeError

        @staticmethod
        def get_languages(*, config: str = "") -> list[str]:  # type: ignore[override]
            return ["eng"]

    monkeypatch.setitem(sys.modules, "pytesseract", DummyTesseract())
    ocr._ensure_ocr_language_available.cache_clear()

    with pytest.raises(RuntimeError, match="language data for 'deu' is not installed"):
        ocr.extract_handwritten_notes(str(pdf_path), out_dir=str(tmp_path))


def test_extract_handwritten_notes_allows_custom_tesseract_path(tmp_path, monkeypatch):
    pdf_path = _make_pdf_with_images(tmp_path)

    class DummyTesseract:
        TesseractNotFoundError = RuntimeError
        TesseractError = RuntimeError

        def __init__(self):
            self.pytesseract = self
            self.tesseract_cmd = "default"

        def get_languages(self, *, config: str = "") -> list[str]:  # type: ignore[override]
            return ["deu"]

        def image_to_string(self, image: Image.Image, *, lang: str) -> str:  # type: ignore[override]
            return self.tesseract_cmd

    dummy = DummyTesseract()
    monkeypatch.setitem(sys.modules, "pytesseract", dummy)
    ocr._ensure_ocr_language_available.cache_clear()

    tesseract_bin = tmp_path / "bin" / "tesseract"
    tesseract_bin.parent.mkdir()
    tesseract_bin.write_text("binary")

    result = ocr.extract_handwritten_notes(
        str(pdf_path), out_dir=str(tmp_path), tesseract_cmd=str(tesseract_bin)
    )

    assert dummy.tesseract_cmd == str(tesseract_bin)
    assert result.page_text == [str(tesseract_bin), str(tesseract_bin)]


def test_extract_handwritten_notes_rejects_missing_tesseract_path(tmp_path, monkeypatch):
    pdf_path = _make_pdf_with_images(tmp_path)

    class DummyTesseract:
        TesseractNotFoundError = RuntimeError
        TesseractError = RuntimeError
        pytesseract = None

    monkeypatch.setitem(sys.modules, "pytesseract", DummyTesseract())
    ocr._ensure_ocr_language_available.cache_clear()

    missing_path = tmp_path / "missing" / "tesseract"

    with pytest.raises(RuntimeError, match="Tesseract executable not found"):
        ocr.extract_handwritten_notes(
            str(pdf_path), out_dir=str(tmp_path), tesseract_cmd=str(missing_path)
        )
