from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from pdf_toolbox.renderers import ms_office
from pdf_toolbox.renderers.ms_office import PptxMsOfficeRenderer, PptxRenderingError
from pdf_toolbox.renderers.pptx import UnsupportedOptionError


class DummyPythonCom:
    """Track COM initialisation lifecycle for tests."""

    def __init__(self) -> None:
        """Initialise counters."""
        self.init_calls = 0
        self.uninit_calls = 0

    def CoInitialize(self) -> None:  # noqa: N802  # pdf-toolbox: mirror COM method name | issue:-
        """Record a COM initialisation call."""
        self.init_calls += 1

    def CoUninitialize(self) -> None:  # noqa: N802  # pdf-toolbox: mirror COM method name | issue:-
        """Record a COM uninitialisation call."""
        self.uninit_calls += 1


class DummyTransition:
    """Expose the slide transition hidden flag."""

    def __init__(self) -> None:
        """Default the hidden flag to ``False``."""
        self.Hidden = False


class DummySlide:
    """Minimal slide wrapper that records export calls."""

    def __init__(self) -> None:
        """Initialise slide transition state."""
        self.SlideShowTransition = DummyTransition()
        self.exports: list[tuple[Path, str, tuple[int, int] | None]] = []

    def Export(  # noqa: N802  # pdf-toolbox: COM style method name | issue:-
        self,
        path: str,
        ext: str,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """Persist an export event to the recorded list."""
        target = Path(path)
        target.write_text(ext)
        size: tuple[int, int] | None = None
        if width is not None and height is not None:
            size = (width, height)
        self.exports.append((target, ext, size))


class DummyPresentation:
    """Record presentation save and close calls."""

    def __init__(self, slides: list[DummySlide]) -> None:
        """Store the slides managed by this presentation."""
        self.Slides = slides
        self.saved: list[tuple[Path, int]] = []
        self.closed = False

    def SaveAs(self, path: str, format_code: int) -> None:  # noqa: N802  # pdf-toolbox: COM style method name | issue:-
        """Simulate saving the presentation to disk."""
        target = Path(path)
        target.write_text("pdf")
        self.saved.append((target, format_code))

    def Close(self) -> None:  # noqa: N802  # pdf-toolbox: COM style method name | issue:-
        """Mark the presentation as closed."""
        self.closed = True


class DummyPresentations:
    """Expose a subset of the COM presentations API."""

    def __init__(self, presentation: DummyPresentation) -> None:
        """Bind the collection to a single presentation object."""
        self._presentation = presentation
        self.opened: list[Path] = []

    def Open(self, path: str, *_flags: object) -> DummyPresentation:  # noqa: N802  # pdf-toolbox: COM style method name | issue:-
        """Record the path that was requested."""
        target = Path(path)
        self.opened.append(target)
        return self._presentation


class DummyApp:
    """Mirror the subset of the PowerPoint application used in tests."""

    def __init__(self, presentation: DummyPresentation) -> None:
        """Initialise the app with a presentation collection."""
        self.Presentations = DummyPresentations(presentation)
        self.Visible = True
        self.DisplayAlerts = 2
        self.quit_called = False

    def Quit(self) -> None:  # noqa: N802  # pdf-toolbox: COM style method name | issue:-
        """Record that ``Quit`` was invoked."""
        self.quit_called = True


class DummyClient:
    """Capture Dispatch calls performed by the renderer."""

    def __init__(self, app: DummyApp) -> None:
        """Store the COM application object that should be returned."""
        self._app = app
        self.calls: list[tuple[str, str]] = []

    def Dispatch(self, prog_id: str) -> DummyApp:  # noqa: N802  # pdf-toolbox: COM style method name | issue:-
        """Record a standard ``Dispatch`` invocation."""
        self.calls.append(("Dispatch", prog_id))
        return self._app

    def DispatchEx(self, prog_id: str) -> DummyApp:  # noqa: N802  # pdf-toolbox: COM style method name | issue:-
        """Record a ``DispatchEx`` invocation."""
        self.calls.append(("DispatchEx", prog_id))
        return self._app


@pytest.fixture
def setup_com(monkeypatch):
    def _setup(slide_count: int = 3) -> SimpleNamespace:
        slides = [DummySlide() for _ in range(slide_count)]
        presentation = DummyPresentation(slides)
        app = DummyApp(presentation)
        client = DummyClient(app)
        pythoncom_mod = DummyPythonCom()

        monkeypatch.setattr(ms_office, "IS_WINDOWS", True)
        monkeypatch.setattr(ms_office, "pythoncom", pythoncom_mod)
        monkeypatch.setattr(ms_office, "win32_client", client)

        return SimpleNamespace(
            pythoncom=pythoncom_mod,
            client=client,
            presentation=presentation,
            app=app,
            slides=slides,
        )

    return _setup


def test_probe_true_when_com_available(setup_com, monkeypatch):
    env = setup_com()
    messages: list[str] = []

    def record(msg: str, *args: object, **_kwargs: object) -> None:
        messages.append(msg % args if args else msg)

    monkeypatch.setattr(ms_office.logger, "info", record)

    assert PptxMsOfficeRenderer.probe() is True
    assert env.pythoncom.init_calls == 1
    assert env.pythoncom.uninit_calls == 1
    assert env.app.quit_called is True
    assert ("DispatchEx", ms_office._POWERPOINT_PROG_ID) in env.client.calls
    assert any("probe available" in message for message in messages)


def test_probe_false_on_non_windows(monkeypatch):
    messages: list[str] = []

    def record(msg: str, *args: object, **_kwargs: object) -> None:
        messages.append(msg % args if args else msg)

    monkeypatch.setattr(ms_office.logger, "info", record)
    monkeypatch.setattr(ms_office, "IS_WINDOWS", False)
    monkeypatch.setattr(ms_office, "pythoncom", None)
    monkeypatch.setattr(ms_office, "win32_client", None)

    assert PptxMsOfficeRenderer.probe() is False
    assert any("unsupported platform" in message for message in messages)


def test_probe_false_when_dispatch_fails(setup_com, monkeypatch):
    env = setup_com()
    messages: list[str] = []

    def record(msg: str, *args: object, **_kwargs: object) -> None:
        messages.append(msg % args if args else msg)

    monkeypatch.setattr(ms_office.logger, "info", record)

    def boom(_prog_id: str) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(env.client, "DispatchEx", boom)

    assert PptxMsOfficeRenderer.probe() is False
    assert env.pythoncom.uninit_calls == 1
    assert any("PowerPoint automation failed" in message for message in messages)


def test_to_pdf_exports_selected_slides(tmp_path, setup_com):
    env = setup_com(slide_count=3)
    src = tmp_path / "deck.pptx"
    src.write_text("pptx")
    out = tmp_path / "deck.pdf"

    renderer = PptxMsOfficeRenderer()
    result = renderer.to_pdf(str(src), str(out), range_spec="1-2")

    assert Path(result) == out
    assert out.read_text() == "pdf"
    assert env.presentation.saved == [(out, ms_office._PP_SAVE_AS_PDF)]
    hidden_flags = [slide.SlideShowTransition.Hidden for slide in env.slides]
    assert hidden_flags == [False, False, True]
    assert env.presentation.closed is True
    assert env.app.quit_called is True
    assert env.pythoncom.uninit_calls == 1


def test_to_pdf_rejects_notes(tmp_path):
    src = tmp_path / "deck.pptx"
    src.write_text("pptx")

    renderer = PptxMsOfficeRenderer()

    with pytest.raises(UnsupportedOptionError) as excinfo:
        renderer.to_pdf(str(src), notes=True)

    assert excinfo.value.code == "unsupported_option"


def test_to_pdf_conflicting_options(tmp_path):
    src = tmp_path / "deck.pptx"
    src.write_text("pptx")

    renderer = PptxMsOfficeRenderer()

    with pytest.raises(UnsupportedOptionError) as excinfo:
        renderer.to_pdf(str(src), notes=True, handout=True)

    assert excinfo.value.code == "conflicting_options"


def test_to_pdf_raises_for_invalid_range(tmp_path, setup_com):
    setup_com(slide_count=2)
    src = tmp_path / "deck.pptx"
    src.write_text("pptx")

    renderer = PptxMsOfficeRenderer()

    with pytest.raises(PptxRenderingError) as excinfo:
        renderer.to_pdf(str(src), range_spec="5")

    assert excinfo.value.code == "invalid_range"


def test_to_pdf_missing_input(tmp_path):
    renderer = PptxMsOfficeRenderer()

    with pytest.raises(PptxRenderingError) as excinfo:
        renderer.to_pdf(str(tmp_path / "missing.pptx"))

    assert excinfo.value.code == "unavailable"


def test_to_images_exports_all_slides(tmp_path, setup_com):
    env = setup_com(slide_count=2)
    src = tmp_path / "deck.pptx"
    src.write_text("pptx")
    out_dir = tmp_path / "images"

    renderer = PptxMsOfficeRenderer()
    result_dir = Path(
        renderer.to_images(
            str(src),
            out_dir=str(out_dir),
            image_format="PNG",
            width=640,
            height=480,
        )
    )

    files = sorted(result_dir.glob("slide-*.png"))
    assert [path.name for path in files] == ["slide-001.png", "slide-002.png"]
    assert [path.read_text() for path in files] == ["PNG", "PNG"]
    assert all(slide.exports for slide in env.slides[:2])
    assert all(
        export[2] == (640, 480) for slide in env.slides[:2] for export in slide.exports
    )
    assert env.presentation.closed is True
    assert env.app.quit_called is True
    assert env.pythoncom.uninit_calls == 1


def test_to_images_rejects_unsupported_format(tmp_path, setup_com):
    setup_com(slide_count=1)
    src = tmp_path / "deck.pptx"
    src.write_text("pptx")

    renderer = PptxMsOfficeRenderer()

    with pytest.raises(PptxRenderingError) as excinfo:
        renderer.to_images(str(src), image_format="GIF")

    assert excinfo.value.code == "unsupported_option"
