"""Renderer plugin interfaces.

Currently only PPTX rendering hooks are provided; more may be added in the
future.
"""

from pdf_toolbox.renderers.pptx import (
    PPTX_PROVIDER_DOCS_URL,
    BasePptxRenderer,
    PptxProviderUnavailableError,
    get_pptx_renderer,
    require_pptx_renderer,
)

__all__ = [
    "BasePptxRenderer",
    "PPTX_PROVIDER_DOCS_URL",
    "PptxProviderUnavailableError",
    "get_pptx_renderer",
    "require_pptx_renderer",
]
