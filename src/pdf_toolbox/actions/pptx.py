"""PPTX manipulation actions."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

from pdf_toolbox.actions import action
from pdf_toolbox.actions.pdf_images import (
    QualityChoice,
    pdf_to_images,
    resolve_image_settings,
)
from pdf_toolbox.renderers.pptx import require_pptx_renderer
from pdf_toolbox.renderers.registry import convert_pptx_to_pdf


@action(category="PPTX", requires_pptx_renderer=True)
def pptx_to_images(  # noqa: PLR0913  # pdf-toolbox: action interface requires many parameters | issue:-
    input_pptx: str,
    out_dir: str | None = None,
    max_size_mb: float | None = None,
    image_format: Literal["PNG", "JPEG", "TIFF"] = "JPEG",
    quality: int | QualityChoice = "High (95)",
    width: int | None = None,
    height: int | None = None,
    pages: str | None = None,
) -> str:
    """Render a PPTX file to images using the configured provider.

    Args:
        input_pptx: Presentation to render.
        out_dir: Destination directory for exported images.
        max_size_mb: Optional size limit per image in megabytes.
        image_format: Output image format (``"JPEG"``, ``"PNG"``, or ``"TIFF"``).
        quality: JPEG/WebP quality (ignored for other formats).
        width: Optional pixel width; requires ``height``.
        height: Optional pixel height; requires ``width``.
        pages: Optional slide selection using the same syntax as PDF exports.

    Returns:
        Path to the directory containing the images.
    """
    fmt, quality_val, _dpi = resolve_image_settings(
        image_format,
        quality,
        allowed_formats={"PNG", "JPEG", "TIFF"},
    )
    fmt_literal = cast(Literal["PNG", "JPEG", "TIFF"], fmt)
    target_out_dir = (
        Path(out_dir) if out_dir is not None else Path(input_pptx).resolve().parent
    )

    with convert_pptx_to_pdf(input_pptx) as pdf_path:
        outputs = pdf_to_images(
            pdf_path,
            pages=pages,
            image_format=fmt_literal,
            quality=quality_val,
            max_size_mb=max_size_mb,
            out_dir=target_out_dir,
            width=width,
            height=height,
        )
        result_dir = Path(outputs[0]).parent if outputs else target_out_dir
    return str(result_dir)


@action(category="PPTX", requires_pptx_renderer=True)
def pptx_to_pdf(
    input_pptx: str, output_path: str | None = None, pages: str | None = None
) -> str:
    """Render a PPTX file to PDF using the configured provider."""
    renderer = require_pptx_renderer()
    return renderer.to_pdf(input_pptx, output_path=output_path, range_spec=pages)


__all__ = [
    "pptx_to_images",
    "pptx_to_pdf",
]
