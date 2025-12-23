"""Tests for CoreDNS configuration parsing and generation."""

import pytest

from dnsscience.core.coredns.config import CorefileParser, CorefileGenerator
from dnsscience.core.models import ValidationResult


class TestCorefileParser:
    """Tests for Corefile parser."""

    def test_parse_simple_corefile(self):
        corefile = """.:53 {
    forward . 8.8.8.8
    cache 30
}
"""
        parser = CorefileParser()
        result = parser.parse(corefile)

        assert "." in result
        assert result["."]["port"] == "53"
        assert "forward" in result["."]["plugins"]
        assert "cache" in result["."]["plugins"]

    def test_parse_multiple_server_blocks(self):
        corefile = """.:53 {
    forward . 8.8.8.8
    cache 30
}

cluster.local:53 {
    kubernetes
    cache 10
}
"""
        parser = CorefileParser()
        result = parser.parse(corefile)

        assert "." in result
        assert "cluster.local" in result

    def test_parse_kubernetes_plugin(self, sample_corefile):
        parser = CorefileParser()
        result = parser.parse(sample_corefile)

        assert "." in result
        assert "kubernetes" in result["."]["plugins"]

    def test_validate_valid_corefile(self, sample_corefile):
        parser = CorefileParser()
        result = parser.validate(sample_corefile)

        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_missing_zone(self):
        corefile = """{
    forward . 8.8.8.8
}
"""
        parser = CorefileParser()
        result = parser.validate(corefile)

        assert result.valid is False
        assert len(result.errors) > 0

    def test_validate_invalid_plugin(self):
        corefile = """.:53 {
    invalid_plugin_name
}
"""
        parser = CorefileParser()
        result = parser.validate(corefile)

        # Should have warnings about unknown plugins
        assert len(result.warnings) > 0 or len(result.errors) > 0

    def test_extract_plugins(self, sample_corefile):
        parser = CorefileParser()
        plugins = parser.extract_plugins(sample_corefile)

        expected_plugins = [
            "errors",
            "health",
            "ready",
            "kubernetes",
            "prometheus",
            "forward",
            "cache",
            "loop",
            "reload",
            "loadbalance",
        ]
        for plugin in expected_plugins:
            assert plugin in plugins

    def test_extract_forwarders(self):
        corefile = """.:53 {
    forward . 8.8.8.8 8.8.4.4
    cache 30
}
"""
        parser = CorefileParser()
        result = parser.parse(corefile)

        # Check forward plugin args contain the forwarders
        forward_config = result["."]["plugins"]["forward"]
        assert "8.8.8.8" in forward_config or "8.8.8.8" in str(forward_config)


class TestCorefileGenerator:
    """Tests for Corefile generator."""

    def test_generate_simple_corefile(self):
        generator = CorefileGenerator()
        config = {
            ".": {
                "port": "53",
                "plugins": {
                    "forward": ". 8.8.8.8",
                    "cache": "30",
                },
            },
        }
        result = generator.generate(config)

        assert ".:53" in result
        assert "forward" in result
        assert "cache" in result
        assert "8.8.8.8" in result

    def test_generate_multiple_zones(self):
        generator = CorefileGenerator()
        config = {
            ".": {
                "port": "53",
                "plugins": {
                    "forward": ". 8.8.8.8",
                },
            },
            "cluster.local": {
                "port": "53",
                "plugins": {
                    "kubernetes": "",
                },
            },
        }
        result = generator.generate(config)

        assert ".:53" in result
        assert "cluster.local:53" in result

    def test_generate_preserves_plugin_order(self):
        generator = CorefileGenerator()
        config = {
            ".": {
                "port": "53",
                "plugins": {
                    "errors": "",
                    "health": "",
                    "cache": "30",
                    "forward": ". 8.8.8.8",
                },
            },
        }
        result = generator.generate(config)

        # Errors should come before forward in standard Corefile
        assert result.index("errors") < result.index("forward")

    def test_roundtrip_parse_generate(self, sample_corefile):
        parser = CorefileParser()
        generator = CorefileGenerator()

        parsed = parser.parse(sample_corefile)
        generated = generator.generate(parsed)

        # Re-parse generated config
        reparsed = parser.parse(generated)

        # Should have same zones
        assert set(parsed.keys()) == set(reparsed.keys())

        # Should have same plugins per zone
        for zone in parsed:
            original_plugins = set(parsed[zone]["plugins"].keys())
            regenerated_plugins = set(reparsed[zone]["plugins"].keys())
            assert original_plugins == regenerated_plugins
