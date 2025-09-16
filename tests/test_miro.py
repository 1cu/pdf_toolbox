from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from pdf_toolbox import miro
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

        def to_images(
            self, *args, **kwargs
        ):  # pragma: no cover - not used here  # pdf-toolbox: ensure dummy renderer keeps simple coverage | issue:-
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
    outputs_default = miro_export(str(pptx_path), export_profile="miro")
    assert outputs_default
    assert all(Path(path).exists() for path in outputs_default)
    assert all(Path(path).parent == tmp_path for path in outputs_default)
    default_manifest = tmp_path / "miro_export.json"
    assert default_manifest.exists()

    explicit_dir = tmp_path / "explicit"
    outputs = miro_export(
        str(pptx_path), out_dir=str(explicit_dir), export_profile="miro"
    )
    assert outputs
    assert all(Path(path).exists() for path in outputs)
    assert all(Path(path).parent == explicit_dir for path in outputs)
    explicit_manifest = explicit_dir / "miro_export.json"
    assert explicit_manifest.exists()


def test_miro_export_rejects_unknown_extension(tmp_path):
    bogus = tmp_path / "data.txt"
    bogus.write_text("hello")
    with pytest.raises(ValueError, match="Unsupported input type"):
        miro_export(str(bogus))


def test_remove_svg_metadata_strips_block():
    svg = "<svg><metadata>foo</metadata><rect/></svg>"
    cleaned = miro._remove_svg_metadata(svg)
    assert cleaned == "<svg><rect/></svg>"


def test_page_is_vector_heavy_only_images():
    class DummyPage:
        def get_drawings(self) -> list[str]:
            return []

        def get_images(self, full: bool = True) -> list[str]:
            _ = full
            return ["image"]

        def get_text(self, _mode: str) -> str:
            return ""

    assert not miro._page_is_vector_heavy(DummyPage())


def test_render_page_bitmap_converts_colorspace(monkeypatch):
    class DummyPixmap:
        def __init__(self) -> None:
            self.colorspace = type("CS", (), {"n": 4})()
            self.alpha = False
            self.width = 1
            self.height = 1
            self.samples = b"\x00\x00\x00"

    class ConvertedPixmap:
        def __init__(self, _colorspace, pix) -> None:
            self.colorspace = type("CS", (), {"n": 3})()
            self.alpha = pix.alpha
            self.width = pix.width
            self.height = pix.height
            self.samples = pix.samples

    class DummyPage:
        def get_pixmap(self, matrix, alpha):
            _ = matrix
            assert alpha is True
            return DummyPixmap()

    monkeypatch.setattr(miro.fitz, "Matrix", lambda *_args: object())
    monkeypatch.setattr(miro.fitz, "Pixmap", ConvertedPixmap)
    image = miro._render_page_bitmap(DummyPage(), 72)
    assert image.mode == "RGB"
    assert image.size == (1, 1)


def test_encode_png_palette_conversion():
    image = Image.new("RGB", (1, 1), color="red")
    data = miro._encode_png(image, palette=True)
    assert data


def test_encode_raster_returns_png_when_webp_missing(monkeypatch):
    image = Image.new("RGB", (1, 1), color="red")
    monkeypatch.setattr(miro, "_iter_webp_candidates", lambda _img: [])

    def fake_png_candidates(_image, _palette):
        attempt = miro.PageExportAttempt(
            dpi=0,
            fmt="PNG",
            size_bytes=0,
            encoder="png",
            lossless=True,
        )
        return [("PNG", b"png", attempt)]

    monkeypatch.setattr(miro, "_iter_png_candidates", fake_png_candidates)
    data, fmt, attempt, attempts, within = miro._encode_raster(
        image,
        max_bytes=1024,
        allow_transparency=True,
    )
    assert fmt == "PNG"
    assert data == b"png"
    assert within is True
    assert attempts[0].fmt == "PNG"
    assert attempt.size_bytes == len(data)


def test_encode_raster_prefers_jpeg_when_needed(monkeypatch):
    image = Image.new("RGB", (1, 1), color="blue")
    monkeypatch.setattr(miro, "_iter_webp_candidates", lambda _img: [])

    def fake_png_candidates(_image, _palette):
        attempt = miro.PageExportAttempt(
            dpi=0,
            fmt="PNG",
            size_bytes=0,
            encoder="png",
            lossless=True,
        )
        return [("PNG", b"x" * 2000, attempt)]

    def fake_jpeg_candidates(_image):
        attempt = miro.PageExportAttempt(
            dpi=0,
            fmt="JPEG",
            size_bytes=0,
            encoder="jpeg",
            quality=90,
            lossless=False,
        )
        return [("JPEG", b"jpeg", attempt)]

    monkeypatch.setattr(miro, "_iter_png_candidates", fake_png_candidates)
    monkeypatch.setattr(miro, "_iter_jpeg_candidates", fake_jpeg_candidates)
    data, fmt, attempt, attempts, within = miro._encode_raster(
        image,
        max_bytes=100,
        allow_transparency=False,
    )
    assert fmt == "JPEG"
    assert data == b"jpeg"
    assert within is True
    assert attempts[-1].fmt == "JPEG"
    assert attempt.size_bytes == len(data)


