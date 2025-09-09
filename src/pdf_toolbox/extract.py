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
    with fitz.open(input_pdf) as doc:
        if start_page < 1 or end_page < start_page or end_page > doc.page_count:
            raise ValueError("Invalid page range")
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=start_page - 1, to_page=end_page - 1)
        update_metadata(new_doc, note=" | extract_range")
        out_path = sane_output_dir(input_pdf, out_dir) / (
            f"{Path(input_pdf).stem}_Auszug_{start_page}_{end_page}.pdf"
        )
        new_doc.save(out_path)
        new_doc.close()
    return str(out_path)


def split_pdf(
    input_pdf: str,
    pages_per_file: int,
    out_dir: str | None = None,
) -> List[str]:
    """Split a PDF into parts of ``pages_per_file`` pages."""

    outputs: List[str] = []
    with fitz.open(input_pdf) as doc:
        for start in range(0, doc.page_count, pages_per_file):
            end = min(start + pages_per_file, doc.page_count)
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=start, to_page=end - 1)
            update_metadata(new_doc, note=" | split_pdf")
            out_path = sane_output_dir(input_pdf, out_dir) / (
                f"{Path(input_pdf).stem}_Split_{start + 1}_{end}.pdf"
            )
            new_doc.save(out_path)
            new_doc.close()
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
