from __future__ import annotations

from typing import cast

import pytest

from scripts import prune_releases
from scripts.github_client import GitHubAPIError, GitHubClient


class DummyClient:
    """Test double that mimics the subset of `GitHubClient` used in pruning."""

    def __init__(
        self, get_responses: list[object], delete_responses: list[object] | None = None
    ) -> None:
        """Initialise the dummy with queued responses for GET and DELETE calls."""
        self._get_responses = get_responses
        self._delete_responses = delete_responses or []
        self.get_calls: list[tuple[str, dict[str, str]]] = []
        self.delete_calls: list[str] = []

    def get(self, path: str, *, params: dict[str, str] | None = None) -> object:
        """Return the next queued response while recording the request details."""
        self.get_calls.append((path, dict(params or {})))
        response = self._get_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def delete(self, path: str) -> None:
        """Consume the next queued delete outcome and track the requested path."""
        self.delete_calls.append(path)
        if self._delete_responses:
            outcome = self._delete_responses.pop(0)
            if isinstance(outcome, Exception):
                raise outcome


def test_coerce_release_valid() -> None:
    info = prune_releases._coerce_release("repo", {"id": 12, "tag_name": "v1"})
    assert info.identifier == 12
    assert info.tag_name == "v1"


def test_coerce_release_invalid_type() -> None:
    with pytest.raises(TypeError):
        prune_releases._coerce_release("repo", object())


def test_fetch_releases_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyClient(
        [
            [{"id": 1, "tag_name": "v1"}],
            [],
        ]
    )
    monkeypatch.setattr(
        prune_releases,
        "_call_with_retry",
        lambda action, **_: action(),
    )
    releases = prune_releases._fetch_releases(
        cast(GitHubClient, client),
        "owner/repo",
    )
    assert [rel.tag_name for rel in releases] == ["v1"]
    assert client.get_calls == [
        ("/repos/owner/repo/releases", {"per_page": "100", "page": "1"}),
        ("/repos/owner/repo/releases", {"per_page": "100", "page": "2"}),
    ]


def test_call_with_retry_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[str] = []

    def action() -> str:
        attempts.append("x")
        if len(attempts) == 1:
            raise GitHubAPIError("boom", url="https://api.github.com/test")
        return "ok"

    sleeps: list[float] = []
    monkeypatch.setattr(prune_releases.time, "sleep", sleeps.append)

    result = prune_releases._call_with_retry(
        action,
        method="GET",
        fallback_url="https://api.github.com/test",
    )
    assert result == "ok"
    assert sleeps == [1]
    assert len(attempts) == 2


def test_call_with_retry_raises_after_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prune_releases.time, "sleep", lambda _seconds: None)

    with pytest.raises(RuntimeError) as excinfo:
        prune_releases._call_with_retry(
            lambda: (_ for _ in ()).throw(
                GitHubAPIError("fail", url="https://api.github.com/test")
            ),
            method="GET",
            fallback_url="https://api.github.com/test",
        )
    assert "GET" in str(excinfo.value)


def test_delete_paths_invokes_client(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyClient([], [])
    calls: list[str] = []

    def fake_retry(action, **_):
        result = action()
        calls.append(client.delete_calls[-1])
        return result

    monkeypatch.setattr(prune_releases, "_call_with_retry", fake_retry)

    prune_releases._delete_paths(cast(GitHubClient, client), ("/one", "/two"))
    assert calls == ["/one", "/two"]
