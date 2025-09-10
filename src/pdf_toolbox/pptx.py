from __future__ import annotations

from pathlib import Path
from typing import List, Literal
import sys

from .actions import action
from .utils import sane_output_dir


def _pptx_to_images_via_powerpoint(  # pragma: no cover - requires Windows + PowerPoint
    pptx_path: str,
    image_format: Literal["PNG", "JPEG", "TIFF"],
    width: int = 1920,
    height: int = 1080,
    out_dir: str | None = None,
) -> List[str]:
    """Hilfsfunktion: Exportiere Folien über PowerPoint."""
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
    presentation.Export(str(target_dir), export_fmt, width, height)
    presentation.Close()
    ppt.Quit()

    ext = export_fmt
    outputs: List[str] = []
    for i, slide in enumerate(sorted(target_dir.glob(f"Slide*.{ext}")), start=1):
        new_name = target_dir / f"{stem}_Folie_{i}.{image_format.lower()}"
        slide.rename(new_name)
        outputs.append(str(new_name))
    return outputs


@action(category="Office")
def pptx_to_images_via_powerpoint(
    pptx_path: str,
    image_format: Literal["PNG", "JPEG", "TIFF"] = "PNG",
    width: int = 1920,
    height: int = 1080,
    out_dir: str | None = None,
) -> List[str]:
    """Exportiere Folien eines PPTX als Bilder über PowerPoint."""
    if sys.platform != "win32":
        raise RuntimeError("PPTX→Bilder erfordert Windows + PowerPoint.")
    return _pptx_to_images_via_powerpoint(
        pptx_path, image_format, width=width, height=height, out_dir=out_dir
    )


__all__ = ["pptx_to_images_via_powerpoint"]
