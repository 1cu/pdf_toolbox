"""PDF optimisation utilities.

Public APIs:
- ``optimise_pdf``: default action with optional progress callback.
- ``batch_optimise_pdfs``: run optimisation on all PDFs in a directory.

Internal helper:
- (none)
"""

from __future__ import annotations

import io
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from threading import Event
from typing import Literal, TypedDict

import fitz  # type: ignore
from PIL import Image

from pdf_toolbox.actions import action
from pdf_toolbox.utils import (
    logger,
    open_pdf,
    raise_if_cancelled,
    sane_output_dir,
    save_pdf,
)

ERR_UNKNOWN_QUALITY = "unknown quality"
ERR_INPUT_DIR = "Input directory not found: {input_dir}"


class QualitySetting(TypedDict):
    """Quality configuration options."""

    pdf_quality: int
    image_quality: int
    min_reduction: float


QualityChoice = Literal["screen", "ebook", "printer", "prepress", "default"]


QUALITY_SETTINGS: dict[QualityChoice, QualitySetting] = {
    "screen": {"pdf_quality": 50, "image_quality": 40, "min_reduction": 0.3},
    "ebook": {"pdf_quality": 75, "image_quality": 60, "min_reduction": 0.2},
    "printer": {"pdf_quality": 90, "image_quality": 85, "min_reduction": 0.1},
    "prepress": {"pdf_quality": 100, "image_quality": 95, "min_reduction": 0.05},
    "default": {"pdf_quality": 80, "image_quality": 75, "min_reduction": 0.15},
}


def _compress_images(
    doc: fitz.Document,
    image_quality: int,
    cancel: Event | None = None,
    *,
    progress_cb: Callable[[int, int], None] | None = None,
    progress_offset: int = 0,
) -> int:
    total = len(doc)
    for current, page in enumerate(doc, start=1):  # type: ignore[assignment]
        raise_if_cancelled(cancel)  # pragma: no cover
        for img in page.get_images(full=True):
            raise_if_cancelled(cancel)  # pragma: no cover
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            try:
                if pix.n in (1, 3, 4):
                    if pix.n in (1, 4):
                        original = pix
                        pix = fitz.Pixmap(fitz.csRGB, original)
                        del original
                    pil_img = Image.frombytes(
                        "RGB", (pix.width, pix.height), pix.samples
                    )
                    with io.BytesIO() as buf:
                        pil_img.save(buf, format="JPEG", quality=image_quality)
                        doc.update_stream(xref, buf.getvalue())
            finally:
                del pix
        if progress_cb:
            progress_cb(progress_offset + current, progress_offset + total)
    return total


## (no private duplicate of optimise logic)


