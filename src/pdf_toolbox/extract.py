from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import fitz  # type: ignore

from .utils import sane_output_dir, update_metadata


def extract_range(
    input_pdf: str,
    start_page: int,
    end_page: int,
    out_dir: str | None = None,
) -> str:
    """Extract a range of pages from ``input_pdf``.

    Returns the path of the created PDF.
    """

    doc = fitz.open(input_pdf)
    if start_page < 1:
        raise ValueError(f"start_page must be >= 1, got {start_page}")
    if end_page < start_page:
        raise ValueError(
            f"start_page ({start_page}) must not exceed end_page ({end_page})"
        )
    if end_page > doc.page_count:
        raise ValueError(
            f"end_page ({end_page}) exceeds document page count ({doc.page_count})"
        )

    new_doc = fitz.open()
    new_doc.insert_pdf(doc, from_page=start_page - 1, to_page=end_page - 1)
    update_metadata(new_doc, note=" | extract_range")
    out_path = sane_output_dir(input_pdf, out_dir) / (
        f"{Path(input_pdf).stem}_Auszug_{start_page}_{end_page}.pdf"
    )
    new_doc.save(out_path)
    return str(out_path)


def split_pdf(
    input_pdf: str,
    pages_per_file: int,
    out_dir: str | None = None,
) -> List[str]:
    """Split a PDF into parts of ``pages_per_file`` pages."""

    doc = fitz.open(input_pdf)
    if pages_per_file < 1:
        raise ValueError(f"pages_per_file must be >= 1, got {pages_per_file}")
    if doc.page_count < 1:
        raise ValueError("document has no pages")

    outputs: List[str] = []
    for start in range(0, doc.page_count, pages_per_file):
        end = min(start + pages_per_file, doc.page_count)
        start_page = start + 1
        end_page = end
        if not (1 <= start_page <= end_page <= doc.page_count):
            raise ValueError(
                f"Invalid page range {start_page}-{end_page} for document with {doc.page_count} pages"
            )
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=start_page - 1, to_page=end_page - 1)
        update_metadata(new_doc, note=" | split_pdf")
        out_path = sane_output_dir(input_pdf, out_dir) / (
            f"{Path(input_pdf).stem}_Split_{start_page}_{end_page}.pdf"
        )
        new_doc.save(out_path)
        outputs.append(str(out_path))
    return outputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF page extraction")
    parser.add_argument("input_pdf")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ex = sub.add_parser("extract")
    p_ex.add_argument("start", type=int)
    p_ex.add_argument("end", type=int)
    p_ex.add_argument("--out-dir")

    p_split = sub.add_parser("split")
    p_split.add_argument("pages", type=int)
    p_split.add_argument("--out-dir")

    args = parser.parse_args()
    if args.cmd == "extract":
        extract_range(args.input_pdf, args.start, args.end, args.out_dir)
    else:
        split_pdf(args.input_pdf, args.pages, args.out_dir)
