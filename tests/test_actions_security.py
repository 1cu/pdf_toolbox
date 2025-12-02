from __future__ import annotations

import json

import pytest

from pdf_toolbox import actions
from pdf_toolbox.config import load_config_at
from pdf_toolbox.paths import PathValidationError, validate_path
from pdf_toolbox.renderers.http_office import PptxHttpOfficeRenderer
from pdf_toolbox.renderers.pptx import PptxRenderingError


def test_register_module_rejects_foreign():
    msg = "module outside allowed packages"
    with pytest.raises(ValueError, match=msg):
        actions._register_module("json")


class TestPathValidation:
    """Security tests for path validation."""

    def test_null_byte_rejected(self):
        """Paths with null bytes should be rejected."""
        with pytest.raises(PathValidationError, match="null bytes"):
            validate_path("test\x00file.pdf")

    def test_path_traversal_with_base(self, tmp_path):
        """Paths escaping base directory should be rejected."""
        base = tmp_path / "safe"
        base.mkdir()

        # Try to escape to parent
        with pytest.raises(PathValidationError, match="escapes base"):
            validate_path("../unsafe.pdf", base=base)

        # Absolute path outside base
        with pytest.raises(PathValidationError, match="escapes base"):
            validate_path("/etc/passwd", base=base)

    def test_valid_path_within_base(self, tmp_path):
        """Valid paths within base should be accepted."""
        base = tmp_path / "safe"
        base.mkdir()
        (base / "test.pdf").touch()

        result = validate_path("test.pdf", base=base, must_exist=True)
        assert result.exists()
        assert base in result.parents or result == base


class TestHttpRendererSSRF:
    """SSRF protection tests for HTTP renderer."""

    def test_localhost_blocked(self):
        """Localhost endpoints should be blocked."""
        renderer = PptxHttpOfficeRenderer(
            {"http_office": {"endpoint": "http://localhost:8080/convert"}}
        )
        with pytest.raises(PptxRenderingError, match="localhost"):
            renderer._normalise_endpoint("http://localhost:8080/convert", "stirling")

    def test_127_0_0_1_blocked(self):
        """127.0.0.1 endpoints should be blocked."""
        renderer = PptxHttpOfficeRenderer({})
        with pytest.raises(PptxRenderingError, match="localhost"):
            renderer._normalise_endpoint("http://127.0.0.1:8080/convert", "stirling")

    def test_ipv6_localhost_blocked(self):
        """IPv6 localhost (::1) should be blocked."""
        renderer = PptxHttpOfficeRenderer({})
        with pytest.raises(PptxRenderingError, match="localhost"):
            renderer._normalise_endpoint("http://[::1]:8080/convert", "stirling")

    def test_link_local_blocked(self):
        """Link-local addresses (169.254.x.x) should be blocked."""
        renderer = PptxHttpOfficeRenderer({})
        with pytest.raises(PptxRenderingError, match="link-local"):
            renderer._normalise_endpoint("http://169.254.1.1:8080/convert", "stirling")

    def test_private_ip_10_blocked(self):
        """Private IP range 10.0.0.0/8 should be blocked."""
        renderer = PptxHttpOfficeRenderer({})
        with pytest.raises(PptxRenderingError, match="private IP"):
            renderer._normalise_endpoint("http://10.0.0.5:8080/convert", "stirling")

    def test_private_ip_192_168_blocked(self):
        """Private IP range 192.168.0.0/16 should be blocked."""
        renderer = PptxHttpOfficeRenderer({})
        with pytest.raises(PptxRenderingError, match="private IP"):
            renderer._normalise_endpoint("http://192.168.1.1:8080/convert", "stirling")

    def test_private_ip_172_16_blocked(self):
        """Private IP range 172.16.0.0/12 should be blocked."""
        renderer = PptxHttpOfficeRenderer({})
        # 172.16.x.x
        with pytest.raises(PptxRenderingError, match="private IP"):
            renderer._normalise_endpoint("http://172.16.0.1:8080/convert", "stirling")
        # 172.20.x.x (within 172.16-172.31)
        with pytest.raises(PptxRenderingError, match="private IP"):
            renderer._normalise_endpoint("http://172.20.0.1:8080/convert", "stirling")
        # 172.31.x.x (last in range)
        with pytest.raises(PptxRenderingError, match="private IP"):
            renderer._normalise_endpoint("http://172.31.255.255:8080/convert", "stirling")

    def test_public_ip_allowed(self):
        """Public IP addresses should be allowed."""
        renderer = PptxHttpOfficeRenderer({})
        # 172.32.x.x is public (outside 172.16-172.31)
        result = renderer._normalise_endpoint("http://172.32.0.1:8080/convert", "stirling")
        assert "172.32.0.1" in result

    def test_valid_domain_allowed(self):
        """Valid external domains should be allowed."""
        renderer = PptxHttpOfficeRenderer({})
        result = renderer._normalise_endpoint("https://example.com/api/convert", "stirling")
        assert "example.com" in result


class TestConfigSecurity:
    """Security tests for configuration loading."""

    def test_corrupted_json_handled(self, tmp_path):
        """Corrupted JSON config should return defaults gracefully."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"invalid": json}')

        # Should not raise exception
        result = load_config_at(config_file)

        # Should return defaults
        assert "pptx_renderer" in result
        assert result["pptx_renderer"] == "auto"  # Default value

    def test_empty_file_handled(self, tmp_path):
        """Empty config file should return defaults."""
        config_file = tmp_path / "config.json"
        config_file.write_text("")

        result = load_config_at(config_file)

        # Should return defaults without crashing
        assert "pptx_renderer" in result

    def test_valid_config_loaded(self, tmp_path):
        """Valid config should be loaded correctly."""
        config_file = tmp_path / "config.json"
        test_config = {"pptx_renderer": "lightweight", "custom_key": "value"}
        config_file.write_text(json.dumps(test_config))

        result = load_config_at(config_file)

        assert result["pptx_renderer"] == "lightweight"
        assert result["custom_key"] == "value"

    def test_empty_string_pptx_renderer(self, tmp_path):
        """Empty string pptx_renderer should default to 'auto'."""
        config_file = tmp_path / "config.json"
        test_config = {"pptx_renderer": "   "}
        config_file.write_text(json.dumps(test_config))

        result = load_config_at(config_file)

        assert result["pptx_renderer"] == "auto"  # Default value

    def test_non_string_pptx_renderer(self, tmp_path):
        """Non-string pptx_renderer should default to 'auto'."""
        config_file = tmp_path / "config.json"
        test_config = {"pptx_renderer": 123}
        config_file.write_text(json.dumps(test_config))

        result = load_config_at(config_file)

        assert result["pptx_renderer"] == "auto"  # Default value

    def test_read_error_handled(self, tmp_path, monkeypatch):
        """File read errors should return defaults gracefully."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"pptx_renderer": "test"}')

        # Simulate a read error by making read_text fail
        def failing_read_text(*_args, **_kwargs):
            raise OSError("Permission denied")  # noqa: TRY003  # pdf-toolbox: test helper error message | issue:-

        from pathlib import Path

        monkeypatch.setattr(Path, "read_text", failing_read_text)

        result = load_config_at(config_file)

        # Should return defaults without crashing
        assert "pptx_renderer" in result
        assert result["pptx_renderer"] == "auto"
