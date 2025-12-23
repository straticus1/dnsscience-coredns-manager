"""Tests for core models."""

import pytest
from pydantic import ValidationError

from dnsscience.core.models import (
    CacheStats,
    CompareResult,
    DNSQuery,
    DNSRecord,
    DNSResponse,
    HealthStatus,
    MigrationPlan,
    MigrationStep,
    RecordType,
    ResolverType,
    ServiceHealth,
    ServiceStatus,
)


class TestDNSQuery:
    """Tests for DNSQuery model."""

    def test_basic_query(self):
        query = DNSQuery(name="example.com", record_type=RecordType.A)
        assert query.name == "example.com"
        assert query.record_type == RecordType.A

    def test_query_with_all_fields(self):
        query = DNSQuery(
            name="example.com",
            record_type=RecordType.MX,
            server="8.8.8.8",
            timeout=5.0,
            use_tcp=True,
        )
        assert query.server == "8.8.8.8"
        assert query.timeout == 5.0
        assert query.use_tcp is True

    def test_query_default_values(self):
        query = DNSQuery(name="test.com", record_type=RecordType.A)
        assert query.server is None
        assert query.timeout is None
        assert query.use_tcp is False


class TestDNSRecord:
    """Tests for DNSRecord model."""

    def test_a_record(self):
        record = DNSRecord(
            name="example.com",
            record_type=RecordType.A,
            ttl=300,
            data="93.184.216.34",
        )
        assert record.name == "example.com"
        assert record.ttl == 300
        assert record.data == "93.184.216.34"

    def test_mx_record(self):
        record = DNSRecord(
            name="example.com",
            record_type=RecordType.MX,
            ttl=3600,
            data="10 mail.example.com",
            priority=10,
        )
        assert record.priority == 10


class TestDNSResponse:
    """Tests for DNSResponse model."""

    def test_successful_response(self, sample_dns_query):
        response = DNSResponse(
            query=sample_dns_query,
            records=[
                DNSRecord(
                    name="example.com",
                    record_type=RecordType.A,
                    ttl=300,
                    data="93.184.216.34",
                )
            ],
            rcode="NOERROR",
            query_time_ms=25.5,
            server="8.8.8.8",
        )
        assert response.rcode == "NOERROR"
        assert len(response.records) == 1
        assert response.query_time_ms == 25.5

    def test_nxdomain_response(self, sample_dns_query):
        response = DNSResponse(
            query=sample_dns_query,
            records=[],
            rcode="NXDOMAIN",
            query_time_ms=10.0,
            server="8.8.8.8",
        )
        assert response.rcode == "NXDOMAIN"
        assert len(response.records) == 0


class TestCacheStats:
    """Tests for CacheStats model."""

    def test_cache_stats(self):
        stats = CacheStats(
            size=1000,
            hits=8000,
            misses=2000,
            hit_rate=0.8,
        )
        assert stats.size == 1000
        assert stats.hit_rate == 0.8

    def test_cache_stats_with_entries(self):
        stats = CacheStats(
            size=500,
            hits=100,
            misses=50,
            hit_rate=0.67,
            entries={"example.com": {"type": "A", "ttl": 300}},
        )
        assert stats.entries is not None
        assert "example.com" in stats.entries


class TestServiceStatus:
    """Tests for ServiceStatus model."""

    def test_coredns_status(self):
        status = ServiceStatus(
            resolver=ResolverType.COREDNS,
            running=True,
            uptime_seconds=3600,
            version="1.11.1",
        )
        assert status.resolver == ResolverType.COREDNS
        assert status.running is True

    def test_unbound_status(self):
        status = ServiceStatus(
            resolver=ResolverType.UNBOUND,
            running=True,
            uptime_seconds=7200,
            version="1.19.0",
        )
        assert status.resolver == ResolverType.UNBOUND


class TestHealthStatus:
    """Tests for HealthStatus model."""

    def test_healthy_status(self):
        health = HealthStatus(
            state=ServiceHealth.HEALTHY,
            checks={"dns": True, "upstream": True},
        )
        assert health.state == ServiceHealth.HEALTHY

    def test_degraded_status(self):
        health = HealthStatus(
            state=ServiceHealth.DEGRADED,
            checks={"dns": True, "upstream": False},
            message="Upstream connectivity issues",
        )
        assert health.state == ServiceHealth.DEGRADED
        assert "Upstream" in health.message


class TestCompareResult:
    """Tests for CompareResult model."""

    def test_matching_result(self, sample_dns_query, sample_dns_response):
        result = CompareResult(
            query=sample_dns_query,
            source_response=sample_dns_response,
            target_response=sample_dns_response,
            match=True,
            timing_diff_ms=0.5,
        )
        assert result.match is True
        assert result.timing_diff_ms == 0.5

    def test_mismatched_result(self, sample_dns_query, sample_dns_response):
        target_response = DNSResponse(
            query=sample_dns_query,
            records=[],
            rcode="NXDOMAIN",
            query_time_ms=15.0,
            server="127.0.0.1",
        )
        result = CompareResult(
            query=sample_dns_query,
            source_response=sample_dns_response,
            target_response=target_response,
            match=False,
            differences=["RCODE mismatch: NOERROR vs NXDOMAIN"],
        )
        assert result.match is False
        assert len(result.differences) > 0


class TestMigrationPlan:
    """Tests for MigrationPlan model."""

    def test_migration_plan(self):
        plan = MigrationPlan(
            source=ResolverType.COREDNS,
            target=ResolverType.UNBOUND,
            steps=[
                MigrationStep(
                    order=1,
                    description="Parse CoreDNS configuration",
                    automated=True,
                ),
                MigrationStep(
                    order=2,
                    description="Generate Unbound configuration",
                    automated=True,
                ),
            ],
            warnings=["Some plugins may not have direct equivalents"],
            source_config=".:53 { forward . 8.8.8.8 }",
            target_config="forward-zone:\n    name: .\n    forward-addr: 8.8.8.8",
        )
        assert plan.source == ResolverType.COREDNS
        assert plan.target == ResolverType.UNBOUND
        assert len(plan.steps) == 2
        assert len(plan.warnings) == 1
