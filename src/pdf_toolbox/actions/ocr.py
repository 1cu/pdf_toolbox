from __future__ import annotations

import io
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Event

import fitz
from PIL import Image, ImageEnhance, ImageOps

from pdf_toolbox.actions import action
from pdf_toolbox.image_utils import apply_unsharp_mask
from pdf_toolbox.utils import (
    logger,
    open_pdf,
    parse_page_spec,
    raise_if_cancelled,
    sane_output_dir,
)


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
            available on the default ``PATH``.
        pages: Optional page specification (e.g. ``"1,3-4"``) limiting the OCR
            pass.
        out_dir: Optional directory for generated files. Defaults to the PDF
            location.
        cancel: Optional cancellation event.

    Returns:
        :class:`OcrExtractionResult` with output paths and collected page text.
    """
    logger.info("Running OCR on embedded images in %s", input_pdf)
    _ensure_ocr_language_available(lang, tesseract_cmd)
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
                tesseract_cmd=tesseract_cmd,
            )
            collected.append(page_text)
        raise_if_cancelled(cancel, doc)

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
        info = doc.extract_image(xref)
        pil_image = Image.open(io.BytesIO(info["image"]))
        text = _run_ocr_on_image(
            pil_image, preprocess=preprocess, lang=lang, tesseract_cmd=tesseract_cmd
        )
        extracted.append(text.strip())
    joined = "\n\n".join(filter(None, extracted)).strip()
    return joined


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

    _apply_tesseract_cmd(pytesseract, tesseract_cmd)
    return pytesseract.image_to_string(image, lang=lang)


@lru_cache(maxsize=None)
def _ensure_ocr_language_available(lang: str, tesseract_cmd: str | None) -> None:
    """Validate that Tesseract has the requested language data installed."""

    import pytesseract

    _apply_tesseract_cmd(pytesseract, tesseract_cmd)
    try:
        available_languages = set(pytesseract.get_languages(config=""))
    except (
        pytesseract.TesseractNotFoundError,
        pytesseract.TesseractError,
    ) as error:
        raise RuntimeError(
            "Tesseract is not available or language data could not be enumerated; "
            "install tesseract-ocr with the desired languages."
        ) from error

    if lang not in available_languages:
        raise RuntimeError(
            f"Tesseract language data for '{lang}' is not installed. "
            "Install the matching tesseract-ocr language package and retry."
        )


def _apply_tesseract_cmd(pytesseract: object, tesseract_cmd: str | None) -> None:
    """Set a custom Tesseract executable if provided and ensure it exists."""

    if tesseract_cmd is None:
        return

    command_path = Path(tesseract_cmd).expanduser()
    if not command_path.exists():
        raise RuntimeError(
            f"Tesseract executable not found at '{command_path}'. "
            "Install tesseract-ocr or provide a valid path."
        )

    pytesseract.pytesseract.tesseract_cmd = str(command_path)


def _write_markdown(
    output_path: Path,
    pdf_name: str,
    page_numbers: list[int],
    page_text: list[str],
) -> None:
    lines = [f"# OCR Ergebnisse für {pdf_name}", ""]
    for page_number, text in zip(page_numbers, page_text, strict=True):
        lines.append(f"## Seite {page_number}")
        lines.append(text or "_Kein Text erkannt._")
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _write_plain_text(
    output_path: Path, page_numbers: list[int], page_text: list[str]
) -> None:
    lines = []
    for page_number, text in zip(page_numbers, page_text, strict=True):
        lines.append(f"Seite {page_number}:")
        if text:
            lines.append(text)
        lines.append("")
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


__all__ = ["OcrExtractionResult", "extract_handwritten_notes"]
