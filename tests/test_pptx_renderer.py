import json
from types import SimpleNamespace

import pytest

from pdf_toolbox import config
from pdf_toolbox.renderers import pptx
from pdf_toolbox.renderers.pptx import (
    NullRenderer,
    PptxProviderUnavailableError,
    get_pptx_renderer,
    require_pptx_renderer,
)
from pdf_toolbox.renderers.pptx_base import BasePptxRenderer


class _BaseTestRenderer(BasePptxRenderer):
    """Minimal renderer implementation for registry tests."""

    def to_images(  # noqa: PLR0913  # pdf-toolbox: renderer stub matches renderer API signature | issue:-
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
        del (out_dir, max_size_mb, image_format, quality, width, height, range_spec)
        return "images"

    def to_pdf(
        self,
        _input_pptx: str,
        output_path: str | None = None,
        notes: bool = False,
        handout: bool = False,
        range_spec: str | None = None,
    ) -> str:
        del output_path, notes, handout, range_spec
        return "pdf"


def test_default_renderer(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "cfg.json")
    assert isinstance(get_pptx_renderer(), NullRenderer)


def test_ms_office_renderer(monkeypatch, tmp_path):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({"pptx_renderer": "ms_office"}))
    monkeypatch.setattr(config, "CONFIG_PATH", cfg_path)

    instance = _BaseTestRenderer()

    def fake_select(name: str):
        assert name == "ms_office"
        return instance

    monkeypatch.setattr(pptx, "registry_select", fake_select)
    assert get_pptx_renderer() is instance


def test_unknown_renderer(monkeypatch, tmp_path):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({"pptx_renderer": "unknown"}))
    monkeypatch.setattr(config, "CONFIG_PATH", cfg_path)

    monkeypatch.setattr(pptx, "registry_select", lambda _name: None)
    assert isinstance(get_pptx_renderer(), NullRenderer)


def test_load_via_registry_delegates(monkeypatch):
    called = SimpleNamespace(name=None)
    renderer = _BaseTestRenderer()

    def fake_select(name: str):
        called.name = name
        return renderer

    monkeypatch.setattr(pptx, "registry_select", fake_select)
    assert pptx._load_via_registry("http_office") is renderer
    assert called.name == "http_office"


def test_require_pptx_renderer_raises_without_backend(monkeypatch, tmp_path):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({"pptx_renderer": "none"}))
    monkeypatch.setattr(config, "CONFIG_PATH", cfg_path)
    monkeypatch.setattr(pptx, "registry_select", lambda _name: None)

    with pytest.raises(PptxProviderUnavailableError):
        require_pptx_renderer()
