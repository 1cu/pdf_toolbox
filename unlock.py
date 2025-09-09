from __future__ import annotations

import argparse
from pathlib import Path

import fitz  # type: ignore

from common_utils import sane_output_dir, update_metadata


def unlock_pdf(
    input_pdf: str,
    password: str | None = None,
    out_dir: str | None = None,
) -> str:
    doc = fitz.open(input_pdf, password=password or "")
    update_metadata(doc, note=" | unlocked")
    out_path = sane_output_dir(input_pdf, out_dir) / (
        f"{Path(input_pdf).stem}_unlocked.pdf"
    )
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
