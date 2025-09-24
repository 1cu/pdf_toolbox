"""Render PDF pages to images."""

from __future__ import annotations

import io
import warnings
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Literal

import fitz
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
ERR_MAX_SIZE_REQUIRED = "max_size_mb must be provided when enforcing limits"

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

ImageFormatChoice = Literal["PNG", "JPEG", "TIFF", "WEBP", "SVG"]

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


@dataclass(slots=True)
class PdfImageOptions:
    """Configuration describing how :func:`pdf_to_images` renders pages."""

    pages: str | None = None
    dpi: int | DpiChoice = "High (300 dpi)"
    image_format: ImageFormatChoice = "PNG"
    width: int | None = None
    height: int | None = None
    quality: int | QualityChoice = "High (95)"
    max_size_mb: float | None = None
    out_dir: str | None = None


@dataclass(slots=True)
class _ImageRenderPlan:
    """Normalised rendering data used internally by the renderer."""

    input_path: str
    page_numbers: list[int]
    dpi: int
    image_format: str
    quality: int
    max_size_mb: float | None
    max_bytes: int | None
    out_dir: Path
    batch_size: int | None

    @property
    def extension(self) -> str:
        return self.image_format.lower()

    @property
    def stem(self) -> str:
        return Path(self.input_path).stem


@dataclass(slots=True)
class _RasterRenderDetails:
    """Metadata describing how a raster page was written."""

    quality: int | None = None
    compress_level: int | None = None
    scale: float | None = None


@dataclass(slots=True)
class _RenderRequest:
    """Inputs accepted by :func:`_render_doc_pages`."""

    input_path: str
    page_numbers: list[int]
    dpi: int
    image_format: str
    quality: int
    max_size_mb: float | None = None
    out_dir: str | None = None
    batch_size: int | None = None


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


def _resolve_dpi(
    doc: fitz.Document,
    *,
    dpi: int | None,
    width: int | None,
    height: int | None,
) -> int:
    """Return the DPI used for rendering pages."""
    if width is not None or height is not None:
        if width is None or height is None:
            raise ValueError(ERR_WIDTH_HEIGHT)
        first = doc.load_page(0)
        w_in = first.rect.width / 72
        h_in = first.rect.height / 72
        return round(max(width / w_in, height / h_in))
    if dpi is None:
        raise ValueError(ERR_DPI_UNRESOLVED)
    return dpi


def _resolve_max_bytes(max_size_mb: float | None) -> int | None:
    if max_size_mb is None:
        return None
    return int(max_size_mb * 1024 * 1024)


def _determine_batch_size(
    page_numbers: list[int], batch_size: int | None
) -> int | None:
    if batch_size:
        return batch_size
    if len(page_numbers) > BATCH_THRESHOLD_PAGES:
        return 10
    return None


def _chunk_pages(
    page_numbers: list[int], batch_size: int | None
) -> Iterator[list[int]]:
    if not batch_size:
        yield page_numbers
        return
    for start in range(0, len(page_numbers), batch_size):
        yield page_numbers[start : start + batch_size]


def _build_render_plan(
    input_path: str,
    doc: fitz.Document,
    options: PdfImageOptions,
    page_numbers: list[int],
) -> _ImageRenderPlan:
    fmt, quality_val, dpi_val = resolve_image_settings(
        options.image_format,
        options.quality,
        None
        if options.width is not None or options.height is not None
        else options.dpi,
    )
    dpi = _resolve_dpi(doc, dpi=dpi_val, width=options.width, height=options.height)
    out_dir = sane_output_dir(input_path, options.out_dir)
    return _ImageRenderPlan(
        input_path=input_path,
        page_numbers=page_numbers,
        dpi=dpi,
        image_format=fmt,
        quality=quality_val,
        max_size_mb=options.max_size_mb,
        max_bytes=_resolve_max_bytes(options.max_size_mb),
        out_dir=out_dir,
        batch_size=_determine_batch_size(page_numbers, None),
    )


def _render_svg_page(
    page: fitz.Page,
    plan: _ImageRenderPlan,
    *,
    page_no: int,
) -> str:
    matrix = fitz.Matrix(plan.dpi / 72, plan.dpi / 72)
    svg = page.get_svg_image(matrix=matrix)
    out_path = plan.out_dir / f"{plan.stem}_Page_{page_no}.{plan.extension}"
    out_path.write_text(svg, encoding="utf-8")
    return str(out_path)


