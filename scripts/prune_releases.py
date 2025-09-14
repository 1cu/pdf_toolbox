#!/usr/bin/env python3
"""Delete old GitHub releases and tags beyond a limit.

Uses the GitHub REST API with the ``GITHUB_TOKEN`` provided by the
workflow. The number of releases to keep can be configured with the
``MAX_RELEASES`` environment variable (defaults to ``20``).
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from urllib.error import HTTPError, URLError

API_URL = "https://api.github.com"  # Base URL for GitHub REST API
HTTP_NO_CONTENT = 204
TIMEOUT = 10
RETRIES = 3
ERR_REQUEST_FAIL = "{method} {url} failed"


def _request(
    method: str, url: str, token: str, *, timeout: float = TIMEOUT
) -> list | dict | None:
    """Perform an HTTP request and return parsed JSON if available."""
    req = urllib.request.Request(url, method=method)  # noqa: S310  # pdf-toolbox: urllib Request for GitHub API | issue:-
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:  # noqa: S310  # nosec B310  # pdf-toolbox: urllib urlopen for GitHub API | issue:-
                if response.status != HTTP_NO_CONTENT:
                    return json.load(response)
        except (HTTPError, URLError) as exc:
            if attempt == RETRIES - 1:
                raise RuntimeError(
                    ERR_REQUEST_FAIL.format(method=method, url=url)
                ) from exc
            time.sleep(2**attempt)
        else:
            return None
    return None


def main() -> None:
    """Remove old releases and their tags beyond ``MAX_RELEASES``."""
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    keep = int(os.environ.get("MAX_RELEASES", "20"))

    releases: list[dict] = []
    page = 1
    while True:
        url = f"{API_URL}/repos/{repo}/releases?per_page=100&page={page}"
        data = _request("GET", url, token)
        if not data:
            break
        releases.extend(data)  # type: ignore[arg-type]  # pdf-toolbox: GitHub API returns untyped data | issue:-
        page += 1

    for rel in releases[keep:]:
        release_id = rel["id"]
        tag = rel["tag_name"]
        _request("DELETE", f"{API_URL}/repos/{repo}/releases/{release_id}", token)
        _request("DELETE", f"{API_URL}/repos/{repo}/git/refs/tags/{tag}", token)


if __name__ == "__main__":
    main()
