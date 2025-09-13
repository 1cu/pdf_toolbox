from __future__ import annotations

import pytest

from pdf_toolbox.paths import PathValidationError, validate_path


def test_validate_path_within_base(tmp_path):
    target = validate_path(tmp_path / "file.txt", base=tmp_path)
    assert target.parent == tmp_path


def test_validate_path_traversal(tmp_path):
    with pytest.raises(PathValidationError):
        validate_path(tmp_path / ".." / "other" / "file.txt", base=tmp_path)


def test_validate_path_must_exist(tmp_path):
    with pytest.raises(PathValidationError):
        validate_path(tmp_path / "missing.txt", must_exist=True)
