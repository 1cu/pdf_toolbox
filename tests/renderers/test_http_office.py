"""Tests for the HTTP PPTX renderer."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import IO, Literal, cast

import pytest

import pdf_toolbox.renderers._http_util as http_util_module
import pdf_toolbox.renderers.http_office as http_office_module
from pdf_toolbox.renderers import registry
from pdf_toolbox.renderers.http_office import (
    HttpOfficeSection,
    PptxHttpOfficeRenderer,
    RendererConfig,
)
from pdf_toolbox.renderers.pptx import PptxRenderingError, UnsupportedOptionError

requests_mod = pytest.importorskip("requests")

_BASE_SECTION = HttpOfficeSection()
HttpFiles = Mapping[str, tuple[str, IO[bytes], str]]
PostResult = tuple[int, Iterable[bytes]]


def _renderer_with_endpoint(
    endpoint: str,
    *,
    mode: Literal["auto", "stirling", "gotenberg"] = "auto",
    timeout_s: float | None = _BASE_SECTION.timeout_s,
    verify_tls: bool = _BASE_SECTION.verify_tls,
    headers: Mapping[str, str] | None = None,
) -> PptxHttpOfficeRenderer:
    section = HttpOfficeSection(
        endpoint=endpoint,
        mode=mode,
        timeout_s=timeout_s,
        verify_tls=verify_tls,
        headers=dict(headers or {}),
    )
    cfg = RendererConfig(http_office=section)
    return PptxHttpOfficeRenderer(cfg)


def test_can_handle_requires_endpoint(monkeypatch):
    renderer = _renderer_with_endpoint("https://example.test/convert")
    assert renderer.can_handle() is True

    monkeypatch.setattr(http_office_module, "requests", None)
    renderer_no_dep = _renderer_with_endpoint("https://example.test/convert")
    assert renderer_no_dep.can_handle() is False


def test_request_context_is_cached(monkeypatch):
    renderer = _renderer_with_endpoint("https://example.test/convert")
    monkeypatch.setattr(http_office_module, "requests", object())

    calls = 0

    def fake_selected_mode(
        _self: PptxHttpOfficeRenderer,
    ) -> Literal["stirling", "gotenberg"]:
        nonlocal calls
        calls += 1
        return "stirling"

    monkeypatch.setattr(PptxHttpOfficeRenderer, "_selected_mode", fake_selected_mode)

    first = renderer._request_context()
    second = renderer._request_context()

    assert first is second
    assert calls == 1


def test_to_pdf_streams_response(tmp_path, monkeypatch):
    captured: dict[str, object] = {}

    def fake_post(
        endpoint: str,
        files: HttpFiles,
        headers: Mapping[str, str] | None,
        timeout: float | None,
        verify: bool,
    ) -> PostResult:
        captured.update(
            {
                "endpoint": endpoint,
                "field": next(iter(files.keys())),
                "filename": files[next(iter(files))][0],
                "mime": files[next(iter(files))][2],
                "headers": dict(headers or {}),
                "timeout": timeout,
                "verify": verify,
            }
        )

        def _chunks() -> Iterable[bytes]:
            yield b"%PDF-1.7\n"

        return 200, _chunks()

    monkeypatch.setattr("pdf_toolbox.renderers.http_office._post_stream_file", fake_post)

    renderer = _renderer_with_endpoint(
        "https://example.test/render",
        timeout_s=42,
        verify_tls=False,
        headers={"X-Test": "1"},
    )

    pptx_path = tmp_path / "deck.pptx"
    pptx_path.write_bytes(b"deck")
    out_path = tmp_path / "out.pdf"

    result = renderer.to_pdf(str(pptx_path), str(out_path))

    assert Path(result).read_bytes() == b"%PDF-1.7\n"
    assert captured["endpoint"] == "https://example.test/render"
    assert captured["field"] == "fileInput"
    assert captured["filename"] == "deck.pptx"
    assert captured["mime"].endswith("presentation")
    assert captured["headers"] == {"X-Test": "1"}
    assert captured["timeout"] == 42
    assert captured["verify"] is False


def test_to_pdf_uses_gotenberg_field(tmp_path, monkeypatch):
    fields: list[str] = []

    def fake_post(
        endpoint: str,
        files: HttpFiles,
        headers: Mapping[str, str] | None,
        timeout: float | None,
        verify: bool,
    ) -> PostResult:
        del endpoint, headers, timeout, verify
        fields.extend(files.keys())

        def _chunks():
            yield b"%PDF-1.4\n"

        return 200, _chunks()

    monkeypatch.setattr("pdf_toolbox.renderers.http_office._post_stream_file", fake_post)

    renderer = _renderer_with_endpoint("https://host/forms/libreoffice/convert")
    pptx = tmp_path / "slides.pptx"
    pptx.write_bytes(b"deck")

    renderer.to_pdf(str(pptx), str(tmp_path / "out.pdf"))

    assert fields == ["files"]


def test_to_pdf_raises_on_bad_status(tmp_path, monkeypatch):
    def fake_post(
        endpoint: str,
        files: HttpFiles,
        headers: Mapping[str, str] | None,
        timeout: float | None,
        verify: bool,
    ) -> PostResult:
        del endpoint, files, headers, timeout, verify

        def _chunks():
            yield b""

        return 500, _chunks()

    monkeypatch.setattr("pdf_toolbox.renderers.http_office._post_stream_file", fake_post)

    renderer = _renderer_with_endpoint("https://example.test")
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"deck")

    with pytest.raises(PptxRenderingError) as exc:
        renderer.to_pdf(str(pptx), str(tmp_path / "out.pdf"))

    assert "unexpected status" in str(exc.value)


def test_to_pdf_raises_on_empty_response(tmp_path, monkeypatch):
    def fake_post(
        endpoint: str,
        files: HttpFiles,
        headers: Mapping[str, str] | None,
        timeout: float | None,
        verify: bool,
    ) -> PostResult:
        del endpoint, files, headers, timeout, verify
        return 200, iter(())

    monkeypatch.setattr("pdf_toolbox.renderers.http_office._post_stream_file", fake_post)

    renderer = _renderer_with_endpoint("https://example.test")
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"deck")
    out_path = tmp_path / "out.pdf"

    with pytest.raises(PptxRenderingError) as exc:
        renderer.to_pdf(str(pptx), str(out_path))

    assert "invalid PDF" in str(exc.value)
    assert not out_path.exists()


def test_to_pdf_maps_timeout(tmp_path, monkeypatch):
    def fake_post(
        endpoint: str,
        files: HttpFiles,
        headers: Mapping[str, str] | None,
        timeout: float | None,
        verify: bool,
    ) -> PostResult:
        del endpoint, files, headers, timeout, verify
        raise requests_mod.Timeout("boom")

    monkeypatch.setattr("pdf_toolbox.renderers.http_office._post_stream_file", fake_post)

    renderer = _renderer_with_endpoint("https://example.test")
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"deck")

    with pytest.raises(PptxRenderingError) as exc:
        renderer.to_pdf(str(pptx), str(tmp_path / "out.pdf"))

    assert "timed out" in str(exc.value)


def test_to_pdf_maps_connection_error(tmp_path, monkeypatch):
    def fake_post(
        endpoint: str,
        files: HttpFiles,
        headers: Mapping[str, str] | None,
        timeout: float | None,
        verify: bool,
    ) -> PostResult:
        del endpoint, files, headers, timeout, verify
        raise requests_mod.ConnectionError("boom")

    monkeypatch.setattr("pdf_toolbox.renderers.http_office._post_stream_file", fake_post)

    renderer = _renderer_with_endpoint("https://example.test")
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"deck")

    with pytest.raises(PptxRenderingError) as exc:
        renderer.to_pdf(str(pptx), str(tmp_path / "out.pdf"))

    assert "Failed to connect" in str(exc.value)


def test_renderer_config_from_mapping_normalises():
    renderer = PptxHttpOfficeRenderer(
        {
            "http_office": {
                "endpoint": "https://example/forms/libreoffice/convert",
                "mode": "GOTENBERG",
                "timeout_s": "15",
                "verify_tls": "no",
                "headers": {"Authorization": 123, "": "", None: "skip"},
            }
        }
    )
    section = renderer.cfg.http_office
    assert section.mode == "gotenberg"
    assert section.timeout_s == 15.0
    assert section.verify_tls is False
    assert section.headers == {"Authorization": "123"}


def test_renderer_config_timeout_disabled():
    renderer = PptxHttpOfficeRenderer(
        {"http_office": {"endpoint": "https://example", "timeout_s": 0}}
    )
    assert renderer.cfg.http_office.timeout_s is None


def test_renderer_config_defaults_when_missing():
    renderer = PptxHttpOfficeRenderer({})
    assert renderer.cfg.http_office.endpoint == ""


def test_renderer_config_accepts_bool_verify_tls():
    renderer = PptxHttpOfficeRenderer(
        {"http_office": {"endpoint": "https://example", "verify_tls": True}}
    )
    assert renderer.cfg.http_office.verify_tls is True


def test_renderer_config_interprets_truthy_verify_tls():
    renderer = PptxHttpOfficeRenderer(
        {"http_office": {"endpoint": "https://example", "verify_tls": "YES"}}
    )
    assert renderer.cfg.http_office.verify_tls is True


def test_renderer_config_invalid_timeout_uses_default():
    renderer = PptxHttpOfficeRenderer(
        {"http_office": {"endpoint": "https://example", "timeout_s": "bad"}}
    )
    assert renderer.cfg.http_office.timeout_s == _BASE_SECTION.timeout_s


def test_renderer_config_timeout_invalid_type_uses_default():
    renderer = PptxHttpOfficeRenderer(
        {"http_office": {"endpoint": "https://example", "timeout_s": {}}}
    )
    assert renderer.cfg.http_office.timeout_s == _BASE_SECTION.timeout_s


def test_probe_reads_loaded_config(monkeypatch):
    monkeypatch.setattr(
        http_office_module,
        "load_config",
        lambda: {"http_office": {"endpoint": "https://example"}},
    )
    assert http_office_module.PptxHttpOfficeRenderer.probe() is True


def test_probe_handles_init_failure(monkeypatch):
    def boom(
        self: http_office_module.PptxHttpOfficeRenderer,
        cfg: Mapping[str, object] | None = None,
    ) -> None:
        del self, cfg
        raise RuntimeError("boom")

    monkeypatch.setattr(http_office_module.PptxHttpOfficeRenderer, "__init__", boom)
    with pytest.raises(RuntimeError):
        http_office_module.PptxHttpOfficeRenderer.probe()


def test_to_pdf_rejects_notes_and_handout(tmp_path):
    renderer = _renderer_with_endpoint("https://example")
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"deck")

    with pytest.raises(UnsupportedOptionError):
        renderer.to_pdf(str(pptx), notes=True)
    with pytest.raises(UnsupportedOptionError):
        renderer.to_pdf(str(pptx), handout=True)
    with pytest.raises(UnsupportedOptionError):
        renderer.to_pdf(str(pptx), notes=True, handout=True)


def test_to_pdf_rejects_range(tmp_path):
    renderer = _renderer_with_endpoint("https://example")
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"deck")

    with pytest.raises(UnsupportedOptionError):
        renderer.to_pdf(str(pptx), range_spec="1")


def test_to_pdf_requires_requests(monkeypatch, tmp_path):
    renderer = _renderer_with_endpoint("https://example")
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"deck")

    monkeypatch.setattr(http_office_module, "requests", None)

    with pytest.raises(PptxRenderingError) as exc:
        renderer.to_pdf(str(pptx), str(tmp_path / "out.pdf"))

    assert "pptx_http" in str(exc.value)


def test_to_pdf_requires_existing_file(tmp_path):
    renderer = _renderer_with_endpoint("https://example")
    with pytest.raises(PptxRenderingError):
        renderer.to_pdf(str(tmp_path / "missing.pptx"), str(tmp_path / "out.pdf"))


def test_to_pdf_requires_endpoint(tmp_path):
    renderer = _renderer_with_endpoint("")
    with pytest.raises(PptxRenderingError) as exc:
        renderer.to_pdf(str(tmp_path / "deck.pptx"), str(tmp_path / "out.pdf"))

    assert "endpoint" in str(exc.value)


def test_to_pdf_rejects_invalid_endpoint(tmp_path):
    renderer = _renderer_with_endpoint("ftp://example")
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"deck")

    with pytest.raises(PptxRenderingError) as exc:
        renderer.to_pdf(str(pptx), str(tmp_path / "out.pdf"))

    assert "HTTP(S) URL" in str(exc.value)


def test_stirling_endpoint_appends_default_path(monkeypatch):
    renderer = _renderer_with_endpoint("https://example.test", mode="stirling")
    monkeypatch.setattr(http_office_module, "requests", object())

    context = renderer._request_context()

    assert context.endpoint == "https://example.test/api/v1/convert/file/pdf"
    assert context.field == "fileInput"


def test_stirling_endpoint_preserves_custom_path(monkeypatch):
    renderer = _renderer_with_endpoint(
        "https://example.test/api/v1/convert/file/pdf", mode="stirling"
    )
    monkeypatch.setattr(http_office_module, "requests", object())

    context = renderer._request_context()

    assert context.endpoint == "https://example.test/api/v1/convert/file/pdf"
    assert context.field == "fileInput"


def test_post_stream_file_streams_and_closes(tmp_path, monkeypatch):
    closed: list[bool] = []

    class DummyResponse:
        status_code = 200

        def iter_content(self, chunk_size: int):
            del chunk_size
            yield b"abc"
            yield b""
            yield b"def"

        def close(self) -> None:
            closed.append(True)

    captured: dict[str, object] = {}

    def fake_post(
        endpoint: str,
        files: HttpFiles,
        **options: object,
    ) -> DummyResponse:
        captured.update(
            {
                "endpoint": endpoint,
                "headers": dict(cast(Mapping[str, str] | None, options.get("headers")) or {}),
                "timeout": cast(float | None, options.get("timeout")),
                "verify": bool(options.get("verify")),
                "stream": bool(options.get("stream", True)),
                "files": {key: (value[0], value[2]) for key, value in files.items()},
            }
        )
        return DummyResponse()

    monkeypatch.setattr(http_util_module, "requests", SimpleNamespace(post=fake_post))

    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"deck")

    with pptx.open("rb") as handle:
        status, chunks = http_util_module._post_stream_file(
            "https://endpoint",
            {"file": (pptx.name, handle, "application/test")},
            {"X-Test": "1"},
            3.5,
            False,
        )
        data = b"".join(chunks)

    assert status == 200
    assert data == b"abcdef"
    assert closed == [True]
    assert captured["files"] == {"file": ("deck.pptx", "application/test")}
    assert captured["headers"] == {"X-Test": "1"}
    assert captured["timeout"] == 3.5
    assert captured["verify"] is False
    assert captured["stream"] is True


def test_post_stream_file_requires_requests(monkeypatch, tmp_path):
    monkeypatch.setattr(http_util_module, "requests", None)
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"deck")

    with pptx.open("rb") as handle, pytest.raises(RuntimeError):
        http_util_module._post_stream_file(
            "https://endpoint",
            {"file": (pptx.name, handle, "application/test")},
            {},
            None,
            True,
        )


def test_to_pdf_maps_request_exception(tmp_path, monkeypatch):
    def fake_post(
        endpoint: str,
        files: HttpFiles,
        headers: Mapping[str, str] | None,
        timeout: float | None,
        verify: bool,
    ) -> PostResult:
        del endpoint, files, headers, timeout, verify
        raise requests_mod.RequestException("boom")

    monkeypatch.setattr(http_office_module, "_post_stream_file", fake_post)

    renderer = _renderer_with_endpoint("https://example")
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"deck")

    with pytest.raises(PptxRenderingError) as exc:
        renderer.to_pdf(str(pptx), str(tmp_path / "out.pdf"))

    assert "Failed to connect" in str(exc.value)


def test_to_pdf_respects_manual_mode(tmp_path, monkeypatch):
    fields: list[str] = []

    def fake_post(
        endpoint: str,
        files: HttpFiles,
        **options: object,
    ) -> SimpleNamespace:
        del endpoint, options
        fields.extend(files.keys())

        class DummyResponse:
            status_code = 200

            def iter_content(self, chunk_size: int):
                del chunk_size
                yield b"%PDF-1.7\n"

            def close(self) -> None:
                pass

        response = DummyResponse()
        return SimpleNamespace(
            status_code=response.status_code,
            iter_content=response.iter_content,
            close=response.close,
        )

    monkeypatch.setattr(http_util_module, "requests", SimpleNamespace(post=fake_post))

    renderer = _renderer_with_endpoint("https://example/manual", mode="gotenberg")
    pptx = tmp_path / "deck.pptx"
    pptx.write_bytes(b"deck")

    renderer.to_pdf(str(pptx), str(tmp_path / "out.pdf"))

    assert fields == ["files"]


def test_to_images_raises_unsupported(tmp_path):
    renderer = _renderer_with_endpoint("https://example")
    with pytest.raises(UnsupportedOptionError):
        renderer.to_images(str(tmp_path / "deck.pptx"))


def test_registry_can_handle_depends_on_endpoint(monkeypatch):
    monkeypatch.setitem(registry._ENTRY_POINT_STATE, "loaded", True)
    monkeypatch.setattr(registry, "_BUILTIN_MODULES", {})
    monkeypatch.setattr(http_office_module, "requests", object())

    monkeypatch.setattr(registry, "_REGISTRY", {})
    monkeypatch.setattr(
        http_office_module,
        "load_config",
        lambda: {"http_office": {"endpoint": "https://example.test/render"}},
    )
    registry.register(http_office_module.PptxHttpOfficeRenderer)
    renderer = registry.select("http_office")
    assert isinstance(renderer, http_office_module.PptxHttpOfficeRenderer)

    monkeypatch.setattr(registry, "_REGISTRY", {})
    monkeypatch.setattr(http_office_module, "load_config", lambda: {})
    registry.register(http_office_module.PptxHttpOfficeRenderer)
    assert registry.select("http_office") is None
