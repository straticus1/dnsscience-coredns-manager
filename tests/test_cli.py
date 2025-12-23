"""Tests for CLI commands."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typer.testing import CliRunner
from click.testing import Result

from dnsscience.cli.main import app
from dnsscience.core.models import (
    CacheStats,
    DNSQuery,
    DNSRecord,
    DNSResponse,
    HealthStatus,
    RecordType,
    ResolverType,
    ServiceHealth,
    ServiceStatus,
)


runner = CliRunner()


class TestServiceCommands:
    """Tests for service commands."""

    def test_status(self):
        with patch("dnsscience.cli.commands.service.coredns") as mock:
            mock.status = AsyncMock(
                return_value=ServiceStatus(
                    resolver=ResolverType.COREDNS,
                    running=True,
                    uptime_seconds=3600,
                    version="1.11.1",
                )
            )

            result = runner.invoke(app, ["service", "status"])

            assert result.exit_code == 0
            assert "coredns" in result.stdout.lower() or "running" in result.stdout.lower()

    def test_start(self):
        with patch("dnsscience.cli.commands.service.coredns") as mock:
            mock.start = AsyncMock(return_value=True)

            result = runner.invoke(app, ["service", "start"])

            assert result.exit_code == 0
            mock.start.assert_called_once()

    def test_stop(self):
        with patch("dnsscience.cli.commands.service.coredns") as mock:
            mock.stop = AsyncMock(return_value=True)

            result = runner.invoke(app, ["service", "stop"])

            assert result.exit_code == 0
            mock.stop.assert_called_once()

    def test_restart(self):
        with patch("dnsscience.cli.commands.service.coredns") as mock:
            mock.restart = AsyncMock(return_value=True)

            result = runner.invoke(app, ["service", "restart"])

            assert result.exit_code == 0
            mock.restart.assert_called_once()

    def test_reload(self):
        with patch("dnsscience.cli.commands.service.coredns") as mock:
            mock.reload = AsyncMock(return_value=True)

            result = runner.invoke(app, ["service", "reload"])

            assert result.exit_code == 0
            mock.reload.assert_called_once()


class TestCacheCommands:
    """Tests for cache commands."""

    def test_stats(self):
        with patch("dnsscience.cli.commands.cache.coredns") as mock:
            mock.get_cache_stats = AsyncMock(
                return_value=CacheStats(
                    size=1000,
                    hits=8000,
                    misses=2000,
                    hit_rate=0.8,
                )
            )

            result = runner.invoke(app, ["cache", "stats"])

            assert result.exit_code == 0
            assert "1000" in result.stdout or "size" in result.stdout.lower()

    def test_flush(self):
        with patch("dnsscience.cli.commands.cache.coredns") as mock:
            mock.flush_cache = AsyncMock(return_value=True)

            result = runner.invoke(app, ["cache", "flush"])

            assert result.exit_code == 0
            mock.flush_cache.assert_called_once()

    def test_flush_domain(self):
        with patch("dnsscience.cli.commands.cache.coredns") as mock:
            mock.flush_cache = AsyncMock(return_value=True)

            result = runner.invoke(app, ["cache", "flush", "--domain", "example.com"])

            assert result.exit_code == 0


class TestQueryCommands:
    """Tests for query commands."""

    def test_query_a_record(self):
        with patch("dnsscience.cli.commands.query.coredns") as mock:
            mock.query = AsyncMock(
                return_value=DNSResponse(
                    query=DNSQuery(name="example.com", record_type=RecordType.A),
                    records=[
                        DNSRecord(
                            name="example.com",
                            record_type=RecordType.A,
                            ttl=300,
                            data="93.184.216.34",
                        )
                    ],
                    rcode="NOERROR",
                    query_time_ms=25.0,
                    server="127.0.0.1",
                )
            )

            result = runner.invoke(app, ["query", "example.com"])

            assert result.exit_code == 0
            assert "93.184.216.34" in result.stdout or "NOERROR" in result.stdout

    def test_query_mx_record(self):
        with patch("dnsscience.cli.commands.query.coredns") as mock:
            mock.query = AsyncMock(
                return_value=DNSResponse(
                    query=DNSQuery(name="example.com", record_type=RecordType.MX),
                    records=[
                        DNSRecord(
                            name="example.com",
                            record_type=RecordType.MX,
                            ttl=3600,
                            data="10 mail.example.com",
                            priority=10,
                        )
                    ],
                    rcode="NOERROR",
                    query_time_ms=30.0,
                    server="127.0.0.1",
                )
            )

            result = runner.invoke(app, ["query", "example.com", "--type", "MX"])

            assert result.exit_code == 0

    def test_query_with_server(self):
        with patch("dnsscience.cli.commands.query.coredns") as mock:
            mock.query = AsyncMock(
                return_value=DNSResponse(
                    query=DNSQuery(
                        name="example.com",
                        record_type=RecordType.A,
                        server="8.8.8.8",
                    ),
                    records=[],
                    rcode="NOERROR",
                    query_time_ms=50.0,
                    server="8.8.8.8",
                )
            )

            result = runner.invoke(
                app, ["query", "example.com", "--server", "8.8.8.8"]
            )

            assert result.exit_code == 0


class TestCompareCommands:
    """Tests for compare commands."""

    def test_compare_single(self):
        with patch("dnsscience.cli.commands.compare.compare_engine") as mock:
            from dnsscience.core.models import CompareResult

            query = DNSQuery(name="example.com", record_type=RecordType.A)
            response = DNSResponse(
                query=query,
                records=[],
                rcode="NOERROR",
                query_time_ms=10.0,
                server="test",
            )
            mock.compare = AsyncMock(
                return_value=CompareResult(
                    query=query,
                    source_response=response,
                    target_response=response,
                    match=True,
                    timing_diff_ms=0.5,
                )
            )

            result = runner.invoke(app, ["compare", "example.com"])

            assert result.exit_code == 0

    def test_compare_bulk(self):
        with patch("dnsscience.cli.commands.compare.compare_engine") as mock:
            from dnsscience.core.models import BulkCompareResult

            mock.compare_bulk = AsyncMock(
                return_value=BulkCompareResult(
                    queries_tested=3,
                    matches=3,
                    mismatches=0,
                    errors=0,
                    confidence_score=1.0,
                    results=[],
                )
            )

            result = runner.invoke(
                app,
                ["compare", "--bulk", "example.com,google.com,cloudflare.com"],
            )

            assert result.exit_code == 0


class TestMigrateCommands:
    """Tests for migrate commands."""

    def test_plan(self):
        with patch("dnsscience.cli.commands.migrate.migration_engine") as mock:
            from dnsscience.core.models import MigrationPlan, MigrationStep

            mock.create_plan = MagicMock(
                return_value=MigrationPlan(
                    source=ResolverType.COREDNS,
                    target=ResolverType.UNBOUND,
                    steps=[
                        MigrationStep(
                            order=1,
                            description="Parse configuration",
                            automated=True,
                        )
                    ],
                    warnings=[],
                    source_config=".:53 { forward . 8.8.8.8 }",
                    target_config="forward-zone:\n    name: .\n    forward-addr: 8.8.8.8",
                )
            )

            result = runner.invoke(
                app,
                [
                    "migrate",
                    "plan",
                    "--source",
                    "coredns",
                    "--target",
                    "unbound",
                    "--config",
                    ".:53 { forward . 8.8.8.8 }",
                ],
            )

            assert result.exit_code == 0

    def test_convert(self):
        with patch("dnsscience.cli.commands.migrate.migration_engine") as mock:
            mock.convert = MagicMock(
                return_value="forward-zone:\n    name: .\n    forward-addr: 8.8.8.8"
            )

            result = runner.invoke(
                app,
                [
                    "migrate",
                    "convert",
                    "--source",
                    "coredns",
                    "--target",
                    "unbound",
                    "--config",
                    ".:53 { forward . 8.8.8.8 }",
                ],
            )

            assert result.exit_code == 0
            assert "forward-zone" in result.stdout


class TestHealthCommands:
    """Tests for health commands."""

    def test_health(self):
        with patch("dnsscience.cli.commands.health.coredns") as mock:
            mock.health_check = AsyncMock(
                return_value=HealthStatus(
                    state=ServiceHealth.HEALTHY,
                    checks={"dns": True, "upstream": True},
                )
            )

            result = runner.invoke(app, ["health"])

            assert result.exit_code == 0
            assert "healthy" in result.stdout.lower()

    def test_health_degraded(self):
        with patch("dnsscience.cli.commands.health.coredns") as mock:
            mock.health_check = AsyncMock(
                return_value=HealthStatus(
                    state=ServiceHealth.DEGRADED,
                    checks={"dns": True, "upstream": False},
                    message="Upstream issues",
                )
            )

            result = runner.invoke(app, ["health"])

            assert result.exit_code == 0
            assert "degraded" in result.stdout.lower()


class TestConfigCommands:
    """Tests for config commands."""

    def test_validate_valid(self):
        with patch("dnsscience.cli.commands.config.CorefileParser") as mock_parser:
            from dnsscience.core.models import ValidationResult

            instance = mock_parser.return_value
            instance.validate.return_value = ValidationResult(
                valid=True,
                errors=[],
                warnings=[],
            )

            result = runner.invoke(
                app,
                ["config", "validate", "--config", ".:53 { forward . 8.8.8.8 }"],
            )

            assert result.exit_code == 0
            assert "valid" in result.stdout.lower()

    def test_validate_invalid(self):
        with patch("dnsscience.cli.commands.config.CorefileParser") as mock_parser:
            from dnsscience.core.models import ValidationResult, ValidationError

            instance = mock_parser.return_value
            instance.validate.return_value = ValidationResult(
                valid=False,
                errors=[
                    ValidationError(
                        line=1,
                        column=1,
                        message="Missing zone declaration",
                        severity="error",
                    )
                ],
                warnings=[],
            )

            result = runner.invoke(
                app,
                ["config", "validate", "--config", "{ forward . 8.8.8.8 }"],
            )

            assert result.exit_code == 1 or "error" in result.stdout.lower()
