"""PDF page extraction utilities."""

from __future__ import annotations

from pathlib import Path
from threading import Event

import fitz  # type: ignore  # pdf-toolbox: PyMuPDF lacks type hints | issue:-

from pdf_toolbox.actions import action
from pdf_toolbox.utils import (
    logger,
    open_pdf,
    parse_page_spec,
    raise_if_cancelled,
    sane_output_dir,
    update_metadata,
)


@action(category="PDF")
def extract_range(
    input_pdf: str,
    pages: str,
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> str:
    """Extract a range of pages from ``input_pdf``.

    ``pages`` may be a single page (``"5"``), ranges like ``"3-7"`` or
    ``"2-"`` and comma separated combinations such as ``"1,5,6"``. If
    ``pages`` is empty all pages are extracted. Returns the path of the
    created PDF.
    """
    logger.info("Extracting pages '%s' from %s", pages, input_pdf)
    with open_pdf(input_pdf) as doc:
        page_numbers = parse_page_spec(pages, doc.page_count)
        new_doc = fitz.open()
        for page in page_numbers:
            raise_if_cancelled(cancel)
            new_doc.insert_pdf(doc, from_page=page - 1, to_page=page - 1)
        update_metadata(new_doc, note=" | extract_range")
        safe_spec = pages.replace(",", "_").replace("-", "_").strip("_")
        out_path = sane_output_dir(input_pdf, out_dir) / (
            f"{Path(input_pdf).stem}_Extract_{safe_spec}.pdf"
        )
        raise_if_cancelled(cancel)
        new_doc.save(out_path)
        new_doc.close()
    logger.info("Extracted pages written to %s", out_path)
    return str(out_path)


@action(category="PDF")
def split_pdf(
    input_pdf: str,
    pages_per_file: int,
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> list[str]:
    """Split a PDF into parts of ``pages_per_file`` pages."""
    logger.info("Splitting %s into chunks of %d pages", input_pdf, pages_per_file)
    outputs: list[str] = []
    with open_pdf(input_pdf) as doc:
        for start in range(0, doc.page_count, pages_per_file):
            raise_if_cancelled(cancel)
            end = min(start + pages_per_file, doc.page_count)
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=start, to_page=end - 1)
            update_metadata(new_doc, note=" | split_pdf")
            out_path = sane_output_dir(input_pdf, out_dir) / (
                f"{Path(input_pdf).stem}_Split_{start + 1}_{end}.pdf"
            )
            raise_if_cancelled(cancel)
            new_doc.save(out_path)
            new_doc.close()
            logger.info("Created %s", out_path)
            outputs.append(str(out_path))
    return outputs
