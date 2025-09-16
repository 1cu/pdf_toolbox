"""PPTX rendering provider interface."""

from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from typing import Literal

from pdf_toolbox.config import load_config
from pdf_toolbox.i18n import tr


class PptxRenderingError(RuntimeError):
    """Error raised when a PPTX renderer fails."""


class BasePptxRenderer(ABC):
    """Abstract base class for PPTX rendering backends."""

    @abstractmethod
    def to_images(  # noqa: PLR0913  # pdf-toolbox: renderer API requires many parameters | issue:-
        self,
        input_pptx: str,
        out_dir: str | None = None,
        max_size_mb: float | None = None,
        image_format: Literal["PNG", "JPEG", "TIFF"] = "JPEG",
        quality: int | None = None,
        width: int | None = None,
        height: int | None = None,
        range_spec: str | None = None,
    ) -> str:
        """Render ``input_pptx`` slides to images."""

    @abstractmethod
    def to_pdf(
        self,
        input_pptx: str,
        output_path: str | None = None,
        notes: bool = False,
        handout: bool = False,
        range_spec: str | None = None,
    ) -> str:
        """Render ``input_pptx`` to a PDF file."""


class NullRenderer(BasePptxRenderer):
    """Renderer placeholder that signals missing backend."""

    def to_images(  # noqa: PLR0913  # pdf-toolbox: renderer API requires many parameters | issue:-
        self,
        input_pptx: str,
        out_dir: str | None = None,
        max_size_mb: float | None = None,
        image_format: Literal["PNG", "JPEG", "TIFF"] = "JPEG",
        quality: int | None = None,
        width: int | None = None,
        height: int | None = None,
        range_spec: str | None = None,
    ) -> str:
        """Always raise because no renderer is configured."""
        del (
            input_pptx,
            out_dir,
            max_size_mb,
            image_format,
            quality,
            width,
            height,
            range_spec,
        )
        raise NotImplementedError(tr("pptx_renderer_missing"))

    def to_pdf(
        self,
        input_pptx: str,
        output_path: str | None = None,
        notes: bool = False,
        handout: bool = False,
        range_spec: str | None = None,
    ) -> str:
        """Always raise because no renderer is configured."""
        raise NotImplementedError(tr("pptx_renderer_missing"))


_INTERNAL_REGISTRY = {
    "ms_office": "pdf_toolbox.renderers.ms_office:PptxMsOfficeRenderer",
    "null": "pdf_toolbox.renderers.pptx:NullRenderer",
}


def _load_via_registry(name: str) -> BasePptxRenderer | None:
    """Return renderer ``name`` from the internal registry if present."""
    target = _INTERNAL_REGISTRY.get(name)
    if not target:
        return None
    module_name, qualname = target.split(":", 1)
    module = importlib.import_module(module_name)
    return getattr(module, qualname)()


def get_pptx_renderer() -> BasePptxRenderer:
    """Return the configured PPTX renderer or a placeholder.

    The ``pptx_renderer`` value from the JSON configuration file selects a
    renderer from the internal registry. Unknown or missing values fall back to
    :class:`NullRenderer`.
    """
    name = (load_config().get("pptx_renderer") or "").strip()
    if name:
        obj = _load_via_registry(name)
        if obj:
            return obj
    return NullRenderer()


__all__ = [
    "BasePptxRenderer",
    "NullRenderer",
    "PptxRenderingError",
    "get_pptx_renderer",
]
