"""Miro export pipeline for PDF and PPTX slides."""

from __future__ import annotations

import dataclasses
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event

import fitz  # type: ignore  # pdf-toolbox: PyMuPDF lacks type hints | issue:-
from PIL import Image, ImageFilter

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


PROFILE_MIRO = ExportProfile(
    name="miro",
    max_bytes=40 * 1024 * 1024,
    target_zoom=4.0,
    min_effective_dpi=200,
    render_dpi=800,
    max_dpi=1200,
)


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
    cleaned = svg[:start] + svg[end:]
    return cleaned


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
    return ratio < 0.4


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


def _apply_unsharp(image: Image.Image) -> Image.Image:
    """Return a mildly sharpened copy of ``image``."""

    return image.filter(ImageFilter.UnsharpMask(radius=0.6, percent=50, threshold=3))


def _render_page_bitmap(page: fitz.Page, dpi: int) -> Image.Image:
    """Render *page* to a PIL image at *dpi* keeping transparency."""

    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=True)
    if pix.colorspace is None or pix.colorspace.n not in (1, 3):
        pix = fitz.Pixmap(fitz.csRGB, pix)
    mode = "RGBA" if pix.alpha else "RGB"
    img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
    return _apply_unsharp(img)


def _encode_webp(
    image: Image.Image,
    *,
    lossless: bool,
    quality: int | None,
) -> bytes:
    """Return WEBP-encoded bytes for ``image``."""

    with io.BytesIO() as buf:
        save_args: dict[str, object] = {"format": "WEBP", "method": 6}
        if lossless:
            save_args["lossless"] = True
        if quality is not None:
            save_args["quality"] = quality
        image.save(buf, **save_args)
        return buf.getvalue()


def _encode_png(image: Image.Image, palette: bool) -> bytes:
    """Return PNG-encoded bytes for ``image``."""

    target = image
    if palette and image.mode not in {"P", "L"}:
        target = image.convert("P", palette=Image.Palette.ADAPTIVE)
    with io.BytesIO() as buf:
        target.save(buf, format="PNG", compress_level=9, optimize=True)
        return buf.getvalue()


def _encode_jpeg(image: Image.Image, quality: int) -> bytes:
    """Return JPEG-encoded bytes for ``image``."""

    rgb = image.convert("RGB")
    with io.BytesIO() as buf:
        rgb.save(buf, format="JPEG", quality=quality, subsampling=0)
        return buf.getvalue()


def _encode_raster(
    image: Image.Image,
    max_bytes: int,
    allow_transparency: bool,
) -> tuple[bytes, str, PageExportAttempt, bool]:
    """Encode ``image`` using preferred formats under ``max_bytes``."""

    attempts: list[tuple[str, bytes, PageExportAttempt]] = []

    try:
        lossless_bytes = _encode_webp(image, lossless=True, quality=None)
        attempts.append(
            (
                "WEBP",
                lossless_bytes,
                PageExportAttempt(
                    dpi=0,
                    fmt="WEBP",
                    size_bytes=len(lossless_bytes),
                    encoder="webp",
                    lossless=True,
                ),
            )
        )
    except Exception:  # pragma: no cover - WebP encoding may fail unexpectedly
        logger.exception("WebP lossless export failed")

    for quality in (95, 90, 85):
        try:
            webp_bytes = _encode_webp(image, lossless=False, quality=quality)
        except Exception:  # pragma: no cover - guard for Pillow edge cases
            logger.exception("WebP quality export failed", exc_info=True)
            continue
        attempts.append(
            (
                "WEBP",
                webp_bytes,
                PageExportAttempt(
                    dpi=0,
                    fmt="WEBP",
                    size_bytes=len(webp_bytes),
                    encoder="webp",
                    quality=quality,
                    lossless=False,
                ),
            )
        )

    png_palette = image.mode not in {"RGBA", "LA"}
    try:
        png_bytes = _encode_png(image, palette=png_palette)
        attempts.append(
            (
                "PNG",
                png_bytes,
                PageExportAttempt(
                    dpi=0,
                    fmt="PNG",
                    size_bytes=len(png_bytes),
                    encoder="png",
                    lossless=True,
                ),
            )
        )
    except Exception:  # pragma: no cover - guard for Pillow edge cases
        logger.exception("PNG export failed", exc_info=True)

    if not allow_transparency:
        for quality in (95, 90):
            try:
                jpeg_bytes = _encode_jpeg(image, quality)
            except Exception:  # pragma: no cover - guard for Pillow edge cases
                logger.exception("JPEG export failed", exc_info=True)
                continue
            attempts.append(
                (
                    "JPEG",
                    jpeg_bytes,
                    PageExportAttempt(
                        dpi=0,
                        fmt="JPEG",
                        size_bytes=len(jpeg_bytes),
                        encoder="jpeg",
                        quality=quality,
                    ),
                )
            )

    best = min(attempts, key=lambda item: item[2].size_bytes, default=None)
    if best is None:
        raise RuntimeError("no raster encoders produced output")

    for fmt, data, attempt in attempts:
        if attempt.size_bytes <= max_bytes:
            attempt.lossless = attempt.lossless if attempt.fmt != "JPEG" else False
            return data, fmt, attempt, True

    chosen_fmt, chosen_data, chosen_attempt = best
    chosen_attempt.lossless = chosen_attempt.lossless if chosen_fmt != "JPEG" else False
    return chosen_data, chosen_fmt, chosen_attempt, False


def _rasterise_page(
    page: fitz.Page,
    profile: ExportProfile,
    max_bytes: int,
    *,
    attempts: list[PageExportAttempt],
) -> tuple[bytes, str, int, int, int, bool]:
    """Return encoded raster bytes for *page* respecting ``profile``."""

    min_dpi = profile.min_dpi
    low = min_dpi
    high = profile.max_dpi
    best_within: tuple[bytes, str, int, int, int, PageExportAttempt] | None = None
    best_any: tuple[bytes, str, int, int, int, PageExportAttempt] | None = None

    while low <= high:
        dpi = (low + high) // 2
        image = _render_page_bitmap(page, dpi)
        allow_transparency = image.mode in {"RGBA", "LA"}
        data, fmt, attempt, within = _encode_raster(
            image,
            max_bytes,
            allow_transparency=allow_transparency,
        )
        attempt.dpi = dpi
        attempts.append(attempt)
        size = len(data)
        result = (data, fmt, dpi, image.width, image.height, attempt)
        if within:
            best_within = result
            low = dpi + 25
        else:
            best_any = result
            high = dpi - 25

    if best_within:
        data, fmt, dpi, width, height, attempt = best_within
    elif best_any:
        data, fmt, dpi, width, height, attempt = best_any
    else:
        raise RuntimeError("no raster attempt produced output")

    return data, fmt, dpi, width, height, len(data) <= max_bytes


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
        data, fmt, dpi, width_px, height_px, within = _rasterise_page(
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
    except Exception as exc:  # pragma: no cover - defensive against rendering edge cases
        logger.exception("Failed to export page %d", page_number)
        result.error = str(exc)
        result.warnings.append(f"Export failed: {exc}")
        out_path.unlink(missing_ok=True)
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
    "ExportProfile",
    "MiroExportOutcome",
    "PROFILE_MIRO",
    "PageExportAttempt",
    "PageExportResult",
    "export_pdf_for_miro",
]
