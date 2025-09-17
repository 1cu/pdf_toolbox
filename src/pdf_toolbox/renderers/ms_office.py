"""Optional Microsoft PowerPoint renderer backed by COM automation."""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from typing import Any, ClassVar, Iterator, Literal

from pdf_toolbox.renderers.pptx import PptxRenderingError
from pdf_toolbox.renderers.pptx_base import BasePptxRenderer
from pdf_toolbox.renderers.registry import register
from pdf_toolbox.utils import logger, parse_page_spec

IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:
    try:  # pragma: no cover - optional dependency import guarded for Windows only  # pdf-toolbox: PowerPoint automation relies on pywin32 | issue:-
        import pythoncom  # type: ignore  # pdf-toolbox: pywin32 is optional and lacks type hints | issue:-
        from win32com import client as win32_client  # type: ignore  # pdf-toolbox: pywin32 is optional and lacks type hints | issue:-
    except Exception:  # pragma: no cover - handled in runtime checks  # pdf-toolbox: gracefully degrade without pywin32 | issue:-
        pythoncom = None  # type: ignore[assignment]
        win32_client = None  # type: ignore[assignment]
else:  # pragma: no cover - import guard for non-Windows platforms  # pdf-toolbox: PowerPoint COM only available on Windows | issue:-
    pythoncom = None  # type: ignore[assignment]
    win32_client = None  # type: ignore[assignment]

_POWERPOINT_PROG_ID = "PowerPoint.Application"
_PP_SAVE_AS_PDF = 32  # ppSaveAsPDF


def _ensure_com_environment() -> tuple[Any, Any]:
    """Return COM modules when Microsoft PowerPoint automation is available."""

    if not IS_WINDOWS:
        msg = "Microsoft PowerPoint-Automatisierung erfordert Windows."
        raise PptxRenderingError(msg)
    if pythoncom is None or win32_client is None:
        msg = "pywin32/PowerPoint nicht verfügbar. Bitte Microsoft Office installieren."
        raise PptxRenderingError(msg)
    return pythoncom, win32_client


@contextlib.contextmanager
def _powerpoint_session() -> Iterator[Any]:
    """Yield a PowerPoint COM application instance and handle lifecycle."""

    pythoncom_mod, client_mod = _ensure_com_environment()
    try:
        pythoncom_mod.CoInitialize()
    except Exception as exc:  # pragma: no cover - depends on Windows COM  # pdf-toolbox: propagate COM initialisation failure | issue:-
        raise PptxRenderingError(f"COM-Initialisierung fehlgeschlagen: {exc}") from exc

    dispatch = getattr(client_mod, "DispatchEx", None) or getattr(client_mod, "Dispatch", None)
    if dispatch is None:
        pythoncom_mod.CoUninitialize()
        msg = "PowerPoint-COM-Dispatch nicht verfügbar."
        raise PptxRenderingError(msg)

    app: Any | None = None
    try:
        try:
            app = dispatch(_POWERPOINT_PROG_ID)
        except Exception as exc:  # pragma: no cover - depends on Windows COM  # pdf-toolbox: propagate COM automation failure | issue:-
            raise PptxRenderingError(f"PowerPoint-Automatisierung fehlgeschlagen: {exc}") from exc
        with contextlib.suppress(Exception):
            app.Visible = False
        with contextlib.suppress(Exception):
            app.DisplayAlerts = 1  # ppAlertsNone
        yield app
    finally:
        if app is not None:
            with contextlib.suppress(Exception):
                app.Quit()
        pythoncom_mod.CoUninitialize()


def _open_presentation(app: Any, path: Path) -> Any:
    """Return a COM presentation object for ``path``."""

    presentations = getattr(app, "Presentations", None)
    if presentations is None:
        msg = "PowerPoint bietet keine Präsentationssammlung an."
        raise PptxRenderingError(msg)
    try:
        return presentations.Open(str(path), True, False, False)
    except Exception as exc:  # pragma: no cover - depends on Windows COM  # pdf-toolbox: propagate PowerPoint open failure | issue:-
        raise PptxRenderingError(f"Präsentation konnte nicht geöffnet werden: {exc}") from exc


