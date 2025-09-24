"""Optional import helper for :mod:`requests`."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from types import ModuleType
from typing import cast

from pdf_toolbox.renderers._requests_types import RequestsModule

Importer = Callable[[str], ModuleType]


def _load_requests(
    importer: Importer = importlib.import_module,
) -> RequestsModule | None:
    """Import :mod:`requests` using ``importer`` and degrade gracefully on failure."""
    try:
        module = importer("requests")
    except (ModuleNotFoundError, ImportError):
        return None
    except Exception:
        return None
    return cast(RequestsModule, module)


requests: RequestsModule | None = _load_requests()


__all__ = ["RequestsModule", "requests"]
