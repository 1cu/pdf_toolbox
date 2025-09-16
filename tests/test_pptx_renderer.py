from __future__ import annotations

import json
import types

import pytest

from pdf_toolbox import config
from pdf_toolbox.renderers import pptx
from pdf_toolbox.renderers import registry as renderer_registry
from pdf_toolbox.renderers.ms_office import PptxMsOfficeRenderer
from pdf_toolbox.renderers.pptx import NullRenderer, get_pptx_renderer
from pdf_toolbox.renderers.pptx_base import BasePptxRenderer


def test_default_renderer(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "cfg.json")
    assert isinstance(get_pptx_renderer(), NullRenderer)


def test_ms_office_renderer(tmp_path, monkeypatch):
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps({"pptx_renderer": "ms_office"}))
    monkeypatch.setattr(config, "CONFIG_PATH", path)
    assert isinstance(get_pptx_renderer(), PptxMsOfficeRenderer)


def test_unknown_renderer(tmp_path, monkeypatch):
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps({"pptx_renderer": "unknown"}))
    monkeypatch.setattr(config, "CONFIG_PATH", path)
    assert isinstance(get_pptx_renderer(), NullRenderer)


def test_load_via_registry_imports_builtin(monkeypatch):
    monkeypatch.setattr(renderer_registry, "_REGISTRY", {})

    class DummyRenderer(BasePptxRenderer):
        name = "dummy"

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

    def fake_import(name: str):
        assert name == "dummy.module"
        renderer_registry.register(DummyRenderer)
        return types.ModuleType(name)

    monkeypatch.setattr(pptx, "_BUILTIN_MODULES", {"dummy": "dummy.module"})
    monkeypatch.setattr(pptx.importlib, "import_module", fake_import)

    renderer = pptx._load_via_registry("dummy")
    assert isinstance(renderer, DummyRenderer)


def test_load_via_registry_auto_prefers_real_renderer(monkeypatch):
    monkeypatch.setattr(renderer_registry, "_REGISTRY", {})
    renderer_registry.register(pptx.NullRenderer)

    class DummyRenderer(BasePptxRenderer):
        name = "dummy"

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

    def fake_import(name: str):
        assert name == "dummy.module"
        renderer_registry.register(DummyRenderer)
        return types.ModuleType(name)

    monkeypatch.setattr(pptx, "_BUILTIN_MODULES", {"dummy": "dummy.module"})
    monkeypatch.setattr(pptx.importlib, "import_module", fake_import)

    renderer = pptx._load_via_registry("auto")
    assert isinstance(renderer, DummyRenderer)


def test_load_via_registry_auto_falls_back_to_null(monkeypatch):
    monkeypatch.setattr(renderer_registry, "_REGISTRY", {})
    renderer_registry.register(pptx.NullRenderer)
    monkeypatch.setattr(pptx, "_BUILTIN_MODULES", {})

    renderer = pptx._load_via_registry("auto")
    assert isinstance(renderer, pptx.NullRenderer)


def test_registry_auto_selection_respects_probe(monkeypatch):
    monkeypatch.setattr(renderer_registry, "_REGISTRY", {})
    renderer_registry.register(pptx.NullRenderer)

    class FailingRenderer(BasePptxRenderer):
        name = "lightweight"

        @classmethod
        def probe(cls) -> bool:
            return False

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

    class WorkingRenderer(BasePptxRenderer):
        name = "ms_office"

        @classmethod
        def probe(cls) -> bool:
            return True

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

    renderer_registry.register(FailingRenderer)
    renderer_registry.register(WorkingRenderer)

    selected = renderer_registry.select("auto")
    assert selected is WorkingRenderer

    monkeypatch.setattr(WorkingRenderer, "probe", classmethod(lambda cls: False))
    assert renderer_registry.select("auto") is pptx.NullRenderer


def test_registry_ensure_raises_for_missing_provider(monkeypatch):
    monkeypatch.setattr(renderer_registry, "_REGISTRY", {"null": pptx.NullRenderer})

    with pytest.raises(renderer_registry.RendererSelectionError) as exc:
        renderer_registry.ensure("lightweight")

    assert "lightweight" in str(exc.value)
