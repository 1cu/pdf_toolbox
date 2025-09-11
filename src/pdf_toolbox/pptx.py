from __future__ import annotations

from pathlib import Path
from typing import Literal
import sys
from threading import Event

from pdf_toolbox.actions import action
from pdf_toolbox.utils import (
    parse_page_spec,
    raise_if_cancelled,
    sane_output_dir,
)


def _pptx_to_images_via_powerpoint(  # pragma: no cover - requires Windows + PowerPoint
    pptx_path: str,
    image_format: Literal["PNG", "JPEG", "TIFF"],
    width: int = 3840,
    height: int = 2160,
    slides: str | None = None,
    out_dir: str | None = None,
    cancel: Event | None = None,
) -> list[str]:
    """Helper: export slides via PowerPoint."""
    import win32com.client  # type: ignore

    fmt = image_format.upper()
    export_map = {"PNG": "PNG", "JPEG": "JPG", "TIFF": "TIF"}
    export_fmt = export_map[fmt]

    out_base = sane_output_dir(pptx_path, out_dir)
    stem = Path(pptx_path).stem
    target_dir = out_base / f"{stem}_{image_format.lower()}"
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
            out_path = target_dir / f"{stem}_Slide_{i}.{image_format.lower()}"
            slide.Export(str(out_path), export_fmt, width, height)
            outputs.append(str(out_path))
    finally:
        presentation.Close()
        ppt.Quit()
    return outputs


if sys.platform == "win32":
    _register_action = action(category="Office")  # pragma: no cover - Windows only
else:

    def _register_action(fn):
        fn.__pdf_toolbox_action__ = True
        return fn


@_register_action
def pptx_to_images_via_powerpoint(
    pptx_path: str,
    image_format: Literal["PNG", "JPEG", "TIFF"] = "PNG",
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


__all__ = ["pptx_to_images_via_powerpoint"]
