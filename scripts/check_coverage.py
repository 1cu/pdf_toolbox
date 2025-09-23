#!/usr/bin/env python3
"""Check per-file coverage thresholds."""

from __future__ import annotations

import logging
import tomllib
from fnmatch import fnmatch
from pathlib import Path

from coverage import Coverage
from coverage.exceptions import NoSource


def load_settings() -> tuple[float, list[str]]:
    """Load coverage threshold and omit patterns from ``pyproject.toml``."""
    with Path("pyproject.toml").open("rb") as f:
        data = tomllib.load(f)
    tool_cfg = data.get("tool", {})
    cov_cfg = tool_cfg.get("coverage", {})
    report_cfg = cov_cfg.get("report", {})
    run_cfg = cov_cfg.get("run", {})
    threshold = float(report_cfg.get("fail_under", 0)) / 100.0
    omit = [str(p) for p in run_cfg.get("omit", [])]
    if threshold <= 0:
        logging.error("fail_under not configured in pyproject.toml")
        raise SystemExit(1)
    return threshold, omit


def main() -> int:
    """Return 0 on success, 1 if coverage falls below thresholds."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    data_file = Path(".coverage")
    if not data_file.exists():
        logging.error(".coverage not found. Run tests first.")
        return 1

    threshold, omit_patterns = load_settings()
    coverage = Coverage(data_file=str(data_file))
    coverage.load()
    data = coverage.get_data()

    total_statements = 0
    total_covered = 0
    failures: list[tuple[str, float]] = []

    for filename in data.measured_files():
        rel_path = _as_posix_relative(Path(filename))
        if any(fnmatch(rel_path, pat) for pat in omit_patterns):
            continue

        try:
            _, statements, _, missing, _ = coverage.analysis2(filename)
        except NoSource:
            logging.debug("Skipping %s because the source is unavailable", filename)
            continue

        statement_count = len(statements)
        if statement_count == 0:
            continue

        missing_count = len(missing)
        covered = statement_count - missing_count
        rate = covered / statement_count

        total_statements += statement_count
        total_covered += covered

        if rate < threshold:
            failures.append((rel_path, rate))

    total_rate = (total_covered / total_statements) if total_statements else 1.0
    if total_rate < threshold:
        logging.error(
            "Total coverage %.2f%% is below %.0f%%",
            total_rate * 100,
            threshold * 100,
        )
        return 1
    if failures:
        for fn, rate in failures:
            logging.error(
                "%s has %.2f%% coverage, below %.0f%%", fn, rate * 100, threshold * 100
            )
        return 1
    return 0


def _as_posix_relative(path: Path) -> str:
    """Return ``path`` relative to the repository root in POSIX form."""
    try:
        relative = path.resolve().relative_to(Path.cwd())
    except ValueError:
        relative = path
    return relative.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
