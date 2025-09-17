from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from pdf_toolbox.renderers import ms_office
from pdf_toolbox.renderers.ms_office import PptxMsOfficeRenderer, PptxRenderingError


class DummyPythonCom:
    def __init__(self) -> None:
        self.init_calls = 0
        self.uninit_calls = 0

    def CoInitialize(self) -> None:
        self.init_calls += 1

    def CoUninitialize(self) -> None:
        self.uninit_calls += 1


class DummyTransition:
    def __init__(self) -> None:
        self.Hidden = False


class DummySlide:
    def __init__(self) -> None:
        self.SlideShowTransition = DummyTransition()
        self.exports: list[tuple[Path, str, tuple[int, int] | None]] = []

    def Export(self, path: str, ext: str, width: int | None = None, height: int | None = None) -> None:  # noqa: N802  # pdf-toolbox: COM style method name | issue:-
        target = Path(path)
        target.write_text(ext)
        size: tuple[int, int] | None = None
        if width is not None and height is not None:
            size = (width, height)
        self.exports.append((target, ext, size))


class DummyPresentation:
    def __init__(self, slides: list[DummySlide]) -> None:
        self.Slides = slides
        self.saved: list[tuple[Path, int]] = []
        self.closed = False

    def SaveAs(self, path: str, format_code: int) -> None:  # noqa: N802  # pdf-toolbox: COM style method name | issue:-
        target = Path(path)
        target.write_text("pdf")
        self.saved.append((target, format_code))

    def Close(self) -> None:  # noqa: N802  # pdf-toolbox: COM style method name | issue:-
        self.closed = True


class DummyPresentations:
    def __init__(self, presentation: DummyPresentation) -> None:
        self._presentation = presentation
        self.opened: list[Path] = []

    def Open(self, path: str, *_flags: object) -> DummyPresentation:  # noqa: N802  # pdf-toolbox: COM style method name | issue:-
        target = Path(path)
        self.opened.append(target)
        return self._presentation


class DummyApp:
    def __init__(self, presentation: DummyPresentation) -> None:
        self.Presentations = DummyPresentations(presentation)
        self.Visible = True
        self.DisplayAlerts = 2
        self.quit_called = False

    def Quit(self) -> None:  # noqa: N802  # pdf-toolbox: COM style method name | issue:-
        self.quit_called = True


class DummyClient:
    def __init__(self, app: DummyApp) -> None:
        self._app = app
        self.calls: list[tuple[str, str]] = []

    def Dispatch(self, prog_id: str) -> DummyApp:  # noqa: N802  # pdf-toolbox: COM style method name | issue:-
        self.calls.append(("Dispatch", prog_id))
        return self._app

    def DispatchEx(self, prog_id: str) -> DummyApp:  # noqa: N802  # pdf-toolbox: COM style method name | issue:-
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


def test_can_handle_true_when_com_available(setup_com):
    env = setup_com()

    assert PptxMsOfficeRenderer.can_handle() is True
    assert env.pythoncom.init_calls == 1
    assert env.pythoncom.uninit_calls == 1
    assert env.app.quit_called is True
    assert ("DispatchEx", ms_office._POWERPOINT_PROG_ID) in env.client.calls


def test_can_handle_false_on_non_windows(monkeypatch):
    monkeypatch.setattr(ms_office, "IS_WINDOWS", False)
    monkeypatch.setattr(ms_office, "pythoncom", None)
    monkeypatch.setattr(ms_office, "win32_client", None)

    assert PptxMsOfficeRenderer.can_handle() is False


def test_can_handle_false_when_dispatch_fails(setup_com, monkeypatch):
    env = setup_com()

    def boom(_prog_id: str) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(env.client, "DispatchEx", boom)

    assert PptxMsOfficeRenderer.can_handle() is False
    assert env.pythoncom.uninit_calls == 1


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

    with pytest.raises(PptxRenderingError):
        renderer.to_pdf(str(src), notes=True)


def test_to_pdf_raises_for_invalid_range(tmp_path, setup_com):
    setup_com(slide_count=2)
    src = tmp_path / "deck.pptx"
    src.write_text("pptx")

    renderer = PptxMsOfficeRenderer()

    with pytest.raises(PptxRenderingError) as excinfo:
        renderer.to_pdf(str(src), range_spec="5")

    assert "Ungültige" in str(excinfo.value)


def test_to_pdf_missing_input(tmp_path):
    renderer = PptxMsOfficeRenderer()

    with pytest.raises(PptxRenderingError):
        renderer.to_pdf(str(tmp_path / "missing.pptx"))


def test_to_images_exports_all_slides(tmp_path, setup_com):
    env = setup_com(slide_count=2)
    src = tmp_path / "deck.pptx"
    src.write_text("pptx")
    out_dir = tmp_path / "images"

    renderer = PptxMsOfficeRenderer()
    result_dir = Path(renderer.to_images(str(src), out_dir=str(out_dir), image_format="PNG", width=640, height=480))

    files = sorted(result_dir.glob("Slide*.png"))
    assert [path.read_text() for path in files] == ["PNG", "PNG"]
    assert all(slide.exports for slide in env.slides[:2])
    assert all(export[2] == (640, 480) for slide in env.slides[:2] for export in slide.exports)
    assert env.presentation.closed is True
    assert env.app.quit_called is True
    assert env.pythoncom.uninit_calls == 1
