"""Common utilities for PDF toolbox modules."""

from __future__ import annotations

import importlib
import json
import logging
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from threading import Event

import fitz  # type: ignore  # pdf-toolbox: PyMuPDF lacks type hints | issue:-
from platformdirs import user_config_dir

from pdf_toolbox.paths import PathValidationError, validate_path
from pdf_toolbox.validation import validate_config

# Modules required at runtime; PowerPoint COM is no longer needed
REQUIRED_LIBS: Iterable[str] = (
    "fitz",
    "PIL.Image",
)
# suggestions for installing optional runtime libraries
LIB_HINTS: dict[str, str] = {
    "fitz": "pip install pymupdf",
    "PIL.Image": "pip install pillow",
}
# store configuration in a platform-specific user config directory
CONFIG_FILE = Path(user_config_dir("pdf_toolbox")) / "pdf_toolbox_config.json"

# central logger for the project
logger = logging.getLogger("pdf_toolbox")
logger.propagate = False

ERR_INVALID_PAGE_SPEC = "Invalid page specification"
ERR_PAGE_RANGE = "page {start}-{end} out of range 1..{total}"
ERR_END_GTE_START = "end must be greater than or equal to start"
ERR_PAGE_OUT_OF_RANGE = "page {page} out of range 1..{total}"
ERR_OUTPUT_DIR_FILE = "Output directory must be a directory, not a file: {out_dir}"
ERR_OPEN_PDF = "Could not open PDF file: {path}"
ERR_SAVE_PDF = "Could not save PDF file: {out_path}"
ERR_MISSING_LIBS = "Missing required libraries: {libs}"
ERR_CANCELLED = "cancelled"


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


@lru_cache(maxsize=1)
def _load_author_info() -> tuple[str, str]:
    """Return configured author information with caching."""
    try:
        data = json.loads(CONFIG_FILE.read_text())
        validate_config(data)
        return data.get("author", ""), data.get("email", "")
    except Exception:
        return "", ""


def ensure_libs() -> None:
    """Ensure optional runtime libraries are importable.

    Raises a ``RuntimeError`` if a library is missing so callers can
    present a helpful message to the user.
    """
    missing: list[str] = []
    for mod in REQUIRED_LIBS:
        try:
            importlib.import_module(mod)
        except Exception:
            missing.append(mod)
    if missing:
        parts = []
        for mod in missing:
            hint = LIB_HINTS.get(mod, "see documentation")
            parts.append(f"{mod} ({hint})")
        raise RuntimeError(ERR_MISSING_LIBS.format(libs=", ".join(parts)))


def parse_page_spec(spec: str | None, total: int) -> list[int]:
    """Parse a page/slide specification into a list of 1-based numbers.

    ``spec`` follows a simple syntax with comma-separated parts. Each part may
    be a single number (``"5"`` or ``"n"`` for the last page), a range like
    ``"3-7"``, an open-ended range such as ``"2-"`` or ``"-4"``, or any
    combination thereof (e.g. ``"1,5,6"`` or ``"8-n"``). ``None`` or an empty
    string selects all pages.

    A ``ValueError`` is raised if the specification is invalid or references
    pages outside ``1..total``.
    """
    if not spec:
        return list(range(1, total + 1))

    pages: set[int] = set()

    def _resolve(token: str, default: int | None) -> int:
        if not token:
            if default is None:
                raise ValueError(ERR_INVALID_PAGE_SPEC)
            return default
        if token.lower() == "n":
            return total
        try:
            return int(token)
        except ValueError as exc:
            raise ValueError(ERR_INVALID_PAGE_SPEC) from exc

    for raw_part in spec.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start = _resolve(start_s, 1)
            end = _resolve(end_s, total)
            if start < 1 or end > total:
                raise ValueError(
                    ERR_PAGE_RANGE.format(start=start, end=end, total=total)
                )
            if end < start:
                raise ValueError(ERR_END_GTE_START)
            pages.update(range(start, end + 1))
        else:
            page = _resolve(part, None)
            if page < 1 or page > total:
                raise ValueError(ERR_PAGE_OUT_OF_RANGE.format(page=page, total=total))
            pages.add(page)
    return sorted(pages)


def sane_output_dir(base_path: str | Path, out_dir: str | Path | None) -> Path:
    """Return a Path for output files.

    If ``out_dir`` is ``None`` the directory of ``base_path`` is returned.
    The directory is created if it does not yet exist.
    """
    base = Path(base_path)
    target = Path(out_dir) if out_dir else base.parent
    target = validate_path(target)
    if target.suffix:
        raise ValueError(ERR_OUTPUT_DIR_FILE.format(out_dir=out_dir))
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


def raise_if_cancelled(cancel: Event | None, doc: fitz.Document | None = None) -> None:
    """Raise ``RuntimeError('cancelled')`` if ``cancel`` is set.

    If ``doc`` is provided it will be closed before raising to free
    resources.
    """
    if cancel and cancel.is_set():
        if doc is not None:
            doc.close()
        raise RuntimeError(ERR_CANCELLED)


def open_pdf(path: str | Path) -> fitz.Document:
    """Open ``path`` as a PDF document with friendly errors."""
    try:
        safe = validate_path(path, must_exist=True)
    except PathValidationError as exc:
        raise RuntimeError(ERR_OPEN_PDF.format(path=path)) from exc
    try:
        return fitz.open(str(safe))
    except Exception as exc:
        raise RuntimeError(ERR_OPEN_PDF.format(path=path)) from exc


def save_pdf(
    doc: fitz.Document,
    out_path: str | Path,
    *,
    note: str | None = None,
    **save_kwargs,
) -> None:
    """Save ``doc`` to ``out_path`` updating metadata and closing it."""
    update_metadata(doc, note)
    safe_out = validate_path(out_path)
    try:
        doc.save(str(safe_out), **save_kwargs)
    except Exception as exc:
        raise RuntimeError(ERR_SAVE_PDF.format(out_path=out_path)) from exc
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
