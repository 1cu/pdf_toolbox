#!/usr/bin/env python3
"""Check per-file coverage thresholds."""

from __future__ import annotations

import logging
import tomllib
import xml.etree.ElementTree as ET  # nosec B405
from fnmatch import fnmatch
from pathlib import Path


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
    xml_file = Path("coverage.xml")
    if not xml_file.exists():
        logging.error("coverage.xml not found. Run tests first.")
        return 1

    threshold, omit_patterns = load_settings()
    tree = ET.parse(xml_file)  # nosec B314
    root = tree.getroot()

    total_rate = float(root.get("line-rate", "0"))
    failures: list[tuple[str, float]] = []
    for cls in root.findall(".//class"):
        filename = cls.get("filename")
        if not filename:
            continue
        filename = Path(filename).as_posix()
        if any(fnmatch(filename, pat) for pat in omit_patterns):
            continue
        rate = float(cls.get("line-rate", "0"))
        if rate < threshold:
            failures.append((filename, rate))

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


if __name__ == "__main__":
    raise SystemExit(main())
