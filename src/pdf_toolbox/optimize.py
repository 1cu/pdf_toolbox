"""PDF optimization utilities."""

from __future__ import annotations

import argparse
import io
import logging
from pathlib import Path
from threading import Event
from typing import TypedDict

import fitz  # type: ignore
from PIL import Image

from pdf_toolbox.actions import action
from pdf_toolbox.utils import (
    open_pdf,
    raise_if_cancelled,
    sane_output_dir,
    save_pdf,
)

logger = logging.getLogger(__name__)


class QualitySetting(TypedDict):
    """Quality configuration options."""

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


def _compress_images(
    doc: fitz.Document, image_quality: int, cancel: Event | None = None
) -> None:
    for page in doc:
        raise_if_cancelled(cancel)  # pragma: no cover
        for img in page.get_images(full=True):
            raise_if_cancelled(cancel)  # pragma: no cover
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            try:
                if pix.n in (1, 3, 4):
                    if pix.n in (1, 4):
                        original = pix
                        pix = fitz.Pixmap(fitz.csRGB, original)
                        del original
                    pil_img = Image.frombytes(
                        "RGB", (pix.width, pix.height), pix.samples
                    )
                    with io.BytesIO() as buf:
                        pil_img.save(buf, format="JPEG", quality=image_quality)
                        doc.update_stream(xref, buf.getvalue())
            finally:
                del pix


@action(category="PDF")
def optimize_pdf(  # noqa: PLR0913
    input_pdf: str,
    quality: str = "default",
    compress_images: bool = False,
    keep: bool = True,
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> tuple[str | None, float]:
    """Optimize ``input_pdf`` and return (output_path, reduction_ratio)."""
    if quality not in QUALITY_SETTINGS:
        raise ValueError("unknown quality")

    settings = QUALITY_SETTINGS[quality]
    input_path = Path(input_pdf)
    out_dir_path = sane_output_dir(input_path, out_dir)
    out_path = out_dir_path / f"{input_path.stem}_optimized_{quality}.pdf"

    original_size = input_path.stat().st_size
    logger.info(
        "Optimizing %s with quality=%s (compress_images=%s)",
        input_pdf,
        quality,
        compress_images,
    )
    doc = open_pdf(input_pdf)
    raise_if_cancelled(cancel, doc)  # pragma: no cover

    if compress_images:
        _compress_images(doc, settings["image_quality"], cancel)

    raise_if_cancelled(cancel, doc)  # pragma: no cover

    pdf_quality = settings["pdf_quality"]
    compression_effort = max(0, min(9, (100 - pdf_quality) // 10))
    save_pdf(
        doc,
        out_path,
        note=" | optimized",
        garbage=3,
        deflate=True,
        clean=True,
        compression_effort=compression_effort,
    )

    optimized_size = out_path.stat().st_size
    reduction = 1 - (optimized_size / original_size)
    logger.info(
        "Reduced size from %.1f kB to %.1f kB (%.1f%%)",
        original_size / 1024,
        optimized_size / 1024,
        reduction * 100,
    )

    if reduction < QUALITY_SETTINGS[quality]["min_reduction"] and not keep:
        out_path.unlink(missing_ok=True)
        logger.info("Reduction below threshold; output discarded")
        return None, reduction
    logger.info("Optimized PDF written to %s", out_path)
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
