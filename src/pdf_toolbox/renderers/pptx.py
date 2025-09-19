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

PPTX_PROVIDER_DOCS_URL = (
    "https://github.com/1cu/pdf_toolbox/blob/main/docs/adr/0001-pptx-provider-"
    "architecture.md"
)


class PptxRenderingError(RuntimeError):
    """Error raised when a PPTX renderer fails."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        detail: str | None = None,
    ) -> None:
        """Initialise the error with optional machine readable metadata."""
        full_message = f"{message}: {detail}" if detail else message
        super().__init__(full_message)
        self.code = code
        self.detail = detail


class UnsupportedOptionError(PptxRenderingError):
    """Raised when a renderer option is not supported."""

    def __init__(self, message: str, *, code: str = "unsupported_option") -> None:
        """Initialise the error with an optional override for ``code``."""
        super().__init__(message, code=code)


class PptxProviderUnavailableError(PptxRenderingError):
    """Raised when no PPTX renderer is configured."""

    def __init__(self) -> None:
        """Initialise the error with a translated message."""
        super().__init__(tr("pptx_no_provider"), code="unavailable")
        self.docs_url = PPTX_PROVIDER_DOCS_URL


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
        raise PptxProviderUnavailableError()

    def to_pdf(
        self,
        input_pptx: str,
        output_path: str | None = None,
        notes: bool = False,
        handout: bool = False,
        range_spec: str | None = None,
    ) -> str:
        """Always raise because no renderer is configured."""
        del input_pptx, output_path, notes, handout, range_spec
        raise PptxProviderUnavailableError()


register_renderer(NullRenderer)

_BUILTIN_MODULES = {
    "lightweight": "pdf_toolbox.renderers.lightweight_stub",
    "http_office": "pdf_toolbox.renderers.http_office",
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


def require_pptx_renderer() -> BasePptxRenderer:
    """Return the configured renderer or raise a clear error."""
    renderer = get_pptx_renderer()
    if isinstance(renderer, NullRenderer):
        raise PptxProviderUnavailableError()
    return renderer


__all__ = [
    "PPTX_PROVIDER_DOCS_URL",
    "BasePptxRenderer",
    "NullRenderer",
    "PptxProviderUnavailableError",
    "PptxRenderingError",
    "UnsupportedOptionError",
    "get_pptx_renderer",
    "require_pptx_renderer",
]
