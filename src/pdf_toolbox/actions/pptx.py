"""PPTX manipulation actions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from pdf_toolbox.actions import action
from pdf_toolbox.actions.pdf_images import (
    PdfImageOptions,
    QualityChoice,
    pdf_to_images,
    resolve_image_settings,
)
from pdf_toolbox.renderers.pptx import require_pptx_renderer
from pdf_toolbox.renderers.registry import convert_pptx_to_pdf


@dataclass(slots=True)
class PptxExportOptions:
    """Options describing PPTX to image exports."""

    pages: str | None = None
    image_format: Literal["PNG", "JPEG", "TIFF"] = "JPEG"
    quality: int | QualityChoice = "High (95)"
    width: int | None = None
    height: int | None = None
    max_size_mb: float | None = None
    out_dir: str | None = None


@action(category="PPTX", requires_pptx_renderer=True)
def pptx_to_images(
    input_pptx: str,
    options: PptxExportOptions | None = None,
) -> str:
    """Render a PPTX file to images using the configured provider.

    Args:
        input_pptx: Presentation to render.
        options: Dataclass describing rendering behaviour.

    Returns:
        Path to the directory containing the images.
    """
    opts = options or PptxExportOptions()
    fmt, quality_val, _dpi = resolve_image_settings(
        opts.image_format,
        opts.quality,
        allowed_formats={"PNG", "JPEG", "TIFF"},
    )
    fmt_literal = cast(Literal["PNG", "JPEG", "TIFF"], fmt)
    target_out_dir = (
        Path(opts.out_dir)
        if opts.out_dir is not None
        else Path(input_pptx).resolve().parent
    )

    with convert_pptx_to_pdf(input_pptx) as pdf_path:
        image_options = PdfImageOptions(
            pages=opts.pages,
            image_format=fmt_literal,
            quality=quality_val,
            max_size_mb=opts.max_size_mb,
            out_dir=str(target_out_dir),
            width=opts.width,
            height=opts.height,
        )
        outputs = pdf_to_images(pdf_path, image_options)
        result_dir = Path(outputs[0]).parent if outputs else target_out_dir
    return str(result_dir)


@action(category="PPTX", requires_pptx_renderer=True)
def pptx_to_pdf(
    input_pptx: str, pages: str | None = None, output_path: str | None = None
) -> str:
    """Render a PPTX file to PDF using the configured provider."""
    renderer = require_pptx_renderer()
    return renderer.to_pdf(input_pptx, output_path=output_path, range_spec=pages)


__all__ = [
    "PptxExportOptions",
    "pptx_to_images",
    "pptx_to_pdf",
]
