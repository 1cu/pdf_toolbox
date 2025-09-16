"""Actions for exporting slides using Miro-specific profiles."""

from __future__ import annotations

import tempfile
from pathlib import Path
from threading import Event
from typing import Literal

from pdf_toolbox.actions import action
from pdf_toolbox.actions.images import (
    DpiChoice,
    QualityChoice,
    pdf_to_images,
    resolve_image_settings,
)
from pdf_toolbox.miro import PROFILE_MIRO, export_pdf_for_miro
from pdf_toolbox.paths import validate_path
from pdf_toolbox.renderers.pptx import get_pptx_renderer
from pdf_toolbox.utils import logger, sane_output_dir

ProfileChoice = Literal["standard", "miro"]
ImageFormatChoice = Literal["PNG", "JPEG", "TIFF", "WEBP", "SVG"]


@action(name="miro_export", category="Export")
def miro_export(  # noqa: PLR0913  # pdf-toolbox: action signature mirrors GUI form | issue:-
    input_path: str,
    out_dir: str | None = None,
    export_profile: ProfileChoice = "standard",
    image_format: ImageFormatChoice = "PNG",
    dpi: int | DpiChoice = "High (300 dpi)",
    quality: int | QualityChoice = "High (95)",
    pages: str | None = None,
    cancel: Event | None = None,
) -> list[str]:
    """Export slides using either the standard or Miro profile.

    Args:
        input_path: PDF or PPTX file to export.
        out_dir: Optional target directory for exported files.
        export_profile: Export profile to use (``"standard"`` or ``"miro"``).
        image_format: Output image format when using the standard profile.
        dpi: DPI or preset for the standard profile.
        quality: Quality preset/value for lossy formats in the standard profile.
        pages: Optional page specification string (``"1-3,5"`` style).
        cancel: Optional cancellation event.

    Returns:
        list[str]: Paths to generated files.
    """
    source = validate_path(input_path, must_exist=True)
    suffix = source.suffix.lower()
    if suffix not in {".pdf", ".pptx"}:
        msg = f"Unsupported input type: {suffix}"
        raise ValueError(msg)

    logger.info("Exporting %s using profile %s", source, export_profile)

    def export_pdf_path(pdf_path: Path, override_out_dir: str | None) -> list[str]:
        """Export *pdf_path* using the configured profile."""
        if export_profile == "standard":
            fmt, quality_val, dpi_val = resolve_image_settings(
                image_format,
                quality,
                dpi,
            )
            return pdf_to_images(
                str(pdf_path),
                pages=pages,
                dpi=dpi_val,
                image_format=fmt,
                quality=quality_val,
                out_dir=override_out_dir,
                cancel=cancel,
            )

        outcome = export_pdf_for_miro(
            str(pdf_path),
            out_dir=override_out_dir,
            pages=pages,
            profile=PROFILE_MIRO,
            cancel=cancel,
        )
        logger.info("Manifest written to %s", outcome.manifest)
        return outcome.files

    if suffix == ".pptx":
        renderer = get_pptx_renderer()
        target_dir = sane_output_dir(source, out_dir)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_pdf = Path(tmp_dir) / f"{source.stem}.pdf"
            pdf_path = Path(renderer.to_pdf(str(source), output_path=str(tmp_pdf)))
            return export_pdf_path(pdf_path, str(target_dir))

    return export_pdf_path(source, out_dir)


__all__ = ["miro_export"]
