from __future__ import annotations

import argparse
from pathlib import Path

import fitz  # type: ignore

from common_utils import sane_output_dir, update_metadata


def repair_pdf(input_pdf: str, out_dir: str | None = None) -> str:
    doc = fitz.open(input_pdf)
    update_metadata(doc, note=" | repaired")
    out_path = sane_output_dir(input_pdf, out_dir) / (
        f"{Path(input_pdf).stem}_repaired.pdf"
    )
    doc.save(out_path, clean=True, deflate=True, garbage=4)
    doc.close()
    return str(out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Repair PDF")
    parser.add_argument("input_pdf")
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    repair_pdf(args.input_pdf, args.out_dir)
