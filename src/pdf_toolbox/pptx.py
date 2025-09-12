"""PowerPoint conversion helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from threading import Event
from typing import Literal

from pdf_toolbox.actions import action
from pdf_toolbox.utils import parse_page_spec, raise_if_cancelled, sane_output_dir


def _pptx_to_images_via_powerpoint(  # pragma: no cover - requires Windows + PowerPoint  # noqa: PLR0913
    pptx_path: str,
    image_format: Literal["PNG", "JPEG", "TIFF", "SVG"],
    width: int = 3840,
    height: int = 2160,
    slides: str | None = None,
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> list[str]:
    """Export slides via PowerPoint."""
    fmt = image_format.upper()
    export_map = {"PNG": "PNG", "JPEG": "JPG", "TIFF": "TIF", "SVG": "SVG"}
    if fmt not in export_map:
        raise ValueError(
            "Unsupported image format "
            f"'{image_format}'. Supported formats: {', '.join(export_map)}"
        )
    import win32com.client  # type: ignore  # noqa: PLC0415

    out_base = sane_output_dir(pptx_path, out_dir)
    stem = Path(pptx_path).stem
    target_dir = out_base / f"{stem}_{fmt.lower()}"
    target_dir.mkdir(parents=True, exist_ok=True)

    ppt = win32com.client.Dispatch("PowerPoint.Application")
    presentation = ppt.Presentations.Open(pptx_path, WithWindow=False)
    try:
        total = presentation.Slides.Count
        slide_numbers = parse_page_spec(slides, total)
        outputs: list[str] = []
        for i in slide_numbers:
            raise_if_cancelled(cancel)  # pragma: no cover
            slide = presentation.Slides(i)
            out_path = target_dir / f"{stem}_Slide_{i}.{fmt.lower()}"
            slide.Export(str(out_path), export_map[fmt], width, height)
            outputs.append(str(out_path))
    finally:
        presentation.Close()
        ppt.Quit()
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
    """Export slides of a PPTX presentation as images via PowerPoint.

    Microsoft PowerPoint renders the selected ``slides`` of ``pptx_path`` and
    exports them to ``image_format`` files. ``width`` and ``height`` define the
    resolution in pixels. ``slides`` accepts comma-separated ranges like
    ``"1,3-5"``; ``None`` exports all slides. The returned list contains the
    paths to the generated image files. The function only works on Windows
    systems with PowerPoint installed.
    """
    if sys.platform != "win32":
        raise RuntimeError("PPTX→images requires Windows and PowerPoint.")
    return _pptx_to_images_via_powerpoint(
        pptx_path,
        image_format,
        width=width,
        height=height,
        slides=slides,
        out_dir=out_dir,
        cancel=cancel,
    )  # pragma: no cover - Windows only


__all__ = ["pptx_to_images"]
