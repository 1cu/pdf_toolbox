from __future__ import annotations

import ssl
from collections.abc import Mapping, Sequence
from typing import cast

import pytest

from pdf_toolbox.github import GitHubAPIError, GitHubClient, Transport, TransportResult


class FakeTransport:
    """Simple callable test double that captures GitHub client requests."""

    def __init__(self, responses: Sequence[TransportResult | Exception]) -> None:
        """Seed the transport with predetermined responses or exceptions."""
        self._responses = list(responses)
        self.calls: list[tuple[str, str, dict[str, str], float]] = []

    def __call__(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        timeout: float,
    ) -> TransportResult:
        """Return the next queued response while recording the call metadata."""
        self.calls.append((method, url, dict(headers), timeout))
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _make_client(
    responses: Sequence[TransportResult | Exception],
    *,
    token: str | None = None,
) -> tuple[GitHubClient, FakeTransport]:
    transport = FakeTransport(responses)
    client = GitHubClient(token, transport=transport, timeout=7.5)
    return client, transport


def test_get_returns_parsed_json() -> None:
    client, transport = _make_client(
        [TransportResult(status=200, body='{"ok": true}', headers={})],
        token="token",
    )
    payload = client.get("/repos/foo/bar", params={"page": "1"})
    assert payload == {"ok": True}
    method, url, headers, timeout = transport.calls[0]
    assert method == "GET"
    assert url == "https://api.github.com/repos/foo/bar?page=1"
    assert headers["Authorization"] == "Bearer token"
    assert headers["User-Agent"] == "pdf-toolbox"
    assert timeout == 7.5


def test_get_handles_empty_body() -> None:
    client, _ = _make_client([TransportResult(status=204, body="", headers={})])
    assert client.get("/repos/foo/bar") is None


def test_get_raises_for_http_error() -> None:
    client, _ = _make_client([TransportResult(status=500, body="boom", headers={})])
    with pytest.raises(GitHubAPIError) as excinfo:
        client.get("/repos/foo/bar")
    err = excinfo.value
    assert err.status == 500
    assert err.url == "https://api.github.com/repos/foo/bar"
    assert "500" in str(err)


def test_get_raises_for_invalid_json() -> None:
    client, _ = _make_client([TransportResult(status=200, body="not-json", headers={})])
    with pytest.raises(GitHubAPIError) as excinfo:
        client.get("/repos/foo/bar")
    assert "decode" in str(excinfo.value)


def test_delete_accepts_success_codes() -> None:
    responses = [TransportResult(status=204, body="", headers={})]
    client, transport = _make_client(responses, token="token")
    client.delete("/repos/foo/bar")
    assert transport.calls[0][0] == "DELETE"


def test_delete_rejects_error_status() -> None:
    client, _ = _make_client([TransportResult(status=404, body="", headers={})])
    with pytest.raises(GitHubAPIError):
        client.delete("/repos/foo/bar")


def test_transport_exception_wrapped() -> None:
    client, _ = _make_client([ValueError("network")])
    with pytest.raises(GitHubAPIError) as excinfo:
        client.get("/repos/foo/bar")
    assert "network" in str(excinfo.value)


def test_requires_https_base_url() -> None:
    with pytest.raises(ValueError, match="requires HTTPS"):
        GitHubClient("token", base_url="http://api.github.com")


def test_requires_netloc_in_base_url() -> None:
    with pytest.raises(ValueError, match="Invalid GitHub API URL"):
        GitHubClient("token", base_url="https:///missing-host")


def test_default_transport_invoked(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class DummyResponse:
        status = 200

        def read(self) -> bytes:
            return b'{"ok": true}'

        def getheaders(self) -> list[tuple[str, str]]:
            return [("Content-Type", "application/json")]

    class DummyConnection:
        def __init__(
            self, host: str, port: int | None, timeout: float, context
        ) -> None:
            captured["init"] = (host, port, timeout, context)

        def request(self, method: str, target: str, headers: Mapping[str, str]) -> None:
            captured["request"] = (method, target, dict(headers))

        def getresponse(self) -> DummyResponse:
            return DummyResponse()

        def close(self) -> None:
            captured["closed"] = True

    monkeypatch.setattr(
        "src.pdf_toolbox.github.http.client.HTTPSConnection",
        DummyConnection,
    )
    client = GitHubClient(None)
    payload = client.get("/repos/foo", params={"page": "1"})
    assert payload == {"ok": True}
    assert captured["request"] == (
        "GET",
        "/repos/foo?page=1",
        {"Accept": "application/vnd.github+json", "User-Agent": "pdf-toolbox"},
    )
    assert captured.get("closed") is True


def test_ssl_context_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    contexts: list[object] = []

    class DummyContext:
        """Dummy SSL context that raises when loading custom certificates."""

        def load_verify_locations(self, *, cafile: str) -> None:
            del cafile
            raise ssl.SSLError("boom")

    def fake_create_default_context() -> DummyContext:
        ctx = DummyContext()
        contexts.append(ctx)
        return ctx

    monkeypatch.setattr("src.pdf_toolbox.github.Path.exists", lambda _path: True)
    monkeypatch.setattr(
        "src.pdf_toolbox.github.ssl.create_default_context",
        fake_create_default_context,
    )

    context = GitHubClient._build_ssl_context()
    assert len(contexts) == 2
    assert context is contexts[-1]


def test_ssl_context_success(monkeypatch: pytest.MonkeyPatch) -> None:
    contexts: list[DummySuccessContext] = []

    class DummySuccessContext:
        """SSL context that tracks whether certificates were loaded."""

        def __init__(self) -> None:
            self.loaded = False

        def load_verify_locations(self, *, cafile: str) -> None:
            del cafile
            self.loaded = True

    def fake_create_default_context() -> DummySuccessContext:
        ctx = DummySuccessContext()
        contexts.append(ctx)
        return ctx

    monkeypatch.setattr("src.pdf_toolbox.github.Path.exists", lambda _path: True)
    monkeypatch.setattr(
        "src.pdf_toolbox.github.ssl.create_default_context",
        fake_create_default_context,
    )

    context = GitHubClient._build_ssl_context()
    assert isinstance(context, DummySuccessContext)
    assert context.loaded is True


def test_perform_propagates_github_errors() -> None:
    error = GitHubAPIError("boom", status=500, url="https://api.github.com/test")

    def broken_transport(
        _method: str, _url: str, _headers: Mapping[str, str], _timeout: float
    ) -> TransportResult:
        raise error

    client = GitHubClient(None, transport=cast(Transport, broken_transport))
    with pytest.raises(GitHubAPIError) as excinfo:
        client.get("/test")
    assert excinfo.value is error
