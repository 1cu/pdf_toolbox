#!/usr/bin/env python3
"""Delete old GitHub releases and tags beyond a limit.

Uses the GitHub REST API with the ``GITHUB_TOKEN`` provided by the
workflow. The number of releases to keep can be configured with the
``MAX_RELEASES`` environment variable (defaults to ``20``).
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import partial
from urllib.parse import quote

from pdf_toolbox.github import GitHubAPIError, GitHubClient

API_PATH = "https://api.github.com"
TIMEOUT = 10
RETRIES = 3
ERR_REQUEST_FAIL = "{method} {url} failed"
ERR_RELEASE_PAYLOAD = "Unexpected release payload from GitHub for {repo}"


@dataclass(frozen=True)
class ReleaseInfo:
    """Minimal release metadata required for pruning."""

    identifier: int
    tag_name: str


def _call_with_retry[T](
    action: Callable[[], T],
    *,
    method: str,
    fallback_url: str,
) -> T:
    """Retry *action* on transient GitHub API errors."""
    for attempt in range(RETRIES):
        try:
            return action()
        except GitHubAPIError as exc:
            if attempt == RETRIES - 1:
                url = exc.url or fallback_url
                raise RuntimeError(
                    ERR_REQUEST_FAIL.format(method=method, url=url)
                ) from exc
            time.sleep(2**attempt)
    raise RuntimeError(ERR_REQUEST_FAIL.format(method=method, url=fallback_url))


def _coerce_release(repo: str, payload: object) -> ReleaseInfo:
    """Convert a GitHub API payload to :class:`ReleaseInfo`."""
    if not isinstance(payload, dict):
        message = f"Release payload for {repo!r} is not an object: {payload!r}"
        raise TypeError(message)
    identifier = payload.get("id")
    tag = payload.get("tag_name")
    if not isinstance(identifier, int) or not isinstance(tag, str):
        message = f"Release payload for {repo!r} missing id/tag_name: {payload!r}"
        raise TypeError(message)
    return ReleaseInfo(identifier=identifier, tag_name=tag)


def _fetch_releases(client: GitHubClient, repo: str) -> list[ReleaseInfo]:
    """Return all releases for *repo* using pagination."""
    releases: list[ReleaseInfo] = []
    path = f"/repos/{repo}/releases"
    page = 1
    while True:
        page_params = {"per_page": "100", "page": str(page)}

        def _load_page(
            current_params: dict[str, str] = page_params,
        ) -> list[ReleaseInfo]:
            data = client.get(path, params=current_params)
            if data is None:
                return []
            if not isinstance(data, list):
                message = ERR_RELEASE_PAYLOAD.format(repo=repo)
                raise TypeError(message)
            return [_coerce_release(repo, item) for item in data]

        page_releases = _call_with_retry(
            _load_page,
            method="GET",
            fallback_url=f"{API_PATH}{path}?per_page=100&page={page}",
        )
        if not page_releases:
            break
        releases.extend(page_releases)
        page += 1
    return releases


def _delete_paths(client: GitHubClient, paths: Iterable[str]) -> None:
    """Delete each API *path* using the GitHub client."""
    for path in paths:
        _call_with_retry(
            partial(client.delete, path),
            method="DELETE",
            fallback_url=f"{API_PATH}{path}",
        )


def main() -> None:
    """Remove old releases and their tags beyond ``MAX_RELEASES``."""
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    keep = int(os.environ.get("MAX_RELEASES", "20"))

    client = GitHubClient(token, timeout=TIMEOUT)
    releases = _fetch_releases(client, repo)

    for release in releases[keep:]:
        encoded_tag = quote(release.tag_name, safe="")
        _delete_paths(
            client,
            (
                f"/repos/{repo}/releases/{release.identifier}",
                f"/repos/{repo}/git/refs/tags/{encoded_tag}",
            ),
        )


if __name__ == "__main__":
    main()
