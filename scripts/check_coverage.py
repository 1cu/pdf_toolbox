#!/usr/bin/env python3
"""Check per-file coverage thresholds."""

from __future__ import annotations

import tomllib
from fnmatch import fnmatch
from pathlib import Path

from coverage import Coverage
from coverage.exceptions import NoSource

from pdf_toolbox.utils import logger as _project_logger

logger = _project_logger.getChild("scripts.check_coverage")


def load_settings() -> tuple[float, list[str]]:
    """Load coverage threshold and omit patterns from ``pyproject.toml``."""
    with Path("pyproject.toml").open("rb") as f:
        data = tomllib.load(f)
    tool_cfg = data.get("tool", {})
    cov_cfg = tool_cfg.get("coverage", {})
    report_cfg = cov_cfg.get("report", {})
    run_cfg = cov_cfg.get("run", {})
    threshold = float(report_cfg.get("fail_under", 0)) / 100.0
    report_omit = [str(p) for p in report_cfg.get("omit", [])]
    run_omit = [str(p) for p in run_cfg.get("omit", [])]
    # Preserve order, remove duplicates
    omit = list(dict.fromkeys([*report_omit, *run_omit]))
    if threshold <= 0:
        logger.error("coverage:report:fail_under must be > 0 in pyproject.toml")
        raise SystemExit(1)
    return threshold, omit


def main() -> int:
    """Return 0 on success, 1 if coverage falls below thresholds."""
    threshold, omit_patterns = load_settings()
    coverage = Coverage()
    data_file_option = coverage.get_option("run:data_file")
    data_file_name = str(data_file_option) if data_file_option else ".coverage"
    data_file = Path(data_file_name)
    data_dir = data_file.parent if str(data_file.parent) else Path.cwd()
    search_dir = data_dir if data_dir.is_absolute() else Path.cwd() / data_dir
    if not any(search_dir.glob(data_file.name + "*")):
        logger.error("%s* not found. Run tests first.", data_file)
        return 1
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
            logger.debug("Skipping %s because the source is unavailable", filename)
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

    if failures:
        for fn, rate in failures:
            logger.error(
                "%s has %.2f%% coverage, below %.0f%%", fn, rate * 100, threshold * 100
            )
    had_failures = bool(failures)
    if total_statements == 0:
        logger.error("No statements were measured; ensure tests ran with coverage.")
        had_failures = True
    else:
        total_rate = total_covered / total_statements
        if total_rate < threshold:
            logger.error(
                "Total coverage %.2f%% is below %.0f%%",
                total_rate * 100,
                threshold * 100,
            )
            had_failures = True
    return 1 if had_failures else 0


def _as_posix_relative(path: Path) -> str:
    """Return ``path`` relative to the repository root in POSIX form."""
    try:
        repo_root = Path.cwd().resolve()
        relative = path.resolve().relative_to(repo_root)
    except ValueError:
        relative = path
    return relative.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
