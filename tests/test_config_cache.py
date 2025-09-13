from __future__ import annotations

import json

from pdf_toolbox import utils


def test_load_author_info_valid(tmp_path, monkeypatch):
    cfg = tmp_path / "pdf_toolbox_config.json"
    cfg.write_text(json.dumps({"author": "Alice", "email": "a@example.com"}))
    monkeypatch.setattr(utils, "CONFIG_FILE", cfg)
    utils._AUTHOR_INFO = None
    assert utils._load_author_info() == ("Alice", "a@example.com")
    cfg.write_text("{}")
    assert utils._load_author_info() == ("Alice", "a@example.com")


def test_load_author_info_missing(tmp_path, monkeypatch):
    cfg = tmp_path / "missing.json"
    monkeypatch.setattr(utils, "CONFIG_FILE", cfg)
    utils._AUTHOR_INFO = None
    assert utils._load_author_info() == ("", "")


def test_load_author_info_invalid(tmp_path, monkeypatch):
    cfg = tmp_path / "pdf_toolbox_config.json"
    cfg.write_text("{not json}")
    monkeypatch.setattr(utils, "CONFIG_FILE", cfg)
    utils._AUTHOR_INFO = None
    assert utils._load_author_info() == ("", "")
