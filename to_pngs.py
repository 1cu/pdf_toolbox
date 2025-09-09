from __future__ import annotations

import argparse
from typing import List, cast

from rasterize import pdf_to_images


def pdf_to_pngs(
    input_pdf: str,
    start_page: int | None = None,
    end_page: int | None = None,
    dpi: int = 300,
    out_dir: str | None = None,
) -> List[str]:
    return cast(
        List[str],
        pdf_to_images(
            input_pdf,
            start_page=start_page,
            end_page=end_page,
            dpi=dpi,
            image_format="PNG",
            out_dir=out_dir,
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF to PNG")
    parser.add_argument("input_pdf")
    parser.add_argument("--start", type=int)
    parser.add_argument("--end", type=int)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    pdf_to_pngs(
        args.input_pdf,
        args.start,
        args.end,
        args.dpi,
        args.out_dir,
    )
