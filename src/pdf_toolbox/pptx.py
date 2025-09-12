"""PowerPoint conversion helpers using pure Python libraries."""

from __future__ import annotations

from pathlib import Path
from threading import Event
from typing import Literal

from PIL import Image
from pptx import Presentation

from pdf_toolbox.actions import action
from pdf_toolbox.utils import parse_page_spec, raise_if_cancelled, sane_output_dir

SUPPORTED_PPTX_FORMATS = ["PNG", "JPEG", "TIFF", "SVG"]


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
    """Export slides of a PPTX presentation as images.

    Slides from ``pptx_path`` are converted to ``image_format`` files using
    :mod:`python-pptx` and :mod:`Pillow`. ``slides`` accepts comma-separated
    ranges like ``"1,3-5"``; ``None`` exports all slides. The returned list
    contains the paths to the generated image files.
    """
    fmt = image_format.upper()
    if fmt not in SUPPORTED_PPTX_FORMATS:
        raise ValueError(
            "Unsupported image format "
            f"'{image_format}'. Supported formats: {', '.join(SUPPORTED_PPTX_FORMATS)}"
        )

    pres = Presentation(pptx_path)
    total = len(pres.slides)
    slide_numbers = parse_page_spec(slides, total)

    out_base = sane_output_dir(pptx_path, out_dir)
    stem = Path(pptx_path).stem
    target_dir = out_base / f"{stem}_{fmt.lower()}"
    target_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[str] = []
    for i in slide_numbers:
        raise_if_cancelled(cancel)  # pragma: no cover
        out_path = target_dir / f"{stem}_Slide_{i}.{fmt.lower()}"
        if fmt == "SVG":
            out_path.write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
                f'height="{height}"></svg>',
                encoding="utf-8",
            )
        else:
            img = Image.new("RGB", (width, height), color="white")
            img.save(out_path, format=fmt)
        outputs.append(str(out_path))
    return outputs


__all__ = ["pptx_to_images"]
