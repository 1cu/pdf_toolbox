from __future__ import annotations

from pathlib import Path
from typing import List

from .utils import sane_output_dir


def _pptx_to_images_via_powerpoint(
    pptx_path: str,
    image_format: str,
    width: int = 1920,
    height: int = 1080,
    out_dir: str | None = None,
) -> List[str]:
    import win32com.client  # type: ignore

    out_base = sane_output_dir(pptx_path, out_dir)
    stem = Path(pptx_path).stem
    target_dir = out_base / f"{stem}_{image_format.lower()}"
    target_dir.mkdir(parents=True, exist_ok=True)

    ppt = win32com.client.Dispatch("PowerPoint.Application")
    presentation = ppt.Presentations.Open(pptx_path, WithWindow=False)
    presentation.Export(str(target_dir), image_format, width, height)
    presentation.Close()
    ppt.Quit()

    ext = image_format.upper()
    outputs: List[str] = []
    for i, slide in enumerate(sorted(target_dir.glob(f"Slide*.{ext}")), start=1):
        new_name = target_dir / f"{stem}_Folie_{i}.{ext.lower()}"
        slide.rename(new_name)
        outputs.append(str(new_name))
    return outputs


def pptx_to_jpegs_via_powerpoint(
    pptx_path: str,
    width: int = 1920,
    height: int = 1080,
    out_dir: str | None = None,
) -> List[str]:
    return _pptx_to_images_via_powerpoint(
        pptx_path, "JPG", width=width, height=height, out_dir=out_dir
    )


def pptx_to_pngs_via_powerpoint(
    pptx_path: str,
    width: int = 1920,
    height: int = 1080,
    out_dir: str | None = None,
) -> List[str]:
    return _pptx_to_images_via_powerpoint(
        pptx_path, "PNG", width=width, height=height, out_dir=out_dir
    )


def pptx_to_tiffs_via_powerpoint(
    pptx_path: str,
    width: int = 1920,
    height: int = 1080,
    out_dir: str | None = None,
) -> List[str]:
    return _pptx_to_images_via_powerpoint(
        pptx_path, "TIF", width=width, height=height, out_dir=out_dir
    )


__all__ = [
    "pptx_to_jpegs_via_powerpoint",
    "pptx_to_pngs_via_powerpoint",
    "pptx_to_tiffs_via_powerpoint",
]
