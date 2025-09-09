from __future__ import annotations

import argparse
from typing import List, cast

from .actions import action
from .rasterize import pdf_to_images


@action(category="PDF")
def pdf_to_jpegs(
    input_pdf: str,
    start_page: int | None = None,
    end_page: int | None = None,
    dpi: int = 300,
    quality: int = 95,
    out_dir: str | None = None,
) -> List[str]:
    """Render a PDF to a sequence of JPEG files."""
    return cast(
        List[str],
        pdf_to_images(
            input_pdf,
            start_page=start_page,
            end_page=end_page,
            dpi=dpi,
            image_format="JPEG",
            quality=quality,
            out_dir=out_dir,
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF to JPEG")
    parser.add_argument("input_pdf")
    parser.add_argument("--start", type=int)
    parser.add_argument("--end", type=int)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--quality", type=int, default=95)
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    pdf_to_jpegs(
        args.input_pdf,
        args.start,
        args.end,
        args.dpi,
        args.quality,
        args.out_dir,
    )
