from __future__ import annotations

from pathlib import Path
from typing import List, Union
import io

import fitz  # type: ignore
from PIL import Image

from .utils import sane_output_dir


def pdf_to_images(
    input_pdf: str,
    start_page: int | None = None,
    end_page: int | None = None,
    dpi: int = 300,
    image_format: str = "PNG",
    quality: int = 95,
    out_dir: str | None = None,
    as_pil: bool = False,
) -> List[Union[str, Image.Image]]:
    """Rasterize a PDF into images.

    Each page of ``input_pdf`` is rendered to the chosen image format.
    ``dpi`` controls the resolution; higher values yield higher quality
    but also larger files. ``quality`` is only used for JPEG output.
    If ``as_pil`` is ``True`` a list of :class:`PIL.Image.Image` objects
    is returned instead of file paths.
    """

    doc = fitz.open(input_pdf)
    start = (start_page - 1) if start_page else 0
    end = end_page if end_page else doc.page_count
    out_base = None if as_pil else sane_output_dir(input_pdf, out_dir)
    outputs: List[Union[str, Image.Image]] = []

    zoom = dpi / 72  # default PDF resolution is 72 dpi
    matrix = fitz.Matrix(zoom, zoom)

    fmt = image_format.upper()
    ext = fmt.lower()

    for page_no in range(start, end):
        page = doc.load_page(page_no)
        pix = page.get_pixmap(matrix=matrix, alpha=True)

        if pix.n == 1 or (pix.n == 2 and pix.alpha):
            mode = "LA" if pix.alpha else "L"
        elif pix.n == 3 or (pix.n == 4 and pix.alpha):
            mode = "RGBA" if pix.alpha else "RGB"
        else:
            pix = fitz.Pixmap(fitz.csRGB, pix)
            mode = "RGBA" if pix.alpha else "RGB"

        if pix.alpha and fmt in {"PNG", "TIFF"}:
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            if img.mode != mode:
                img = img.convert(mode)
            if img.mode in {"RGBA", "LA"} and img.getchannel("A").getextrema() == (255, 255):
                img = img.convert(img.mode.replace("A", ""))
        else:
            img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
            if pix.alpha:
                alpha = pix.samples[pix.n - 1 :: pix.n]
                if alpha.count(255) == len(alpha) or fmt not in {"PNG", "TIFF"}:
                    img = img.convert(mode.replace("A", ""))

        save_kwargs = {}
        if fmt == "JPEG":
            save_kwargs["quality"] = quality
        elif fmt == "PNG":  # lossless; avoid heavy compression for speed
            save_kwargs["compress_level"] = 0

        if as_pil:
            outputs.append(img)
        else:
            assert out_base is not None
            out_path = out_base / f"{Path(input_pdf).stem}_Seite_{page_no + 1}.{ext}"
            img.save(out_path, format=fmt, **save_kwargs)
            outputs.append(str(out_path))
    return outputs


__all__ = ["pdf_to_images"]
