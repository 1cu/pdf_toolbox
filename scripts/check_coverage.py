#!/usr/bin/env python3
"""Check per-file coverage thresholds."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from coverage import Coverage
from coverage.exceptions import NoSource

from pdf_toolbox.utils import logger as _project_logger

logger = _project_logger.getChild("scripts.check_coverage")


@dataclass
class _FileCoverage:
    path: str
    statements: int
    covered: int

    @property
    def rate(self) -> float:
        return self.covered / self.statements


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
    search_dir, data_file_name = _coverage_search_location(coverage)
    data_path = search_dir / data_file_name
    if not _has_coverage_files(search_dir, data_file_name):
        logger.error("%s* not found. Run tests first.", data_path)
        return 1

    coverage.load()
    file_stats = _collect_file_stats(coverage, omit_patterns)
    if not file_stats:
        logger.error("No statements were measured; ensure tests ran with coverage.")
        return 1

    failures = [(stat.path, stat.rate) for stat in file_stats if stat.rate < threshold]
    for filename, rate in failures:
        logger.error("%s has %.2f%% coverage, below %.0f%%", filename, rate * 100, threshold * 100)

    total_rate = _overall_rate(file_stats)
    if total_rate < threshold:
        logger.error(
            "Total coverage %.2f%% is below %.0f%%",
            total_rate * 100,
            threshold * 100,
        )

    return 0 if not failures and total_rate >= threshold else 1


def _coverage_search_location(coverage: Coverage) -> tuple[Path, str]:
    """Return the directory and filename base for coverage data files."""
    data_file_option = coverage.get_option("run:data_file")
    data_file_name = str(data_file_option) if data_file_option else ".coverage"
    data_file = Path(data_file_name)
    directory = data_file.parent if str(data_file.parent) else Path.cwd()
    search_dir = directory if directory.is_absolute() else Path.cwd() / directory
    return search_dir, data_file.name


def _has_coverage_files(directory: Path, filename: str) -> bool:
    """Return whether coverage data files for ``filename`` exist in ``directory``."""
    return any(directory.glob(f"{filename}*"))


def _collect_file_stats(coverage: Coverage, omit_patterns: list[str]) -> list[_FileCoverage]:
    """Return per-file coverage statistics excluding patterns in ``omit_patterns``."""
    data = coverage.get_data()
    stats: list[_FileCoverage] = []
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
        covered = statement_count - len(missing)
        stats.append(_FileCoverage(rel_path, statement_count, covered))
    return stats


def _overall_rate(stats: list[_FileCoverage]) -> float:
    """Return the overall coverage rate from ``stats``."""
    total_statements = sum(entry.statements for entry in stats)
    if total_statements == 0:
        return 0.0
    total_covered = sum(entry.covered for entry in stats)
    return total_covered / total_statements


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
