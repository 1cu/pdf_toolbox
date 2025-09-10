from __future__ import annotations

import argparse
from pathlib import Path
from threading import Event

import fitz  # type: ignore

from .actions import action
from .utils import sane_output_dir, update_metadata


@action(category="PDF")
def unlock_pdf(
    input_pdf: str,
    password: str | None = None,
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> str:
    """Entferne den Kennwortschutz eines PDFs."""
    if cancel and cancel.is_set():  # pragma: no cover
        raise RuntimeError("cancelled")  # pragma: no cover
    doc = fitz.open(input_pdf)
    if doc.needs_pass and not doc.authenticate(password or ""):
        raise ValueError("Invalid password")
    update_metadata(doc, note=" | unlocked")
    out_path = sane_output_dir(input_pdf, out_dir) / (
        f"{Path(input_pdf).stem}_unlocked.pdf"
    )
    if cancel and cancel.is_set():  # pragma: no cover
        doc.close()
        raise RuntimeError("cancelled")  # pragma: no cover
    doc.save(out_path, encryption=fitz.PDF_ENCRYPT_NONE)
    doc.close()
    return str(out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unlock PDF")
    parser.add_argument("input_pdf")
    parser.add_argument("--password")
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    unlock_pdf(args.input_pdf, args.password, args.out_dir)
