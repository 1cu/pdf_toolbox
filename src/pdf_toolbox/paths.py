"""Path validation utilities."""

from __future__ import annotations

from pathlib import Path

ERR_ESCAPES_BASE = "path escapes base directory"
ERR_NOT_EXIST = "path does not exist"


class PathValidationError(ValueError):
    """Raised when a user-supplied path is invalid or unsafe."""


def validate_path(
    path: str | Path,
    *,
    base: str | Path | None = None,
    must_exist: bool = False,
) -> Path:
    """Return a sanitized absolute path.

    Security Note:
        When ``base`` is None, this function allows access to any path on the
        filesystem (subject to OS permissions). This is intentional for desktop
        applications where users need to access files anywhere on their system.

        For multi-user or service contexts where path access should be restricted,
        always provide a ``base`` directory to enforce containment.

    Parameters
    ----------
    path:
        User-supplied path to validate. Must not contain null bytes or other
        invalid characters.
    base:
        Optional base directory the path must reside in. When provided, the
        resolved path must be within this directory tree (prevents directory
        traversal attacks).
    must_exist:
        If ``True`` the path must already exist.

    Raises:
    ------
    PathValidationError:
        If the path contains invalid characters, escapes the base directory,
        or doesn't exist when required.
    """
    # Validate path string for malicious patterns
    path_str = str(path)
    if "\x00" in path_str:
        raise PathValidationError("path contains null bytes")  # noqa: TRY003  # pdf-toolbox: path validation error message | issue:-

    p = Path(path)
    candidate = p
    if base is not None:
        base_path = Path(base).resolve()
        candidate = (base_path / p).resolve() if not p.is_absolute() else p.resolve()
        if base_path not in [candidate, *candidate.parents]:
            raise PathValidationError(ERR_ESCAPES_BASE)
    else:
        candidate = p.resolve()
    if must_exist and not candidate.exists():
        raise PathValidationError(ERR_NOT_EXIST)
    return candidate


__all__ = ["PathValidationError", "validate_path"]
