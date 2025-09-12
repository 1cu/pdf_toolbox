"""Render PDF pages to raster images."""

from __future__ import annotations

import io
import shutil
import subprocess
import sys
import tempfile
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Event
from typing import Literal

import fitz  # type: ignore
from PIL import Image
from pptx import Presentation

from pdf_toolbox.actions import action
from pdf_toolbox.utils import (
    open_pdf,
    parse_page_spec,
    raise_if_cancelled,
    sane_output_dir,
)

# Include WebP for better quality/size tradeoffs
SUPPORTED_IMAGE_FORMATS = ["PNG", "JPEG", "TIFF", "WEBP", "SVG"]
PPTX_IMAGE_FORMATS = ["PNG", "JPEG", "TIFF", "SVG"]

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

SCALE_EPS = 0.01


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
def pdf_to_images(  # noqa: PLR0913, PLR0912, PLR0915
    input_pdf: str,
    pages: str | None = None,
    dpi: int | DpiChoice = "High (300 dpi)",
    image_format: Literal["PNG", "JPEG", "TIFF", "WEBP", "SVG"] = "PNG",
    quality: int | QualityChoice = "High (95)",
    max_size_mb: float | None = None,
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> list[str]:
    """Render PDF pages to images.

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
                if fmt == "SVG":
                    svg = page.get_svg_image(matrix=matrix)
                    out_path = out_base / f"{Path(input_pdf).stem}_Page_{page_no}.{ext}"
                    out_path.write_text(svg, encoding="utf-8")
                    outputs.append(str(out_path))
                    continue
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
                                scale_low, scale_high = 0.0, 1.0
                                best_lossy: Image.Image | None = None
                                while scale_high - scale_low > SCALE_EPS:
                                    mid = (scale_low + scale_high) / 2
                                    resized = img.resize(
                                        (
                                            max(1, int(img.width * mid)),
                                            max(1, int(img.height * mid)),
                                        ),
                                        Image.Resampling.LANCZOS,
                                    )
                                    buf = io.BytesIO()
                                    resized.save(buf, format=fmt, quality=1)
                                    if buf.tell() <= max_bytes:
                                        best_lossy = resized  # pragma: no cover
                                        scale_low = mid  # pragma: no cover
                                    else:
                                        scale_high = mid
                                if best_lossy is None:  # pragma: no cover
                                    raise RuntimeError(
                                        "Could not reduce image below max_size_mb",
                                    )
                                img = best_lossy  # pragma: no cover
                                quality_val = 1  # pragma: no cover
                                low = high = 1  # pragma: no cover
                            else:
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
                        if max_bytes is None:
                            save_kwargs["compress_level"] = 0
                        else:
                            save_kwargs["compress_level"] = 9
                    out_path = out_base / f"{Path(input_pdf).stem}_Page_{page_no}.{ext}"
                    if max_bytes is not None:
                        buf = io.BytesIO()
                        img.save(buf, format=fmt, **save_kwargs)
                        if buf.tell() > max_bytes:
                            warnings.warn(
                                "max_size_mb with lossless formats will downscale image dimensions to meet the target size; use JPEG or WebP to keep dimensions",
                                UserWarning,
                                stacklevel=2,
                            )
                            scale_low, scale_high = 0.0, 1.0
                            best_img: Image.Image | None = None
                            while scale_high - scale_low > SCALE_EPS:
                                mid = (scale_low + scale_high) / 2
                                resized = img.resize(
                                    (
                                        max(1, int(img.width * mid)),
                                        max(1, int(img.height * mid)),
                                    ),
                                    Image.Resampling.LANCZOS,
                                )
                                buf = io.BytesIO()
                                resized.save(buf, format=fmt, **save_kwargs)
                                if buf.tell() <= max_bytes:
                                    best_img = resized
                                    scale_low = mid
                                else:
                                    scale_high = mid
                            if best_img is None:  # pragma: no cover
                                raise RuntimeError(
                                    "Could not reduce image below max_size_mb",
                                )
                            img = best_img
                            buf = io.BytesIO()
                            img.save(buf, format=fmt, **save_kwargs)
                        with open(out_path, "wb") as f:
                            f.write(buf.getbuffer())
                    else:
                        img.save(out_path, format=fmt, **save_kwargs)

            outputs.append(str(out_path))
    return outputs


@action(category="Office")
def pptx_to_images(  # noqa: PLR0913
    pptx_path: str,
    image_format: Literal["PNG", "JPEG", "TIFF", "SVG"] = "PNG",
    width: int = 3840,
    height: int = 2160,
    slides: str | None = None,
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> list[str]:
    """Export slides of a PPTX presentation as images using LibreOffice.

    LibreOffice renders ``pptx_path`` to a temporary PDF and
    :func:`pdf_to_images` performs the actual image generation.
    ``width`` and ``height`` specify the target pixel dimensions for each
    slide; ``slides`` may be a comma-separated list or range like ``"1,3-5"``.
    """
    fmt = image_format.upper()
    if fmt not in PPTX_IMAGE_FORMATS:
        raise ValueError(
            f"Unsupported image format '{image_format}'. Supported formats: {', '.join(PPTX_IMAGE_FORMATS)}"
        )
    exe = shutil.which("libreoffice") or shutil.which("soffice")
    if exe is None:
        raise RuntimeError("LibreOffice is required for PPTX to images conversion")

    prs = Presentation(pptx_path)
    total = len(prs.slides)
    slide_numbers = parse_page_spec(slides, total)
    pages_spec = ",".join(str(n) for n in slide_numbers) if slides else None

    slide_w = prs.slide_width
    slide_h = prs.slide_height
    if slide_w is None or slide_h is None:  # pragma: no cover - defensive
        raise RuntimeError("Presentation has no slide dimensions")
    slide_w_in = slide_w / 914400
    slide_h_in = slide_h / 914400
    dpi_x = width / slide_w_in
    dpi_y = height / slide_h_in
    dpi = round(max(dpi_x, dpi_y))

    with tempfile.TemporaryDirectory() as tmpdir:
        raise_if_cancelled(cancel)  # pragma: no cover
        cmd = [
            exe,
            "--headless",
            "--convert-to",
            "pdf",
            pptx_path,
            "--outdir",
            tmpdir,
        ]
        subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603
        pdf_path = Path(tmpdir) / f"{Path(pptx_path).stem}.pdf"
        if not pdf_path.exists():  # pragma: no cover - LibreOffice should create
            raise RuntimeError(
                "LibreOffice failed to create PDF from PPTX"
            )  # pragma: no cover
        return pdf_to_images(
            str(pdf_path),
            pages=pages_spec,
            dpi=dpi,
            image_format=fmt,
            out_dir=out_dir,
            cancel=cancel,
        )


__all__ = [
    "DPI_PRESETS",
    "LOSSY_QUALITY_PRESETS",
    "pdf_to_images",
    "pptx_to_images",
]
