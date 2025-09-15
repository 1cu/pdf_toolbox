"""PPTX rendering provider interface."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from importlib import metadata
from typing import Literal

from pdf_toolbox.i18n import tr


class BasePptxRenderer(ABC):
    """Abstract base class for PPTX rendering backends."""

    @abstractmethod
    def to_images(
        self,
        input_pptx: str,
        out_dir: str | None = None,
        max_size_mb: float | None = None,
        img_format: Literal["jpeg", "png", "tiff"] = "jpeg",
    ) -> str:
        """Render ``input_pptx`` slides to images."""

    @abstractmethod
    def to_pdf(self, input_pptx: str, output_path: str | None = None) -> str:
        """Render ``input_pptx`` to a PDF file."""


class NullRenderer(BasePptxRenderer):
    """Renderer placeholder that signals missing backend."""

    def to_images(
        self,
        input_pptx: str,
        out_dir: str | None = None,
        max_size_mb: float | None = None,
        img_format: Literal["jpeg", "png", "tiff"] = "jpeg",
    ) -> str:
        """Always raise because no renderer is configured."""
        raise NotImplementedError(tr("pptx_renderer_missing"))

    def to_pdf(self, input_pptx: str, output_path: str | None = None) -> str:
        """Always raise because no renderer is configured."""
        raise NotImplementedError(tr("pptx_renderer_missing"))


def get_pptx_renderer() -> BasePptxRenderer:
    """Return the configured PPTX renderer or a placeholder.

    A renderer can be selected via the ``PDF_TOOLBOX_PPTX_RENDERER`` environment
    variable referring to an entry point in the ``pdf_toolbox.pptx_renderers``
    group. If no matching entry point is found a :class:`NullRenderer` instance
    is returned.
    """
    name = os.getenv("PDF_TOOLBOX_PPTX_RENDERER")
    if name:
        for ep in metadata.entry_points(group="pdf_toolbox.pptx_renderers"):
            if ep.name == name:
                renderer_cls = ep.load()
                return renderer_cls()
    return NullRenderer()


__all__ = ["BasePptxRenderer", "NullRenderer", "get_pptx_renderer"]
