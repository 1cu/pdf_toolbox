from __future__ import annotations

import json
import re
from pathlib import Path


def _load_locale(root: Path, lang: str) -> dict:
    p = root / "src" / "pdf_toolbox" / "locales" / f"{lang}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _scan_referenced_keys(root: Path) -> tuple[set[str], set[str]]:
    src = root / "src"
    tr_re = re.compile(r"\btr\(\"([a-z0-9_]+)\"")
    lab_re = re.compile(r"\blabel\(\"([a-z0-9_]+)\"\)")
    strings: set[str] = set()
    labels: set[str] = set()
    for path in src.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        strings.update(tr_re.findall(text))
        labels.update(lab_re.findall(text))
    return strings, labels


def test_locales_complete_and_consistent():
    root = Path(__file__).resolve().parents[1]
    locales_dir = root / "src" / "pdf_toolbox" / "locales"
    locales = {p.stem: _load_locale(root, p.stem) for p in locales_dir.glob("*.json")}
    assert locales, "no locales found"

    first = next(iter(locales.values()))
    for grp in ("strings", "labels"):
        base = set(first[grp].keys())
        for data in locales.values():
            assert set(data[grp].keys()) == base

    ref_strings, _ = _scan_referenced_keys(root)
    assert set(first["strings"].keys()) == ref_strings
