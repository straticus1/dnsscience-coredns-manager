"""Tests for migration engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dnsscience.core.migrate.engine import MigrationEngine
from dnsscience.core.migrate.coredns_to_unbound import CoreDNSToUnboundMigrator
from dnsscience.core.migrate.unbound_to_coredns import UnboundToCoreDNSMigrator
from dnsscience.core.models import MigrationPlan, ResolverType


class TestCoreDNSToUnboundMigrator:
    """Tests for CoreDNS to Unbound migration."""

    @pytest.fixture
    def migrator(self):
        return CoreDNSToUnboundMigrator()

    def test_convert_simple_forward(self, migrator):
        corefile = """.:53 {
    forward . 8.8.8.8 8.8.4.4
}
"""
        result = migrator.convert(corefile)

        assert "forward-zone:" in result
        assert 'name: "."' in result
        assert "forward-addr: 8.8.8.8" in result
        assert "forward-addr: 8.8.4.4" in result

    def test_convert_cache_settings(self, migrator):
        corefile = """.:53 {
    forward . 8.8.8.8
    cache 300
}
"""
        result = migrator.convert(corefile)

        assert "server:" in result
        # Cache settings should be converted
        assert "cache" in result.lower() or "ttl" in result.lower()

    def test_convert_multiple_zones(self, migrator):
        corefile = """.:53 {
    forward . 8.8.8.8
}

internal.local:53 {
    forward . 10.0.0.1
}
"""
        result = migrator.convert(corefile)

        # Should have multiple forward zones
        assert result.count("forward-zone:") == 2

    def test_convert_kubernetes_plugin_warning(self, migrator, sample_corefile):
        plan = migrator.create_plan(sample_corefile)

        # Should have warnings about kubernetes plugin
        assert any("kubernetes" in w.lower() for w in plan.warnings)

    def test_convert_preserves_port(self, migrator):
        corefile = """.:5353 {
    forward . 8.8.8.8
}
"""
        result = migrator.convert(corefile)

        assert "port: 5353" in result

    def test_create_plan(self, migrator):
        corefile = """.:53 {
    forward . 8.8.8.8
    cache 30
}
"""
        plan = migrator.create_plan(corefile)

        assert isinstance(plan, MigrationPlan)
        assert plan.source == ResolverType.COREDNS
        assert plan.target == ResolverType.UNBOUND
        assert len(plan.steps) > 0
        assert plan.source_config == corefile
        assert plan.target_config is not None

    def test_convert_prometheus_to_stats(self, migrator):
        corefile = """.:53 {
    forward . 8.8.8.8
    prometheus :9153
}
"""
        result = migrator.convert(corefile)

        # Should have stats or remote-control equivalent
        assert "extended-statistics" in result or "statistics" in result.lower()


class TestUnboundToCoreDNSMigrator:
    """Tests for Unbound to CoreDNS migration."""

    @pytest.fixture
    def migrator(self):
        return UnboundToCoreDNSMigrator()

    def test_convert_simple_forward(self, migrator, sample_unbound_conf):
        result = migrator.convert(sample_unbound_conf)

        assert ".:53" in result
        assert "forward" in result
        assert "8.8.8.8" in result

    def test_convert_preserves_interface(self, migrator):
        unbound_conf = """server:
    interface: 127.0.0.1
    port: 5353

forward-zone:
    name: "."
    forward-addr: 8.8.8.8
"""
        result = migrator.convert(unbound_conf)

        assert ":5353" in result

    def test_convert_multiple_forward_zones(self, migrator):
        unbound_conf = """server:
    interface: 0.0.0.0

forward-zone:
    name: "."
    forward-addr: 8.8.8.8

forward-zone:
    name: "internal.local"
    forward-addr: 10.0.0.1
"""
        result = migrator.convert(unbound_conf)

        assert ".:53" in result or "." in result
        assert "internal.local" in result

    def test_convert_cache_settings(self, migrator):
        unbound_conf = """server:
    cache-max-ttl: 86400
    cache-min-ttl: 300
    prefetch: yes

forward-zone:
    name: "."
    forward-addr: 8.8.8.8
"""
        result = migrator.convert(unbound_conf)

        # Should have cache plugin
        assert "cache" in result

    def test_create_plan(self, migrator, sample_unbound_conf):
        plan = migrator.create_plan(sample_unbound_conf)

        assert isinstance(plan, MigrationPlan)
        assert plan.source == ResolverType.UNBOUND
        assert plan.target == ResolverType.COREDNS
        assert len(plan.steps) > 0


class TestMigrationEngine:
    """Tests for MigrationEngine."""

    @pytest.fixture
    def engine(self):
        return MigrationEngine()

    def test_get_migrator_coredns_to_unbound(self, engine):
        migrator = engine.get_migrator(ResolverType.COREDNS, ResolverType.UNBOUND)
        assert isinstance(migrator, CoreDNSToUnboundMigrator)

    def test_get_migrator_unbound_to_coredns(self, engine):
        migrator = engine.get_migrator(ResolverType.UNBOUND, ResolverType.COREDNS)
        assert isinstance(migrator, UnboundToCoreDNSMigrator)

    def test_get_migrator_same_resolver(self, engine):
        with pytest.raises(ValueError):
            engine.get_migrator(ResolverType.COREDNS, ResolverType.COREDNS)

    def test_create_plan_coredns_to_unbound(self, engine):
        corefile = """.:53 {
    forward . 8.8.8.8
    cache 30
}
"""
        plan = engine.create_plan(ResolverType.COREDNS, ResolverType.UNBOUND, corefile)

        assert plan.source == ResolverType.COREDNS
        assert plan.target == ResolverType.UNBOUND

    def test_create_plan_unbound_to_coredns(self, engine, sample_unbound_conf):
        plan = engine.create_plan(
            ResolverType.UNBOUND,
            ResolverType.COREDNS,
            sample_unbound_conf,
        )

        assert plan.source == ResolverType.UNBOUND
        assert plan.target == ResolverType.COREDNS

    def test_convert(self, engine):
        corefile = """.:53 {
    forward . 8.8.8.8
}
"""
        result = engine.convert(ResolverType.COREDNS, ResolverType.UNBOUND, corefile)

        assert "forward-zone:" in result
        assert "8.8.8.8" in result


class TestMigrationValidation:
    """Tests for migration validation."""

    @pytest.fixture
    def engine(self):
        return MigrationEngine()

    def test_validate_plan_valid(self, engine):
        plan = MigrationPlan(
            source=ResolverType.COREDNS,
            target=ResolverType.UNBOUND,
            steps=[],
            warnings=[],
            source_config=".:53 { forward . 8.8.8.8 }",
            target_config="forward-zone:\n    name: .\n    forward-addr: 8.8.8.8",
        )

        result = engine.validate_plan(plan)
        assert result.valid is True

    def test_validate_plan_missing_target_config(self, engine):
        plan = MigrationPlan(
            source=ResolverType.COREDNS,
            target=ResolverType.UNBOUND,
            steps=[],
            warnings=[],
            source_config=".:53 { forward . 8.8.8.8 }",
            target_config="",
        )

        result = engine.validate_plan(plan)
        assert result.valid is False