def _write_raster_without_limit(
    image: Image.Image,
    plan: _ImageRenderPlan,
    out_path: Path,
) -> _RasterRenderDetails:
    details = _RasterRenderDetails()
    fmt = plan.image_format
    if fmt == "JPEG":
        out_path.write_bytes(encode_jpeg(image, quality=plan.quality))
        details.quality = plan.quality
    elif fmt == "WEBP":
        out_path.write_bytes(encode_webp(image, lossless=False, quality=plan.quality))
        details.quality = plan.quality
    elif fmt == "PNG":
        out_path.write_bytes(
            encode_png(
                image,
                compress_level=0,
                optimize=False,
            )
        )
        details.compress_level = 0
    else:
        image.save(out_path, format=fmt)
    return details


def _try_png_levels(
    image: Image.Image,
    *,
    max_bytes: int,
    out_path: Path,
) -> _RasterRenderDetails | None:
    for level in range(10):
        data = encode_png(image, compress_level=level, optimize=True)
        if len(data) <= max_bytes:
            out_path.write_bytes(data)
            return _RasterRenderDetails(compress_level=level)
    return None


def _try_direct_lossless(
    image: Image.Image,
    *,
    image_format: str,
    max_bytes: int,
    out_path: Path,
) -> bool:
    with io.BytesIO() as buf:
        image.save(buf, format=image_format)
        data = buf.getvalue()
    if len(data) <= max_bytes:
        out_path.write_bytes(data)
        return True
    return False


def _scale_lossless_image(
    image: Image.Image,
    *,
    image_format: str,
    max_bytes: int,
    out_path: Path,
) -> _RasterRenderDetails:
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
            max(1, int(image.width * scale)),
            max(1, int(image.height * scale)),
        )
        scaled = image.resize(new_size, Image.Resampling.LANCZOS)
        if image_format == "PNG":
            data = encode_png(scaled, compress_level=9, optimize=True)
        else:
            with io.BytesIO() as buf:
                scaled.save(buf, format=image_format)
                data = buf.getvalue()
        if len(data) <= max_bytes:
            scaled_bytes = data
            scale_low = scale
        else:
            scale_high = scale
    if scaled_bytes is None:
        raise RuntimeError(ERR_COULD_NOT_REDUCE)
    out_path.write_bytes(scaled_bytes)
    details = _RasterRenderDetails(scale=scale_low)
    if image_format == "PNG":
        details.compress_level = 9
    return details


def _write_lossy_with_limit(
    image: Image.Image,
    plan: _ImageRenderPlan,
    out_path: Path,
) -> _RasterRenderDetails:
    if plan.max_bytes is None:
        raise ValueError(ERR_MAX_SIZE_REQUIRED)
    q_low, q_high = 1, plan.quality
    best_quality: int | None = None
    best_data: bytes | None = None
    while q_low <= q_high:
        mid = (q_low + q_high) // 2
        if plan.image_format == "JPEG":
            data = encode_jpeg(image, quality=mid)
        else:
            data = encode_webp(image, lossless=False, quality=mid)
        if len(data) <= plan.max_bytes:
            best_quality = mid
            best_data = data
            q_low = mid + 1
        else:
            q_high = mid - 1
    if best_data is None or best_quality is None:
        raise RuntimeError(ERR_COULD_NOT_REDUCE)
    out_path.write_bytes(best_data)
    return _RasterRenderDetails(quality=best_quality)


def _write_lossless_with_limit(
    image: Image.Image,
    plan: _ImageRenderPlan,
    out_path: Path,
) -> _RasterRenderDetails:
    if plan.max_bytes is None:
        raise ValueError(ERR_MAX_SIZE_REQUIRED)
    fmt = plan.image_format
    max_bytes = plan.max_bytes
    if fmt == "PNG":
        details = _try_png_levels(image, max_bytes=max_bytes, out_path=out_path)
        if details is not None:
            return details
    elif _try_direct_lossless(
        image,
        image_format=fmt,
        max_bytes=max_bytes,
        out_path=out_path,
    ):
        return _RasterRenderDetails()
    return _scale_lossless_image(
        image,
        image_format=fmt,
        max_bytes=max_bytes,
        out_path=out_path,
    )


def _write_raster_with_limit(
    image: Image.Image,
    plan: _ImageRenderPlan,
    out_path: Path,
) -> _RasterRenderDetails:
    if plan.image_format in {"JPEG", "WEBP"}:
        return _write_lossy_with_limit(image, plan, out_path)
    return _write_lossless_with_limit(image, plan, out_path)


