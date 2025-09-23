"""Small helper for interacting with the GitHub REST API."""

from __future__ import annotations

import http.client
import json
import ssl
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Protocol
from urllib.parse import urlencode, urlsplit, urlunsplit


class GitHubAPIError(RuntimeError):
    """Raised when a GitHub API request fails."""

    def __init__(
        self, message: str, *, status: int | None = None, url: str | None = None
    ) -> None:
        """Initialise the error with optional status and URL metadata."""
        super().__init__(message)
        self.status = status
        self.url = url


@dataclass(frozen=True)
class TransportResult:
    """Raw HTTP response returned by a :class:`Transport`."""

    status: int
    body: str
    headers: Mapping[str, str]


class Transport(Protocol):
    """Callable capable of issuing HTTP requests for the client."""

    def __call__(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        timeout: float,
    ) -> TransportResult:
        """Perform an HTTP request and return the raw response."""
        ...


class GitHubClient:
    """Lightweight client for GitHub's REST API."""

    def __init__(
        self,
        token: str | None,
        *,
        base_url: str = "https://api.github.com",
        timeout: float = 10.0,
        transport: Transport | None = None,
    ) -> None:
        """Configure the client for a specific GitHub base URL."""
        parts = urlsplit(base_url)
        if parts.scheme != "https":
            message = f"GitHub API requires HTTPS (got {parts.scheme or 'missing'})"
            raise ValueError(message)
        if not parts.netloc:
            message = f"Invalid GitHub API URL: {base_url!r}"
            raise ValueError(message)
        self._scheme = parts.scheme
        self._netloc = parts.netloc
        self._base_path = parts.path.rstrip("/")
        self._timeout = timeout
        headers: MutableMapping[str, str] = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "pdf-toolbox",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._headers = headers
        self._context = self._build_ssl_context()
        self._transport: Transport = transport or self._default_transport

    @staticmethod
    def _build_ssl_context() -> ssl.SSLContext:
        """Return an SSL context that prefers system certificates."""
        context = ssl.create_default_context()
        fallback_cafile = Path("/etc/ssl/certs/ca-certificates.crt")
        if fallback_cafile.exists():
            try:
                context.load_verify_locations(cafile=str(fallback_cafile))
            except ssl.SSLError:
                # Fall back to the platform defaults when custom loading fails.
                context = ssl.create_default_context()
        return context

    def _default_transport(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        timeout: float,
    ) -> TransportResult:
        parsed = urlsplit(url)
        connection = http.client.HTTPSConnection(
            parsed.hostname or parsed.netloc,
            parsed.port,
            timeout=timeout,
            context=self._context,
        )
        target = parsed.path or "/"
        if parsed.query:
            target = f"{target}?{parsed.query}"
        try:
            connection.request(method, target, headers=dict(headers))
            response = connection.getresponse()
            body = response.read().decode("utf-8")
            header_map = dict(response.getheaders())
            return TransportResult(
                status=response.status, body=body, headers=header_map
            )
        finally:
            connection.close()

    def _build_url(self, path: str, params: Mapping[str, str] | None) -> str:
        raw_path = path if path.startswith("/") else f"/{path}"
        merged_path = f"{self._base_path}{raw_path}" if self._base_path else raw_path
        query = urlencode(params or {})
        return urlunsplit((self._scheme, self._netloc, merged_path or "/", query, ""))

    def _perform(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
    ) -> tuple[TransportResult, str]:
        url = self._build_url(path, params)
        try:
            result = self._transport(method, url, dict(self._headers), self._timeout)
        except GitHubAPIError:
            raise
        except Exception as exc:
            message = f"GitHub API request failed for {method} {url}: {exc}"
            raise GitHubAPIError(message, url=url) from exc
        return result, url

    def get(self, path: str, *, params: Mapping[str, str] | None = None) -> object:
        """Execute a GET request and return the decoded JSON payload."""
        response, url = self._perform("GET", path, params=params)
        if response.status >= HTTPStatus.BAD_REQUEST:
            message = f"GitHub API responded with {response.status} for GET {url}"
            raise GitHubAPIError(message, status=response.status, url=url)
        if not response.body:
            return None
        try:
            return json.loads(response.body)
        except json.JSONDecodeError as exc:
            message = f"Unable to decode GitHub response for {path}: {exc}"
            raise GitHubAPIError(message, url=url) from exc

    def delete(self, path: str, *, params: Mapping[str, str] | None = None) -> None:
        """Execute a DELETE request and ensure a successful status."""
        response, url = self._perform("DELETE", path, params=params)
        if response.status not in {
            HTTPStatus.OK,
            HTTPStatus.ACCEPTED,
            HTTPStatus.NO_CONTENT,
            HTTPStatus.RESET_CONTENT,
        }:
            message = f"GitHub API responded with {response.status} for DELETE {path}"
            raise GitHubAPIError(message, status=response.status, url=url)


__all__ = ["GitHubAPIError", "GitHubClient", "Transport", "TransportResult"]
