from __future__ import annotations

import json
from pathlib import Path

import pytest

from pdf_toolbox.actions.miro import miro_export
from pdf_toolbox.miro import PROFILE_MIRO, ExportProfile, export_pdf_for_miro


def test_export_pdf_prefers_svg(sample_pdf, tmp_path):
    outcome = export_pdf_for_miro(sample_pdf, out_dir=str(tmp_path))
    assert outcome.files
    assert outcome.files[0].endswith(".svg")
    manifest = json.loads((tmp_path / "miro_export.json").read_text())
    assert manifest[0]["vector_export"] is True


def test_export_pdf_rasterises_images(pdf_with_image, tmp_path):
    outcome = export_pdf_for_miro(pdf_with_image, out_dir=str(tmp_path))
    assert outcome.files
    assert outcome.files[0].endswith(".webp")
    manifest = json.loads((tmp_path / "miro_export.json").read_text())
    assert manifest[0]["vector_export"] is False


def test_export_warns_when_limit_impossible(pdf_with_image, tmp_path):
    tight_profile = ExportProfile(
        name="test",
        max_bytes=1,
        target_zoom=PROFILE_MIRO.target_zoom,
        min_effective_dpi=PROFILE_MIRO.min_effective_dpi,
        render_dpi=PROFILE_MIRO.render_dpi,
        max_dpi=PROFILE_MIRO.render_dpi,
    )
    outcome = export_pdf_for_miro(
        pdf_with_image,
        out_dir=str(tmp_path),
        profile=tight_profile,
    )
    assert outcome.page_results[0].warnings


def test_export_prefers_highest_allowed_dpi(monkeypatch, sample_pdf, tmp_path):
    from pdf_toolbox import miro

    class DummyImage:
        def __init__(self, dpi: int) -> None:
            self.width = dpi
            self.height = dpi
            self.mode = "RGB"

    def fake_render(_page, dpi: int) -> DummyImage:
        return DummyImage(dpi)

    def fake_encode(
        image, max_bytes: int, allow_transparency: bool, *, apply_unsharp: bool = True
    ):
        del allow_transparency, apply_unsharp
        size = image.width
        attempt = miro.PageExportAttempt(
            dpi=0,
            fmt="WEBP",
            size_bytes=size,
            encoder="fake",
        )
        return b"x" * size, "WEBP", attempt, [attempt], size <= max_bytes

    profile = ExportProfile(
        name="binary",
        max_bytes=1000,
        target_zoom=PROFILE_MIRO.target_zoom,
        min_effective_dpi=PROFILE_MIRO.min_effective_dpi,
        render_dpi=PROFILE_MIRO.render_dpi,
        max_dpi=PROFILE_MIRO.max_dpi,
    )
    monkeypatch.setattr(miro, "_render_page_bitmap", fake_render)
    monkeypatch.setattr(miro, "_encode_raster", fake_encode)
    monkeypatch.setattr(miro, "_page_is_vector_heavy", lambda _page: False)
    outcome = export_pdf_for_miro(
        sample_pdf,
        out_dir=str(tmp_path),
        profile=profile,
    )
    result = outcome.page_results[0]
    assert result.dpi == 1000
    assert result.width_px == 1000
    assert result.height_px == 1000
    assert not result.warnings
    assert result.attempts


def test_miro_export_standard_pdf(sample_pdf, tmp_path):
    outputs = miro_export(
        sample_pdf,
        out_dir=str(tmp_path),
        export_profile="standard",
        image_format="PNG",
        dpi="High (300 dpi)",
    )
    assert len(outputs) == 3
    assert all(Path(path).exists() for path in outputs)


def test_miro_export_miro_pdf(sample_pdf, tmp_path):
    outputs = miro_export(sample_pdf, out_dir=str(tmp_path), export_profile="miro")
    assert outputs
    manifest = tmp_path / "miro_export.json"
    assert manifest.exists()
    recorded = json.loads(manifest.read_text())
    assert recorded


def test_miro_export_miro_pptx(monkeypatch, sample_pdf, tmp_path):
    from pdf_toolbox import config
    from pdf_toolbox.renderers import pptx as pptx_module

    class DummyRenderer:
        def to_pdf(
            self, input_pptx: str, output_path: str | None = None, **_kwargs
        ) -> str:
            target = (
                Path(output_path)
                if output_path
                else Path(input_pptx).with_suffix(".pdf")
            )
            target.write_bytes(Path(sample_pdf).read_bytes())
            return str(target)

        def to_images(self, *args, **kwargs):  # pragma: no cover - not used here
            raise NotImplementedError

    original_loader = pptx_module._load_via_registry

    def loader(name: str):
        if name == "dummy":
            return DummyRenderer()
        return original_loader(name)

    monkeypatch.setattr(pptx_module, "_load_via_registry", loader)
    cfg_path = tmp_path / "pptx.json"
    cfg_path.write_text(json.dumps({"pptx_renderer": "dummy"}))
    monkeypatch.setattr(config, "CONFIG_PATH", cfg_path)
    pptx_path = tmp_path / "deck.pptx"
    pptx_path.write_bytes(b"pptx")
    outputs = miro_export(str(pptx_path), out_dir=str(tmp_path), export_profile="miro")
    assert outputs
    assert all(Path(path).exists() for path in outputs)


def test_miro_export_rejects_unknown_extension(tmp_path):
    bogus = tmp_path / "data.txt"
    bogus.write_text("hello")
    with pytest.raises(ValueError, match="Unsupported input type"):
        miro_export(str(bogus))
