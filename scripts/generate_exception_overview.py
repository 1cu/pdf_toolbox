#!/usr/bin/env python3
"""Generate a table of linter and coverage exceptions."""

from __future__ import annotations

import re
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_FILE = ROOT / "DEVELOPMENT_EXCEPTIONS.md"

ISSUE_SPLIT = re.compile(r"\s*\|\s*issue:")
NOQA_RE = re.compile(r"# noqa: (?P<codes>[A-Z0-9_, ]+)")
TYPE_IGNORE_RE = re.compile(r"# type: ignore(?P<brack>\[[^\]]+\])?")
NOSEC_RE = re.compile(r"# nosec\s+(?P<codes>[A-Z0-9, ]+)")
PRAGMA_NOCOVER_RE = re.compile(r"# pragma: no cover")


def gather() -> tuple[list[tuple[str, str, str, str]], list[str]]:  # noqa: PLR0912  # pdf-toolbox: parsing requires several branches | issue:-
    """Return exception records and a list of validation errors."""
    records: list[tuple[str, str, str, str]] = []
    errors: list[str] = []
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT).as_posix()
        with tokenize.open(path) as fh:
            for tok_type, tok_string, (lineno, _), _, _ in tokenize.generate_tokens(
                fh.readline
            ):
                if tok_type != tokenize.COMMENT:
                    continue
                comment = tok_string
                codes: list[str] = []
                if m := NOQA_RE.search(comment):
                    codes.extend(c.strip() for c in m.group("codes").split(","))
                if m := TYPE_IGNORE_RE.search(comment):
                    codes.append("type: ignore" + (m.group("brack") or ""))
                if m := NOSEC_RE.search(comment):
                    codes.extend(c.strip() for c in m.group("codes").split(","))
                if PRAGMA_NOCOVER_RE.search(comment):
                    codes.append("pragma: no cover")
                has_pdf = "pdf-toolbox:" in comment
                if codes and not has_pdf:
                    errors.append(
                        f"{rel}:{lineno}: missing '# pdf-toolbox: <reason> | issue:<id>'"
                    )
                    continue
                if has_pdf and not codes:
                    errors.append(f"{rel}:{lineno}: pdf-toolbox comment without marker")
                    continue
                if not codes and not has_pdf:
                    continue
                reason_issue = comment.split("pdf-toolbox:", 1)[1]
                if "| issue:" not in reason_issue:
                    errors.append(f"{rel}:{lineno}: missing '| issue:'")
                    continue
                reason, issue = reason_issue.split("| issue:", 1)
                reason = reason.strip()
                issue = issue.split("#", 1)[0].strip()
                if not reason:
                    errors.append(f"{rel}:{lineno}: empty reason")
                if not issue:
                    errors.append(f"{rel}:{lineno}: empty issue")
                records.append((f"{rel}:{lineno}", ", ".join(codes), reason, issue))

    def sort_key(rec: tuple[str, str, str, str]) -> tuple[str, int]:
        path, line = rec[0].rsplit(":", 1)
        return path, int(line)

    return sorted(records, key=sort_key), errors


def render_table(rows: list[tuple[str, str, str, str]]) -> str:
    """Return a Markdown table for *rows* with padded columns."""
    headers = ["File", "Rule", "Reason", "Issue/PR"]
    matrix = [headers] + [list(r) for r in rows]
    widths = [max(len(row[i]) for row in matrix) for i in range(4)]

    def fmt(row: list[str]) -> str:
        return (
            "| "
            + " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))
            + " |"
        )

    lines = [fmt(headers), "| " + " | ".join("-" * widths[i] for i in range(4)) + " |"]
    if not rows:
        lines.append(fmt(["*(none yet)*", "-", "-", "-"]))
    else:
        for row in rows:
            lines.append(fmt(list(row)))
    return "\n".join(lines)


def main() -> int:
    """Write the current exception table and validate comment format."""
    rows, errors = gather()
    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        return 1
    table = render_table(rows)
    content = "# Documented Exceptions\n\n" + table + "\n"
    existing = OUT_FILE.read_text(encoding="utf8") if OUT_FILE.exists() else ""
    if content == existing:
        return 0
    OUT_FILE.write_text(content, encoding="utf8")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
