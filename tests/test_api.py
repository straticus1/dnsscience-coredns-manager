"""Tests for REST API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient

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


@pytest.fixture
def mock_coredns():
    """Mock CoreDNS client."""
    with patch("dnsscience.api.routers.service.coredns") as mock:
        mock.status = AsyncMock(
            return_value=ServiceStatus(
                resolver=ResolverType.COREDNS,
                running=True,
                uptime_seconds=3600,
                version="1.11.1",
            )
        )
        mock.start = AsyncMock(return_value=True)
        mock.stop = AsyncMock(return_value=True)
        mock.restart = AsyncMock(return_value=True)
        mock.reload = AsyncMock(return_value=True)
        yield mock


@pytest.fixture
def mock_cache():
    """Mock cache operations."""
    with patch("dnsscience.api.routers.cache.coredns") as mock:
        mock.get_cache_stats = AsyncMock(
            return_value=CacheStats(
                size=1000,
                hits=8000,
                misses=2000,
                hit_rate=0.8,
            )
        )
        mock.flush_cache = AsyncMock(return_value=True)
        yield mock


class TestServiceEndpoints:
    """Tests for /service endpoints."""

    @pytest.mark.asyncio
    async def test_get_status(self, api_client, mock_coredns):
        response = await api_client.get("/api/v1/service/status")
        assert response.status_code == 200
        data = response.json()
        assert data["resolver"] == "coredns"
        assert data["running"] is True

    @pytest.mark.asyncio
    async def test_start_service(self, api_client, mock_coredns):
        response = await api_client.post("/api/v1/service/start")
        assert response.status_code == 200
        mock_coredns.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_service(self, api_client, mock_coredns):
        response = await api_client.post("/api/v1/service/stop")
        assert response.status_code == 200
        mock_coredns.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_restart_service(self, api_client, mock_coredns):
        response = await api_client.post("/api/v1/service/restart")
        assert response.status_code == 200
        mock_coredns.restart.assert_called_once()

    @pytest.mark.asyncio
    async def test_reload_config(self, api_client, mock_coredns):
        response = await api_client.post("/api/v1/service/reload")
        assert response.status_code == 200
        mock_coredns.reload.assert_called_once()


class TestCacheEndpoints:
    """Tests for /cache endpoints."""

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, api_client, mock_cache):
        response = await api_client.get("/api/v1/cache/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["size"] == 1000
        assert data["hit_rate"] == 0.8

    @pytest.mark.asyncio
    async def test_flush_cache(self, api_client, mock_cache):
        response = await api_client.post("/api/v1/cache/flush")
        assert response.status_code == 200
        mock_cache.flush_cache.assert_called_once()


class TestQueryEndpoints:
    """Tests for /query endpoints."""

    @pytest.mark.asyncio
    async def test_query_domain(self, api_client):
        with patch("dnsscience.api.routers.query.coredns") as mock:
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

            response = await api_client.get(
                "/api/v1/query",
                params={"domain": "example.com", "type": "A"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["rcode"] == "NOERROR"
            assert len(data["records"]) == 1

    @pytest.mark.asyncio
    async def test_query_with_server(self, api_client):
        with patch("dnsscience.api.routers.query.coredns") as mock:
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

            response = await api_client.get(
                "/api/v1/query",
                params={"domain": "example.com", "type": "A", "server": "8.8.8.8"},
            )

            assert response.status_code == 200


class TestCompareEndpoints:
    """Tests for /compare endpoints."""

    @pytest.mark.asyncio
    async def test_compare_single(self, api_client):
        with patch("dnsscience.api.routers.compare.compare_engine") as mock:
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

            response = await api_client.get(
                "/api/v1/compare/single",
                params={"domain": "example.com", "type": "A"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["match"] is True

    @pytest.mark.asyncio
    async def test_compare_bulk(self, api_client):
        with patch("dnsscience.api.routers.compare.compare_engine") as mock:
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

            response = await api_client.post(
                "/api/v1/compare/bulk",
                json={
                    "domains": ["example.com", "google.com", "cloudflare.com"],
                    "type": "A",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["confidence_score"] == 1.0


class TestMigrateEndpoints:
    """Tests for /migrate endpoints."""

    @pytest.mark.asyncio
    async def test_create_plan(self, api_client):
        with patch("dnsscience.api.routers.migrate.migration_engine") as mock:
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
                    warnings=["Some plugins may not convert"],
                    source_config=".:53 { forward . 8.8.8.8 }",
                    target_config="forward-zone:\n    name: .\n    forward-addr: 8.8.8.8",
                )
            )

            response = await api_client.post(
                "/api/v1/migrate/plan",
                json={
                    "source": "coredns",
                    "target": "unbound",
                    "config": ".:53 { forward . 8.8.8.8 }",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["source"] == "coredns"
            assert data["target"] == "unbound"
            assert len(data["steps"]) > 0

    @pytest.mark.asyncio
    async def test_convert_config(self, api_client):
        with patch("dnsscience.api.routers.migrate.migration_engine") as mock:
            mock.convert = MagicMock(
                return_value="forward-zone:\n    name: .\n    forward-addr: 8.8.8.8"
            )

            response = await api_client.post(
                "/api/v1/migrate/convert",
                json={
                    "source": "coredns",
                    "target": "unbound",
                    "config": ".:53 { forward . 8.8.8.8 }",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "forward-zone" in data["converted_config"]


class TestHealthEndpoints:
    """Tests for /health endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, api_client):
        with patch("dnsscience.api.routers.health.coredns") as mock:
            mock.health_check = AsyncMock(
                return_value=HealthStatus(
                    state=ServiceHealth.HEALTHY,
                    checks={"dns": True, "upstream": True},
                )
            )

            response = await api_client.get("/api/v1/health")

            assert response.status_code == 200
            data = response.json()
            assert data["state"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_liveness(self, api_client):
        response = await api_client.get("/api/v1/health/live")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_readiness(self, api_client):
        with patch("dnsscience.api.routers.health.coredns") as mock:
            mock.health_check = AsyncMock(
                return_value=HealthStatus(
                    state=ServiceHealth.HEALTHY,
                    checks={},
                )
            )

            response = await api_client.get("/api/v1/health/ready")
            assert response.status_code == 200
