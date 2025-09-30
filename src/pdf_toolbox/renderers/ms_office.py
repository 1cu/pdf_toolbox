"""Optional Microsoft PowerPoint renderer backed by COM automation."""

from __future__ import annotations

import contextlib
import sys
from collections.abc import Callable, Iterator
from importlib import import_module
from pathlib import Path
from typing import Any, ClassVar

from pdf_toolbox.renderers.pptx import PptxRenderingError, UnsupportedOptionError
from pdf_toolbox.renderers.pptx_base import BasePptxRenderer, RenderOptions
from pdf_toolbox.renderers.registry import register
from pdf_toolbox.utils import logger, parse_page_spec

IS_WINDOWS = sys.platform.startswith("win")


def _load_pywin32(
    importer: Callable[[str], Any] = import_module,
) -> tuple[Any | None, Any | None]:
    """Return the optional pywin32 modules when available."""
    if not IS_WINDOWS:
        return None, None

    try:
        pythoncom_mod = importer("pythoncom")
        client_mod = importer("win32com.client")
    except Exception:
        return None, None

    return pythoncom_mod, client_mod


pythoncom: Any | None
win32_client: Any | None
pythoncom, win32_client = _load_pywin32()

_POWERPOINT_PROG_ID = "PowerPoint.Application"
_PP_SAVE_AS_PDF = 32  # ppSaveAsPDF

_ERR_AUTOMATION_FAILED = "PowerPoint automation failed"
_ERR_COM_INIT_FAILED = "COM initialisation failed"
_ERR_OPEN_PRESENTATION_FAILED = "Failed to open presentation"
_ERR_EXPORT_PDF_FAILED = "Export to PDF failed"
_ERR_EXPORT_IMAGES_FAILED = "Export to images failed"


def _log_probe_result(name: str, available: bool, detail: str) -> bool:
    """Log the probe outcome and return ``available`` for convenience."""
    status = "available" if available else "unavailable"
    logger.info("pptx renderer '%s' probe %s: %s", name, status, detail)
    return available


def _ensure_com_environment() -> tuple[Any, Any]:
    """Return COM modules when Microsoft PowerPoint automation is available."""
    if not IS_WINDOWS:
        msg = "Microsoft PowerPoint automation requires Windows."
        raise PptxRenderingError(msg, code="unavailable")
    if pythoncom is None or win32_client is None:
        msg = "pywin32/PowerPoint not available. Install Microsoft Office."
        raise PptxRenderingError(msg, code="unavailable")
    return pythoncom, win32_client


def _get_dispatch(client_mod: Any) -> Callable[[str], Any]:
    """Return the PowerPoint ``Dispatch`` callable from ``client_mod``."""
    dispatch = getattr(client_mod, "DispatchEx", None) or getattr(client_mod, "Dispatch", None)
    if dispatch is None:
        msg = "PowerPoint COM dispatch is unavailable."
        raise PptxRenderingError(msg, code="backend_crashed")
    return dispatch


def _dispatch_powerpoint(client_mod: Any) -> Any:
    """Return the PowerPoint application COM object."""
    dispatch = _get_dispatch(client_mod)
    try:
        return dispatch(_POWERPOINT_PROG_ID)
    except Exception as exc:
        raise PptxRenderingError(
            _ERR_AUTOMATION_FAILED,
            code="backend_crashed",
            detail=str(exc),
        ) from exc


def _resolve_slide_numbers(range_spec: str | None, total: int) -> list[int]:
    """Return 1-based slide numbers respecting ``range_spec``."""
    if total == 0:
        return []
    if range_spec is None:
        return list(range(1, total + 1))
    try:
        numbers = parse_page_spec(range_spec, total)
    except ValueError as exc:
        raise PptxRenderingError("invalid_range", code="invalid_range") from exc
    if not numbers:
        raise PptxRenderingError("empty_selection", code="empty_selection")
    return numbers


@contextlib.contextmanager
def _powerpoint_session() -> Iterator[Any]:
    """Yield a PowerPoint COM application instance and handle lifecycle."""
    pythoncom_mod, client_mod = _ensure_com_environment()
    try:
        pythoncom_mod.CoInitialize()
    except Exception as exc:
        raise PptxRenderingError(
            _ERR_COM_INIT_FAILED,
            code="backend_crashed",
            detail=str(exc),
        ) from exc

    app: Any | None = None
    try:
        app = _dispatch_powerpoint(client_mod)
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
        msg = "PowerPoint did not expose a presentations collection."
        raise PptxRenderingError(msg, code="backend_crashed")
    try:
        return presentations.Open(str(path), True, False, False)
    except Exception as exc:
        raise PptxRenderingError(
            _ERR_OPEN_PRESENTATION_FAILED,
            code="backend_crashed",
            detail=str(exc),
        ) from exc


