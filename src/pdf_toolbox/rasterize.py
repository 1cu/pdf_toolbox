from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Union, Literal

import fitz  # type: ignore
from PIL import Image

from .actions import action
from .utils import sane_output_dir, parse_page_spec


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
    pages: str | None = None,
    dpi: int | DpiChoice = "High (300 dpi)",
    image_format: Literal["PNG", "JPEG", "TIFF"] = "PNG",
    quality: int = 95,
    out_dir: str | None = None,
    as_pil: bool = False,
) -> List[Union[str, Image.Image]]:
    """Rasterize a PDF into images.

    Each page of ``input_pdf`` specified by ``pages`` is rendered to the chosen
    image format. ``pages`` accepts comma separated ranges like ``"1-3,5"``;
    ``None`` selects all pages. Supported formats are listed in
    :data:`SUPPORTED_IMAGE_FORMATS`. ``dpi`` may be one of the labels defined in
    :data:`DPI_PRESETS` or any integer DPI value; higher values yield higher
    quality but also larger files. ``quality`` is only used for JPEG output. If
    ``as_pil`` is ``True`` a list of :class:`PIL.Image.Image` objects is
    returned instead of file paths.
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

    try:
        doc = fitz.open(input_pdf)
    except Exception as exc:  # pragma: no cover - exercised in tests
        raise ValueError(f"Could not open PDF file: {input_pdf}") from exc

    with doc:
        page_numbers = parse_page_spec(pages, doc.page_count)
        out_base = None if as_pil else sane_output_dir(input_pdf, out_dir)

        for page_no in page_numbers:
            page = doc.load_page(page_no - 1)
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
                out_path = out_base / f"{Path(input_pdf).stem}_Seite_{page_no}.{ext}"
                img.save(out_path, format=fmt, **save_kwargs)
                outputs.append(str(out_path))
    return outputs


__all__ = ["pdf_to_images", "DPI_PRESETS"]
