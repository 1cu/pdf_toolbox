"""Tests for PPTX actions."""

from __future__ import annotations

import json

import pytest
from pptx import Presentation

from pdf_toolbox import config
from pdf_toolbox.actions.pptx import pptx_to_images, pptx_to_pdf
from pdf_toolbox.renderers import pptx
from pdf_toolbox.renderers.pptx import (
    BasePptxRenderer,
    PptxProviderUnavailableError,
    get_pptx_renderer,
)


@pytest.fixture
def simple_pptx(tmp_path) -> str:
    prs = Presentation()
    for idx in range(5):
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = f"Slide {idx + 1}"
    path = tmp_path / "simple.pptx"
    prs.save(path)
    return str(path)


def test_rendering_actions_raise(simple_pptx):
    with pytest.raises(PptxProviderUnavailableError):
        pptx_to_images(simple_pptx)
    with pytest.raises(PptxProviderUnavailableError):
        pptx_to_pdf(simple_pptx)


def test_null_renderer_methods_raise():
    renderer = pptx.NullRenderer()

    with pytest.raises(PptxProviderUnavailableError) as excinfo:
        renderer.to_images("deck.pptx")

    assert excinfo.value.docs_url == pptx.PPTX_PROVIDER_DOCS_URL

    with pytest.raises(PptxProviderUnavailableError):
        renderer.to_pdf("deck.pptx")


def test_ensure_registered_skips_unknown(monkeypatch):
    monkeypatch.setattr(pptx, "registry_available", lambda: set())
    called: list[str] = []

    def fake_import(name: str) -> None:
        called.append(name)

    monkeypatch.setattr(pptx.importlib, "import_module", fake_import)

    pptx._ensure_registered("missing")

    assert called == []


def test_load_via_registry_handles_empty_and_missing(monkeypatch):
    monkeypatch.setattr(pptx, "registry_available", lambda: set())
    seen: list[str] = []
    monkeypatch.setattr(pptx, "_ensure_registered", lambda name: seen.append(name))
    monkeypatch.setattr(pptx, "registry_select", lambda _name: None)

    assert pptx._load_via_registry("") is None
    assert pptx._load_via_registry("custom") is None
    assert seen == ["custom"]


def test_get_pptx_renderer_falls_back(monkeypatch, tmp_path):
    cfg_path = tmp_path / "pptx.json"
    cfg_path.write_text(json.dumps({"pptx_renderer": "custom"}))
    monkeypatch.setattr(config, "CONFIG_PATH", cfg_path)
    monkeypatch.setattr(pptx, "_load_via_registry", lambda _name: None)

    renderer = pptx.get_pptx_renderer()

    assert isinstance(renderer, pptx.NullRenderer)


def test_renderer_config(monkeypatch, tmp_path):
    captured_pdf: dict[str, str | None] = {}

    class DummyRenderer(BasePptxRenderer):
        def to_images(  # noqa: PLR0913  # pdf-toolbox: renderer API requires many parameters | issue:-
            self,
            _input_pptx: str,
            out_dir: str | None = None,
            max_size_mb: float | None = None,
            image_format: str = "JPEG",
            quality: int | None = None,
            width: int | None = None,
            height: int | None = None,
            range_spec: str | None = None,
        ) -> str:
            del out_dir, max_size_mb, image_format, quality, width, height, range_spec
            return "ok"

        def to_pdf(
            self,
            _input_pptx: str,
            output_path: str | None = None,
            notes: bool = False,
            handout: bool = False,
            range_spec: str | None = None,
        ) -> str:
            del output_path, notes, handout
            captured_pdf["range_spec"] = range_spec
            return "ok.pdf"

    monkeypatch.setattr(
        pptx,
        "_load_via_registry",
        lambda name: DummyRenderer() if name == "dummy" else None,
    )
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({"pptx_renderer": "dummy"}))
    monkeypatch.setattr(config, "CONFIG_PATH", cfg_path)
    renderer = get_pptx_renderer()
    assert isinstance(renderer, DummyRenderer)
    assert pptx_to_images(simple_pptx) == "ok"
    assert pptx_to_pdf(simple_pptx, pages="2-3") == "ok.pdf"
    assert captured_pdf["range_spec"] == "2-3"


def test_pptx_to_images_normalises_params(monkeypatch, simple_pptx, tmp_path):
    captured: dict[str, object] = {}

    class DummyRenderer(BasePptxRenderer):
        def to_images(  # noqa: PLR0913  # pdf-toolbox: renderer API requires many parameters | issue:-
            self,
            _input_pptx: str,
            out_dir: str | None = None,
            max_size_mb: float | None = None,
            image_format: str = "JPEG",
            quality: int | None = None,
            width: int | None = None,
            height: int | None = None,
            range_spec: str | None = None,
        ) -> str:
            del out_dir, max_size_mb, width, height
            captured["format"] = image_format
            captured["quality"] = quality
            captured["range_spec"] = range_spec
            return "ok"

        def to_pdf(
            self,
            _input_pptx: str,
            output_path: str | None = None,
            notes: bool = False,
            handout: bool = False,
            range_spec: str | None = None,
        ) -> str:
            del output_path, notes, handout, range_spec
            return "ok.pdf"

    monkeypatch.setattr(
        pptx,
        "_load_via_registry",
        lambda name: DummyRenderer() if name == "dummy" else None,
    )
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({"pptx_renderer": "dummy"}))
    monkeypatch.setattr(config, "CONFIG_PATH", cfg_path)

    out = pptx_to_images(
        simple_pptx,
        image_format="png",
        quality="Low (70)",
        pages="1-2",
    )
    assert out == "ok"
    assert captured["format"] == "PNG"
    assert captured["quality"] == 70
    assert captured["range_spec"] == "1-2"