class PptxMsOfficeRenderer(BasePptxRenderer):
    """Render PPTX files using Microsoft PowerPoint."""

    name: ClassVar[str] = "ms_office"
    _PP_SAVE_AS_PDF: ClassVar[int] = _PP_SAVE_AS_PDF

    @classmethod
    def probe(cls) -> bool:
        """Return ``True`` when PowerPoint automation is reachable."""
        renderer_name = cls.name or "ms_office"
        if not IS_WINDOWS:
            return _log_probe_result(renderer_name, False, "unsupported platform")
        if pythoncom is None or win32_client is None:
            return _log_probe_result(renderer_name, False, "pywin32 libraries missing")

        pythoncom_mod = pythoncom
        client_mod = win32_client
        try:
            pythoncom_mod.CoInitialize()
        except Exception as exc:
            return _log_probe_result(
                renderer_name,
                False,
                f"COM initialisation failed: {exc}",
            )

        app: Any | None = None
        available = False
        detail = "PowerPoint automation unreachable"
        try:
            app = _dispatch_powerpoint(client_mod)
        except PptxRenderingError as exc:
            detail = str(exc)
        except Exception as exc:
            detail = f"unexpected error: {exc}"
        else:
            available = True
            detail = "PowerPoint automation reachable"
        finally:
            if app is not None:
                with contextlib.suppress(Exception):
                    app.Quit()
            pythoncom_mod.CoUninitialize()

        return _log_probe_result(renderer_name, available, detail)

    @classmethod
    def can_handle(cls) -> bool:
        """Backward compatible alias for :meth:`probe`."""
        return cls.probe()

    def to_pdf(
        self,
        input_pptx: str,
        output_path: str | None = None,
        notes: bool = False,
        handout: bool = False,
        range_spec: str | None = None,
    ) -> str:
        """Render ``input_pptx`` to a PDF file via Microsoft PowerPoint."""
        if notes and handout:
            msg = "Notes and handout export cannot be combined."
            raise UnsupportedOptionError(msg, code="conflicting_options")
        if notes or handout:
            msg = "Notes export is not supported." if notes else "Handout export is not supported."
            raise UnsupportedOptionError(msg)

        inp = Path(input_pptx).resolve()
        if not inp.exists():
            msg = f"Input file not found: {inp}"
            raise PptxRenderingError(msg, code="unavailable")

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
                exported = _resolve_slide_numbers(range_spec, total)
                selected = set(exported)
                if total and len(selected) != total:
                    for index, slide in enumerate(slides, start=1):
                        transition = getattr(slide, "SlideShowTransition", None)
                        if transition is None:
                            continue
                        with contextlib.suppress(Exception):
                            transition.Hidden = index not in selected
                presentation.SaveAs(str(out), self._PP_SAVE_AS_PDF)
            except PptxRenderingError:
                raise
            except Exception as exc:
                raise PptxRenderingError(
                    _ERR_EXPORT_PDF_FAILED,
                    code="backend_crashed",
                    detail=str(exc),
                ) from exc
            finally:
                if presentation is not None:
                    with contextlib.suppress(Exception):
                        presentation.Close()

        logger.info("Rendered %d slide(s) to %s", len(exported), out)
        return str(out)

    def to_images(
        self,
        input_pptx: str,
        options: RenderOptions | None = None,
    ) -> str:
        """Render ``input_pptx`` slides to images."""
        opts = options or RenderOptions()

        inp = Path(input_pptx).resolve()
        if not inp.exists():
            msg = f"Input file not found: {inp}"
            raise PptxRenderingError(msg, code="unavailable")

        out = Path(opts.out_dir) if opts.out_dir else inp.with_suffix("")
        out.mkdir(parents=True, exist_ok=True)

        ext_map = {"JPEG": "JPEG", "PNG": "PNG", "TIFF": "TIFF"}
        fmt = (opts.image_format or "").upper()
        try:
            ext = ext_map[fmt]
        except KeyError as exc:
            msg = f"Unsupported image format: {opts.image_format}"
            raise PptxRenderingError(msg, code="unsupported_option") from exc

        logger.info("Rendering %s to images (%s)", inp, fmt)

        with _powerpoint_session() as app:
            presentation = None
            try:
                presentation = _open_presentation(app, inp)
                slides = list(presentation.Slides)
                total = len(slides)
                numbers = _resolve_slide_numbers(opts.range_spec, total)
                padding = max(3, len(str(total or 1)))
                pattern = f"slide-*.{fmt.lower()}"
                for existing in out.glob(pattern):
                    with contextlib.suppress(Exception):
                        existing.unlink()
                count = 0
                for number in numbers:
                    slide = slides[number - 1]
                    filename = out / f"slide-{number:0{padding}d}.{fmt.lower()}"
                    if opts.width is not None and opts.height is not None:
                        slide.Export(
                            str(filename),
                            ext,
                            int(opts.width),
                            int(opts.height),
                        )
                    else:
                        slide.Export(str(filename), ext)
                    count += 1
                logger.info("Exported %d image(s) to %s", count, out)
            except PptxRenderingError:
                raise
            except Exception as exc:
                raise PptxRenderingError(
                    _ERR_EXPORT_IMAGES_FAILED,
                    code="backend_crashed",
                    detail=str(exc),
                ) from exc
            finally:
                if presentation is not None:
                    with contextlib.suppress(Exception):
                        presentation.Close()
        return str(out)


register(PptxMsOfficeRenderer)


__all__ = ["PptxMsOfficeRenderer"]
