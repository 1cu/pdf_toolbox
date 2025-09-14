"""Validation helpers for inputs and configuration."""

from __future__ import annotations

from pathlib import Path

ERR_PDF_NOT_FOUND = "PDF file not found: {path}"
ERR_EXPECTED_FILE = "Expected a file, got directory: {path}"
ERR_MUST_BE_PDF = "File must be a PDF: {path}"
ERR_MISSING_CONFIG = "Missing required config field: {key}"


def validate_pdf_path(path: str | Path) -> Path:
    """Validate and sanitize a PDF file path.

    Returns a ``Path`` object if valid, otherwise raises a descriptive
    exception.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(ERR_PDF_NOT_FOUND.format(path=path))
    if p.is_dir():
        raise IsADirectoryError(ERR_EXPECTED_FILE.format(path=path))
    if p.suffix.lower() != ".pdf":
        raise ValueError(ERR_MUST_BE_PDF.format(path=path))
    return p


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


__all__ = ["validate_config", "validate_pdf_path"]
