"""Render PDF pages to images."""

from __future__ import annotations

import io
import warnings
from pathlib import Path
from threading import Event
from typing import Literal

import fitz  # type: ignore  # pdf-toolbox: PyMuPDF lacks type hints | issue:-
from PIL import Image

from pdf_toolbox.actions import action
from pdf_toolbox.image_utils import (
    encode_jpeg,
    encode_png,
    encode_webp,
    render_page_image,
)
from pdf_toolbox.utils import (
    logger,
    open_pdf,
    parse_page_spec,
    raise_if_cancelled,
    sane_output_dir,
)

ERR_UNKNOWN_DPI = "Unknown DPI preset '{dpi}'"
ERR_UNSUPPORTED_FORMAT = (
    "Unsupported image format '{image_format}'. Supported formats: {formats}"
)
ERR_UNKNOWN_QUALITY = "Unknown quality preset '{quality}'"
ERR_COULD_NOT_REDUCE = "Could not reduce image below max_size_mb"
ERR_WIDTH_HEIGHT = "width and height must be provided together"
ERR_DPI_UNRESOLVED = "dpi could not be resolved"

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

# Tune batching for very large documents to keep peak memory lower
BATCH_THRESHOLD_PAGES = 200

# Preset quality options for lossy formats like JPEG and WebP. The GUI presents
# the human readable key while the value is the numeric quality passed to
# :func:`PIL.Image.Image.save`.
LOSSY_QUALITY_PRESETS: dict[str, int] = {
    "Low (70)": 70,
    "Medium (85)": 85,
    "High (95)": 95,
}

QualityChoice = Literal["Low (70)", "Medium (85)", "High (95)"]


def resolve_image_settings(
    image_format: str,
    quality: int | QualityChoice = "High (95)",
    dpi: int | DpiChoice | None = None,
    *,
    allowed_formats: set[str] | None = None,
) -> tuple[str, int, int | None]:
    """Normalise ``image_format``, ``quality`` and optional ``dpi`` values.

    Args:
        image_format: Requested output format. Case is ignored.
        quality: Lossy quality preset or explicit value.
        dpi: Optional DPI preset or value.
        allowed_formats: Restrict accepted formats; defaults to
            :data:`IMAGE_FORMATS`.

    Returns:
        A tuple ``(fmt, quality_val, dpi_val)`` where ``fmt`` is the validated
        upper-case format, ``quality_val`` is the numeric quality value and
        ``dpi_val`` the resolved DPI or ``None`` if ``dpi`` was ``None``.
    """
    fmt = image_format.upper()
    formats = allowed_formats or set(IMAGE_FORMATS)
    if fmt not in formats:
        raise ValueError(
            ERR_UNSUPPORTED_FORMAT.format(
                image_format=image_format,
                formats=", ".join(sorted(formats)),
            )
        )

    if isinstance(quality, str):
        try:
            quality_val = LOSSY_QUALITY_PRESETS[quality]
        except KeyError as exc:
            raise ValueError(ERR_UNKNOWN_QUALITY.format(quality=quality)) from exc
    else:
        quality_val = int(quality)

    dpi_val: int | None = None
    if dpi is not None:
        if isinstance(dpi, str):
            try:
                dpi_val = DPI_PRESETS[dpi]
            except KeyError as exc:
                raise ValueError(ERR_UNKNOWN_DPI.format(dpi=dpi)) from exc
        else:
            dpi_val = int(dpi)

    return fmt, quality_val, dpi_val


