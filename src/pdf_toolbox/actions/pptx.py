"""PPTX manipulation actions."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Literal

from pptx import Presentation as load_presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.presentation import Presentation
from pptx.slide import Slide

from pdf_toolbox.actions import action
from pdf_toolbox.paths import validate_path
from pdf_toolbox.renderers.pptx import get_pptx_renderer
from pdf_toolbox.utils import logger


def _copy_slide(prs: Presentation, slide: Slide) -> None:
    """Append ``slide`` to ``prs`` preserving shapes and media."""

    new_slide = prs.slides.add_slide(slide.slide_layout)
    title = getattr(slide.shapes, "title", None)
    if title is not None:
        new_slide.shapes.title.text = title.text
    for shape in slide.shapes:
        if title is not None and shape == title:
            continue
        if getattr(shape, "shape_type", None) == MSO_SHAPE_TYPE.PICTURE:
            img = getattr(shape, "image")
            new_slide.shapes.add_picture(
                BytesIO(img.blob), shape.left, shape.top, shape.width, shape.height
            )
        elif getattr(shape, "has_text_frame", False):
            box = new_slide.shapes.add_textbox(
                shape.left, shape.top, shape.width, shape.height
            )
            box.text = getattr(shape, "text", "")


def _parse_range_spec(spec: str, total: int) -> list[int]:
    """Return slide numbers described by ``spec`` preserving order."""

    if not spec:
        return list(range(1, total + 1))
    result: list[int] = []
    for raw_part in spec.split(","):
        part = raw_part.strip().replace("n", str(total))
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start = int(start_s) if start_s else 1
            end = int(end_s) if end_s else total
            if start < 1 or end > total or end < start:
                msg = f"invalid range {part}"
                raise ValueError(msg)
            result.extend(range(start, end + 1))
        else:
            page = int(part)
            if page < 1 or page > total:
                msg = f"page {page} out of range"
                raise ValueError(msg)
            result.append(page)
    return result


@action(category="PPTX")
def extract_pptx_images(input_pptx: str, out_dir: str | None = None) -> str:
    """Extract embedded images from ``input_pptx``.

    Args:
        input_pptx: Path to the presentation.
        out_dir: Destination directory; defaults to ``<input>_images``.

    Returns:
        Path to the directory containing the extracted images.

    Example:
        >>> extract_pptx_images("slides.pptx")
        'slides_images'
    """

    pres = load_presentation(str(validate_path(input_pptx, must_exist=True)))
    base_dir = Path(input_pptx).parent
    target = (
        Path(out_dir)
        if out_dir
        else base_dir / f"{Path(input_pptx).stem}_images"
    )
    target = validate_path(target)
    target.mkdir(parents=True, exist_ok=True)

    count = 0
    for slide in pres.slides:
        for shape in slide.shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                image = shape.image
                filename = target / f"image_{count + 1}.{image.ext}"
                filename.write_bytes(image.blob)
                count += 1
    logger.info("Extracted %d image(s) from %s", count, input_pptx)
    return str(target)


@action(category="PPTX")
def pptx_properties(input_pptx: str) -> str:
    """Write core document properties of ``input_pptx`` to JSON.

    Args:
        input_pptx: Path to the presentation.

    Returns:
        Path to the JSON file with extracted properties.
    """

    pres = load_presentation(str(validate_path(input_pptx, must_exist=True)))
    props = pres.core_properties
    data = {
        "author": props.author,
        "title": props.title,
        "subject": props.subject,
        "keywords": props.keywords,
        "created": props.created.isoformat() if props.created else None,
        "modified": props.modified.isoformat() if props.modified else None,
    }
    out_path = Path(input_pptx).with_name(f"{Path(input_pptx).stem}_props.json")
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Properties for %s written to %s", input_pptx, out_path)
    return str(out_path)


@action(category="PPTX")
def merge_pptx(
    first: str,
    second: str,
    output_path: str | None = None,
) -> str:
    """Append slides from ``second`` to ``first`` presentation.

    Args:
        first: Base presentation to extend.
        second: Presentation whose slides are appended.
        output_path: Optional path for the merged file. Defaults to
            ``<first>_merged.pptx``.
    """

    pres1 = load_presentation(str(validate_path(first, must_exist=True)))
    pres2 = load_presentation(str(validate_path(second, must_exist=True)))
    for slide in pres2.slides:
        _copy_slide(pres1, slide)
    out = (
        Path(output_path)
        if output_path
        else Path(first).with_name(f"{Path(first).stem}_merged.pptx")
    )
    out = validate_path(out)
    pres1.save(str(out))
    logger.info(
        "Merged %s and %s into %s (%d slides)",
        first,
        second,
        out,
        len(pres1.slides),
    )
    return str(out)


@action(category="PPTX")
def reorder_pptx(
    input_pptx: str,
    range_spec: str,
    output_path: str | None = None,
) -> str:
    """Reorder slides of ``input_pptx`` according to ``range_spec``.

    Args:
        input_pptx: Presentation to reorder.
        range_spec: Slide specification such as ``"1-3,7,4-5,8-n"``.
        output_path: Optional path for the reordered file. Defaults to
            ``<input>_reordered.pptx``.
    """

    pres = load_presentation(str(validate_path(input_pptx, must_exist=True)))
    numbers = _parse_range_spec(range_spec, len(pres.slides))
    sld_id_lst = pres.slides._sldIdLst  # noqa: SLF001  # pdf-toolbox: reorder slides via private API | issue:-
    slides = list(sld_id_lst)
    sld_id_lst.clear()
    for num in numbers:
        sld_id_lst.append(slides[num - 1])
    out = (
        Path(output_path)
        if output_path
        else Path(input_pptx).with_name(f"{Path(input_pptx).stem}_reordered.pptx")
    )
    out = validate_path(out)
    pres.save(str(out))
    logger.info("Reordered %s to %s", input_pptx, out)
    return str(out)


@action(category="PPTX")
def pptx_to_images(
    input_pptx: str,
    out_dir: str | None = None,
    max_size_mb: float | None = None,
    format: Literal["jpeg", "png", "tiff"] = "jpeg",
) -> str:
    """Render a PPTX file to images using the configured provider."""

    renderer = get_pptx_renderer()
    return renderer.to_images(
        input_pptx,
        out_dir=out_dir,
        max_size_mb=max_size_mb,
        format=format,
    )


@action(category="PPTX")
def pptx_to_pdf(input_pptx: str, output_path: str | None = None) -> str:
    """Render a PPTX file to PDF using the configured provider."""

    renderer = get_pptx_renderer()
    return renderer.to_pdf(input_pptx, output_path=output_path)


__all__ = [
    "extract_pptx_images",
    "pptx_properties",
    "merge_pptx",
    "reorder_pptx",
    "pptx_to_images",
    "pptx_to_pdf",
]

