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
    en = _load_locale(root, "en")
    de = _load_locale(root, "de")

    # same keys in en/de
    for grp in ("strings", "labels"):
        assert set(en[grp].keys()) == set(de[grp].keys())

    ref_strings, ref_labels = _scan_referenced_keys(root)
    # exact sets for strings: no obsolete, no missing
    assert set(en["strings"]) == ref_strings
    # labels are dynamic; ensure parity between locales only
    assert set(en["labels"]) == set(de["labels"])  # not compared to ref_labels
