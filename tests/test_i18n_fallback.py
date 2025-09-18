from __future__ import annotations

from pdf_toolbox import i18n


def test_unknown_language_falls_back(monkeypatch):
    monkeypatch.setattr(i18n, "autodetect", lambda: "en")
    i18n.set_language("es_ES")
    try:
        assert i18n.tr("about") == "About"
    finally:
        i18n.set_language("en")


def test_missing_translation_uses_default_language():
    i18n._CACHE.clear()
    i18n.set_language("de")
    try:
        i18n._CACHE["de"] = {"strings": {}, "labels": {}}
        assert i18n.tr("start") == "Start"
    finally:
        i18n._CACHE.clear()
        i18n.set_language("en")


def test_missing_label_uses_default_language():
    i18n._CACHE.clear()
    i18n.set_language("de")
    try:
        i18n._CACHE["de"] = {"strings": {}, "labels": {}}
        assert i18n.label("output_dir") == "Output Directory"
    finally:
        i18n._CACHE.clear()
        i18n.set_language("en")
