from __future__ import annotations

from pathlib import Path
from typing import List, Literal
import sys

from .actions import action
from .utils import sane_output_dir


def _pptx_to_images_via_powerpoint(  # pragma: no cover - requires Windows + PowerPoint
    pptx_path: str,
    image_format: Literal["PNG", "JPEG", "TIFF"],
    width: int = 3840,
    height: int = 2160,
    start_slide: int | None = None,
    end_slide: int | None = None,
    out_dir: str | None = None,
) -> List[str]:
    """Hilfsfunktion: Exportiere Folien über PowerPoint."""
    import win32com.client  # type: ignore

    fmt = image_format.upper()
    export_map = {"PNG": "PNG", "JPEG": "JPG", "TIFF": "TIF"}
    export_fmt = export_map[fmt]

    if start_slide is not None:
        try:
            start_slide = int(start_slide)
        except (TypeError, ValueError) as exc:
            raise ValueError("start_slide must be an integer") from exc
    if end_slide is not None:
        try:
            end_slide = int(end_slide)
        except (TypeError, ValueError) as exc:
            raise ValueError("end_slide must be an integer") from exc

    out_base = sane_output_dir(pptx_path, out_dir)
    stem = Path(pptx_path).stem
    target_dir = out_base / f"{stem}_{image_format.lower()}"
    target_dir.mkdir(parents=True, exist_ok=True)

    ppt = win32com.client.Dispatch("PowerPoint.Application")
    presentation = ppt.Presentations.Open(pptx_path, WithWindow=False)
    try:
        total = presentation.Slides.Count
        if start_slide is not None and not 1 <= start_slide <= total:
            raise ValueError(f"start_slide {start_slide} out of range 1..{total}")
        if end_slide is not None and not 1 <= end_slide <= total:
            raise ValueError(f"end_slide {end_slide} out of range 1..{total}")
        if (
            start_slide is not None
            and end_slide is not None
            and end_slide < start_slide
        ):
            raise ValueError("end_slide must be greater than or equal to start_slide")

        start = start_slide or 1
        end = end_slide or total
        outputs: List[str] = []
        for i in range(start, end + 1):
            slide = presentation.Slides(i)
            out_path = target_dir / f"{stem}_Folie_{i}.{image_format.lower()}"
            slide.Export(str(out_path), export_fmt, width, height)
            outputs.append(str(out_path))
    finally:
        presentation.Close()
        ppt.Quit()
    return outputs


@action(category="Office")
def pptx_to_images_via_powerpoint(
    pptx_path: str,
    image_format: Literal["PNG", "JPEG", "TIFF"] = "PNG",
    width: int = 3840,
    height: int = 2160,
    start_slide: int | None = None,
    end_slide: int | None = None,
    out_dir: str | None = None,
) -> List[str]:
    """Exportiere Folien eines PPTX als Bilder über PowerPoint."""
    if sys.platform != "win32":
        raise RuntimeError("PPTX→Bilder erfordert Windows + PowerPoint.")
    return _pptx_to_images_via_powerpoint(
        pptx_path,
        image_format,
        width=width,
        height=height,
        start_slide=start_slide,
        end_slide=end_slide,
        out_dir=out_dir,
    )


__all__ = ["pptx_to_images_via_powerpoint"]
