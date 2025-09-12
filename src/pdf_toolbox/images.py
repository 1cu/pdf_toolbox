"""Render PDF pages to images."""

from __future__ import annotations

import warnings
from pathlib import Path
from threading import Event
from typing import Literal

import fitz  # type: ignore
from PIL import Image

from pdf_toolbox.actions import action
from pdf_toolbox.utils import (
    open_pdf,
    parse_page_spec,
    raise_if_cancelled,
    sane_output_dir,
)

# Supported output formats for PDF rendering; WebP offers
# smaller files with good quality.
IMAGE_FORMATS = ["PNG", "JPEG", "TIFF", "WEBP", "SVG"]

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

# Preset quality options for lossy formats like JPEG and WebP. The GUI presents
# the human readable key while the value is the numeric quality passed to
# :func:`PIL.Image.Image.save`.
LOSSY_QUALITY_PRESETS: dict[str, int] = {
    "Low (70)": 70,
    "Medium (85)": 85,
    "High (95)": 95,
}

QualityChoice = Literal["Low (70)", "Medium (85)", "High (95)"]


def _render_doc_pages(  # noqa: PLR0913, PLR0912, PLR0915
    input_path: str,
    doc: fitz.Document,
    page_numbers: list[int],
    dpi: int | DpiChoice,
    image_format: str,
    quality: int | QualityChoice = "High (95)",
    max_size_mb: float | None = None,
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> list[str]:
    """Render ``page_numbers`` of ``doc`` to images.

    This helper contains the core image-generation logic used by
    :func:`pdf_to_images`. ``input_path`` is used to derive sensible output names
    and locations.
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

    fmt = image_format.upper()
    if fmt not in IMAGE_FORMATS:
        raise ValueError(
            f"Unsupported image format '{image_format}'. Supported formats: {', '.join(IMAGE_FORMATS)}"
        )
    ext = fmt.lower()
    max_bytes = int(max_size_mb * 1024 * 1024) if max_size_mb else None

    out_base = sane_output_dir(input_path, out_dir)

    for page_no in page_numbers:
        raise_if_cancelled(cancel)  # pragma: no cover
        page = doc.load_page(page_no - 1)
        matrix = fitz.Matrix(zoom, zoom)
        if fmt == "SVG":
            svg = page.get_svg_image(matrix=matrix)
            out_path = out_base / f"{Path(input_path).stem}_Page_{page_no}.{ext}"
            out_path.write_text(svg, encoding="utf-8")
            outputs.append(str(out_path))
            continue
        pix = page.get_pixmap(matrix=matrix)
        if pix.colorspace is None or pix.colorspace.n not in (1, 3):  # pragma: no cover
            pix = fitz.Pixmap(fitz.csRGB, pix)
        if pix.alpha:  # pragma: no cover
            pix = fitz.Pixmap(pix, 0)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

        if max_bytes is not None:
            bpp = 3
            total = img.width * img.height * bpp
            if total > max_bytes:
                scale = (max_bytes / total) ** 0.5
                new_size = (
                    max(1, int(img.width * scale)),
                    max(1, int(img.height * scale)),
                )
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                warnings.warn(
                    "Image scaled down to meet max_size_mb; size is approximate",
                    UserWarning,
                    stacklevel=2,
                )

        save_kwargs: dict[str, int] = {}
        if fmt in {"JPEG", "WEBP"}:
            if isinstance(quality, str):
                try:
                    quality_val = LOSSY_QUALITY_PRESETS[quality]
                except KeyError as exc:
                    raise ValueError(f"Unknown quality preset '{quality}'") from exc
            else:
                quality_val = int(quality)
            save_kwargs["quality"] = quality_val
        elif fmt == "PNG":
            save_kwargs["compress_level"] = 0 if max_bytes is None else 9

        out_path = out_base / f"{Path(input_path).stem}_Page_{page_no}.{ext}"
        img.save(out_path, format=fmt, **save_kwargs)
        if max_bytes is not None and Path(out_path).stat().st_size > max_bytes:
            raise RuntimeError("Could not reduce image below max_size_mb")

        outputs.append(str(out_path))
    return outputs


@action(category="PDF")
def pdf_to_images(  # noqa: PLR0913
    input_pdf: str,
    pages: str | None = None,
    dpi: int | DpiChoice = "High (300 dpi)",
    image_format: Literal["PNG", "JPEG", "TIFF", "WEBP", "SVG"] = "PNG",
    width: int | None = None,
    height: int | None = None,
    quality: int | QualityChoice = "High (95)",
    max_size_mb: float | None = None,
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> list[str]:
    """Render PDF pages to images.

    Each page of ``input_pdf`` specified by ``pages`` is rendered to the chosen
    image format. ``pages`` accepts comma separated ranges like ``"1-3,5"``;
    ``None`` selects all pages. Supported formats are listed in
    :data:`IMAGE_FORMATS`. ``dpi`` may be one of the labels defined in
    :data:`DPI_PRESETS` or any integer value. Alternatively, ``width`` and
    ``height`` may be supplied to scale pages to specific pixel dimensions; both
    must be given together. ``quality`` is only used for JPEG and WebP output.
    ``max_size_mb`` limits the resulting JPEG or WebP files by reducing image
    quality and scales down PNG or TIFF images to roughly fit within the given
    size, emitting a warning when this fallback is used. Images are written to
    ``out_dir`` or the PDF's directory and the paths are returned.
    """
    doc = open_pdf(input_pdf)
    with doc:
        page_numbers = parse_page_spec(pages, doc.page_count)
        dpi_val: int | DpiChoice = dpi
        if width is not None or height is not None:
            if width is None or height is None:
                raise ValueError("width and height must be provided together")
            first = doc.load_page(0)
            w_in = first.rect.width / 72
            h_in = first.rect.height / 72
            dpi_val = round(max(width / w_in, height / h_in))
        return _render_doc_pages(
            input_pdf,
            doc,
            page_numbers,
            dpi_val,
            image_format,
            quality=quality,
            max_size_mb=max_size_mb,
            out_dir=out_dir,
            cancel=cancel,
        )


__all__ = [
    "DPI_PRESETS",
    "LOSSY_QUALITY_PRESETS",
    "pdf_to_images",
]
