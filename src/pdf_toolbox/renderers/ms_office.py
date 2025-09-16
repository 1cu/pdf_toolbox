"""Microsoft PowerPoint based PPTX renderer."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Literal

from pdf_toolbox.renderers.pptx import BasePptxRenderer, PptxRenderingError
from pdf_toolbox.utils import logger, parse_page_spec

try:  # pragma: no cover - import guarded for non-Windows platforms  # pdf-toolbox: Windows-only COM modules | issue:-
    import pythoncom  # type: ignore  # pdf-toolbox: pywin32 missing on non-Windows | issue:-
    import win32com.client  # type: ignore  # pdf-toolbox: pywin32 missing on non-Windows | issue:-
except Exception:  # pragma: no cover - handled in _require_env  # pdf-toolbox: gracefully handle missing COM | issue:-
    win32com = None  # type: ignore  # pdf-toolbox: indicate COM unavailability | issue:-


class PptxMsOfficeRenderer(BasePptxRenderer):
    """Render PPTX files using Microsoft PowerPoint.

    The renderer relies on COM automation and therefore only works on Windows
    systems with an installed version of Microsoft PowerPoint. Enable it via
    the configuration file (``pptx_renderer = "ms_office"``) and the optional
    ``pptx-render`` extras.

    Example:
        >>> from pdf_toolbox.renderers.ms_office import PptxMsOfficeRenderer
        >>> PptxMsOfficeRenderer().to_pdf("slides.pptx")
        'slides.pdf'
    """

    _PP_SAVE_AS_PDF = 32  # ppSaveAsPDF

    def _require_env(self) -> None:
        if win32com is None:
            msg = "MS-Office Renderer nicht verfügbar: Windows/PowerPoint/pywin32 erforderlich."
            raise PptxRenderingError(msg)

    def _open_app(
        self,
    ):  # pragma: no cover - Windows only  # pdf-toolbox: relies on PowerPoint COM | issue:-
        """Start a hidden PowerPoint instance."""
        pythoncom.CoInitialize()
        app = win32com.client.DispatchEx("PowerPoint.Application")
        with contextlib.suppress(Exception):
            app.DisplayAlerts = 1  # ppAlertsNone
        app.Visible = False
        return app

    def _close_app(
        self, app
    ) -> None:  # pragma: no cover - Windows only  # pdf-toolbox: PowerPoint COM cleanup | issue:-
        try:
            app.Quit()
        finally:
            pythoncom.CoUninitialize()

    def _open_presentation(
        self, app, path: Path
    ):  # pragma: no cover - Windows only  # pdf-toolbox: PowerPoint COM | issue:-
        """Open ``path`` as read-only presentation."""
        return app.Presentations.Open(str(path), True, False, False)

    @staticmethod
    def _parse_range(spec: str | None, max_index: int) -> set[int]:
        return set(parse_page_spec(spec, max_index))

    # ------------------------------------------------------------------
    # BasePptxRenderer API
    # ------------------------------------------------------------------
    def to_pdf(
        self,
        input_pptx: str,
        output_path: str | None = None,
        _notes: bool = False,
        _handout: bool = False,
        range_spec: str | None = None,
    ) -> str:
        """Render ``input_pptx`` to a PDF file."""
        self._require_env()
        inp = Path(input_pptx).resolve()
        if not inp.exists():
            msg = f"Eingabe nicht gefunden: {inp}"
            raise PptxRenderingError(msg)

        out = Path(output_path) if output_path else inp.with_suffix(".pdf")
        out.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Rendering %s to PDF", inp)
        app = self._open_app()
        try:
            prs = self._open_presentation(app, inp)
            try:
                wanted = self._parse_range(range_spec, len(prs.Slides))
                for i, slide in enumerate(list(prs.Slides), start=1):
                    slide.SlideShowTransition.Hidden = i not in wanted
                prs.SaveAs(str(out), self._PP_SAVE_AS_PDF)
                logger.info("Rendered %d slide(s) to %s", len(wanted), out)
            finally:
                prs.Close()
        except Exception as exc:  # pragma: no cover - Windows only  # pdf-toolbox: COM export failures | issue:-
            msg = f"Export nach PDF fehlgeschlagen: {exc}"
            raise PptxRenderingError(msg) from exc
        finally:
            self._close_app(app)
        return str(out)

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
        self._require_env()
        del quality, max_size_mb
        inp = Path(input_pptx).resolve()
        if not inp.exists():
            msg = f"Eingabe nicht gefunden: {inp}"
            raise PptxRenderingError(msg)

        out = Path(out_dir) if out_dir else inp.with_suffix("")
        out.mkdir(parents=True, exist_ok=True)

        ext_map = {"JPEG": "JPG", "PNG": "PNG", "TIFF": "TIFF"}
        fmt = image_format.upper()
        try:
            ext = ext_map[fmt]
        except KeyError as exc:
            msg = f"Unsupported image format: {image_format}"
            raise PptxRenderingError(msg) from exc

        logger.info("Rendering %s to images (%s)", inp, fmt)
        app = self._open_app()
        try:
            prs = self._open_presentation(app, inp)
            try:
                slides = list(prs.Slides)
                numbers = parse_page_spec(range_spec, len(slides))
                if not numbers:
                    numbers = list(range(1, len(slides) + 1))
                for existing in out.glob(f"Slide*.{fmt.lower()}"):
                    with contextlib.suppress(Exception):
                        existing.unlink()
                count = 0
                for number in numbers:
                    slide = slides[number - 1]
                    filename = out / f"Slide{number}.{fmt.lower()}"
                    if width is not None and height is not None:
                        slide.Export(str(filename), ext, int(width), int(height))
                    else:
                        slide.Export(str(filename), ext)
                    count += 1
                logger.info("Exported %d image(s) to %s", count, out)
            finally:
                prs.Close()
        except Exception as exc:  # pragma: no cover - Windows only  # pdf-toolbox: COM export failures | issue:-
            msg = f"Export nach Bildern fehlgeschlagen: {exc}"
            raise PptxRenderingError(msg) from exc
        finally:
            self._close_app(app)
        return str(out)


__all__ = ["PptxMsOfficeRenderer"]
