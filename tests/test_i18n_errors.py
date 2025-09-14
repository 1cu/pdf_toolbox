from pdf_toolbox import i18n


def test_autodetect_handles_locale_errors(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(i18n.locale, "getlocale", boom)
    monkeypatch.setattr(i18n.locale, "getdefaultlocale", boom)
    assert i18n.autodetect() == "en"


def test_load_handles_json_errors(monkeypatch):
    def bad_load(*_args, **_kwargs):
        raise ValueError("bad")

    monkeypatch.setattr(i18n.json, "loads", bad_load)
    i18n._CACHE.clear()
    try:
        assert i18n._load("en") == {"strings": {}, "labels": {}}
    finally:
        i18n._CACHE.clear()


def test_tr_format_error():
    i18n.set_language("en")
    try:
        assert (
            i18n.tr("Field '{name}' cannot be empty.")
            == "Field '{name}' cannot be empty."
        )
    finally:
        i18n.set_language("en")
