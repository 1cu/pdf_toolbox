from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, cast

from PIL import Image

from rasterize import pdf_to_images
from common_utils import sane_output_dir


def pdf_to_tiff(
    input_pdf: str,
    dpi: int = 300,
    out_dir: str | None = None,
) -> str:
    images = cast(List[Image.Image], pdf_to_images(input_pdf, dpi=dpi, as_pil=True))
    out_path = sane_output_dir(input_pdf, out_dir) / f"{Path(input_pdf).stem}_tiff.tiff"
    if images:
        images[0].save(
            out_path,
            save_all=True,
            append_images=images[1:],
            compression="tiff_deflate",
        )
    return str(out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF to TIFF")
    parser.add_argument("input_pdf")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    pdf_to_tiff(args.input_pdf, args.dpi, args.out_dir)
