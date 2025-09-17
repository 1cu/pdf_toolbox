"""Tests for the lightweight PPTX renderer stub."""

from __future__ import annotations

import pytest

from pdf_toolbox.renderers.lightweight_stub import PptxLightweightStub


def test_lightweight_stub_probe_and_can_handle() -> None:
    """The stub advertises itself as unavailable."""

    assert not PptxLightweightStub.probe()
    assert not PptxLightweightStub.can_handle()


def test_lightweight_stub_to_pdf_raises_not_implemented(tmp_path) -> None:
    """Rendering attempts raise ``NotImplementedError`` until it exists."""

    stub = PptxLightweightStub()
    with pytest.raises(NotImplementedError):
        stub.to_pdf(str(tmp_path / "input.pptx"))


def test_lightweight_stub_to_images_raises_not_implemented(tmp_path) -> None:
    """Image export raises ``NotImplementedError`` until implemented."""

    stub = PptxLightweightStub()
    with pytest.raises(NotImplementedError):
        stub.to_images(str(tmp_path / "input.pptx"))
