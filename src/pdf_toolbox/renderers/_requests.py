"""Optional import helper for :mod:`requests`."""

from __future__ import annotations

from types import ModuleType

from pdf_toolbox.renderers._requests_types import RequestsModule

_requests_module: ModuleType | None

try:  # pragma: no cover  # pdf-toolbox: optional dependency import guard exercised via unit tests | issue:-
    import requests as _requests_module
except Exception:  # pragma: no cover  # pdf-toolbox: gracefully handle missing optional dependency | issue:-
    _requests_module = None

requests: ModuleType | None = _requests_module


__all__ = ["requests", "RequestsModule"]
