from __future__ import annotations

import argparse
from pathlib import Path
from threading import Event


from .actions import action
from .utils import open_pdf, raise_if_cancelled, save_pdf, sane_output_dir


@action(category="PDF")
def repair_pdf(
    input_pdf: str, out_dir: str | None = None, cancel: Event | None = None
) -> str:
    """Repair a PDF and clean up inconsistent data."""
    raise_if_cancelled(cancel)  # pragma: no cover
    doc = open_pdf(input_pdf)
    out_path = sane_output_dir(input_pdf, out_dir) / (
        f"{Path(input_pdf).stem}_repaired.pdf"
    )
    raise_if_cancelled(cancel, doc)  # pragma: no cover
    save_pdf(doc, out_path, note=" | repaired", clean=True, deflate=True, garbage=4)
    return str(out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Repair PDF")
    parser.add_argument("input_pdf")
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    repair_pdf(args.input_pdf, args.out_dir)
