"""Remove restrictions from password-protected PDFs."""

from __future__ import annotations

from pathlib import Path
from threading import Event

import fitz  # type: ignore  # pdf-toolbox: PyMuPDF lacks type hints | issue:-

from pdf_toolbox.actions import action
from pdf_toolbox.utils import (
    logger,
    open_pdf,
    raise_if_cancelled,
    sane_output_dir,
    save_pdf,
)

ERR_INVALID_PW = "Invalid password"


@action(category="PDF")
def unlock_pdf(
    input_pdf: str,
    password: str | None = None,
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> str:
    """Remove password protection from a PDF."""
    raise_if_cancelled(cancel)
    logger.info("Unlocking %s", input_pdf)
    doc = open_pdf(input_pdf)
    if doc.needs_pass and not doc.authenticate(password or ""):
        raise ValueError(ERR_INVALID_PW)
    out_path = sane_output_dir(input_pdf, out_dir) / (
        f"{Path(input_pdf).stem}_unlocked.pdf"
    )
    raise_if_cancelled(cancel, doc)
    save_pdf(
        doc,
        out_path,
        note=" | unlocked",
        encryption=fitz.PDF_ENCRYPT_NONE,
    )
    logger.info("Unlocked PDF written to %s", out_path)
    return str(out_path)
