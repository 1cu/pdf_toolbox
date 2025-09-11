from __future__ import annotations

import argparse
from pathlib import Path
from threading import Event

import fitz  # type: ignore

from .actions import action
from .utils import open_pdf, raise_if_cancelled, save_pdf, sane_output_dir


@action(category="PDF")
def unlock_pdf(
    input_pdf: str,
    password: str | None = None,
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> str:
    """Remove password protection from a PDF."""
    raise_if_cancelled(cancel)  # pragma: no cover
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
    return str(out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unlock PDF")
    parser.add_argument("input_pdf")
    parser.add_argument("--password")
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    unlock_pdf(args.input_pdf, args.password, args.out_dir)
