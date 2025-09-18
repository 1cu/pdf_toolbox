"""JSON-backed i18n helper for English and German.

Loads translations from ``pdf_toolbox/locales/<lang>.json``. Supports two maps:

- ``strings``: general UI strings
- ``labels``: field/parameter label overrides

Use ``tr(key)`` for UI strings and ``label(name)`` to resolve parameter labels.

Missing translations fall back to the English default so adding a new key only
requires translating it once to keep the interface usable.
"""

from __future__ import annotations

import json
import locale
from contextlib import suppress
from importlib import resources
from typing import Any

_LC_MESSAGES: int = getattr(locale, "LC_MESSAGES", locale.LC_CTYPE)

_DEFAULT_LANGUAGE = "en"
_SECTIONS: tuple[str, ...] = ("strings", "labels")

_CACHE: dict[str, dict[str, dict[str, str]]] = {}
_STATE: dict[str, str] = {"lang": _DEFAULT_LANGUAGE}


def _coerce_section(data: Any) -> dict[str, str]:
    """Return a mapping of string keys to string values."""
    if not isinstance(data, dict):
        return {}
    return {
        str(key): value
        for key, value in data.items()
        if isinstance(key, str) and isinstance(value, str)
    }


def set_language(lang: str | None) -> None:
    """Set current UI language to 'en', 'de', or system default."""
    if not lang:
        _STATE["lang"] = autodetect()
        return
    low = lang.lower()
    if low.startswith("de"):
        _STATE["lang"] = "de"
        return
    if low.startswith("en"):
        _STATE["lang"] = "en"
        return
    if low == "system":
        _STATE["lang"] = autodetect()
        return
    _STATE["lang"] = autodetect()


def _current_language() -> str:
    """Return the active language code."""
    lang = _STATE.get("lang")
    if not lang:
        return autodetect()
    return lang


def autodetect() -> str:
    """Return language code inferred from the OS locale."""
    lang = ""
    with suppress(Exception):
        lang = (locale.getlocale(_LC_MESSAGES)[0] or "").lower()
    if not lang:
        with suppress(Exception):
            lang = (locale.getdefaultlocale()[0] or "").lower()
    if isinstance(lang, str) and lang.startswith("de"):
        return "de"
    return "en"


def _load(lang: str) -> dict[str, dict[str, str]]:
    if lang in _CACHE:
        return _CACHE[lang]
    filename = f"{lang}.json"
    try:
        raw = json.loads(
            resources.files("pdf_toolbox.locales")
            .joinpath(filename)
            .read_text(encoding="utf-8")
        )
    except Exception:
        raw = {}
    data = {section: _coerce_section(raw.get(section)) for section in _SECTIONS}
    _CACHE[lang] = data
    return data


def _lookup(section: str, key: str, default: str) -> str:
    lang = _current_language()
    data = _load(lang).get(section, {})
    text = data.get(key)
    if text is None and lang != _DEFAULT_LANGUAGE:
        text = _load(_DEFAULT_LANGUAGE).get(section, {}).get(key)
    return text if text is not None else default


def tr(key: str, **kwargs: Any) -> str:
    """Translate a UI string by key using current language."""
    s = _lookup("strings", key, key)
    try:
        return s.format(**kwargs)
    except Exception:
        return s


def label(name: str) -> str:
    """Translate a parameter/field label by its canonical name."""
    return _lookup("labels", name, name)


__all__ = ["autodetect", "label", "set_language", "tr"]
