from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from pdf_toolbox import image_utils, miro
from pdf_toolbox.actions.miro import miro_export
from pdf_toolbox.renderers.pptx import PptxProviderUnavailableError
from pdf_toolbox.miro import PROFILE_MIRO, ExportProfile, export_pdf_for_miro


def test_export_pdf_prefers_svg(monkeypatch, sample_pdf, tmp_path):
    def fake_export_page_as_svg(page, dpi, out_path, max_bytes):
        del page, max_bytes
        out_path.write_text("<svg></svg>")
        attempt = miro.PageExportAttempt(
            dpi=dpi,
            fmt="SVG",
            size_bytes=12,
            encoder="svg",
            lossless=True,
        )
        return True, 12, attempt

    monkeypatch.setattr(miro, "_page_is_vector_heavy", lambda _page: True)
    monkeypatch.setattr(miro, "_export_page_as_svg", fake_export_page_as_svg)

    outcome = export_pdf_for_miro(sample_pdf, out_dir=str(tmp_path))
    assert outcome.files
    assert outcome.files[0].endswith(".svg")
    manifest = json.loads((tmp_path / "miro_export.json").read_text())
    assert manifest[0]["vector_export"] is True


def test_export_pdf_rasterises_images(monkeypatch, pdf_with_image, tmp_path):
    def fake_rasterise_page(page, profile, max_bytes, *, attempts):
        del page, profile, max_bytes
        attempt = miro.PageExportAttempt(
            dpi=150,
            fmt="WEBP",
            size_bytes=20,
            encoder="webp",
        )
        attempts.append(attempt)
        return b"data", "WEBP", 150, 10, 10, True, False

    monkeypatch.setattr(miro, "_page_is_vector_heavy", lambda _page: False)
    monkeypatch.setattr(miro, "_rasterise_page", fake_rasterise_page)

    outcome = export_pdf_for_miro(pdf_with_image, out_dir=str(tmp_path))
    assert outcome.files
    assert outcome.files[0].endswith(".webp")
    manifest = json.loads((tmp_path / "miro_export.json").read_text())
    assert manifest[0]["vector_export"] is False


def test_export_warns_when_limit_impossible(monkeypatch, pdf_with_image, tmp_path):
    tight_profile = ExportProfile(
        name="test",
        max_bytes=1,
        target_zoom=PROFILE_MIRO.target_zoom,
        min_effective_dpi=PROFILE_MIRO.min_effective_dpi,
        render_dpi=PROFILE_MIRO.render_dpi,
        max_dpi=PROFILE_MIRO.render_dpi,
    )

    def fake_rasterise_page(page, profile, max_bytes, *, attempts):
        del page, profile, max_bytes
        attempt = miro.PageExportAttempt(
            dpi=PROFILE_MIRO.render_dpi,
            fmt="WEBP",
            size_bytes=50,
            encoder="webp",
        )
        attempts.append(attempt)
        return b"data", "WEBP", PROFILE_MIRO.render_dpi, 10, 10, False, False

    monkeypatch.setattr(miro, "_page_is_vector_heavy", lambda _page: False)
    monkeypatch.setattr(miro, "_rasterise_page", fake_rasterise_page)

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

    def fake_render(_page, dpi: int, *, keep_alpha: bool = False) -> DummyImage:
        assert keep_alpha is True
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
    monkeypatch.setattr(miro, "render_page_image", fake_render)
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


@pytest.mark.slow
def test_export_pdf_for_miro_integration(sample_pdf, pdf_with_image, tmp_path):
    light_profile = ExportProfile(
        name="light",
        max_bytes=2 * 1024 * 1024,
        target_zoom=1.0,
        min_effective_dpi=120,
        render_dpi=160,
        max_dpi=200,
    )
    vector_dir = tmp_path / "vector"
    vector_outcome = export_pdf_for_miro(
        sample_pdf,
        out_dir=str(vector_dir),
        profile=light_profile,
    )
    assert vector_outcome.files
    assert vector_outcome.page_results[0].vector_export is True
    assert Path(vector_outcome.files[0]).exists()

    raster_dir = tmp_path / "raster"
    raster_outcome = export_pdf_for_miro(
        pdf_with_image,
        out_dir=str(raster_dir),
        profile=light_profile,
    )
    assert raster_outcome.files
    assert raster_outcome.page_results[0].vector_export is False
    assert Path(raster_outcome.files[0]).exists()


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


