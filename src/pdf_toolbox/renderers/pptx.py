"""PPTX rendering provider interface."""

from __future__ import annotations

import importlib
from typing import Literal

from pdf_toolbox.config import load_config
from pdf_toolbox.i18n import tr
from pdf_toolbox.renderers.pptx_base import BasePptxRenderer
from pdf_toolbox.renderers.registry import available as registry_available
from pdf_toolbox.renderers.registry import register as register_renderer
from pdf_toolbox.renderers.registry import select as registry_select


class PptxRenderingError(RuntimeError):
    """Error raised when a PPTX renderer fails."""


class NullRenderer(BasePptxRenderer):
    """Renderer placeholder that signals missing backend."""

    name = "null"

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


register_renderer(NullRenderer)

_BUILTIN_MODULES = {
    "ms_office": "pdf_toolbox.renderers.ms_office",
}


def _ensure_registered(name: str) -> None:
    """Import and register built-in providers on demand."""
    key = name.strip().lower()
    if not key or key in registry_available():
        return
    module = _BUILTIN_MODULES.get(key)
    if not module:
        return
    importlib.import_module(module)


def _load_via_registry(name: str) -> BasePptxRenderer | None:
    """Return renderer ``name`` from the internal registry if present."""
    lookup = (name or "").strip().lower()
    if not lookup:
        return None
    if lookup == "auto":
        for candidate in _BUILTIN_MODULES:
            _ensure_registered(candidate)
    else:
        _ensure_registered(lookup)
    renderer_cls = registry_select(lookup)
    if renderer_cls is None:
        return None
    return renderer_cls()


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
