from __future__ import annotations

"""Microsoft PowerPoint based PPTX renderer."""

from pathlib import Path
from typing import Literal, Optional

from pdf_toolbox.renderers.pptx import BasePptxRenderer, PptxRenderingError
from pdf_toolbox.utils import logger

try:  # pragma: no cover - import guarded for non-Windows platforms
    import pythoncom  # type: ignore
    import win32com.client  # type: ignore
except Exception:  # pragma: no cover - handled in _require_env
    win32com = None  # type: ignore


class PptxMsOfficeRenderer(BasePptxRenderer):
    """Render PPTX files using Microsoft PowerPoint.

    The renderer relies on COM automation and therefore only works on Windows
    systems with an installed version of Microsoft PowerPoint. It must be
    enabled explicitly via the ``PDF_TOOLBOX_PPTX_RENDERER`` environment
    variable and the optional ``pptx-render`` extras.

    Example:
        >>> from pdf_toolbox.renderers.ms_office import PptxMsOfficeRenderer
        >>> PptxMsOfficeRenderer().to_pdf("slides.pptx")
        'slides.pdf'
    """

    _PP_SAVE_AS_PDF = 32  # ppSaveAsPDF

    def _require_env(self) -> None:
        if win32com is None:
            msg = (
                "MS-Office Renderer nicht verfügbar: Windows/PowerPoint/pywin32 erforderlich."
            )
            raise PptxRenderingError(msg)

    def _open_app(self):  # pragma: no cover - Windows only
        pythoncom.CoInitialize()
        app = win32com.client.DispatchEx("PowerPoint.Application")
        try:
            app.DisplayAlerts = 1  # ppAlertsNone
        except Exception:  # noqa: BLE001 - best effort
            pass
        app.Visible = False
        return app

    def _close_app(self, app) -> None:  # pragma: no cover - Windows only
        try:
            app.Quit()
        finally:
            pythoncom.CoUninitialize()

    def _open_presentation(self, app, path: Path):  # pragma: no cover - Windows only
        return app.Presentations.Open(str(path), True, False, False)

    @staticmethod
    def _parse_range(spec: Optional[str], max_index: int) -> set[int]:
        if not spec:
            return set(range(1, max_index + 1))
        s = spec.replace(" ", "")
        result: set[int] = set()
        for part in s.split(","):
            if "-" in part:
                a, b = part.split("-", 1)
                start = max_index if a.lower() == "n" else int(a)
                end = max_index if b.lower() == "n" else int(b)
                if start > end:
                    start, end = end, start
                result.update(range(max(1, start), min(max_index, end) + 1))
            elif part:
                idx = max_index if part.lower() == "n" else int(part)
                if 1 <= idx <= max_index:
                    result.add(idx)
        return result

    # ------------------------------------------------------------------
    # BasePptxRenderer API
    # ------------------------------------------------------------------
    def to_pdf(
        self,
        input_pptx: str,
        output_path: str | None = None,
        notes: bool = False,
        handout: bool = False,
        range_spec: str | None = None,
    ) -> str:
        self._require_env()
        inp = Path(input_pptx).resolve()
        if not inp.exists():
            raise PptxRenderingError(f"Eingabe nicht gefunden: {inp}")

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
        except Exception as exc:  # pragma: no cover - Windows only
            raise PptxRenderingError(f"Export nach PDF fehlgeschlagen: {exc}") from exc
        finally:
            self._close_app(app)
        return str(out)

    def to_images(
        self,
        input_pptx: str,
        out_dir: str | None = None,
        max_size_mb: float | None = None,
        format: Literal["jpeg", "png", "tiff"] = "jpeg",
        width: int | None = None,
        height: int | None = None,
    ) -> str:
        self._require_env()
        inp = Path(input_pptx).resolve()
        if not inp.exists():
            raise PptxRenderingError(f"Eingabe nicht gefunden: {inp}")

        out = Path(out_dir) if out_dir else inp.with_suffix("")
        out.mkdir(parents=True, exist_ok=True)

        ext_map = {"jpeg": "JPG", "png": "PNG", "tiff": "TIFF"}
        ext = ext_map[format.lower()]

        logger.info("Rendering %s to images (%s)", inp, format)
        app = self._open_app()
        try:
            prs = self._open_presentation(app, inp)
            try:
                if width is not None and height is not None:
                    prs.Export(str(out), ext, int(width), int(height))
                else:
                    prs.Export(str(out), ext)
                count = len(list(out.glob(f"*.{format.lower()}")))
                logger.info("Exported %d image(s) to %s", count, out)
            finally:
                prs.Close()
        except Exception as exc:  # pragma: no cover - Windows only
            raise PptxRenderingError(f"Export nach Bildern fehlgeschlagen: {exc}") from exc
        finally:
            self._close_app(app)
        return str(out)


__all__ = ["PptxMsOfficeRenderer"]
