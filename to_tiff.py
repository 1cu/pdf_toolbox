from __future__ import annotations

import argparse
from pathlib import Path

import fitz  # type: ignore
from PIL import Image

from common_utils import sane_output_dir


def pdf_to_tiff(input_pdf: str, out_dir: str | None = None) -> str:
    doc = fitz.open(input_pdf)
    images = []
    for page in doc:
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    out_path = sane_output_dir(input_pdf, out_dir) / f"{Path(input_pdf).stem}_tiff.tiff"
    if images:
        images[0].save(out_path, save_all=True, append_images=images[1:], compression="tiff_deflate")
    return str(out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF to TIFF")
    parser.add_argument("input_pdf")
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    pdf_to_tiff(args.input_pdf, args.out_dir)
