"""Actions for exporting slides using Miro-specific profiles."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Literal

from pdf_toolbox.actions import action
from pdf_toolbox.actions.pdf_images import (
    DpiChoice,
    QualityChoice,
    pdf_to_images,
    resolve_image_settings,
)
from pdf_toolbox.i18n import tr
from pdf_toolbox.miro import PROFILE_MIRO, export_pdf_for_miro
from pdf_toolbox.paths import validate_path
from pdf_toolbox.renderers.pptx import require_pptx_renderer
from pdf_toolbox.utils import logger, sane_output_dir

ProfileChoice = Literal["custom", "miro"]
ImageFormatChoice = Literal["PNG", "JPEG", "TIFF", "WEBP", "SVG"]


@dataclass(slots=True)
class MiroExportOptions:
    """Options exposed by the :func:`miro_export` action."""

    pages: str | None = None
    export_profile: ProfileChoice = "miro"
    image_format: ImageFormatChoice = "PNG"
    dpi: int | DpiChoice = "High (300 dpi)"
    quality: int | QualityChoice = "High (95)"
    out_dir: str | None = None
    write_manifest: bool = False


@action(name="miro_export", category="Export")
def miro_export(
    input_path: str,
    options: MiroExportOptions | None = None,
    *,
    cancel: Event | None = None,
) -> list[str]:
    """Export slides using either the custom or Miro profile.

    Args:
        input_path: PDF or PPTX file to export.
        options: Dataclass describing the export behaviour.
        cancel: Optional cancellation event.

    Returns:
        list[str]: Paths to generated files.
    """
    opts = options or MiroExportOptions()
    source = validate_path(input_path, must_exist=True)
    suffix = source.suffix.lower()
    if suffix not in {".pdf", ".pptx"}:
        msg = tr("miro_unsupported_input", suffix=suffix)
        raise ValueError(msg)

    logger.info("Exporting %s using profile %s", source, opts.export_profile)

    target_dir = sane_output_dir(source, opts.out_dir)
    target_dir_str = str(target_dir)

    def export_pdf_path(pdf_path: Path, override_out_dir: str | None) -> list[str]:
        """Export *pdf_path* using the configured profile."""
        if opts.export_profile == "custom":
            fmt, quality_val, dpi_val = resolve_image_settings(
                opts.image_format,
                opts.quality,
                opts.dpi,
            )
            return pdf_to_images(
                str(pdf_path),
                pages=opts.pages,
                dpi=dpi_val,
                image_format=fmt,
                quality=quality_val,
                out_dir=override_out_dir,
                cancel=cancel,
            )

        outcome = export_pdf_for_miro(
            str(pdf_path),
            out_dir=override_out_dir,
            pages=opts.pages,
            profile=PROFILE_MIRO,
            cancel=cancel,
            write_manifest=opts.write_manifest,
        )
        if outcome.manifest:
            logger.info("Manifest written to %s", outcome.manifest)
        return outcome.files

    if suffix == ".pptx":
        renderer = require_pptx_renderer()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_pdf = Path(tmp_dir) / f"{source.stem}.pdf"
            pdf_path = Path(renderer.to_pdf(str(source), output_path=str(tmp_pdf)))
            return export_pdf_path(pdf_path, target_dir_str)

    return export_pdf_path(source, target_dir_str)


__all__ = ["MiroExportOptions", "miro_export"]
