"""Abstract base classes for PPTX rendering providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Literal


class BasePptxRenderer(ABC):
    """Define the public PPTX rendering interface.

    Subclasses may implement ``can_handle`` either as a class method with the
    signature ``can_handle() -> bool`` or as an instance method returning a
    boolean. Additional parameters are not supported so the registry can probe
    availability uniformly.
    """

    #: Canonical provider name used for registry lookups.
    name: ClassVar[str] = ""

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
        """Render ``input_pptx`` slides to individual images.

        Args:
            input_pptx: Path to the PPTX presentation to render.
            out_dir: Optional destination directory. Implementations may create
                one when omitted.
            max_size_mb: Maximum size for each output image when supported.
            image_format: Desired image format.
            quality: Encoder quality hint where supported by the backend.
            width: Optional override for the exported image width in pixels.
            height: Optional override for the exported image height in pixels.
            range_spec: Normalised page selection passed from the UI layer.

        Returns:
            Path to the directory that contains the exported slide images.

        Raises:
            PptxRenderingError: Subclasses raise this when the conversion
                backend fails.
        """

    @abstractmethod
    def to_pdf(
        self,
        input_pptx: str,
        output_path: str | None = None,
        notes: bool = False,
        handout: bool = False,
        range_spec: str | None = None,
    ) -> str:
        """Render ``input_pptx`` into a PDF document.

        Args:
            input_pptx: Path to the PPTX presentation to render.
            output_path: Target PDF path. Implementations may create a
                temporary file when omitted.
            notes: Whether to include speaker notes in the generated PDF.
            handout: Whether to create a handout style PDF.
            range_spec: Normalised page selection passed from the UI layer.

        Returns:
            Path to the generated PDF file.

        Raises:
            PptxRenderingError: Subclasses raise this when the conversion
                backend fails.
        """


__all__ = ["BasePptxRenderer"]
