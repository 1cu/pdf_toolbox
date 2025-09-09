from __future__ import annotations

import argparse
import io
from pathlib import Path
from typing import Tuple, TypedDict

import fitz  # type: ignore
from PIL import Image

from .actions import action
from .utils import sane_output_dir, update_metadata


class QualitySetting(TypedDict):
    pdf_quality: int
    image_quality: int
    min_reduction: float


QUALITY_SETTINGS: dict[str, QualitySetting] = {
    "screen": {"pdf_quality": 50, "image_quality": 40, "min_reduction": 0.3},
    "ebook": {"pdf_quality": 75, "image_quality": 60, "min_reduction": 0.2},
    "printer": {"pdf_quality": 90, "image_quality": 85, "min_reduction": 0.1},
    "prepress": {"pdf_quality": 100, "image_quality": 95, "min_reduction": 0.05},
    "default": {"pdf_quality": 80, "image_quality": 75, "min_reduction": 0.15},
}


def _compress_images(doc: fitz.Document, image_quality: int) -> None:
    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            if pix.n in (1, 3, 4):
                if pix.n == 1:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                if pix.n == 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                pil_img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=image_quality)
                doc.update_stream(xref, buf.getvalue())


@action(category="PDF")
def optimize_pdf(
    input_pdf: str,
    quality: str = "default",
    compress_images: bool = False,
    keep: bool = True,
    out_dir: str | None = None,
) -> Tuple[str | None, float]:
    """Optimize ``input_pdf`` and return (output_path, reduction_ratio)."""

    if quality not in QUALITY_SETTINGS:
        raise ValueError("unknown quality")

    settings = QUALITY_SETTINGS[quality]
    input_path = Path(input_pdf)
    out_dir_path = sane_output_dir(input_path, out_dir)
    out_path = out_dir_path / f"{input_path.stem}_optimized_{quality}.pdf"

    original_size = input_path.stat().st_size
    doc = fitz.open(input_pdf)
    update_metadata(doc, note=" | optimized")

    if compress_images:
        _compress_images(doc, settings["image_quality"])

    pdf_quality = settings["pdf_quality"]
    compression_effort = max(0, min(9, (100 - pdf_quality) // 10))
    doc.save(
        out_path,
        garbage=3,
        deflate=True,
        clean=True,
        compression_effort=compression_effort,
    )
    doc.close()

    optimized_size = out_path.stat().st_size
    reduction = 1 - (optimized_size / original_size)

    if reduction < QUALITY_SETTINGS[quality]["min_reduction"] and not keep:
        out_path.unlink(missing_ok=True)
        return None, reduction
    return str(out_path), reduction


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize PDF")
    parser.add_argument("input_pdf")
    parser.add_argument(
        "quality", nargs="?", default="default", choices=QUALITY_SETTINGS.keys()
    )
    parser.add_argument("--compress-images", action="store_true")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    optimize_pdf(
        args.input_pdf, args.quality, args.compress_images, args.keep, args.out_dir
    )
