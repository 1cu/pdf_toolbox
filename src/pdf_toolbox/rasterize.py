from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Union, Literal

import fitz  # type: ignore
from PIL import Image

from .actions import action
from .utils import sane_output_dir


SUPPORTED_IMAGE_FORMATS = ["PNG", "JPEG", "TIFF"]

# Preset DPI options exposed via the GUI. The key is the human readable label
# presented to users while the value is the numeric DPI used for rendering.
DPI_PRESETS: Dict[str, int] = {
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


@action(category="PDF")
def pdf_to_images(
    input_pdf: str,
    start_page: int | None = None,
    end_page: int | None = None,
    dpi: int | DpiChoice = "High (300 dpi)",
    image_format: Literal["PNG", "JPEG", "TIFF"] = "PNG",
    quality: int = 95,
    out_dir: str | None = None,
    as_pil: bool = False,
) -> List[Union[str, Image.Image]]:
    """Rasterize a PDF into images.

    Each page of ``input_pdf`` is rendered to the chosen image format. Supported
    formats are listed in :data:`SUPPORTED_IMAGE_FORMATS`.
    ``dpi`` may be one of the labels defined in :data:`DPI_PRESETS` or any
    integer DPI value; higher values yield higher quality but also larger files.
    ``quality`` is only used for JPEG output. If ``as_pil`` is ``True`` a list
    of :class:`PIL.Image.Image` objects is returned instead of file paths.
    """

    outputs: List[Union[str, Image.Image]] = []

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

    if start_page is not None:
        try:
            start_page = int(start_page)
        except (TypeError, ValueError) as exc:
            raise ValueError("start_page must be an integer") from exc
    if end_page is not None:
        try:
            end_page = int(end_page)
        except (TypeError, ValueError) as exc:
            raise ValueError("end_page must be an integer") from exc

    try:
        doc = fitz.open(input_pdf)
    except Exception as exc:  # pragma: no cover - exercised in tests
        raise ValueError(f"Could not open PDF file: {input_pdf}") from exc

    with doc:
        total = doc.page_count
        if start_page is not None and not 1 <= start_page <= total:
            raise ValueError(f"start_page {start_page} out of range 1..{total}")
        if end_page is not None and not 1 <= end_page <= total:
            raise ValueError(f"end_page {end_page} out of range 1..{total}")
        if start_page is not None and end_page is not None and end_page < start_page:
            raise ValueError("end_page must be greater than or equal to start_page")

        start = (start_page - 1) if start_page else 0
        end = end_page if end_page else total
        out_base = None if as_pil else sane_output_dir(input_pdf, out_dir)

        for page_no in range(start, end):
            page = doc.load_page(page_no)
            pix = page.get_pixmap(matrix=matrix)
            if pix.colorspace is None or pix.colorspace.n not in (1, 3):
                pix = fitz.Pixmap(fitz.csRGB, pix)
            if pix.alpha:
                pix = fitz.Pixmap(pix, 0)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            save_kwargs = {}
            if fmt == "JPEG":
                save_kwargs["quality"] = quality
            elif fmt == "PNG":  # lossless; avoid heavy compression for speed
                save_kwargs["compress_level"] = 0

            if as_pil:
                outputs.append(img)
            else:
                assert out_base is not None
                out_path = (
                    out_base / f"{Path(input_pdf).stem}_Seite_{page_no + 1}.{ext}"
                )
                img.save(out_path, format=fmt, **save_kwargs)
                outputs.append(str(out_path))
    return outputs


__all__ = ["pdf_to_images", "DPI_PRESETS"]
