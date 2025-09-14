from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _load_locale(root: Path, lang: str) -> dict:
    path = root / "src" / "pdf_toolbox" / "locales" / f"{lang}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _scan_referenced_keys(root: Path) -> tuple[set[str], set[str]]:
    src = root / "src"
    tr_re = re.compile(r"\btr\(\"([a-z0-9_]+)\"")
    lab_re = re.compile(r"\blabel\(\"([a-z0-9_]+)\"\)")
    strings: set[str] = set()
    labels: set[str] = set()
    for file_path in src.rglob("*.py"):
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        strings.update(tr_re.findall(text))
        labels.update(lab_re.findall(text))
    from pdf_toolbox import actions as actions_mod

    actions_mod._registry.clear()
    actions_mod._auto_discover.cache_clear()
    for name in list(sys.modules):
        if name.startswith("pdf_toolbox.builtin"):
            sys.modules.pop(name)
    sys.path.insert(0, str(src))
    try:
        for act in actions_mod.list_actions():
            strings.add(act.key)
    finally:
        sys.path.remove(str(src))
    return strings, labels


def test_locales_complete_and_consistent():
    root = Path(__file__).resolve().parents[1]
    locales_dir = root / "src" / "pdf_toolbox" / "locales"
    locales = {p.stem: _load_locale(root, p.stem) for p in locales_dir.glob("*.json")}
    assert locales, "no locales found"

    first = next(iter(locales.values()))
    for group in ("strings", "labels"):
        base = set(first[group].keys())
        for data in locales.values():
            assert set(data[group].keys()) == base

    ref_strings, _ = _scan_referenced_keys(root)
    assert set(first["strings"].keys()) == ref_strings
