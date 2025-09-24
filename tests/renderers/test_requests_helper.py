from __future__ import annotations

import types
from typing import Any, cast

import pytest

from pdf_toolbox.renderers import _requests


@pytest.fixture
def requests_stub() -> types.ModuleType:
    module = cast(Any, types.ModuleType("requests"))
    timeout_error = type("Timeout", (Exception,), {})
    connection_error = type("ConnectionError", (Exception,), {})
    request_exception = type("RequestException", (Exception,), {})

    module.Timeout = timeout_error
    module.ConnectionError = connection_error
    module.RequestException = request_exception

    def post(*_: Any, **__: Any) -> None:
        raise timeout_error

    module.post = post
    return cast(types.ModuleType, module)


def test_load_requests_imports_requests(requests_stub: types.ModuleType) -> None:
    calls: list[str] = []

    def importer(name: str) -> types.ModuleType:
        calls.append(name)
        return requests_stub

    module = _requests._load_requests(importer)

    assert calls == ["requests"]
    assert module is requests_stub


def test_load_requests_handles_missing_dependency() -> None:
    def importer(name: str) -> types.ModuleType:
        raise ModuleNotFoundError(name)

    assert _requests._load_requests(importer) is None


def test_load_requests_handles_unexpected_error() -> None:
    def importer(name: str) -> types.ModuleType:
        raise RuntimeError(name)

    assert _requests._load_requests(importer) is None