def test_encode_raster_no_candidates_raises(monkeypatch):
    image = Image.new("RGB", (1, 1))
    monkeypatch.setattr(miro, "_iter_webp_candidates", lambda _img: [])
    monkeypatch.setattr(miro, "_iter_png_candidates", lambda _img, _palette: [])
    monkeypatch.setattr(miro, "_iter_jpeg_candidates", lambda _img: [])
    with pytest.raises(RuntimeError):
        miro._encode_raster(image, max_bytes=10, allow_transparency=True)


def test_select_raster_output_refines_dpi(monkeypatch):
    calls: list[int] = []
    attempt_map: dict[int, miro.PageExportAttempt] = {}

    def build_attempt(dpi: int) -> miro.PageExportAttempt:
        attempt = miro.PageExportAttempt(
            dpi=dpi,
            fmt="WEBP",
            size_bytes=0,
            encoder="webp",
        )
        attempt_map[dpi] = attempt
        return attempt

    responses: dict[int, tuple[bytes, str, miro.PageExportAttempt, bool, int, int]] = {
        900: (b"a", "WEBP", build_attempt(900), False, 100, 100),
        875: (b"b", "WEBP", build_attempt(875), False, 90, 90),
        850: (b"c", "WEBP", build_attempt(850), True, 80, 80),
    }

    def fake_finalise(page, dpi: int, max_bytes: int, attempts):
        del page, max_bytes
        calls.append(dpi)
        data, fmt, attempt, within, width, height = responses[dpi]
        attempt.size_bytes = len(data)
        attempts.append(attempt)
        return data, fmt, attempt, within, width, height

    monkeypatch.setattr(miro, "_finalise_candidate", fake_finalise)
    dummy_page = object()
    attempts: list[miro.PageExportAttempt] = []
    data, fmt, attempt, width, height, within, dpi_used = miro._select_raster_output(
        dummy_page,
        max_bytes=100,
        attempts=attempts,
        candidate_dpis=[900],
        min_dpi=800,
    )
    assert calls == [900, 875, 850]
    assert data == b"c"
    assert fmt == "WEBP"
    assert within is True
    assert dpi_used == 850
    assert width == 80
    assert height == 80
    assert attempt is attempt_map[850]


def test_rasterise_page_errors_without_candidates(monkeypatch):
    monkeypatch.setattr(
        miro, "_binary_search_dpi_candidates", lambda *_args, **_kwargs: []
    )
    with pytest.raises(RuntimeError):
        miro._rasterise_page(
            page=object(),
            profile=PROFILE_MIRO,
            max_bytes=100,
            attempts=[],
        )


def test_export_page_svg_fallback_adds_warning(monkeypatch, tmp_path):
    class DummyDoc:
        name = "dummy.pdf"

        def load_page(self, index: int):
            assert index == 0
            return DummyPage()

    class DummyRect:
        width = 72
        height = 72

    class DummyPage:
        rect = DummyRect()

    monkeypatch.setattr(miro, "_page_is_vector_heavy", lambda _page: True)

    def fake_export_svg(page, dpi, out_path, max_bytes):
        del page, dpi, out_path, max_bytes
        attempt = miro.PageExportAttempt(
            dpi=0,
            fmt="SVG",
            size_bytes=50,
            encoder="svg",
            lossless=True,
        )
        return False, 50, attempt

    def fake_rasterise(page, profile, max_bytes, attempts):
        del page, max_bytes
        attempt = miro.PageExportAttempt(
            dpi=profile.render_dpi,
            fmt="WEBP",
            size_bytes=20,
            encoder="webp",
        )
        attempts.append(attempt)
        return b"data", "WEBP", profile.render_dpi, 100, 100, True

    monkeypatch.setattr(miro, "_export_page_as_svg", fake_export_svg)
    monkeypatch.setattr(miro, "_rasterise_page", fake_rasterise)
    result = miro._export_page(
        doc=DummyDoc(),
        page_number=1,
        out_base=tmp_path,
        profile=PROFILE_MIRO,
        max_bytes=PROFILE_MIRO.max_bytes,
    )
    assert any("SVG exceeded" in warning for warning in result.warnings)
    assert result.fmt == "WEBP"


def test_export_page_raster_limit_warning(monkeypatch, tmp_path):
    class DummyDoc:
        name = "dummy.pdf"

        def load_page(self, index: int):
            assert index == 0
            return DummyPage()

    class DummyRect:
        width = 72
        height = 72

    class DummyPage:
        rect = DummyRect()

    monkeypatch.setattr(miro, "_page_is_vector_heavy", lambda _page: False)

    def fake_rasterise(page, profile, max_bytes, attempts):
        del page, max_bytes
        attempt = miro.PageExportAttempt(
            dpi=profile.render_dpi,
            fmt="WEBP",
            size_bytes=20,
            encoder="webp",
        )
        attempts.append(attempt)
        return b"data", "WEBP", profile.render_dpi, 100, 100, False

    monkeypatch.setattr(miro, "_rasterise_page", fake_rasterise)
    result = miro._export_page(
        doc=DummyDoc(),
        page_number=1,
        out_base=tmp_path,
        profile=PROFILE_MIRO,
        max_bytes=PROFILE_MIRO.max_bytes,
    )
    assert any("minimum acceptable sharpness" in warning for warning in result.warnings)


def test_export_pdf_for_miro_respects_page_selection(sample_pdf, tmp_path):
    outcome = export_pdf_for_miro(
        sample_pdf,
        out_dir=str(tmp_path),
        pages="1",
    )
    assert len(outcome.page_results) == 1
