"""Common utilities for PDF toolbox modules."""

from __future__ import annotations

import importlib
import json
import logging
from collections.abc import Iterable
from pathlib import Path
from threading import Event

import fitz  # type: ignore
from platformdirs import user_config_dir

from .validation import validate_config

# Modules required at runtime; PowerPoint COM is no longer needed
REQUIRED_LIBS: Iterable[str] = (
    "fitz",
    "PIL.Image",
    "docx",
)
# suggestions for installing optional runtime libraries
LIB_HINTS: dict[str, str] = {
    "fitz": "pip install pymupdf",
    "PIL.Image": "pip install pillow",
    "docx": "pip install python-docx",
}
# store configuration in a platform-specific user config directory
CONFIG_FILE = Path(user_config_dir("pdf_toolbox")) / "pdf_toolbox_config.json"

# central logger for the project
logger = logging.getLogger("pdf_toolbox")
logger.propagate = False


def configure_logging(
    level: str = "INFO", handler: logging.Handler | None = None
) -> logging.Logger:
    """Configure and return the package logger."""
    numeric = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric)
    logger.handlers.clear()
    if handler is None:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)

    # forward warnings.warn() calls through the logging system
    logging.captureWarnings(True)
    wlog = logging.getLogger("py.warnings")
    wlog.setLevel(numeric)
    wlog.handlers.clear()
    wlog.addHandler(handler)
    wlog.propagate = False
    return logger


# configure default logging on import
configure_logging()


def _load_author_info() -> tuple[str, str]:
    """Return configured author information.

    The configuration must provide ``author`` and ``email`` fields in
    ``pdf_toolbox_config.json`` located in the user's configuration directory.
    A ``RuntimeError`` is raised if the configuration is missing or incomplete.
    """
    try:
        data = json.loads(CONFIG_FILE.read_text())
        # Validate presence of required fields with a stable message.
        validate_config(data)
        author = data["author"]
        email = data["email"]
    except Exception as exc:  # pragma: no cover - best effort
        raise RuntimeError(
            "pdf_toolbox_config.json must define 'author' and 'email'"
        ) from exc
    return author, email


def ensure_libs() -> None:
    """Ensure optional runtime libraries are importable.

    Raises a ``RuntimeError`` if a library is missing so callers can
    present a helpful message to the user.
    """
    missing: list[str] = []
    for mod in REQUIRED_LIBS:
        try:
            importlib.import_module(mod)
        except Exception:  # pragma: no cover - best effort
            missing.append(mod)
    if missing:
        parts = []
        for mod in missing:
            hint = LIB_HINTS.get(mod, "see documentation")
            parts.append(f"{mod} ({hint})")
        raise RuntimeError("Missing required libraries: " + ", ".join(parts))


def parse_page_spec(spec: str | None, total: int) -> list[int]:
    """Parse a page/slide specification into a list of 1-based numbers.

    ``spec`` follows a simple syntax with comma-separated parts. Each part may
    be a single number (``"5"``), a range like ``"3-7"``, an open-ended range
    such as ``"2-"`` or ``"-4"``, or any combination thereof
    (e.g. ``"1,5,6"``). ``None`` or an empty string selects all pages.

    A ``ValueError`` is raised if the specification is invalid or references
    pages outside ``1..total``.
    """
    if not spec:
        return list(range(1, total + 1))

    pages: set[int] = set()
    for raw_part in spec.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            try:
                start = int(start_s) if start_s else 1
                end = int(end_s) if end_s else total
            except ValueError as exc:
                raise ValueError("Invalid page specification") from exc
            if start < 1 or end > total:
                raise ValueError(f"page {start}-{end} out of range 1..{total}")
            if end < start:
                raise ValueError("end must be greater than or equal to start")
            pages.update(range(start, end + 1))
        else:
            try:
                page = int(part)
            except ValueError as exc:
                raise ValueError("Invalid page specification") from exc
            if page < 1 or page > total:
                raise ValueError(f"page {page} out of range 1..{total}")
            pages.add(page)
    return sorted(pages)


def sane_output_dir(base_path: str | Path, out_dir: str | Path | None) -> Path:
    """Return a Path for output files.

    If ``out_dir`` is ``None`` the directory of ``base_path`` is returned.
    The directory is created if it does not yet exist.
    """
    base = Path(base_path)
    target = Path(out_dir) if out_dir else base.parent
    if target.suffix:
        raise ValueError(f"Output directory must be a directory, not a file: {out_dir}")
    target.mkdir(parents=True, exist_ok=True)
    return target


def update_metadata(fitz_doc: fitz.Document, note: str | None = None) -> None:
    """Update metadata with a custom note."""
    metadata = dict(fitz_doc.metadata or {})
    if note:
        existing_subject = metadata.get("subject") or ""
        metadata["subject"] = existing_subject + note
    metadata.setdefault("producer", "pdf_toolbox")
    author, _email = _load_author_info()
    metadata["author"] = metadata.get("author") or author
    fitz_doc.set_metadata(metadata)


def raise_if_cancelled(
    cancel: Event | None, doc: fitz.Document | None = None
) -> None:  # pragma: no cover - cooperative cancellation helper
    """Raise ``RuntimeError('cancelled')`` if ``cancel`` is set.

    If ``doc`` is provided it will be closed before raising to free
    resources. The function is excluded from coverage as it depends on
    timing-sensitive user interaction.
    """
    if cancel and cancel.is_set():
        if doc is not None:
            doc.close()
        raise RuntimeError("cancelled")


def open_pdf(path: str | Path) -> fitz.Document:
    """Open ``path`` as a PDF document with friendly errors."""
    try:
        return fitz.open(str(path))
    except Exception as exc:  # pragma: no cover - best effort
        raise RuntimeError(f"Could not open PDF file: {path}") from exc


def save_pdf(
    doc: fitz.Document,
    out_path: str | Path,
    *,
    note: str | None = None,
    **save_kwargs,
) -> None:
    """Save ``doc`` to ``out_path`` updating metadata and closing it."""
    update_metadata(doc, note)
    try:
        doc.save(str(out_path), **save_kwargs)
    except Exception as exc:  # pragma: no cover - best effort
        raise RuntimeError(f"Could not save PDF file: {out_path}") from exc
    finally:
        doc.close()


__all__ = [
    "configure_logging",
    "ensure_libs",
    "logger",
    "open_pdf",
    "parse_page_spec",
    "raise_if_cancelled",
    "sane_output_dir",
    "save_pdf",
    "update_metadata",
]