class PptxMsOfficeRenderer(BasePptxRenderer):
    """Render PPTX files using Microsoft PowerPoint."""

    name: ClassVar[str] = "ms_office"
    _PP_SAVE_AS_PDF: ClassVar[int] = _PP_SAVE_AS_PDF

    @classmethod
    def can_handle(cls) -> bool:
        """Return ``True`` when PowerPoint automation is available."""

        if not IS_WINDOWS or pythoncom is None or win32_client is None:
            return False
        try:
            with _powerpoint_session():
                pass
        except PptxRenderingError:
            return False
        except Exception:  # pragma: no cover - defensive fallback  # pdf-toolbox: guard unexpected COM errors | issue:-
            return False
        return True

    def to_pdf(
        self,
        input_pptx: str,
        output_path: str | None = None,
        notes: bool = False,
        handout: bool = False,
        range_spec: str | None = None,
    ) -> str:
        """Render ``input_pptx`` to a PDF file via Microsoft PowerPoint."""

        if notes or handout:
            msg = "Notizen- oder Handout-Export wird aktuell nicht unterstützt."
            raise PptxRenderingError(msg)

        inp = Path(input_pptx).resolve()
        if not inp.exists():
            msg = f"Eingabe nicht gefunden: {inp}"
            raise PptxRenderingError(msg)

        out = Path(output_path) if output_path else inp.with_suffix(".pdf")
        out.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Rendering %s to PDF via Microsoft PowerPoint", inp)

        exported: list[int] = []
        with _powerpoint_session() as app:
            presentation = None
            try:
                presentation = _open_presentation(app, inp)
                slides = list(presentation.Slides)
                total = len(slides)
                try:
                    exported = parse_page_spec(range_spec, total) if total else []
                except ValueError as exc:
                    raise PptxRenderingError(f"Ungültige Seitenauswahl: {exc}") from exc
                if not exported and total:
                    exported = list(range(1, total + 1))
                selected = set(exported)
                if total:
                    for index, slide in enumerate(slides, start=1):
                        transition = getattr(slide, "SlideShowTransition", None)
                        if transition is None:
                            continue
                        with contextlib.suppress(Exception):
                            transition.Hidden = index not in selected
                presentation.SaveAs(str(out), self._PP_SAVE_AS_PDF)
            except PptxRenderingError:
                raise
            except Exception as exc:  # pragma: no cover - depends on Windows COM  # pdf-toolbox: propagate COM export failure | issue:-
                raise PptxRenderingError(f"Export nach PDF fehlgeschlagen: {exc}") from exc
            finally:
                if presentation is not None:
                    with contextlib.suppress(Exception):
                        presentation.Close()

        logger.info("Rendered %d slide(s) to %s", len(exported), out)
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

        with _powerpoint_session() as app:
            presentation = None
            try:
                presentation = _open_presentation(app, inp)
                slides = list(presentation.Slides)
                total = len(slides)
                try:
                    numbers = parse_page_spec(range_spec, total)
                except ValueError as exc:
                    raise PptxRenderingError(f"Ungültige Seitenauswahl: {exc}") from exc
                if not numbers and total:
                    numbers = list(range(1, total + 1))
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
            except PptxRenderingError:
                raise
            except Exception as exc:  # pragma: no cover - depends on Windows COM  # pdf-toolbox: propagate COM export failure | issue:-
                raise PptxRenderingError(f"Export nach Bildern fehlgeschlagen: {exc}") from exc
            finally:
                if presentation is not None:
                    with contextlib.suppress(Exception):
                        presentation.Close()
        return str(out)


register(PptxMsOfficeRenderer)


__all__ = ["PptxMsOfficeRenderer"]
