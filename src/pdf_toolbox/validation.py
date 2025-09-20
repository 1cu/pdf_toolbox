"""Validation helpers for inputs and configuration."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

SUPPORTED_INPUT_SUFFIXES = {".pdf", ".pptx"}

ERR_FILE_NOT_FOUND = "File not found: {path}"
ERR_EXPECTED_FILE = "Expected a file, got directory: {path}"
ERR_UNSUPPORTED_TYPE = "File must be one of {types}: {path}"
ERR_MISSING_CONFIG = "Missing required config field: {key}"


def validate_pdf_path(
    path: str | Path,
    *,
    allowed_suffixes: Iterable[str] | None = None,
) -> Path:
    """Validate and sanitize a document path.

    Args:
        path: Path to validate.
        allowed_suffixes: Optional iterable of accepted suffixes. When omitted,
            only ``.pdf`` files are accepted. Suffix matching is
            case-insensitive.

    Returns:
        ``Path``: Absolute path when validation succeeds.
    """

    def _normalise(ext: str) -> str:
        ext = ext.strip().lower()
        return ext if ext.startswith(".") else f".{ext}"

    suffixes = {".pdf"}
    if allowed_suffixes is not None:
        suffixes = {_normalise(suffix) for suffix in allowed_suffixes}

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(ERR_FILE_NOT_FOUND.format(path=path))
    if p.is_dir():
        raise IsADirectoryError(ERR_EXPECTED_FILE.format(path=path))
    resolved = p.resolve()
    if suffixes and resolved.suffix.lower() not in suffixes:
        kinds = ", ".join(sorted(ext.lstrip(".").upper() for ext in suffixes))
        raise ValueError(ERR_UNSUPPORTED_TYPE.format(types=kinds, path=path))
    return resolved


def validate_config(config: dict) -> dict:
    """Validate configuration values and return them unchanged.

    The configuration must include ``author`` and ``email`` fields.
    """
    required = ("author", "email")
    for key in required:
        val = (config or {}).get(key)
        if not val:
            raise ValueError(ERR_MISSING_CONFIG.format(key=key))
    return config


def is_supported_input(path: str | Path) -> bool:
    """Return ``True`` when *path* points to a supported document type."""
    suffix = Path(path).suffix.lower()
    return suffix in SUPPORTED_INPUT_SUFFIXES


__all__ = ["is_supported_input", "validate_config", "validate_pdf_path"]
