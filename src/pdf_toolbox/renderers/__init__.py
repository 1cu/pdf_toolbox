"""Renderer plugin interfaces.

Currently only PPTX rendering hooks are provided; more may be added in the
future.
"""

from pdf_toolbox.renderers.pptx import BasePptxRenderer, get_pptx_renderer

__all__ = ["BasePptxRenderer", "get_pptx_renderer"]