def test_miro_export_pptx_without_provider(tmp_path):
    pptx_path = tmp_path / "deck.pptx"
    pptx_path.write_text("pptx")
    with pytest.raises(PptxProviderUnavailableError):
        miro_export(str(pptx_path))


def test_miro_export_rejects_unknown_extension(tmp_path):
    bogus = tmp_path / "data.txt"
    bogus.write_text("hello")
    with pytest.raises(ValueError, match="Unsupported input type"):
        miro_export(str(bogus))


def test_remove_svg_metadata_strips_block():
    svg = "<svg><metadata>foo</metadata><rect/></svg>"
    cleaned = miro._remove_svg_metadata(svg)
    assert cleaned == "<svg><rect/></svg>"


def test_remove_svg_metadata_missing_end_tag():
    svg = "<svg><metadata>foo<rect/></svg>"
    assert miro._remove_svg_metadata(svg) == svg


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


def test_page_is_vector_heavy_ratio_threshold():
    class MixedPage:
        def get_drawings(self) -> list[str]:
            return ["vector"]

        def get_images(self, full: bool = True) -> list[str]:
            _ = full
            return ["image", "image"]

        def get_text(self, _mode: str) -> str:
            return "text"

    class VectorFavouredPage:
        def get_drawings(self) -> list[str]:
            return ["vector", "line", "shape"]

        def get_images(self, full: bool = True) -> list[str]:
            _ = full
            return ["image"]

        def get_text(self, _mode: str) -> str:
            return ""

    assert not miro._page_is_vector_heavy(MixedPage())
    assert miro._page_is_vector_heavy(VectorFavouredPage())


def test_calculate_dpi_window_clamps_resolution():
    class DummyRect:
        def __init__(self, width: float, height: float) -> None:
            self.width = width
            self.height = height

    class DummyPage:
        def __init__(self, width_pt: float, height_pt: float) -> None:
            self.rect = DummyRect(width_pt, height_pt)

    # 10" x 5" slide hits the 32 MP / 8192x4096 limit
    wide_page = DummyPage(720, 360)
    min_dpi, max_dpi = miro._calculate_dpi_window(wide_page, PROFILE_MIRO)
    assert min_dpi == PROFILE_MIRO.min_dpi
    assert max_dpi == 800

    # Square page within limits preserves profile max
    small_page = DummyPage(144, 144)
    min_dpi, max_dpi = miro._calculate_dpi_window(small_page, PROFILE_MIRO)
    assert min_dpi == PROFILE_MIRO.min_dpi
    assert max_dpi == PROFILE_MIRO.max_dpi


def test_render_page_image_converts_colorspace(monkeypatch):
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

    monkeypatch.setattr(image_utils.fitz, "Matrix", lambda *_args: object())
    monkeypatch.setattr(image_utils.fitz, "Pixmap", ConvertedPixmap)
    image = image_utils.render_page_image(DummyPage(), 72, keep_alpha=True)
    assert image.mode == "RGB"
    assert image.size == (1, 1)


def test_encode_png_palette_conversion():
    image = Image.new("RGB", (1, 1), color="red")
    data = image_utils.encode_png(image, palette=True)
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


def test_iter_webp_candidates_yield_lossless_and_quality(monkeypatch):
    image = Image.new("RGB", (1, 1), color="red")

    def fake_encode(_image, *, lossless: bool, quality: int | None = None) -> bytes:
        return ("lossless" if lossless else f"q{quality}").encode()

    monkeypatch.setattr(miro, "encode_webp", fake_encode)
    candidates = list(miro._iter_webp_candidates(image))
    assert candidates
    assert candidates[0][0] == "WEBP"
    assert candidates[0][1] == b"lossless"
    assert candidates[0][2].lossless is True
    assert [attempt.quality for _, _, attempt in candidates[1:]] == [95, 90, 85]


def test_iter_png_candidates_returns_lossless(monkeypatch):
    image = Image.new("RGB", (1, 1), color="green")

    def fake_encode(_image, *, palette: bool = True, **_kwargs) -> bytes:
        assert palette is True
        return b"png"

    monkeypatch.setattr(miro, "encode_png", fake_encode)
    candidates = list(miro._iter_png_candidates(image, palette=True))
    assert candidates == [("PNG", b"png", candidates[0][2])]
    assert candidates[0][2].lossless is True


