from __future__ import annotations

from pathlib import Path
from typing import Literal
from threading import Event

import fitz  # type: ignore
from PIL import Image

from .actions import action
from .utils import open_pdf, parse_page_spec, raise_if_cancelled, sane_output_dir


SUPPORTED_IMAGE_FORMATS = ["PNG", "JPEG", "TIFF"]

# Preset DPI options exposed via the GUI. The key is the human readable label
# presented to users while the value is the numeric DPI used for rendering.
DPI_PRESETS: dict[str, int] = {
    "Low (72 dpi)": 72,
    "Medium (150 dpi)": 150,
    "High (300 dpi)": 300,
    "Very High (600 dpi)": 600,
    "Ultra (1200 dpi)": 1200,
}

DpiChoice = Literal[
    "Low (72 dpi)",
    "Medium (150 dpi)",
    "High (300 dpi)",
    "Very High (600 dpi)",
    "Ultra (1200 dpi)",
]

# Preset JPEG quality options similar to DPI presets. These are only used when
# ``image_format`` is ``"JPEG"``. The GUI presents the human readable key while
# the value is the numeric quality passed to :func:`PIL.Image.Image.save`.
JPEG_QUALITY_PRESETS: dict[str, int] = {
    "Low (70)": 70,
    "Medium (85)": 85,
    "High (95)": 95,
}

QualityChoice = Literal["Low (70)", "Medium (85)", "High (95)"]


@action(category="PDF")
def pdf_to_images(
    input_pdf: str,
    pages: str | None = None,
    dpi: int | DpiChoice = "High (300 dpi)",
    image_format: Literal["PNG", "JPEG", "TIFF"] = "PNG",
    quality: int | QualityChoice = "High (95)",
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> list[str]:
    """Rasterize a PDF into images.

    Each page of ``input_pdf`` specified by ``pages`` is rendered to the chosen
    image format. ``pages`` accepts comma separated ranges like ``"1-3,5"``;
    ``None`` selects all pages. Supported formats are listed in
    :data:`SUPPORTED_IMAGE_FORMATS`. ``dpi`` may be one of the labels defined in
    :data:`DPI_PRESETS` or any integer DPI value; higher values yield higher
    quality but also larger files. ``quality`` is only used for JPEG output.
    Images are written to ``out_dir`` or the PDF's directory and the paths are
    returned.
    """

    outputs: list[str] = []

    if isinstance(dpi, str):
        try:
            dpi_value = DPI_PRESETS[dpi]
        except KeyError as exc:
            raise ValueError(f"Unknown DPI preset '{dpi}'") from exc
    else:
        dpi_value = int(dpi)
    zoom = dpi_value / 72  # default PDF resolution is 72 dpi
    matrix = fitz.Matrix(zoom, zoom)

    fmt = image_format.upper()
    if fmt not in SUPPORTED_IMAGE_FORMATS:
        raise ValueError(
            f"Unsupported image format '{image_format}'. Supported formats: {', '.join(SUPPORTED_IMAGE_FORMATS)}"
        )
    ext = fmt.lower()

    doc = open_pdf(input_pdf)
    with doc:
        page_numbers = parse_page_spec(pages, doc.page_count)
        out_base = sane_output_dir(input_pdf, out_dir)

        for page_no in page_numbers:
            raise_if_cancelled(cancel)  # pragma: no cover
            page = doc.load_page(page_no - 1)
            pix = page.get_pixmap(matrix=matrix)
            if pix.colorspace is None or pix.colorspace.n not in (1, 3):
                pix = fitz.Pixmap(fitz.csRGB, pix)
            if pix.alpha:
                pix = fitz.Pixmap(pix, 0)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            save_kwargs = {}
            if fmt == "JPEG":
                if isinstance(quality, str):
                    try:
                        quality_val = JPEG_QUALITY_PRESETS[quality]
                    except KeyError as exc:
                        raise ValueError(
                            f"Unknown JPEG quality preset '{quality}'"
                        ) from exc
                else:
                    quality_val = int(quality)
                save_kwargs["quality"] = quality_val
            elif fmt == "PNG":  # lossless; avoid heavy compression for speed
                save_kwargs["compress_level"] = 0

            out_path = out_base / f"{Path(input_pdf).stem}_Page_{page_no}.{ext}"
            img.save(out_path, format=fmt, **save_kwargs)
            outputs.append(str(out_path))
    return outputs


__all__ = [
    "pdf_to_images",
    "DPI_PRESETS",
    "JPEG_QUALITY_PRESETS",
]
