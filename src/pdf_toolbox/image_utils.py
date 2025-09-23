"""Shared helpers for rendering PDF pages and encoding PIL images."""

from __future__ import annotations

import io
from typing import Any

import fitz
from PIL import Image, ImageFilter


def render_page_image(
    page: fitz.Page,
    dpi: int,
    *,
    keep_alpha: bool = False,
) -> Image.Image:
    """Return a :class:`PIL.Image.Image` rendered from ``page`` at ``dpi``.

    Args:
        page: PDF page to render.
        dpi: Target dots per inch used for rasterisation.
        keep_alpha: When ``True`` the resulting image preserves transparency
            if the page contains an alpha channel. Otherwise the image is
            converted to RGB.

    Returns:
        PIL image containing the rendered page.
    """
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    kwargs: dict[str, bool] = {"alpha": True} if keep_alpha else {}
    pix = page.get_pixmap(matrix=matrix, **kwargs)
    if pix.colorspace is None or pix.colorspace.n not in (1, 3):
        pix = fitz.Pixmap(fitz.csRGB, pix)
    if not keep_alpha and pix.alpha:
        pix = fitz.Pixmap(pix, 0)
    mode = "RGBA" if pix.alpha else "RGB"
    return Image.frombytes(mode, (pix.width, pix.height), pix.samples)


def apply_unsharp_mask(
    image: Image.Image,
    *,
    radius: float = 0.6,
    amount: float = 0.5,
    threshold: int = 3,
) -> Image.Image:
    """Return a mildly sharpened copy of ``image`` using an unsharp mask."""
    percent = int(amount * 100)
    return image.filter(
        ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold)
    )


def encode_webp(
    image: Image.Image,
    *,
    lossless: bool,
    quality: int | None,
    method: int = 6,
) -> bytes:
    """Return WebP-encoded bytes for ``image``."""
    with io.BytesIO() as buf:
        params: dict[str, Any] = {"method": method}
        if lossless:
            params["lossless"] = True
        if quality is not None:
            params["quality"] = int(quality)
        image.save(buf, format="WEBP", **params)
        return buf.getvalue()


def encode_png(
    image: Image.Image,
    *,
    palette: bool = False,
    compress_level: int = 9,
    optimize: bool = True,
) -> bytes:
    """Return PNG-encoded bytes for ``image``."""
    target = image
    if palette and image.mode not in {"P", "L"}:
        target = image.convert("P", palette=Image.Palette.ADAPTIVE)
    with io.BytesIO() as buf:
        target.save(
            buf,
            format="PNG",
            compress_level=compress_level,
            optimize=optimize,
        )
        return buf.getvalue()


def encode_jpeg(
    image: Image.Image,
    *,
    quality: int,
    subsampling: int = 0,
) -> bytes:
    """Return JPEG-encoded bytes for ``image`` using the requested quality."""
    rgb = image.convert("RGB")
    with io.BytesIO() as buf:
        rgb.save(buf, format="JPEG", quality=quality, subsampling=subsampling)
        return buf.getvalue()


__all__ = [
    "apply_unsharp_mask",
    "encode_jpeg",
    "encode_png",
    "encode_webp",
    "render_page_image",
]
