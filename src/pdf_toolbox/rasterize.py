from __future__ import annotations

import io
import math
import sys
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
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

# Include WebP for better quality/size tradeoffs
SUPPORTED_IMAGE_FORMATS = ["PNG", "JPEG", "TIFF", "WEBP"]

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


@contextmanager
def _unlimited_int_str_digits() -> Iterator[None]:
    """Temporarily disable Python's string-to-int digit limit.

    Pillow may convert very large integers to strings when saving images,
    which can exceed the default safety limit introduced in Python 3.11 and
    trigger a ``ValueError``. This context manager lifts the restriction while
    preserving the previous value.
    """

    if hasattr(sys, "set_int_max_str_digits"):
        prev = sys.get_int_max_str_digits()
        try:
            sys.set_int_max_str_digits(0)
            yield
        finally:
            sys.set_int_max_str_digits(prev)
    else:
        yield  # pragma: no cover


@action(category="PDF")
def pdf_to_images(
    input_pdf: str,
    pages: str | None = None,
    dpi: int | DpiChoice = "High (300 dpi)",
    image_format: Literal["PNG", "JPEG", "TIFF", "WEBP"] = "PNG",
    quality: int | QualityChoice = "High (95)",
    max_size_mb: float | None = None,
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> list[str]:
    """Rasterize a PDF into images.

    Each page of ``input_pdf`` specified by ``pages`` is rendered to the chosen
    image format. ``pages`` accepts comma separated ranges like ``"1-3,5"``;
    ``None`` selects all pages. Supported formats are listed in
    :data:`SUPPORTED_IMAGE_FORMATS`. ``dpi`` may be one of the labels defined in
    :data:`DPI_PRESETS` or any integer DPI value; higher values yield higher
    quality but also larger files. ``quality`` is only used for JPEG and WebP
    output. ``max_size_mb`` limits the resulting JPEG or WebP files by reducing
    image quality and scales down PNG or TIFF images to roughly fit within the
    given size, emitting a warning when this fallback is used. Images are written
    to ``out_dir`` or the PDF's directory and the paths are returned.
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
    if fmt not in SUPPORTED_IMAGE_FORMATS:
        raise ValueError(
            f"Unsupported image format '{image_format}'. Supported formats: {', '.join(SUPPORTED_IMAGE_FORMATS)}"
        )
    ext = fmt.lower()
    max_bytes = int(max_size_mb * 1024 * 1024) if max_size_mb else None

    doc = open_pdf(input_pdf)
    with doc:
        page_numbers = parse_page_spec(pages, doc.page_count)
        out_base = sane_output_dir(input_pdf, out_dir)

        for page_no in page_numbers:
            raise_if_cancelled(cancel)  # pragma: no cover
            with _unlimited_int_str_digits():
                page = doc.load_page(page_no - 1)
                matrix = fitz.Matrix(zoom, zoom)
                if max_bytes is not None:
                    width_px = math.ceil(page.rect.width * zoom)
                    height_px = math.ceil(page.rect.height * zoom)
                    uncompressed = width_px * height_px * 3
                    if uncompressed > max_bytes:
                        warnings.warn(
                            "max_size_mb with lossless formats will downscale image dimensions to meet the target size; use JPEG or WebP to keep dimensions",
                            UserWarning,
                            stacklevel=2,
                        )
                        scale = math.sqrt(max_bytes / uncompressed)
                        matrix = fitz.Matrix(zoom * scale, zoom * scale)
                pix = page.get_pixmap(matrix=matrix)
                if pix.colorspace is None or pix.colorspace.n not in (
                    1,
                    3,
                ):  # pragma: no cover
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                if pix.alpha:  # pragma: no cover
                    pix = fitz.Pixmap(pix, 0)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                save_kwargs = {}
                if fmt in {"JPEG", "WEBP"}:
                    if isinstance(quality, str):
                        try:
                            quality_val = LOSSY_QUALITY_PRESETS[quality]
                        except KeyError as exc:
                            raise ValueError(
                                f"Unknown quality preset '{quality}'"
                            ) from exc
                    else:
                        quality_val = int(quality)
                    if max_bytes is not None:
                        # Start at the requested quality and decrease in fixed steps
                        # before falling back to a binary search to refine.
                        step = 10
                        prev = quality_val
                        found = False
                        for q in range(quality_val, 0, -step):
                            buf = io.BytesIO()
                            img.save(buf, format=fmt, quality=q)
                            if buf.tell() <= max_bytes:
                                low = q
                                high = prev
                                found = True
                                break
                            prev = q
                        if not found:
                            buf = io.BytesIO()
                            img.save(buf, format=fmt, quality=1)
                            if buf.tell() > max_bytes:
                                raise RuntimeError(
                                    "Could not reduce image below max_size_mb"
                                )  # pragma: no cover
                            low, high = 1, prev  # pragma: no cover
                        while low < high:
                            mid = (low + high + 1) // 2
                            buf = io.BytesIO()
                            img.save(buf, format=fmt, quality=mid)
                            if buf.tell() <= max_bytes:
                                low = mid
                            else:
                                high = mid - 1
                        quality_val = low
                    save_kwargs["quality"] = quality_val
                    out_path = out_base / f"{Path(input_pdf).stem}_Page_{page_no}.{ext}"
                    img.save(out_path, format=fmt, **save_kwargs)
                    if (
                        max_bytes is not None
                        and Path(out_path).stat().st_size > max_bytes
                    ):
                        raise RuntimeError(
                            "Could not reduce image below max_size_mb"
                        )  # pragma: no cover
                else:  # lossless formats
                    if fmt == "PNG":
                        # avoid heavy compression for speed
                        save_kwargs["compress_level"] = 0
                    out_path = out_base / f"{Path(input_pdf).stem}_Page_{page_no}.{ext}"
                    if max_bytes is not None:
                        buf = io.BytesIO()
                        img.save(buf, format=fmt, **save_kwargs)
                        if buf.tell() > max_bytes:
                            ratio = math.sqrt(max_bytes / buf.tell())
                            img = img.resize(
                                (
                                    max(1, int(img.width * ratio)),
                                    max(1, int(img.height * ratio)),
                                ),
                                Image.Resampling.LANCZOS,
                            )
                            buf = io.BytesIO()
                            img.save(buf, format=fmt, **save_kwargs)
                            if buf.tell() > max_bytes:
                                raise RuntimeError(
                                    "Could not reduce image below max_size_mb"
                                )
                        with open(out_path, "wb") as f:
                            f.write(buf.getbuffer())
                    else:
                        img.save(out_path, format=fmt, **save_kwargs)

            outputs.append(str(out_path))
    return outputs


__all__ = [
    "pdf_to_images",
    "DPI_PRESETS",
    "LOSSY_QUALITY_PRESETS",
]
