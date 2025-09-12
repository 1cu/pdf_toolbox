#!/usr/bin/env python3
"""Delete old GitHub releases and tags beyond a limit.

Uses the GitHub REST API with the ``GITHUB_TOKEN`` provided by the
workflow. The number of releases to keep can be configured with the
``MAX_RELEASES`` environment variable (defaults to ``20``).
"""

from __future__ import annotations

import json
import os
import urllib.request

API_URL = "https://api.github.com"  # Base URL for GitHub REST API


def _request(method: str, url: str, token: str) -> list | dict | None:
    """Perform an HTTP request and return parsed JSON if available."""
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req) as response:
        if response.status != 204:
            return json.load(response)
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
        releases.extend(data)  # type: ignore[arg-type]
        page += 1

    for rel in releases[keep:]:
        release_id = rel["id"]
        tag = rel["tag_name"]
        _request("DELETE", f"{API_URL}/repos/{repo}/releases/{release_id}", token)
        _request("DELETE", f"{API_URL}/repos/{repo}/git/refs/tags/{tag}", token)


if __name__ == "__main__":
    main()
