"""Optional import helper for :mod:`requests`."""

from __future__ import annotations

from types import ModuleType
from typing import cast

from pdf_toolbox.renderers._requests_types import RequestsModule

_requests_module: ModuleType | None

try:  # pragma: no cover  # pdf-toolbox: optional dependency import guard exercised via unit tests | issue:-
    import requests as _requests_module
except (
    ModuleNotFoundError,
    ImportError,
):  # pragma: no cover  # pdf-toolbox: optional dependency missing | issue:-
    _requests_module = None
except Exception:  # pragma: no cover  # pdf-toolbox: environments may raise arbitrary errors during import; degrade gracefully | issue:-
    _requests_module = None

requests: RequestsModule | None = cast(RequestsModule | None, _requests_module)


__all__ = ["RequestsModule", "requests"]