def test_iter_jpeg_candidates_returns_quality_levels(monkeypatch):
    image = Image.new("RGB", (1, 1), color="blue")

    def fake_encode(_image, *, quality: int) -> bytes:
        return f"jpeg{quality}".encode()

    monkeypatch.setattr(miro, "encode_jpeg", fake_encode)
    candidates = list(miro._iter_jpeg_candidates(image))
    assert [attempt.quality for _, _, attempt in candidates] == [95, 90]


def test_encode_raster_uses_first_webp_candidate(monkeypatch):
    image = Image.new("RGB", (1, 1), color="purple")
    attempt = miro.PageExportAttempt(dpi=0, fmt="WEBP", size_bytes=0, encoder="webp")

    def fake_webp_candidates(_image):
        yield "WEBP", b"data", attempt

    monkeypatch.setattr(miro, "apply_unsharp_mask", lambda img: img)
    monkeypatch.setattr(miro, "_iter_webp_candidates", fake_webp_candidates)
    monkeypatch.setattr(miro, "_iter_png_candidates", lambda _image, _palette: [])
    monkeypatch.setattr(miro, "_iter_jpeg_candidates", lambda _image: [])
    data, fmt, selected, attempts, within = miro._encode_raster(
        image,
        max_bytes=1024,
        allow_transparency=True,
    )
    assert fmt == "WEBP"
    assert data == b"data"
    assert within is True
    assert selected is attempt
    assert attempts == [attempt]


def test_encode_raster_returns_best_when_over_limit(monkeypatch):
    image = Image.new("RGB", (1, 1), color="orange")

    def fake_webp_candidates(_image):
        attempt = miro.PageExportAttempt(
            dpi=0, fmt="WEBP", size_bytes=0, encoder="webp"
        )
        yield "WEBP", b"w" * 20, attempt

    def fake_png_candidates(_image, _palette: bool):
        attempt = miro.PageExportAttempt(
            dpi=0, fmt="PNG", size_bytes=0, encoder="png", lossless=True
        )
        yield "PNG", b"p" * 15, attempt

    def fake_jpeg_candidates(_image):
        attempt = miro.PageExportAttempt(
            dpi=0,
            fmt="JPEG",
            size_bytes=0,
            encoder="jpeg",
            quality=90,
            lossless=False,
        )
        yield "JPEG", b"j" * 12, attempt

    monkeypatch.setattr(miro, "apply_unsharp_mask", lambda img: img)
    monkeypatch.setattr(miro, "_iter_webp_candidates", fake_webp_candidates)
    monkeypatch.setattr(miro, "_iter_png_candidates", fake_png_candidates)
    monkeypatch.setattr(miro, "_iter_jpeg_candidates", fake_jpeg_candidates)
    data, fmt, selected, attempts, within = miro._encode_raster(
        image,
        max_bytes=10,
        allow_transparency=False,
    )
    assert fmt == "JPEG"
    assert within is False
    assert len(data) == 12
    assert selected.fmt == "JPEG"
    assert any(entry.fmt == "PNG" for entry in attempts)


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

    def fake_finalise(page, _dpi: int, max_bytes: int, attempts):
        del page, max_bytes
        calls.append(_dpi)
        data, fmt, attempt, within, width, height = responses[_dpi]
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


def test_select_raster_output_reuses_existing_dpis(monkeypatch):
    recorded: list[int] = []

    def fake_finalise(page, dpi: int, max_bytes: int, attempts):
        _ = page, max_bytes
        recorded.append(dpi)
        attempt = miro.PageExportAttempt(
            dpi=dpi, fmt="WEBP", size_bytes=0, encoder="webp"
        )
        attempts.append(attempt)
        within = dpi <= 100
        data = bytes([dpi % 256])
        return data, "WEBP", attempt, within, dpi, dpi

    monkeypatch.setattr(miro, "_finalise_candidate", fake_finalise)
    attempts: list[miro.PageExportAttempt] = []
    data, fmt, attempt, width, height, within, used_dpi = miro._select_raster_output(
        object(),
        max_bytes=1024,
        attempts=attempts,
        candidate_dpis=[150, 200],
        min_dpi=100,
    )
    assert fmt == "WEBP"
    assert within is True
    assert used_dpi == 100
    assert data == bytes([100])
    assert width == 100
    assert height == 100
    assert attempt.dpi == 100
    assert recorded[:2] == [150, 200]
    assert 125 in recorded


