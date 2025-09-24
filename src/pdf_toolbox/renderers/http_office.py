"""HTTP-backed PPTX renderer that targets Stirling and Gotenberg."""

from __future__ import annotations

import contextlib
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Literal, cast
from urllib.parse import urlparse, urlunparse

from pdf_toolbox.config import load_config
from pdf_toolbox.i18n import tr
from pdf_toolbox.renderers._http_util import _post_stream_file
from pdf_toolbox.renderers._requests import RequestsModule, requests
from pdf_toolbox.renderers.pptx import (
    PptxRenderingError,
    UnsupportedOptionError,
)
from pdf_toolbox.renderers.pptx_base import BasePptxRenderer, RenderOptions
from pdf_toolbox.renderers.registry import register
from pdf_toolbox.utils import logger

Mode = Literal["auto", "stirling", "gotenberg"]

_DEFAULT_TIMEOUT = 60.0
_HTTP_OK = 200
_MIME_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
_STIRLING_PDF_PATH = "/api/v1/convert/file/pdf"


def _coerce_bool(value: object, default: bool) -> bool:
    """Return ``value`` coerced to :class:`bool` when possible."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _coerce_timeout(value: object) -> float | None:
    """Normalise ``timeout`` seconds, returning ``None`` for disabled timeouts."""
    if value is None:
        return _DEFAULT_TIMEOUT
    number: float
    if isinstance(value, int | float):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            return _DEFAULT_TIMEOUT
    else:
        return _DEFAULT_TIMEOUT
    if number <= 0:
        return None
    return number


def _coerce_mode(value: object) -> Mode:
    """Return a valid renderer mode from ``value``."""
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"stirling", "gotenberg"}:
            return cast(Mode, lowered)
    return "auto"


def _normalise_headers(headers: object) -> Mapping[str, str]:
    """Return a case-preserving header mapping from ``headers``."""
    if not isinstance(headers, Mapping):
        return {}
    result: MutableMapping[str, str] = {}
    for key, value in headers.items():
        if key is None:
            continue
        key_str = str(key).strip()
        if not key_str:
            continue
        result[key_str] = "" if value is None else str(value)
    return dict(result)


@dataclass(frozen=True, slots=True)
class HttpOfficeSection:
    """Configuration block for the HTTP renderer."""

    endpoint: str = ""
    mode: Mode = "auto"
    timeout_s: float | None = _DEFAULT_TIMEOUT
    verify_tls: bool = True
    headers: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, object] | None) -> HttpOfficeSection:
        """Create an :class:`HttpOfficeSection` from a configuration mapping."""
        if not isinstance(data, Mapping):
            return cls()
        endpoint = str(data.get("endpoint") or "").strip()
        mode = _coerce_mode(data.get("mode"))
        timeout_s = _coerce_timeout(data.get("timeout_s"))
        verify_tls = _coerce_bool(data.get("verify_tls"), True)
        headers = _normalise_headers(data.get("headers"))
        return cls(
            endpoint=endpoint,
            mode=mode,
            timeout_s=timeout_s,
            verify_tls=verify_tls,
            headers=headers,
        )


@dataclass(frozen=True, slots=True)
class RendererConfig:
    """Renderer configuration wrapper exposing the ``http_office`` block."""

    http_office: HttpOfficeSection = field(default_factory=HttpOfficeSection)

    @classmethod
    def from_mapping(cls, cfg: Mapping[str, object] | None) -> RendererConfig:
        """Return :class:`RendererConfig` created from ``cfg``."""
        http_section: Mapping[str, object] | None = None
        if isinstance(cfg, Mapping):
            candidate = cfg.get("http_office")
            if isinstance(candidate, Mapping):
                http_section = candidate
        return cls(http_office=HttpOfficeSection.from_mapping(http_section))


@dataclass(frozen=True, slots=True)
class _HttpRequestContext:
    """Request metadata computed for an HTTP rendering call."""

    endpoint: str
    field: Literal["file", "files", "fileInput"]
    headers: Mapping[str, str]
    timeout_s: float | None
    verify_tls: bool
    mode: Literal["stirling", "gotenberg"]
    requests: RequestsModule


class PptxHttpOfficeRenderer(BasePptxRenderer):
    """Render PPTX files to PDF using an HTTP Office service."""

    name: ClassVar[str] = "http_office"

    def __init__(
        self,
        cfg: RendererConfig | Mapping[str, object] | None = None,
    ) -> None:
        """Initialise the renderer configuration from ``cfg`` or disk."""
        if isinstance(cfg, RendererConfig):
            self._cfg = cfg
        elif isinstance(cfg, Mapping):
            self._cfg = RendererConfig.from_mapping(cfg)
        else:
            self._cfg = RendererConfig.from_mapping(load_config())
        self._cached_context: _HttpRequestContext | None = None

    @property
    def cfg(self) -> RendererConfig:
        """Expose the renderer configuration for tests and debugging."""
        return self._cfg

    @classmethod
    def probe(cls) -> bool:
        """Return ``True`` when the renderer has a usable configuration."""
        try:
            renderer = cls()
        except (FileNotFoundError, ValueError) as exc:
            logger.info(
                "HTTP PPTX renderer probe failed (%s): %s",
                type(exc).__name__,
                exc,
                extra={"renderer": cls.name},
            )
            return False
        return renderer.can_handle()

    def can_handle(self) -> bool:
        """Return ``True`` when endpoint and dependencies are available."""
        if requests is None:
            return False
        return bool(self._cfg.http_office.endpoint)

    def _selected_mode(self) -> Literal["stirling", "gotenberg"]:
        mode = self._cfg.http_office.mode
        if mode == "auto":
            parsed = urlparse(self._cfg.http_office.endpoint)
            path = parsed.path.lower()
            if "/forms/libreoffice/convert" in path:
                return "gotenberg"
            return "stirling"
        return mode

    def _normalise_endpoint(
        self,
        endpoint: str,
        mode: Literal["stirling", "gotenberg"],
    ) -> str:
        """Return a validated endpoint for ``mode``."""
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise PptxRenderingError(
                tr("pptx.http.invalid_endpoint"),
                code="unavailable",
            )

        if mode == "stirling" and parsed.path in {"", "/"}:
            # Allow users to supply either the full endpoint or the base host.
            parsed = parsed._replace(
                path=_STIRLING_PDF_PATH,
                params="",
                query="",
                fragment="",
            )
            return urlunparse(parsed)
        return endpoint

    def _validate_pdf_options(
        self,
        *,
        notes: bool,
        handout: bool,
        range_spec: str | None,
    ) -> None:
        """Ensure mutually exclusive options are not set for PDF export."""
        if notes and handout:
            msg = "Notes and handout export cannot be combined."
            raise UnsupportedOptionError(msg, code="conflicting_options")
        if notes or handout:
            msg = "Notes/handout export is not supported by the HTTP renderer."
            raise UnsupportedOptionError(msg)
        if range_spec:
            msg = "Slide range selection is not supported by the HTTP renderer."
            raise UnsupportedOptionError(msg)

    def _prepare_paths(
        self,
        input_pptx: str,
        output_path: str | None,
    ) -> tuple[Path, Path]:
        """Return validated source and destination paths for the export."""
        source = Path(input_pptx).resolve()
        if not source.exists():
            msg = f"Input file not found: {source}"
            raise PptxRenderingError(msg, code="unavailable")
        destination = Path(output_path) if output_path else source.with_suffix(".pdf")
        destination.parent.mkdir(parents=True, exist_ok=True)
        return source, destination

    def _request_context(self) -> _HttpRequestContext:
        """Compute request metadata for the current renderer configuration."""
        if self._cached_context is not None:
            return self._cached_context

        endpoint = self._cfg.http_office.endpoint
        if not endpoint:
            raise PptxRenderingError(
                tr("pptx.http.endpoint_missing"),
                code="unavailable",
            )
        if requests is None:
            msg = tr("pptx.http.missing_dependency")
            raise PptxRenderingError(msg, code="unavailable")
        req = cast(RequestsModule, requests)
        mode = self._selected_mode()
        endpoint = self._normalise_endpoint(endpoint, mode)
        if mode == "gotenberg":
            field: Literal["file", "files", "fileInput"] = "files"
        elif mode == "stirling":
            field = "fileInput"
        else:
            field = "file"
        self._cached_context = _HttpRequestContext(
            endpoint=endpoint,
            field=field,
            headers=self._cfg.http_office.headers,
            timeout_s=self._cfg.http_office.timeout_s,
            verify_tls=self._cfg.http_office.verify_tls,
            mode=mode,
            requests=req,
        )
        return self._cached_context

    def to_pdf(
        self,
        input_pptx: str,
        output_path: str | None = None,
        notes: bool = False,
        handout: bool = False,
        range_spec: str | None = None,
    ) -> str:
        """Render ``input_pptx`` to ``output_path`` via the configured endpoint."""
        self._validate_pdf_options(notes=notes, handout=handout, range_spec=range_spec)
        context = self._request_context()
        source, destination = self._prepare_paths(input_pptx, output_path)

        req = context.requests

        try:
            with source.open("rb") as handle:
                status, chunks = _post_stream_file(
                    context.endpoint,
                    {context.field: (source.name, handle, _MIME_TYPE)},
                    context.headers,
                    context.timeout_s,
                    context.verify_tls,
                )
        except req.Timeout as exc:
            raise PptxRenderingError(
                tr("pptx.http.timeout"),
                code="timeout",
            ) from exc
        except req.ConnectionError as exc:
            raise PptxRenderingError(
                tr("pptx.http.connection_failed"),
                code="backend_crashed",
            ) from exc
        except req.RequestException as exc:
            raise PptxRenderingError(
                tr("pptx.http.connection_failed"),
                code="backend_crashed",
            ) from exc

        if status != _HTTP_OK:
            detail = f"HTTP {status}"
            raise PptxRenderingError(
                tr("pptx.http.bad_status"),
                code="backend_crashed",
                detail=detail,
            )

        written = 0
        with destination.open("wb") as target:
            for chunk in chunks:
                target.write(chunk)
                written += len(chunk)

        if written == 0:
            with contextlib.suppress(Exception):
                destination.unlink(missing_ok=True)
            raise PptxRenderingError(
                tr("pptx.http.invalid_response"),
                code="backend_crashed",
            )

        logger.info(
            "Rendered %s via HTTP provider to %s (%.1f kB)",
            source,
            destination,
            written / 1024,
            extra={
                "renderer": self.name,
                "mode": context.mode,
                "endpoint": context.endpoint,
                "bytes": written,
                "source": str(source),
                "destination": str(destination),
                "timeout_s": context.timeout_s,
                "verify_tls": context.verify_tls,
                "field": context.field,
            },
        )

        return str(destination)

    def to_images(
        self,
        input_pptx: str,
        options: RenderOptions | None = None,
    ) -> str:
        """The HTTP renderer does not support slide image export."""
        del input_pptx, options
        msg = "Slide image export is not supported."
        raise UnsupportedOptionError(msg)


register(PptxHttpOfficeRenderer)


__all__ = [
    "HttpOfficeSection",
    "PptxHttpOfficeRenderer",
    "RendererConfig",
]
