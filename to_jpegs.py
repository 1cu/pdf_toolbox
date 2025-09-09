from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import fitz  # type: ignore
from PIL import Image

from common_utils import sane_output_dir


def pdf_to_jpegs(
    input_pdf: str,
    start_page: int | None = None,
    end_page: int | None = None,
    quality: int = 95,
    out_dir: str | None = None,
) -> List[str]:
    doc = fitz.open(input_pdf)
    start = (start_page - 1) if start_page else 0
    end = (end_page) if end_page else doc.page_count
    outputs: List[str] = []
    out_base = sane_output_dir(input_pdf, out_dir)
    for page_no in range(start, end):
        page = doc.load_page(page_no)
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        out_path = out_base / f"{Path(input_pdf).stem}_Seite_{page_no + 1}.jpg"
        img.save(out_path, format="JPEG", quality=quality)
        outputs.append(str(out_path))
    return outputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF to JPEG")
    parser.add_argument("input_pdf")
    parser.add_argument("--start", type=int)
    parser.add_argument("--end", type=int)
    parser.add_argument("--quality", type=int, default=95)
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    pdf_to_jpegs(args.input_pdf, args.start, args.end, args.quality, args.out_dir)