def _render_raster_page(
    page: fitz.Page,
    plan: _ImageRenderPlan,
    *,
    page_no: int,
) -> str:
    image = render_page_image(page, plan.dpi, keep_alpha=False)
    out_path = plan.out_dir / f"{plan.stem}_Page_{page_no}.{plan.extension}"
    if plan.max_bytes is None:
        details = _write_raster_without_limit(image, plan, out_path)
    else:
        details = _write_raster_with_limit(image, plan, out_path)
    size_out = out_path.stat().st_size / 1024
    scale_factor = details.scale if details.scale is not None else 1
    final_width = int(image.width * scale_factor)
    final_height = int(image.height * scale_factor)
    final_dpi = int(plan.dpi * scale_factor)
    summary = [f"{final_width}x{final_height} @ {final_dpi} dpi"]
    if details.scale is not None:
        summary.append(f"scale={int(details.scale * 100)}%")
    if details.quality is not None:
        summary.append(f"quality={details.quality}")
    if details.compress_level is not None:
        summary.append(f"compress_level={details.compress_level}")
    detail_str = ", ".join(summary)
    if plan.max_size_mb is None:
        logger.info("Page %d rendered %s (%.1f kB)", page_no, detail_str, size_out)
    else:
        logger.info(
            "Page %d saved %s to meet %.1f MB (%.1f kB)",
            page_no,
            detail_str,
            plan.max_size_mb,
            size_out,
        )
    return str(out_path)


def _render_batches(
    doc: fitz.Document,
    plan: _ImageRenderPlan,
    *,
    cancel: Event | None,
) -> list[str]:
    outputs: list[str] = []
    for group in _chunk_pages(plan.page_numbers, plan.batch_size):
        for page_no in group:
            raise_if_cancelled(cancel)
            page = doc.load_page(page_no - 1)
            if plan.image_format == "SVG":
                outputs.append(_render_svg_page(page, plan, page_no=page_no))
                continue
            outputs.append(_render_raster_page(page, plan, page_no=page_no))
    return outputs


def _render_doc_pages(
    doc: fitz.Document,
    request: _RenderRequest,
    *,
    cancel: Event | None = None,
) -> list[str]:
    """Render the pages described by ``request`` from ``doc``."""
    plan = _ImageRenderPlan(
        input_path=request.input_path,
        page_numbers=request.page_numbers,
        dpi=request.dpi,
        image_format=request.image_format,
        quality=request.quality,
        max_size_mb=request.max_size_mb,
        max_bytes=_resolve_max_bytes(request.max_size_mb),
        out_dir=sane_output_dir(request.input_path, request.out_dir),
        batch_size=_determine_batch_size(request.page_numbers, request.batch_size),
    )
    return _render_batches(doc, plan, cancel=cancel)


@action(category="PDF")
def pdf_to_images(
    input_pdf: str,
    options: PdfImageOptions | None = None,
    *,
    cancel: Event | None = None,
) -> list[str]:
    """Render PDF pages to images.

    Each page of ``input_pdf`` specified by ``options.pages`` is rendered to the
    chosen image format. ``pages`` accepts comma separated ranges like
    ``"1-3,5"``; ``None`` selects all pages. Supported formats are listed in
    :data:`IMAGE_FORMATS`. ``options.dpi`` may be one of the labels defined in
    :data:`DPI_PRESETS` or any integer value. Alternatively, ``options.width``
    and ``options.height`` may be supplied to scale pages to specific pixel
    dimensions; both must be given together. ``options.quality`` is only used for
    JPEG and WebP output. ``options.max_size_mb`` limits the resulting file size.
    JPEG and WebP images progressively lower their quality to satisfy the limit,
    while PNG and TIFF images increase compression and are only downscaled when
    necessary, emitting a warning if resizing occurs. Images are written to
    ``options.out_dir`` or the PDF's directory and the paths are returned.

    Examples:
        >>> # Convert all pages to PNG at 300 DPI
        >>> pdf_to_images("document.pdf")

        >>> # Convert specific pages to JPEG
        >>> pdf_to_images(
        ...     "document.pdf",
        ...     PdfImageOptions(pages="1-3,5", image_format="JPEG", quality="Medium (85)"),
        ... )

    """
    opts = options or PdfImageOptions()
    logger.info("pdf_to_images called for %s", input_pdf)
    doc = open_pdf(input_pdf)
    with doc:
        page_numbers = parse_page_spec(opts.pages, doc.page_count)
        plan = _build_render_plan(input_pdf, doc, opts, page_numbers)
        return _render_batches(
            doc,
            plan,
            cancel=cancel,
        )


__all__ = [
    "DPI_PRESETS",
    "LOSSY_QUALITY_PRESETS",
    "PdfImageOptions",
    "pdf_to_images",
    "resolve_image_settings",
]
