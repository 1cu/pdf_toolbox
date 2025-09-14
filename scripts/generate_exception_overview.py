#!/usr/bin/env python3
"""Generate a table of linter and coverage exceptions."""

from __future__ import annotations

import re
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_FILE = ROOT / "DEVELOPMENT_EXCEPTIONS.md"

ISSUE_SPLIT = re.compile(r"\s*\|\s*issue:")
NOQA_RE = re.compile(r"# noqa: (?P<codes>[A-Z0-9_, ]+)")
TYPE_IGNORE_RE = re.compile(r"# type: ignore(?P<brack>\[[^\]]+\])?")
NOSEC_RE = re.compile(r"# nosec\s+(?P<codes>[A-Z0-9, ]+)")
PRAGMA_NOCOVER_RE = re.compile(r"# pragma: no cover")


def gather() -> list[tuple[str, str, str, str]]:
    """Return records of (file, rule, reason, issue)."""
    records: list[tuple[str, str, str, str]] = []
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT).as_posix()
        with tokenize.open(path) as fh:
            for tok_type, tok_string, (lineno, _), _, line in tokenize.generate_tokens(
                fh.readline
            ):
                if tok_type != tokenize.COMMENT or "pdf-toolbox:" not in tok_string:
                    continue
                reason_issue = tok_string.split("pdf-toolbox:", 1)[1].strip()
                reason, issue = (
                    ISSUE_SPLIT.split(reason_issue)
                    if "|" in reason_issue
                    else (reason_issue, "-")
                )
                issue = issue.split("#", 1)[0].strip()
                codes: list[str] = []
                if m := NOQA_RE.search(line):
                    codes.extend(c.strip() for c in m.group("codes").split(","))
                if m := TYPE_IGNORE_RE.search(line):
                    codes.append("type: ignore" + (m.group("brack") or ""))
                if m := NOSEC_RE.search(line):
                    codes.extend(c.strip() for c in m.group("codes").split(","))
                if PRAGMA_NOCOVER_RE.search(line):
                    codes.append("pragma: no cover")
                records.append(
                    (f"{rel}:{lineno}", ", ".join(codes), reason.strip(), issue.strip())
                )

    def sort_key(rec: tuple[str, str, str, str]) -> tuple[str, int]:
        path, line = rec[0].rsplit(":", 1)
        return path, int(line)

    return sorted(records, key=sort_key)


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
    """Write the current exception table to ``DEVELOPMENT_EXCEPTIONS.md``."""
    rows = gather()
    table = render_table(rows)
    content = "# Documented Exceptions\n\n" + table + "\n"
    existing = OUT_FILE.read_text(encoding="utf8") if OUT_FILE.exists() else ""
    if content == existing:
        return 0
    OUT_FILE.write_text(content, encoding="utf8")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
