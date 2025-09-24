import types

import pytest

from pdf_toolbox.renderers import _requests


@pytest.fixture
def requests_stub() -> types.ModuleType:
    module = types.ModuleType("requests")
    Timeout = type("Timeout", (Exception,), {})
    setattr(module, "Timeout", Timeout)
    setattr(module, "ConnectionError", type("ConnectionError", (Exception,), {}))
    setattr(module, "RequestException", type("RequestException", (Exception,), {}))

    def post(
        url: str,
        *,
        files,
        headers,
        timeout,
        verify: bool,
        stream: bool,
    ) -> None:
        raise Timeout

    setattr(module, "post", post)
    return module


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
