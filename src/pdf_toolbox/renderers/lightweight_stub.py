"""Lightweight PPTX renderer placeholder."""

from __future__ import annotations

from typing import ClassVar, Literal

from pdf_toolbox.renderers.pptx import PptxProviderUnavailableError
from pdf_toolbox.renderers.pptx_base import BasePptxRenderer
from pdf_toolbox.renderers.registry import register


class PptxLightweightStub(BasePptxRenderer):
    """Stub renderer reserved for the upcoming lightweight backend."""

    name: ClassVar[str] = "lightweight"

    @classmethod
    def probe(cls) -> bool:
        """Return ``False`` until the lightweight backend lands."""
        return False

    @classmethod
    def can_handle(cls) -> bool:
        """Backward compatible alias for :meth:`probe`."""
        return cls.probe()

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
        """Raise because the lightweight renderer has not been implemented yet."""
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
        """Raise because the lightweight renderer has not been implemented yet."""
        del input_pptx, output_path, notes, handout, range_spec
        raise PptxProviderUnavailableError()


register(PptxLightweightStub)


__all__ = ["PptxLightweightStub"]
