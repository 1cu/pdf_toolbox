from __future__ import annotations

from pathlib import Path
from typing import List

from common_utils import sane_output_dir


def pptx_to_jpegs_via_powerpoint(
    pptx_path: str,
    width: int = 1920,
    height: int = 1080,
    out_dir: str | None = None,
) -> List[str]:
    import win32com.client  # type: ignore

    out_base = sane_output_dir(pptx_path, out_dir)
    ppt = win32com.client.Dispatch("PowerPoint.Application")
    presentation = ppt.Presentations.Open(pptx_path, WithWindow=False)
    presentation.Export(str(out_base), "JPG", width, height)
    presentation.Close()
    ppt.Quit()

    stem = Path(pptx_path).stem
    outputs: List[str] = []
    for i, slide in enumerate(sorted(out_base.glob("Slide*.JPG")), start=1):
        new_name = out_base / f"{stem}_Folie_{i}.jpg"
        slide.rename(new_name)
        outputs.append(str(new_name))
    return outputs


__all__ = ["pptx_to_jpegs_via_powerpoint"]
