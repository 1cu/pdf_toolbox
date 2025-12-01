"""Utilities for running OCR on PDF-embedded images and exporting results.

This module provides the ``extract_handwritten_notes`` action, which scans a
PDF for embedded images, optionally preprocesses them, applies Tesseract OCR
with configurable languages and executables, and returns page-level text along
with Markdown/plain-text exports.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from threading import Event
from typing import Protocol, cast

import fitz
from PIL import Image, ImageEnhance, ImageOps

from pdf_toolbox import config
from pdf_toolbox.actions import action
from pdf_toolbox.i18n import tr
from pdf_toolbox.image_utils import apply_unsharp_mask
from pdf_toolbox.utils import (
    logger,
    open_pdf,
    parse_page_spec,
    raise_if_cancelled,
    sane_output_dir,
)

TESSERACT_NOT_AVAILABLE_MSG = (
    "Tesseract is not available or language data could not be enumerated; "
    "install tesseract-ocr with the desired languages."
)
TESSERACT_LANG_MISSING_MSG = (
    "Tesseract language data for '{lang}' is not installed. Install the matching "
    "tesseract-ocr language package and retry."
)
TESSERACT_CMD_NOT_FOUND_MSG = (
    "Tesseract executable not found at '{path}'. Install tesseract-ocr or provide a valid path."
)


class _PytesseractInner(Protocol):
    tesseract_cmd: str


class _PytesseractModule(Protocol):
    """Subset of pytesseract used by this module."""

    TesseractNotFoundError: type[Exception]
    TesseractError: type[Exception]
    pytesseract: _PytesseractInner

    def image_to_string(self, image: Image.Image, *, lang: str) -> str: ...

    def get_languages(self, *, config: str = "") -> list[str]: ...


@dataclass(slots=True)
class OcrExtractionResult:
    """Result of running OCR across embedded images."""

    markdown_path: str
    text_path: str | None
    page_text: list[str]


@action(category="PDF")
def extract_handwritten_notes(
    input_pdf: str,
    output_txt: str | None = None,
    *,
    preprocess: bool = False,
    lang: str = "deu",
    tesseract_cmd: str | None = None,
    remember_tesseract_cmd: bool = False,
    pages: str | None = None,
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> OcrExtractionResult:
    """Extract embedded images, run OCR, and export the text per page.

    Args:
        input_pdf: Path to the PDF containing handwritten notes.
        output_txt: Optional path for a plain text export. When ``None`` only the
            Markdown file is written.
        preprocess: Apply a simple preprocessing pipeline (grayscale, contrast,
            sharpening) before OCR when ``True``.
        lang: Language code passed to the OCR engine. Defaults to ``"deu"`` for
            German.
        tesseract_cmd: Optional path to the Tesseract executable when it is not
            available on the default ``PATH``. When omitted a previously stored
            value from the application configuration is used when present.
        remember_tesseract_cmd: When ``True`` the provided Tesseract path is
            saved to the application config and reused automatically in future
            runs when ``tesseract_cmd`` is omitted.
        pages: Optional page specification (e.g. ``"1,3-4"``) limiting the OCR
            pass.
        out_dir: Optional directory for generated files. Defaults to the PDF
            location.
        cancel: Optional cancellation event.

    Returns:
        :class:`OcrExtractionResult` with output paths and collected page text.
    """
    logger.info("Running OCR on embedded images in %s", input_pdf)
    effective_tesseract_cmd = _resolve_tesseract_cmd(tesseract_cmd)
    _ensure_ocr_language_available(lang, effective_tesseract_cmd)
    output_dir = sane_output_dir(input_pdf, out_dir)
    markdown_path = output_dir / f"{Path(input_pdf).stem}_ocr.md"
    txt_path = output_dir / output_txt if output_txt else None

    with open_pdf(input_pdf) as doc:
        page_numbers = parse_page_spec(pages, doc.page_count)
        collected: list[str] = []
        for page_number in page_numbers:
            raise_if_cancelled(cancel, doc)
            page = doc.load_page(page_number - 1)
            page_text = _extract_page_text(
                doc,
                page,
                preprocess=preprocess,
                lang=lang,
                tesseract_cmd=effective_tesseract_cmd,
            )
            collected.append(page_text)
        raise_if_cancelled(cancel, doc)

    if tesseract_cmd is not None and remember_tesseract_cmd:
        _remember_tesseract_cmd(tesseract_cmd)

    _write_markdown(markdown_path, Path(input_pdf).name, page_numbers, collected)
    if txt_path is not None:
        _write_plain_text(txt_path, page_numbers, collected)

    logger.info("OCR results written to %s", markdown_path)
    return OcrExtractionResult(
        markdown_path=str(markdown_path),
        text_path=str(txt_path) if txt_path is not None else None,
        page_text=collected,
    )


def _extract_page_text(
    doc: fitz.Document,
    page: fitz.Page,
    *,
    preprocess: bool,
    lang: str,
    tesseract_cmd: str | None,
) -> str:
    seen_xrefs: set[int] = set()
    extracted: list[str] = []
    for image in page.get_images(full=True):
        xref = image[0]
        if xref in seen_xrefs:
            continue
        seen_xrefs.add(xref)
        info = doc.extract_image(xref)  # type: ignore[attr-defined]  # pdf-toolbox: pymupdf stubs lack extract_image | issue:-
        pil_image = Image.open(io.BytesIO(info["image"]))
        text = _run_ocr_on_image(
            pil_image, preprocess=preprocess, lang=lang, tesseract_cmd=tesseract_cmd
        )
        extracted.append(text.strip())
    return "\n\n".join(filter(None, extracted)).strip()


def _run_ocr_on_image(
    image: Image.Image, *, preprocess: bool, lang: str, tesseract_cmd: str | None
) -> str:
    prepared = image.convert("RGB")
    if preprocess:
        prepared = ImageOps.grayscale(prepared)
        prepared = ImageEnhance.Contrast(prepared).enhance(1.4)
        prepared = apply_unsharp_mask(prepared, radius=0.8, amount=0.7, threshold=2)
    return _run_ocr(prepared, lang=lang, tesseract_cmd=tesseract_cmd).strip()


def _run_ocr(image: Image.Image, *, lang: str, tesseract_cmd: str | None = None) -> str:
    import pytesseract

    module = cast(_PytesseractModule, pytesseract)
    _apply_tesseract_cmd(module, tesseract_cmd)
    return module.image_to_string(image, lang=lang)


@cache
def _ensure_ocr_language_available(lang: str, tesseract_cmd: str | None) -> None:
    """Validate that Tesseract has the requested language data installed."""
    import pytesseract

    module = cast(_PytesseractModule, pytesseract)
    _apply_tesseract_cmd(module, tesseract_cmd)
    try:
        available_languages = set(module.get_languages(config=""))
    except (
        module.TesseractNotFoundError,
        module.TesseractError,
    ) as error:
        raise RuntimeError(TESSERACT_NOT_AVAILABLE_MSG) from error

    for component in (part for part in lang.split("+") if part):
        if component not in available_languages:
            raise RuntimeError(TESSERACT_LANG_MISSING_MSG.format(lang=component))


def _apply_tesseract_cmd(pytesseract: _PytesseractModule, tesseract_cmd: str | None) -> None:
    """Set a custom Tesseract executable if provided and ensure it exists."""
    if tesseract_cmd is None:
        return

    command_path = Path(tesseract_cmd).expanduser()
    if not command_path.exists():
        raise RuntimeError(TESSERACT_CMD_NOT_FOUND_MSG.format(path=command_path))

    pytesseract.pytesseract.tesseract_cmd = str(command_path)


def _resolve_tesseract_cmd(tesseract_cmd: str | None) -> str | None:
    """Return the provided command or a persisted configuration value."""
    if tesseract_cmd:
        return tesseract_cmd
    return config.get_tesseract_cmd()


def _remember_tesseract_cmd(tesseract_cmd: str) -> None:
    """Persist the Tesseract path for future OCR runs."""
    config.remember_tesseract_cmd(tesseract_cmd)


def _write_markdown(
    output_path: Path,
    pdf_name: str,
    page_numbers: list[int],
    page_text: list[str],
) -> None:
    lines = [f'# {tr("ocr.results_for", name=pdf_name)}', ""]
    for page_number, text in zip(page_numbers, page_text, strict=True):
        lines.append(f'## {tr("ocr.page", number=page_number)}')
        lines.append(text or tr("ocr.no_text_detected"))
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _write_plain_text(output_path: Path, page_numbers: list[int], page_text: list[str]) -> None:
    lines = []
    for page_number, text in zip(page_numbers, page_text, strict=True):
        lines.append(f'{tr("pdf_toolbox.ocr.page_label")} {page_number}:')
        if text:
            lines.append(text)
        lines.append("")
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


__all__ = ["OcrExtractionResult", "extract_handwritten_notes"]
