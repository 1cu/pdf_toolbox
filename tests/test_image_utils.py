"""Tests for image_utils module."""

from __future__ import annotations

from PIL import Image

from pdf_toolbox.image_utils import encode_webp


def test_encode_webp_lossless():
    """Test WebP encoding in lossless mode."""
    img = Image.new("RGB", (100, 100), color="red")
    result = encode_webp(img, lossless=True, quality=None)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_encode_webp_with_quality():
    """Test WebP encoding with quality parameter."""
    img = Image.new("RGB", (100, 100), color="blue")
    result = encode_webp(img, lossless=False, quality=80)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_encode_webp_default():
    """Test WebP encoding with defaults."""
    img = Image.new("RGB", (100, 100), color="green")
    result = encode_webp(img, lossless=False, quality=None)
    assert isinstance(result, bytes)
    assert len(result) > 0