@action(category="PDF")
def optimise_pdf(  # noqa: PLR0913
    input_pdf: str,
    quality: QualityChoice = "default",
    compress_images: bool = False,
    keep: bool = True,
    out_dir: str | None = None,
    cancel: Event | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> tuple[str | None, float]:
    """Optimise *input_pdf* and report the size change.

    The document is rewritten with garbage collection, deflated streams and an
    optional JPEG recompression pass for embedded images.  When
    ``progress_callback`` is provided it receives ``current`` and ``total``
    counts as the work advances.  ``total`` equals the number of pages when
    ``compress_images`` is enabled; otherwise it is ``1``.  Depending on the
    content, the rewritten file may be larger or unchanged and is then reported
    as not optimised.

    Args:
        input_pdf: Path to the PDF to optimise.
        quality: Preset that controls compression effort.
        compress_images: Recompress images as JPEG if ``True``.
        keep: Preserve the output if the size reduction is below the preset
            minimum.
        out_dir: Optional directory for the output file.
        cancel: Cancellation event.
        progress_callback: Function receiving progress updates.

    Returns:
        Tuple of the output path and the size reduction ratio.  A negative
        ratio indicates that the optimised file is larger than the input.

    Examples:
        >>> # Optimise a PDF with image compression and observe progress
        >>> from pdf_toolbox.builtin.optimise import optimise_pdf
        >>> def on_progress(c, t):
        ...     print(f"{c}/{t}")
        >>> out, reduction = optimise_pdf(
        ...     "input.pdf", quality="ebook", compress_images=True,
        ...     progress_callback=on_progress
        ... )
        >>> isinstance(out, str)
        True

    """
    if quality not in QUALITY_SETTINGS:
        raise ValueError(ERR_UNKNOWN_QUALITY)
    settings = QUALITY_SETTINGS[quality]
    input_path = Path(input_pdf)
    out_dir_path = sane_output_dir(input_path, out_dir)
    out_path = out_dir_path / f"{input_path.stem}_optimised_{quality}.pdf"

    original_size = input_path.stat().st_size
    logger.info(
        "Optimising %s with quality=%s (compress_images=%s)",
        input_pdf,
        quality,
        compress_images,
    )
    doc = open_pdf(input_pdf)
    saved = False
    try:
        raise_if_cancelled(cancel, doc)  # pragma: no cover

        progress_total = len(doc) if compress_images else 1
        if compress_images:
            _compress_images(
                doc,
                settings["image_quality"],
                cancel,
                progress_cb=progress_callback,
                progress_offset=0,
            )
        if progress_callback:
            progress_callback(progress_total, progress_total)

        raise_if_cancelled(cancel, doc)  # pragma: no cover

        pdf_quality = settings["pdf_quality"]
        compression_effort = max(0, min(9, (100 - pdf_quality) // 10))
        save_pdf(
            doc,
            out_path,
            note=" | optimised",
            garbage=3,
            deflate=True,
            clean=True,
            compression_effort=compression_effort,
        )
        saved = True
    finally:
        if not saved:
            with suppress(Exception):
                doc.close()

    optimised_size = out_path.stat().st_size
    reduction = 1 - (optimised_size / original_size)
    change_pct = reduction * 100
    if reduction < QUALITY_SETTINGS[quality]["min_reduction"] and not keep:
        out_path.unlink(missing_ok=True)
        if reduction >= 0:
            logger.info(
                "Optimised PDF discarded; reduction %.2f%% below threshold",
                change_pct,
            )
        else:
            logger.info(
                "Optimised PDF discarded; size increased by %.2f%%",
                abs(change_pct),
            )
        return None, reduction
    if reduction > 0:
        msg = f"size reduced by {change_pct:.2f}%"
        logger.info("Optimised PDF written to %s (%s)", out_path, msg)
    else:
        if reduction < 0:
            msg = f"size increased by {abs(change_pct):.2f}%"
        else:
            msg = "size unchanged"
        logger.info("PDF written to %s (%s)", out_path, msg)
    return str(out_path), reduction


@action(category="PDF")
def batch_optimise_pdfs(  # noqa: PLR0913
    input_dir: str,
    output_dir: str | None = None,
    quality: QualityChoice = "default",
    compress_images: bool = False,
    keep: bool = True,
    cancel: Event | None = None,
) -> list[str]:
    """Optimise all PDFs in a directory and return output paths.

    Examples:
        >>> from pdf_toolbox.builtin.optimise import batch_optimise_pdfs
        >>> outs = batch_optimise_pdfs("/path/to/dir", quality="ebook", compress_images=True)
        >>> isinstance(outs, list)
        True

    """
    in_dir = Path(input_dir)
    if not in_dir.exists() or not in_dir.is_dir():
        raise FileNotFoundError(ERR_INPUT_DIR.format(input_dir=input_dir))
    out_dir = Path(output_dir) if output_dir else in_dir / "optimised"
    out_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[str] = []
    for pdf in sorted(in_dir.glob("*.pdf")):
        raise_if_cancelled(cancel)  # pragma: no cover
        out, _ = optimise_pdf(
            str(pdf),
            quality=quality,
            compress_images=compress_images,
            keep=keep,
            out_dir=str(out_dir),
            cancel=cancel,
        )
        if out:
            outputs.append(out)
    return outputs
