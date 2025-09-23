#!/usr/bin/env python3
"""Generate a table of linter and coverage exceptions."""

from __future__ import annotations

import logging
import re
import tokenize
from collections.abc import Iterator
from pathlib import Path
from typing import NotRequired, TypedDict

import mdformat

ROOT = Path(__file__).resolve().parent.parent
OUT_FILE = ROOT / "DEVELOPMENT_EXCEPTIONS.md"

SEARCH_DIRS = [ROOT / "src", ROOT / "scripts", ROOT / "tests"]


class RuntimeExceptionEntry(TypedDict):
    """Metadata describing a documented runtime exception."""

    exception: str
    message_key: str
    locales: list[tuple[str, str]]
    docs: str
    docs_label: NotRequired[str]


RUNTIME_EXCEPTIONS: list[RuntimeExceptionEntry] = [
    {
        "exception": "pdf_toolbox.renderers.pptx.PptxProviderUnavailableError",
        "message_key": "pptx.no_provider",
        "locales": [
            ("en", "src/pdf_toolbox/locales/en.json"),
            ("de", "src/pdf_toolbox/locales/de.json"),
        ],
        "docs": (
            "https://github.com/1cu/pdf_toolbox/blob/main/README.md#select-a-pptx-"
            "renderer"
        ),
        "docs_label": "PPTX_PROVIDER_DOCS_URL",
    }
]

BARE_NOQA_RE = re.compile(r"#\s*noqa\b(?!:)")
NOQA_RE = re.compile(r"# noqa:\s*(?P<codes>[A-Z0-9_, ]+)")
NOQA_EMPTY_RE = re.compile(r"#\s*noqa\s*:\s*(?=$|#)")
TYPE_IGNORE_RE = re.compile(r"# type: ignore(?P<brack>\[[^\]]+\])?")
NOSEC_RE = re.compile(r"# nosec\s+(?P<codes>[A-Z0-9, ]+)")
PRAGMA_NOCOVER_RE = re.compile(r"# pragma: no cover")


def gather() -> tuple[list[tuple[str, str, str, str]], list[str]]:
    """Return exception records and a list of validation errors."""
    records: list[tuple[str, str, str, str]] = []
    errors: list[str] = []
    for base in SEARCH_DIRS:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            for lineno, comment in _iter_comments(path):
                record, comment_errors = _parse_exception_comment(rel, lineno, comment)
                errors.extend(comment_errors)
                if record:
                    records.append(record)

    return sorted(records, key=_sort_key), sorted(errors)


def _iter_comments(path: Path) -> Iterator[tuple[int, str]]:
    """Yield ``(lineno, comment)`` pairs from *path*."""
    with tokenize.open(path) as fh:
        for tok_type, tok_string, (lineno, _), _, _ in tokenize.generate_tokens(
            fh.readline
        ):
            if tok_type == tokenize.COMMENT:
                yield lineno, tok_string


def _parse_exception_comment(
    rel: str, lineno: int, comment: str
) -> tuple[tuple[str, str, str, str] | None, list[str]]:
    """Parse a single comment and return a record with validation errors."""
    errors: list[str] = []
    if message := _noqa_format_error(comment):
        errors.append(f"{rel}:{lineno}: {message}")
        return None, errors
    codes = _collect_codes(comment)
    has_pdf = "pdf-toolbox:" in comment
    if codes and not has_pdf:
        errors.append(f"{rel}:{lineno}: missing '# pdf-toolbox: <reason> | issue:<id>'")
        return None, errors
    if has_pdf and not codes:
        errors.append(
            f"{rel}:{lineno}: pdf-toolbox comment without disable marker (# noqa/# type: ignore/# nosec/# pragma: no cover)"
        )
        return None, errors
    if not codes:
        return None, errors

    reason_issue = comment.split("pdf-toolbox:", 1)[1]
    if "| issue:" not in reason_issue:
        errors.append(f"{rel}:{lineno}: missing '| issue:'")
        return None, errors

    reason, issue = reason_issue.split("| issue:", 1)
    reason = reason.strip()
    issue = issue.split(" # ", 1)[0].strip()
    issue = issue.lstrip("#").strip()
    if not reason:
        errors.append(f"{rel}:{lineno}: empty reason")
    if not issue:
        errors.append(f"{rel}:{lineno}: empty issue")

    record = (f"{rel}:{lineno}", ", ".join(codes), reason, issue)
    return record, errors


