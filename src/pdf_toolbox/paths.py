"""Path validation utilities."""

from __future__ import annotations

from pathlib import Path


class PathValidationError(ValueError):
    """Raised when a user-supplied path is invalid or unsafe."""


def validate_path(
    path: str | Path,
    *,
    base: str | Path | None = None,
    must_exist: bool = False,
) -> Path:
    """Return a sanitized absolute path.

    Parameters
    ----------
    path:
        User-supplied path to validate.
    base:
        Optional base directory the path must reside in.
    must_exist:
        If ``True`` the path must already exist.
    """
    p = Path(path)
    candidate = p
    if base is not None:
        base_path = Path(base).resolve()
        candidate = (base_path / p).resolve() if not p.is_absolute() else p.resolve()
        if base_path not in [candidate, *candidate.parents]:
            raise PathValidationError("path escapes base directory")
    else:
        candidate = p.resolve()
    if must_exist and not candidate.exists():
        raise PathValidationError("path does not exist")
    return candidate


__all__ = ["PathValidationError", "validate_path"]
