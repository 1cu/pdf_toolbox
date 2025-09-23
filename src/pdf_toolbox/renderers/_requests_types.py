"""Typed protocols for the optional :mod:`requests` dependency."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import IO, Protocol


class ResponseProtocol(Protocol):
    """Subset of :class:`requests.Response` used by the renderers."""

    status_code: int

    def iter_content(self, chunk_size: int) -> Iterator[bytes]:
        """Yield streaming chunks from the HTTP response body."""

    def close(self) -> None:
        """Release the HTTP response resources."""


class RequestsModule(Protocol):
    """Protocol describing the :mod:`requests` APIs we rely on."""

    Timeout: type[Exception]
    ConnectionError: type[Exception]
    RequestException: type[Exception]

    def post(
        self,
        url: str,
        *,
        files: Mapping[str, tuple[str, IO[bytes], str]],
        headers: Mapping[str, str] | None,
        timeout: float | tuple[float, float] | None,
        verify: bool,
        stream: bool,
    ) -> ResponseProtocol:
        """Submit a multipart POST request and return the streaming response."""


__all__ = ["RequestsModule", "ResponseProtocol"]
