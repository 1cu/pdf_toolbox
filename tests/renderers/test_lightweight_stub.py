"""Tests for the lightweight PPTX renderer stub."""

from __future__ import annotations

import pytest

from pdf_toolbox.renderers import pptx as pptx_mod
from pdf_toolbox.renderers.lightweight_stub import PptxLightweightStub
from pdf_toolbox.renderers.pptx import PptxProviderUnavailableError


def test_lightweight_stub_probe_and_can_handle() -> None:
    """The stub advertises itself as unavailable."""
    assert not PptxLightweightStub.probe()
    assert not PptxLightweightStub.can_handle()


def test_lightweight_stub_to_pdf_raises_unavailable(tmp_path) -> None:
    """Rendering attempts raise ``PptxProviderUnavailableError`` until it exists."""
    stub = PptxLightweightStub()
    with pytest.raises(PptxProviderUnavailableError):
        stub.to_pdf(str(tmp_path / "input.pptx"))


def test_lightweight_stub_to_images_raises_unavailable(tmp_path) -> None:
    """Image export raises ``PptxProviderUnavailableError`` until implemented."""
    stub = PptxLightweightStub()
    with pytest.raises(PptxProviderUnavailableError):
        stub.to_images(str(tmp_path / "input.pptx"))


def test_lightweight_mapping_falls_back_to_null(monkeypatch) -> None:
    """Selecting ``lightweight`` falls back to the null renderer."""
    monkeypatch.setattr(pptx_mod, "load_config", lambda: {"pptx_renderer": "lightweight"})
    renderer = pptx_mod.get_pptx_renderer()
    assert not isinstance(renderer, PptxLightweightStub)
    with pytest.raises(PptxProviderUnavailableError):
        pptx_mod.require_pptx_renderer()
