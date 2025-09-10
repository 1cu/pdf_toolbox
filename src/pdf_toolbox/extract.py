from __future__ import annotations

import argparse
from pathlib import Path
from typing import List
from threading import Event

import fitz  # type: ignore

from .actions import action
from .utils import sane_output_dir, update_metadata, parse_page_spec


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

    with fitz.open(input_pdf) as doc:
        page_numbers = parse_page_spec(pages, doc.page_count)
        new_doc = fitz.open()
        for page in page_numbers:
            if cancel and cancel.is_set():  # pragma: no cover
                raise RuntimeError("cancelled")  # pragma: no cover
            new_doc.insert_pdf(doc, from_page=page - 1, to_page=page - 1)
        update_metadata(new_doc, note=" | extract_range")
        safe_spec = pages.replace(",", "_").replace("-", "_").strip("_")
        out_path = sane_output_dir(input_pdf, out_dir) / (
            f"{Path(input_pdf).stem}_Auszug_{safe_spec}.pdf"
        )
        if cancel and cancel.is_set():  # pragma: no cover
            raise RuntimeError("cancelled")  # pragma: no cover
        new_doc.save(out_path)
        new_doc.close()
    return str(out_path)


@action(category="PDF")
def split_pdf(
    input_pdf: str,
    pages_per_file: int,
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> List[str]:
    """Split a PDF into parts of ``pages_per_file`` pages."""

    outputs: List[str] = []
    with fitz.open(input_pdf) as doc:
        for start in range(0, doc.page_count, pages_per_file):
            if cancel and cancel.is_set():  # pragma: no cover
                raise RuntimeError("cancelled")  # pragma: no cover
            end = min(start + pages_per_file, doc.page_count)
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=start, to_page=end - 1)
            update_metadata(new_doc, note=" | split_pdf")
            out_path = sane_output_dir(input_pdf, out_dir) / (
                f"{Path(input_pdf).stem}_Split_{start + 1}_{end}.pdf"
            )
            if cancel and cancel.is_set():  # pragma: no cover
                raise RuntimeError("cancelled")  # pragma: no cover
            new_doc.save(out_path)
            new_doc.close()
            outputs.append(str(out_path))
    return outputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF page extraction")
    parser.add_argument("input_pdf")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ex = sub.add_parser("extract")
    p_ex.add_argument("pages")
    p_ex.add_argument("--out-dir")

    p_split = sub.add_parser("split")
    p_split.add_argument("pages", type=int)
    p_split.add_argument("--out-dir")

    args = parser.parse_args()
    if args.cmd == "extract":
        extract_range(args.input_pdf, args.pages, args.out_dir)
    else:
        split_pdf(args.input_pdf, args.pages, args.out_dir)
