#!/usr/bin/env python3
from __future__ import annotations

from fnmatch import fnmatch
import sys
from pathlib import Path
import tomllib
import xml.etree.ElementTree as ET


def load_settings() -> tuple[float, list[str]]:
    """Load coverage threshold and omit patterns from ``pyproject.toml``."""
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    tool_cfg = data.get("tool", {})
    cov_cfg = tool_cfg.get("coverage", {})
    report_cfg = cov_cfg.get("report", {})
    run_cfg = cov_cfg.get("run", {})
    threshold = float(report_cfg.get("fail_under", 0)) / 100.0
    omit = [str(p) for p in run_cfg.get("omit", [])]
    if threshold <= 0:
        print("fail_under not configured in pyproject.toml", file=sys.stderr)
        raise SystemExit(1)
    return threshold, omit


def main() -> int:
    xml_file = Path("coverage.xml")
    if not xml_file.exists():
        print("coverage.xml not found. Run tests first.", file=sys.stderr)
        return 1

    threshold, omit_patterns = load_settings()
    tree = ET.parse(xml_file)
    root = tree.getroot()

    total_rate = float(root.get("line-rate", "0"))
    failures: list[tuple[str, float]] = []
    for cls in root.findall(".//class"):
        filename = cls.get("filename")
        if not filename:
            continue
        if any(fnmatch(filename, pat) for pat in omit_patterns):
            continue
        rate = float(cls.get("line-rate", "0"))
        if rate < threshold:
            failures.append((filename, rate))

    if total_rate < threshold:
        print(
            f"Total coverage {total_rate * 100:.2f}% is below {threshold * 100:.0f}%",
            file=sys.stderr,
        )
        return 1
    if failures:
        for fn, rate in failures:
            print(f"{fn} has {rate * 100:.2f}% coverage, below {threshold * 100:.0f}%")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