def test_select_raster_output_refine_returns_fallback(monkeypatch):
    def fake_finalise(page, dpi: int, max_bytes: int, attempts):
        del page, max_bytes
        attempt = miro.PageExportAttempt(
            dpi=dpi, fmt="WEBP", size_bytes=0, encoder="webp"
        )
        attempts.append(attempt)
        if dpi == 900:
            return b"base", "WEBP", attempt, False, 100, 100
        return b"", "", None, False, 0, 0

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
    assert data == b"base"
    assert fmt == "WEBP"
    assert attempt is attempts[0]
    assert width == 100
    assert height == 100
    assert not within
    assert dpi_used == 900


def test_select_raster_output_retains_minimum(monkeypatch):
    attempt = miro.PageExportAttempt(dpi=0, fmt="WEBP", size_bytes=0, encoder="webp")

    def fake_finalise(page, _dpi: int, max_bytes: int, attempts):
        del page, max_bytes, _dpi
        attempt.size_bytes = 10
        attempts.append(attempt)
        return b"x" * 10, "WEBP", attempt, False, 100, 100

    monkeypatch.setattr(miro, "_finalise_candidate", fake_finalise)
    dummy_page = object()
    attempts: list[miro.PageExportAttempt] = []
    data, fmt, selected, width, height, within, dpi_used = miro._select_raster_output(
        dummy_page,
        max_bytes=5,
        attempts=attempts,
        candidate_dpis=[PROFILE_MIRO.min_dpi],
        min_dpi=PROFILE_MIRO.min_dpi,
    )
    assert data == b"x" * 10
    assert fmt == "WEBP"
    assert selected is attempt
    assert not within
    assert dpi_used == PROFILE_MIRO.min_dpi
    assert width == 100
    assert height == 100


def test_rasterise_page_errors_without_candidates(monkeypatch):
    class DummyRect:
        width = 72
        height = 72

    class DummyPage:
        rect = DummyRect()

    monkeypatch.setattr(
        miro, "_binary_search_dpi_candidates", lambda *_args, **_kwargs: []
    )
    with pytest.raises(RuntimeError):
        miro._rasterise_page(
            page=DummyPage(),
            profile=PROFILE_MIRO,
            max_bytes=100,
            attempts=[],
        )


def test_rasterise_page_raises_when_select_returns_none(monkeypatch):
    class DummyRect:
        width = 72
        height = 72

    class DummyPage:
        rect = DummyRect()

    monkeypatch.setattr(
        miro,
        "_binary_search_dpi_candidates",
        lambda *_args, **_kwargs: [PROFILE_MIRO.min_dpi],
    )
    monkeypatch.setattr(
        miro,
        "_select_raster_output",
        lambda *_args, **_kwargs: (b"", "", None, 0, 0, False, PROFILE_MIRO.min_dpi),
    )
    with pytest.raises(RuntimeError):
        miro._rasterise_page(
            page=DummyPage(),
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
        return b"data", "WEBP", profile.render_dpi, 100, 100, True, False

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
        return b"data", "WEBP", profile.render_dpi, 100, 100, False, False

    monkeypatch.setattr(miro, "_rasterise_page", fake_rasterise)
    result = miro._export_page(
        doc=DummyDoc(),
        page_number=1,
        out_base=tmp_path,
        profile=PROFILE_MIRO,
        max_bytes=PROFILE_MIRO.max_bytes,
    )
    assert any("minimum acceptable sharpness" in warning for warning in result.warnings)


def test_export_page_resolution_warning(monkeypatch, tmp_path):
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
        return b"data", "WEBP", profile.min_dpi - 100, 100, 100, True, True

    monkeypatch.setattr(miro, "_rasterise_page", fake_rasterise)
    result = miro._export_page(
        doc=DummyDoc(),
        page_number=1,
        out_base=tmp_path,
        profile=PROFILE_MIRO,
        max_bytes=PROFILE_MIRO.max_bytes,
    )
    assert any("Clamped" in warning for warning in result.warnings)


def test_export_pdf_for_miro_respects_page_selection(sample_pdf, tmp_path):
    outcome = export_pdf_for_miro(
        sample_pdf,
        out_dir=str(tmp_path),
        pages="1",
    )
    assert len(outcome.page_results) == 1