def _collect_codes(comment: str) -> list[str]:
    """Extract all disable codes from *comment*."""
    codes: list[str] = []
    if m := NOQA_RE.search(comment):
        codes.extend(c.strip() for c in m.group("codes").split(","))
    if m := TYPE_IGNORE_RE.search(comment):
        codes.append("type: ignore" + (m.group("brack") or ""))
    if m := NOSEC_RE.search(comment):
        codes.extend(c.strip() for c in m.group("codes").split(","))
    if PRAGMA_NOCOVER_RE.search(comment):
        codes.append("pragma: no cover")
    return sorted(dict.fromkeys(codes))


def _noqa_format_error(comment: str) -> str | None:
    """Return an error message for invalid ``# noqa`` usage."""
    if BARE_NOQA_RE.search(comment):
        return "bare '# noqa' is not allowed; specify explicit codes"
    if NOQA_EMPTY_RE.search(comment):
        return "empty '# noqa:' marker; specify explicit codes (e.g., '# noqa: S506')"
    return None


def _sort_key(rec: tuple[str, str, str, str]) -> tuple[str, int]:
    """Return a stable sort key for exception records."""
    path, line = rec[0].rsplit(":", 1)
    return path, int(line)


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    """Return a Markdown table for *rows* with padded columns."""
    matrix = [headers, *rows]
    escaped_matrix = [[cell.replace("_", "\\_") for cell in row] for row in matrix]
    widths = [max(len(row[i]) for row in escaped_matrix) for i in range(len(headers))]

    def fmt(row: list[str]) -> str:
        escaped = [cell.replace("_", "\\_") for cell in row]
        return (
            "| "
            + " | ".join(escaped[i].ljust(widths[i]) for i in range(len(row)))
            + " |"
        )

    lines = [
        fmt(headers),
        "| " + " | ".join("-" * widths[i] for i in range(len(headers))) + " |",
    ]
    if not rows:
        lines.append(fmt(["*(none yet)*"] + ["-" for _ in headers[1:]]))
    else:
        for row in rows:
            lines.append(fmt(list(row)))
    return "\n".join(lines)


def main() -> int:
    """Write the current exception table and validate comment format."""
    rows, errors = gather()
    if errors:
        logging.error("\n".join(errors))
        return 1
    lint_table = render_table(
        ["File", "Rule", "Reason", "Issue/PR"], [list(r) for r in rows]
    )
    runtime_rows: list[list[str]] = []
    for entry in RUNTIME_EXCEPTIONS:
        locales = ", ".join(f"[{code}]({path})" for code, path in entry["locales"])
        doc_label = entry.get("docs_label", "Documentation")
        runtime_rows.append(
            [
                entry["exception"],
                entry["message_key"],
                locales,
                f"[{doc_label}]({entry['docs']})",
            ]
        )
    runtime_table = render_table(
        ["Exception", "Message key", "Locales", "Docs"],
        runtime_rows,
    )
    content = (
        "# Documented Exceptions\n\n"
        "<!-- mdformat off -->\n\n" + lint_table + "\n<!-- mdformat on -->\n\n"
        "## Runtime Exceptions\n\n"
        "<!-- mdformat off -->\n\n" + runtime_table + "\n<!-- mdformat on -->\n"
    )
    content = mdformat.text(content, extensions={"gfm"})
    existing = OUT_FILE.read_text(encoding="utf8") if OUT_FILE.exists() else ""
    if content == existing:
        return 0
    OUT_FILE.write_text(content, encoding="utf8")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
