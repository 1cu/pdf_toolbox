"""Miro export pipeline for PDF and PPTX slides."""

from __future__ import annotations

import dataclasses
import json
import math
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event

from PIL import Image

import fitz
from pdf_toolbox.image_utils import (
    apply_unsharp_mask,
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


@dataclass(slots=True)
class ExportProfile:
    """Settings that define an export profile.

    Attributes:
        name: Identifier of the profile used in logs and manifests.
        max_bytes: Maximum allowed size per exported page in bytes.
        target_zoom: Zoom factor representing the target viewing zoom.
        min_effective_dpi: Required effective DPI at ``target_zoom``.
        render_dpi: Initial DPI used for rendering.
        max_dpi: Upper bound for DPI search.
    """

    name: str
    max_bytes: int
    target_zoom: float
    min_effective_dpi: int
    render_dpi: int
    max_dpi: int

    @property
    def min_dpi(self) -> int:
        """Return the minimum render DPI to satisfy the sharpness goal."""
        return int(self.target_zoom * self.min_effective_dpi)


MIRO_MAX_BYTES = 30 * 1024 * 1024
MIRO_MAX_PIXELS = 32_000_000
MIRO_MAX_LONG_EDGE = 8192
MIRO_MAX_SHORT_EDGE = 4096

PROFILE_MIRO = ExportProfile(
    name="miro",
    max_bytes=MIRO_MAX_BYTES,
    target_zoom=4.0,
    min_effective_dpi=200,
    render_dpi=800,
    max_dpi=1200,
)

VECTOR_DOMINANCE_THRESHOLD = 0.4
NO_RASTER_ENCODER_MSG = "no raster encoders produced output"
NO_RASTER_ATTEMPT_MSG = "no raster attempt produced output"


def _calculate_dpi_window(page: fitz.Page, profile: ExportProfile) -> tuple[int, int]:
    """Return the effective min/max DPI window respecting board limits."""
    rect = page.rect
    width_in = rect.width / 72 if rect.width > 0 else 0.0
    height_in = rect.height / 72 if rect.height > 0 else 0.0
    candidates = [profile.max_dpi]

    if width_in > 0 and height_in > 0:
        long_in, short_in = sorted((width_in, height_in), reverse=True)
        area_in = width_in * height_in
        if long_in > 0:
            candidates.append(int(MIRO_MAX_LONG_EDGE / long_in))
        if short_in > 0:
            candidates.append(int(MIRO_MAX_SHORT_EDGE / short_in))
        if area_in > 0:
            candidates.append(int(math.sqrt(MIRO_MAX_PIXELS / area_in)))

    positive = [value for value in candidates if value > 0]
    allowed_max = max(min(positive), 1) if positive else max(profile.max_dpi, 1)
    effective_min = max(1, min(profile.min_dpi, allowed_max))
    return effective_min, allowed_max


@dataclass(slots=True)
class PageExportAttempt:
    """Details about a single encoding attempt for a page.

    Attributes:
        dpi: Render DPI used for this attempt.
        fmt: Output format attempted.
        size_bytes: Size of the encoded result in bytes.
        encoder: Encoder identifier such as ``"webp"`` or ``"png"``.
        quality: Optional quality value if applicable.
        lossless: Whether the attempt used lossless encoding if known.
    """

    dpi: int
    fmt: str
    size_bytes: int
    encoder: str
    quality: int | None = None
    lossless: bool | None = None


@dataclass(slots=True)
class PageExportResult:
    """Result of exporting a single page.

    Attributes:
        page: Page number starting at 1.
        output_path: Path to the exported file or ``None`` when failed.
        width_px: Width of the rendered bitmap in pixels when applicable.
        height_px: Height of the rendered bitmap in pixels when applicable.
        dpi: Render DPI of the final output if rasterised.
        fmt: Output format, e.g. ``"SVG"`` or ``"WEBP"``.
        filesize_bytes: Size of the emitted file or ``0`` when missing.
        vector_export: ``True`` when the result is an SVG export.
        attempts: Attempts performed during export.
        warnings: Collected warnings for the page.
        error: Error message if export failed.
    """

    page: int
    output_path: Path | None
    width_px: int | None
    height_px: int | None
    dpi: int | None
    fmt: str | None
    filesize_bytes: int
    vector_export: bool
    attempts: list[PageExportAttempt] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    def to_manifest_entry(self) -> dict[str, object]:
        """Return a JSON-serialisable dictionary for the manifest."""
        return {
            "page": self.page,
            "width_px": self.width_px,
            "height_px": self.height_px,
            "dpi": self.dpi,
            "format": self.fmt,
            "filesize_bytes": self.filesize_bytes,
            "vector_export": self.vector_export,
            "attempts": [dataclasses.asdict(attempt) for attempt in self.attempts],
            "warnings": list(self.warnings),
            "error": self.error,
        }


@dataclass(slots=True)
class MiroExportOutcome:
    """Aggregate result of running the Miro export pipeline.

    Attributes:
        files: Exported file paths.
        manifest: Path to the generated manifest JSON file.
        page_results: Detailed per-page results.
        warnings: Combined warnings across all pages.
    """

    files: list[str]
    manifest: Path
    page_results: list[PageExportResult]
    warnings: list[str]


def _remove_svg_metadata(svg: str) -> str:
    """Remove ``<metadata>`` blocks from *svg* to keep files lean."""
    start_tag = "<metadata"
    end_tag = "</metadata>"
    lower = svg.lower()
    start = lower.find(start_tag)
    if start == -1:
        return svg
    end = lower.find(end_tag, start)
    if end == -1:
        return svg
    end += len(end_tag)
    return svg[:start] + svg[end:]


def _page_is_vector_heavy(page: fitz.Page) -> bool:
    """Return ``True`` when vector/text dominates *page*."""
    drawings = page.get_drawings()
    images = page.get_images(full=True)
    text = page.get_text("text").strip()
    vector_elements = len(drawings) + (1 if text else 0)
    image_count = len(images)
    if image_count == 0:
        return True
    if vector_elements == 0:
        return False
    ratio = image_count / (image_count + vector_elements)
    return ratio < VECTOR_DOMINANCE_THRESHOLD


def _export_page_as_svg(
    page: fitz.Page,
    dpi: int,
    out_path: Path,
    max_bytes: int,
) -> tuple[bool, int, PageExportAttempt]:
    """Attempt to export *page* to SVG."""
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    svg = page.get_svg_image(matrix=matrix, text_as_path=True)
    svg = _remove_svg_metadata(svg)
    data = svg.encode("utf-8")
    out_path.write_bytes(data)
    size = len(data)
    attempt = PageExportAttempt(
        dpi=dpi,
        fmt="SVG",
        size_bytes=size,
        encoder="svg",
        lossless=True,
    )
    within_limit = size <= max_bytes
    return within_limit, size, attempt


def _iter_webp_candidates(
    image: Image.Image,
) -> Iterator[tuple[str, bytes, PageExportAttempt]]:
    """Yield WebP encoding attempts for ``image``."""
    try:
        lossless_bytes = encode_webp(image, lossless=True, quality=None)
    except Exception:  # pragma: no cover - WebP encoding may fail unexpectedly  # pdf-toolbox: guard against environment-specific WebP encoder issues | issue:-
        logger.exception("WebP lossless export failed")
    else:
        attempt = PageExportAttempt(
            dpi=0,
            fmt="WEBP",
            size_bytes=0,
            encoder="webp",
            lossless=True,
        )
        yield "WEBP", lossless_bytes, attempt

    for quality in (95, 90, 85):
        try:
            webp_bytes = encode_webp(image, lossless=False, quality=quality)
        except Exception:  # pragma: no cover - guard for Pillow edge cases  # pdf-toolbox: Pillow sometimes lacks WebP support | issue:-
            logger.exception("WebP quality export failed", exc_info=True)
            continue
        attempt = PageExportAttempt(
            dpi=0,
            fmt="WEBP",
            size_bytes=0,
            encoder="webp",
            quality=quality,
            lossless=False,
        )
        yield "WEBP", webp_bytes, attempt


def _iter_png_candidates(
    image: Image.Image, palette: bool
) -> Iterator[tuple[str, bytes, PageExportAttempt]]:
    """Yield PNG encoding attempts for ``image``."""
    try:
        png_bytes = encode_png(image, palette=palette)
    except Exception:  # pragma: no cover - guard for Pillow edge cases  # pdf-toolbox: PNG encoder failure varies by platform | issue:-
        logger.exception("PNG export failed", exc_info=True)
        return
    attempt = PageExportAttempt(
        dpi=0,
        fmt="PNG",
        size_bytes=0,
        encoder="png",
        lossless=True,
    )
    yield "PNG", png_bytes, attempt


def _iter_jpeg_candidates(
    image: Image.Image,
) -> Iterator[tuple[str, bytes, PageExportAttempt]]:
    """Yield JPEG encoding attempts for ``image``."""
    for quality in (95, 90):
        try:
            jpeg_bytes = encode_jpeg(image, quality=quality)
        except Exception:  # pragma: no cover - guard for Pillow edge cases  # pdf-toolbox: JPEG encoder may be unavailable | issue:-
            logger.exception("JPEG export failed", exc_info=True)
            continue
        attempt = PageExportAttempt(
            dpi=0,
            fmt="JPEG",
            size_bytes=0,
            encoder="jpeg",
            quality=quality,
            lossless=False,
        )
        yield "JPEG", jpeg_bytes, attempt


def _encode_raster(
    image: Image.Image,
    max_bytes: int,
    allow_transparency: bool,
    *,
    apply_unsharp: bool = True,
) -> tuple[bytes, str, PageExportAttempt, list[PageExportAttempt], bool]:
    """Encode ``image`` using preferred formats under ``max_bytes``."""
    working_image = apply_unsharp_mask(image) if apply_unsharp else image
    attempts: list[PageExportAttempt] = []
    best: tuple[int, bytes, str, PageExportAttempt] | None = None

    def record_candidate(
        fmt: str,
        data: bytes,
        attempt: PageExportAttempt,
    ) -> tuple[bytes, str, PageExportAttempt, list[PageExportAttempt], bool] | None:
        nonlocal best

        size = len(data)
        attempt.size_bytes = size
        attempts.append(attempt)
        if size <= max_bytes:
            return data, fmt, attempt, list(attempts), True
        if best is None or size < best[0]:
            best = (size, data, fmt, attempt)
        return None

    for fmt, data, attempt in _iter_webp_candidates(working_image):
        result = record_candidate(fmt, data, attempt)
        if result is not None:
            return result

    palette = working_image.mode not in {"RGBA", "LA"}
    for fmt, data, attempt in _iter_png_candidates(working_image, palette):
        result = record_candidate(fmt, data, attempt)
        if result is not None:
            return result

    if not allow_transparency:
        for fmt, data, attempt in _iter_jpeg_candidates(working_image):
            result = record_candidate(fmt, data, attempt)
            if result is not None:
                return result

    if best is None:
        raise RuntimeError(NO_RASTER_ENCODER_MSG)

    size, data, fmt, attempt = best
    attempt.size_bytes = size
    return data, fmt, attempt, attempts, False


def _binary_search_dpi_candidates(
    page: fitz.Page,
    min_dpi: int,
    max_dpi: int,
    max_bytes: int,
    attempts: list[PageExportAttempt],
) -> list[int]:
    """Return promising DPI values discovered via binary search."""
    low = min_dpi
    high = max_dpi
    best_within_dpi: int | None = None
    best_any: tuple[int, int] | None = None

    while low <= high:
        dpi = (low + high) // 2
        image = render_page_image(page, dpi, keep_alpha=True)
        allow_transparency = image.mode in {"RGBA", "LA"}
        data, _fmt, _selected, encode_attempts, within = _encode_raster(
            image,
            max_bytes,
            allow_transparency=allow_transparency,
            apply_unsharp=False,
        )
        for attempt in encode_attempts:
            attempt.dpi = dpi
        attempts.extend(encode_attempts)
        size = len(data)
        if within:
            best_within_dpi = (
                dpi if best_within_dpi is None else max(best_within_dpi, dpi)
            )
            low = dpi + 25
        else:
            if (
                best_any is None
                or size < best_any[0]
                or (size == best_any[0] and dpi < best_any[1])
            ):
                best_any = (size, dpi)
            high = dpi - 25

    candidates: list[int] = []
    if best_within_dpi is not None:
        candidates.append(best_within_dpi)
    if best_any is not None and best_any[1] not in candidates:
        candidates.append(best_any[1])
    return candidates


def _finalise_candidate(
    page: fitz.Page,
    dpi: int,
    max_bytes: int,
    attempts: list[PageExportAttempt],
) -> tuple[bytes, str, PageExportAttempt, bool, int, int]:
    """Render and encode ``page`` at ``dpi`` capturing result metadata."""
    image = render_page_image(page, dpi, keep_alpha=True)
    allow_transparency = image.mode in {"RGBA", "LA"}
    data, fmt, selected_attempt, encode_attempts, within = _encode_raster(
        image,
        max_bytes,
        allow_transparency=allow_transparency,
        apply_unsharp=True,
    )
    for attempt in encode_attempts:
        attempt.dpi = dpi
    attempts.extend(encode_attempts)
    return data, fmt, selected_attempt, within, image.width, image.height


def _select_raster_output(
    page: fitz.Page,
    max_bytes: int,
    attempts: list[PageExportAttempt],
    candidate_dpis: list[int],
    min_dpi: int,
) -> tuple[bytes, str, PageExportAttempt | None, int, int, bool, int]:
    """Evaluate candidates and choose the final raster export."""
    tested_dpis: set[int] = set()
    final_data = b""
    final_fmt = ""
    final_attempt: PageExportAttempt | None = None
    final_within = False
    final_width = 0
    final_height = 0
    dpi_used = candidate_dpis[0]

    def refine(
        start_dpi: int,
    ) -> tuple[int, bytes, str, PageExportAttempt | None, bool, int, int]:
        """Try progressively lower DPIs when results exceed the size limit."""
        refined_data = b""
        refined_fmt = ""
        refined_attempt: PageExportAttempt | None = None
        refined_within = False
        refined_width = 0
        refined_height = 0
        dpi = start_dpi

        while dpi > min_dpi:
            next_dpi = max(min_dpi, dpi - 25)
            if next_dpi in tested_dpis and next_dpi == dpi:
                break
            if next_dpi in tested_dpis:
                dpi = next_dpi
                continue
            (
                refined_data,
                refined_fmt,
                refined_attempt,
                refined_within,
                refined_width,
                refined_height,
            ) = _finalise_candidate(page, next_dpi, max_bytes, attempts)
            tested_dpis.add(next_dpi)
            dpi = next_dpi
            if refined_within or dpi == min_dpi:
                break

        return (
            dpi,
            refined_data,
            refined_fmt,
            refined_attempt,
            refined_within,
            refined_width,
            refined_height,
        )

    for dpi in candidate_dpis:
        (
            final_data,
            final_fmt,
            final_attempt,
            final_within,
            final_width,
            final_height,
        ) = _finalise_candidate(page, dpi, max_bytes, attempts)
        tested_dpis.add(dpi)
        dpi_used = dpi
        if final_within:
            return (
                final_data,
                final_fmt,
                final_attempt,
                final_width,
                final_height,
                final_within,
                dpi_used,
            )

    fallback = (
        final_data,
        final_fmt,
        final_attempt,
        final_width,
        final_height,
        final_within,
        dpi_used,
    )

    if dpi_used <= min_dpi:
        return fallback

    (
        refined_dpi,
        final_data,
        final_fmt,
        final_attempt,
        final_within,
        final_width,
        final_height,
    ) = refine(dpi_used)

    if final_attempt is None or not final_data:
        return fallback

    return (
        final_data,
        final_fmt,
        final_attempt,
        final_width,
        final_height,
        final_within,
        refined_dpi,
    )


def _rasterise_page(
    page: fitz.Page,
    profile: ExportProfile,
    max_bytes: int,
    *,
    attempts: list[PageExportAttempt],
) -> tuple[bytes, str, int, int, int, bool, bool]:
    """Return encoded raster bytes for *page* respecting ``profile``."""
    effective_min_dpi, effective_max_dpi = _calculate_dpi_window(page, profile)
    candidate_dpis = _binary_search_dpi_candidates(
        page,
        effective_min_dpi,
        effective_max_dpi,
        max_bytes,
        attempts,
    )
    if not candidate_dpis:
        raise RuntimeError(NO_RASTER_ATTEMPT_MSG)

    (
        final_data,
        final_fmt,
        final_attempt,
        final_width,
        final_height,
        final_within,
        dpi_used,
    ) = _select_raster_output(
        page,
        max_bytes,
        attempts,
        candidate_dpis,
        effective_min_dpi,
    )

    if final_attempt is None:
        raise RuntimeError(NO_RASTER_ATTEMPT_MSG)

    resolution_limited = effective_max_dpi < profile.min_dpi
    return (
        final_data,
        final_fmt,
        dpi_used,
        final_width,
        final_height,
        final_within,
        resolution_limited,
    )


def _export_page(
    doc: fitz.Document,
    page_number: int,
    out_base: Path,
    profile: ExportProfile,
    max_bytes: int,
) -> PageExportResult:
    """Export a single page and return its result."""
    page = doc.load_page(page_number - 1)
    result = PageExportResult(
        page=page_number,
        output_path=None,
        width_px=None,
        height_px=None,
        dpi=None,
        fmt=None,
        filesize_bytes=0,
        vector_export=False,
    )

    vector_first = _page_is_vector_heavy(page)
    stem = Path(doc.name).stem or "page"
    ext = "svg" if vector_first else "webp"
    out_path = out_base / f"{stem}_Page_{page_number}.{ext}"
    try:
        if vector_first:
            within, size, attempt = _export_page_as_svg(
                page,
                profile.render_dpi,
                out_path,
                max_bytes,
            )
            result.filesize_bytes = size
            result.vector_export = True
            result.attempts.append(attempt)
            if within:
                logger.info(
                    "Page %d exported as SVG (%.1f MB)",
                    page_number,
                    size / (1024 * 1024),
                )
                rect = page.rect
                width_px = int(rect.width / 72 * profile.render_dpi)
                height_px = int(rect.height / 72 * profile.render_dpi)
                result.width_px = width_px
                result.height_px = height_px
                result.dpi = profile.render_dpi
                result.fmt = "SVG"
                result.output_path = out_path
                return result
            result.warnings.append(
                "SVG exceeded size limit; falling back to raster pipeline",
            )
            out_path.unlink(missing_ok=True)

        attempts: list[PageExportAttempt] = []
        (
            data,
            fmt,
            dpi,
            width_px,
            height_px,
            within,
            resolution_limited,
        ) = _rasterise_page(
            page,
            profile,
            max_bytes,
            attempts=attempts,
        )
        result.attempts.extend(attempts)
        out_path = out_base / f"{stem}_Page_{page_number}.{fmt.lower()}"
        out_path.write_bytes(data)
        size = len(data)
        result.filesize_bytes = size
        result.width_px = width_px
        result.height_px = height_px
        result.dpi = dpi
        result.fmt = fmt
        result.output_path = out_path
        if not within:
            result.warnings.append(
                "File exceeds limit at minimum acceptable sharpness",
            )
        if resolution_limited or (dpi and dpi < profile.min_dpi):
            result.warnings.append(
                "Clamped by Miro dimension limits (max 8192x4096 @ 32 MP)",
            )
    except Exception as exc:  # pragma: no cover - defensive against rendering edge cases  # pdf-toolbox: keep GUI responsive despite renderer crashes | issue:-
        logger.exception("Failed to export page %d", page_number)
        result.error = str(exc)
        result.warnings.append(f"Export failed: {exc}")
        out_path.unlink(missing_ok=True)
        return result
    else:
        logger.info(
            "Page %d exported as %s (%dx%d @ %d dpi, %.1f MB)%s",
            page_number,
            fmt,
            width_px,
            height_px,
            dpi,
            size / (1024 * 1024),
            " [warning]" if result.warnings else "",
        )
        return result


def export_pdf_for_miro(
    input_pdf: str,
    out_dir: str | None = None,
    *,
    pages: str | None = None,
    profile: ExportProfile = PROFILE_MIRO,
    cancel: Event | None = None,
) -> MiroExportOutcome:
    """Export ``input_pdf`` pages using ``PROFILE_MIRO`` constraints.

    Args:
        input_pdf: PDF file to export.
        out_dir: Optional target directory for output images.
        pages: Optional page specification string (``"1-3,5"`` style).
        profile: Export profile controlling rendering heuristics.
        cancel: Optional event used for cooperative cancellation.

    Returns:
        MiroExportOutcome: Result containing exported files and metadata.
    """
    doc = open_pdf(input_pdf)
    with doc:
        raise_if_cancelled(cancel, doc)
        if pages:
            page_numbers = parse_page_spec(pages, doc.page_count)
        else:
            page_numbers = list(range(1, doc.page_count + 1))
        out_base = sane_output_dir(input_pdf, out_dir)
        manifest_path = out_base / "miro_export.json"
        results: list[PageExportResult] = []
        files: list[str] = []
        warnings: list[str] = []

        for page_no in page_numbers:
            raise_if_cancelled(cancel, doc)
            res = _export_page(doc, page_no, out_base, profile, profile.max_bytes)
            results.append(res)
            if res.output_path:
                files.append(str(res.output_path))
            warnings.extend(res.warnings)
        manifest_data = [entry.to_manifest_entry() for entry in results]
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
        if warnings:
            logger.warning("Warnings during export: %s", "; ".join(warnings))
        return MiroExportOutcome(
            files=files,
            manifest=manifest_path,
            page_results=results,
            warnings=warnings,
        )


__all__ = [
    "PROFILE_MIRO",
    "ExportProfile",
    "MiroExportOutcome",
    "PageExportAttempt",
    "PageExportResult",
    "export_pdf_for_miro",
]