def _render_doc_pages(  # noqa: PLR0913, PLR0912, PLR0915  # pdf-toolbox: rendering pages needs many parameters and branches | issue:-
    input_path: str,
    doc: fitz.Document,
    page_numbers: list[int],
    dpi: int,
    image_format: str,
    quality: int,
    max_size_mb: float | None = None,
    out_dir: str | None = None,
    cancel: Event | None = None,
    *,
    batch_size: int | None = None,
) -> list[str]:
    """Render ``page_numbers`` of ``doc`` to images.

    This helper contains the core image-generation logic used by
    :func:`pdf_to_images`. ``input_path`` is used to derive sensible output names
    and locations.
    """
    outputs: list[str] = []

    dpi_value = int(dpi)
    zoom = dpi_value / 72  # default PDF resolution is 72 dpi

    fmt = image_format
    ext = fmt.lower()
    max_bytes = int(max_size_mb * 1024 * 1024) if max_size_mb else None

    out_base = sane_output_dir(input_path, out_dir)
    logger.info(
        "Rendering %d page(s) from %s at %d dpi to %s%s",
        len(page_numbers),
        input_path,
        dpi_value,
        fmt,
        f" with max {max_size_mb} MB" if max_bytes is not None else "",
    )

    # Process pages in memory-friendly batches
    batches = [page_numbers]
    if batch_size and batch_size > 0:
        batches = [
            page_numbers[start : start + batch_size]
            for start in range(0, len(page_numbers), batch_size)
        ]

    for group in batches:
        for page_no in group:
            raise_if_cancelled(cancel)
            page = doc.load_page(page_no - 1)
            if fmt == "SVG":
                matrix = fitz.Matrix(zoom, zoom)
                svg = page.get_svg_image(matrix=matrix)
                out_path = out_base / f"{Path(input_path).stem}_Page_{page_no}.{ext}"
                out_path.write_text(svg, encoding="utf-8")
                outputs.append(str(out_path))
                continue
            img = render_page_image(page, dpi_value, keep_alpha=False)
            out_path = out_base / f"{Path(input_path).stem}_Page_{page_no}.{ext}"

            used_quality: int | None = None
            used_level: int | None = None
            final_scale: float | None = None
            if max_bytes is None:
                if fmt == "JPEG":
                    used_quality = quality
                    out_path.write_bytes(encode_jpeg(img, quality=quality))
                elif fmt == "WEBP":
                    used_quality = quality
                    out_path.write_bytes(
                        encode_webp(img, lossless=False, quality=quality)
                    )
                elif fmt == "PNG":
                    used_level = 0
                    out_path.write_bytes(
                        encode_png(
                            img,
                            compress_level=0,
                            optimize=False,
                        )
                    )
                else:
                    img.save(out_path, format=fmt)
            elif fmt in {"JPEG", "WEBP"}:
                q_low, q_high = 1, quality
                best: bytes | None = None
                while q_low <= q_high:
                    mid = (q_low + q_high) // 2
                    if fmt == "JPEG":
                        data = encode_jpeg(img, quality=mid)
                    else:
                        data = encode_webp(img, lossless=False, quality=mid)
                    size = len(data)
                    if size <= max_bytes:
                        best = data
                        used_quality = mid
                        q_low = mid + 1
                    else:
                        q_high = mid - 1
                if best is None:
                    raise RuntimeError(ERR_COULD_NOT_REDUCE)
                out_path.write_bytes(best)
            else:
                need_scale = True
                if fmt == "PNG":
                    for level in range(10):
                        data = encode_png(
                            img,
                            compress_level=level,
                            optimize=True,
                        )
                        size = len(data)
                        if size <= max_bytes:
                            out_path.write_bytes(data)
                            used_level = level
                            need_scale = False
                            break
                else:
                    with io.BytesIO() as buf:
                        img.save(buf, format=fmt)
                        size = buf.tell()
                        data = buf.getvalue()
                    if size <= max_bytes:
                        out_path.write_bytes(data)
                        need_scale = False
                if need_scale:
                    warnings.warn(
                        "Image scaled down to meet max_size_mb; size is approximate",
                        UserWarning,
                        stacklevel=1,
                    )
                    scale_low, scale_high = 0.0, 1.0
                    scaled_bytes: bytes | None = None
                    for _ in range(20):
                        scale = (scale_low + scale_high) / 2
                        if scale <= 0:
                            break
                        new_size = (
                            max(1, int(img.width * scale)),
                            max(1, int(img.height * scale)),
                        )
                        scaled = img.resize(new_size, Image.Resampling.LANCZOS)
                        if fmt == "PNG":
                            data = encode_png(scaled, compress_level=9, optimize=True)
                        else:
                            with io.BytesIO() as buf:
                                scaled.save(buf, format=fmt)
                                data = buf.getvalue()
                        size = len(data)
                        if size <= max_bytes:
                            scaled_bytes = data
                            scale_low = scale
                        else:
                            scale_high = scale
                    if scaled_bytes is None:
                        raise RuntimeError(ERR_COULD_NOT_REDUCE)
                    out_path.write_bytes(scaled_bytes)
                    final_scale = scale_low
                    if fmt == "PNG":
                        used_level = 9

            size_out = out_path.stat().st_size / 1024
            scale_factor = final_scale if final_scale is not None else 1
            final_width = int(img.width * scale_factor)
            final_height = int(img.height * scale_factor)
            final_dpi = int(dpi_value * scale_factor)
            details = [f"{final_width}x{final_height} @ {final_dpi} dpi"]
            if final_scale is not None:
                details.append(f"scale={int(final_scale * 100)}%")
            if used_quality is not None:
                details.append(f"quality={used_quality}")
            if used_level is not None:
                details.append(f"compress_level={used_level}")
            detail_str = ", ".join(details)
            if max_bytes is None:
                logger.info(
                    "Page %d rendered %s (%.1f kB)",
                    page_no,
                    detail_str,
                    size_out,
                )
            else:
                logger.info(
                    "Page %d saved %s to meet %.1f MB (%.1f kB)",
                    page_no,
                    detail_str,
                    max_size_mb,
                    size_out,
                )

            outputs.append(str(out_path))
    return outputs


