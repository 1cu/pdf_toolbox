"""Tests for the PPTX renderer registry."""

from __future__ import annotations

import pytest

from pdf_toolbox.renderers import registry
from pdf_toolbox.renderers.pptx_base import BasePptxRenderer


class _BaseStub(BasePptxRenderer):
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


def test_register_and_available(monkeypatch):
    monkeypatch.setattr(registry, "_REGISTRY", {})

    class DemoRenderer(_BaseStub):
        name = "demo"

    registered = registry.register(DemoRenderer)
    assert registered is DemoRenderer
    assert registry.available() == ("demo",)
    assert registry.select("demo") is DemoRenderer


def test_register_requires_unique_name(monkeypatch):
    monkeypatch.setattr(registry, "_REGISTRY", {})

    class DemoRenderer(_BaseStub):
        name = "demo"

    registry.register(DemoRenderer)

    class OtherRenderer(_BaseStub):
        name = "demo"

    with pytest.raises(ValueError, match="demo"):
        registry.register(OtherRenderer)


def test_register_requires_name(monkeypatch):
    monkeypatch.setattr(registry, "_REGISTRY", {})

    class NamelessRenderer(_BaseStub):
        name = ""

    with pytest.raises(ValueError, match="non-empty"):
        registry.register(NamelessRenderer)


def test_select_auto_prefers_non_null(monkeypatch):
    monkeypatch.setattr(registry, "_REGISTRY", {})

    class NullRenderer(_BaseStub):
        name = "null"

    class PrimaryRenderer(_BaseStub):
        name = "primary"

    registry.register(NullRenderer)
    registry.register(PrimaryRenderer)

    assert registry.select("auto") is PrimaryRenderer

    monkeypatch.setattr(registry, "_REGISTRY", {"null": NullRenderer})
    assert registry.select("auto") is NullRenderer
