"""Shared HTTP helpers for PPTX renderers."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from typing import IO

try:  # pragma: no cover  # pdf-toolbox: optional dependency import guard exercised via unit tests | issue:-
    import requests  # type: ignore[import-untyped]  # pdf-toolbox: requests library does not ship type information | issue:-
except Exception:  # pragma: no cover  # pdf-toolbox: gracefully handle missing optional dependency | issue:-
    requests = None  # type: ignore[assignment]  # pdf-toolbox: sentinel assignment when dependency unavailable | issue:-

_CHUNK_SIZE = 65536


def _post_stream_file(
    endpoint: str,
    files: Mapping[str, tuple[str, IO[bytes], str]],
    headers: Mapping[str, str] | None,
    timeout: float | tuple[float, float] | None,
    verify: bool,
) -> tuple[int, Iterable[bytes]]:
    """POST ``files`` to ``endpoint`` and return the response stream."""
    if (
        requests is None
    ):  # pragma: no cover  # pdf-toolbox: renderer checks dependency availability before calling helper | issue:-
        msg = "The 'requests' dependency is required for HTTP PPTX rendering."
        raise RuntimeError(msg)

    response = requests.post(  # type: ignore[no-untyped-call]  # pdf-toolbox: requests call lacks typing information | issue:-
        endpoint,
        files=files,
        headers=dict(headers) if headers else None,
        timeout=timeout,
        verify=verify,
        stream=True,
    )

    def _iter_content() -> Iterator[bytes]:
        try:
            for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
                if chunk:
                    yield chunk
        finally:
            response.close()

    return response.status_code, _iter_content()


__all__ = ["_post_stream_file"]