@action(category="PDF")
def pdf_to_images(  # noqa: PLR0913  # pdf-toolbox: conversion helper requires many parameters | issue:-
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
    ``max_size_mb`` limits the resulting file size. JPEG and WebP images
    progressively lower their quality to satisfy the limit, while PNG and TIFF
    images increase compression and are only downscaled when necessary,
    emitting a warning if resizing occurs. Images are written to ``out_dir`` or
    the PDF's directory and the paths are returned.

    Examples:
        >>> # Convert all pages to PNG at 300 DPI
        >>> pdf_to_images("document.pdf")

        >>> # Convert specific pages to JPEG
        >>> pdf_to_images(
        ...     "document.pdf", pages="1-3,5", image_format="JPEG", quality="Medium (85)"
        ... )

    """
    logger.info("pdf_to_images called for %s", input_pdf)
    doc = open_pdf(input_pdf)
    with doc:
        page_numbers = parse_page_spec(pages, doc.page_count)
        fmt, quality_val, dpi_val = resolve_image_settings(
            image_format,
            quality,
            None if width is not None or height is not None else dpi,
        )
        if width is not None or height is not None:
            if width is None or height is None:
                raise ValueError(ERR_WIDTH_HEIGHT)
            first = doc.load_page(0)
            w_in = first.rect.width / 72
            h_in = first.rect.height / 72
            dpi_val = round(max(width / w_in, height / h_in))
        elif dpi_val is None:
            raise ValueError(ERR_DPI_UNRESOLVED)
        return _render_doc_pages(
            input_pdf,
            doc,
            page_numbers,
            dpi_val,
            fmt,
            quality_val,
            max_size_mb=max_size_mb,
            out_dir=out_dir,
            cancel=cancel,
            batch_size=10 if len(page_numbers) > BATCH_THRESHOLD_PAGES else None,
        )


__all__ = [
    "DPI_PRESETS",
    "LOSSY_QUALITY_PRESETS",
    "pdf_to_images",
    "resolve_image_settings",
]
