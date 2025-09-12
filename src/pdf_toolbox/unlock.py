"""Remove restrictions from password-protected PDFs."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from threading import Event

import fitz  # type: ignore

from pdf_toolbox.actions import action
from pdf_toolbox.utils import (
    open_pdf,
    raise_if_cancelled,
    sane_output_dir,
    save_pdf,
)

logger = logging.getLogger(__name__)


@action(category="PDF")
def unlock_pdf(
    input_pdf: str,
    password: str | None = None,
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> str:
    """Remove password protection from a PDF."""
    raise_if_cancelled(cancel)  # pragma: no cover
    logger.info("Unlocking %s", input_pdf)
    doc = open_pdf(input_pdf)
    if doc.needs_pass and not doc.authenticate(password or ""):
        raise ValueError("Invalid password")
    out_path = sane_output_dir(input_pdf, out_dir) / (
        f"{Path(input_pdf).stem}_unlocked.pdf"
    )
    raise_if_cancelled(cancel, doc)  # pragma: no cover
    save_pdf(
        doc,
        out_path,
        note=" | unlocked",
        encryption=fitz.PDF_ENCRYPT_NONE,
    )
    logger.info("Unlocked PDF written to %s", out_path)
    return str(out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unlock PDF")
    parser.add_argument("input_pdf")
    parser.add_argument("--password")
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    unlock_pdf(args.input_pdf, args.password, args.out_dir)
