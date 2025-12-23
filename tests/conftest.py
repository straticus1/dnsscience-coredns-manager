"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
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
from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.unbound.client import UnboundClient


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_dns_query() -> DNSQuery:
    """Sample DNS query fixture."""
    return DNSQuery(
        name="example.com",
        record_type=RecordType.A,
    )


@pytest.fixture
def sample_dns_response(sample_dns_query: DNSQuery) -> DNSResponse:
    """Sample DNS response fixture."""
    return DNSResponse(
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
        server="127.0.0.1",
    )


@pytest.fixture
def sample_cache_stats() -> CacheStats:
    """Sample cache stats fixture."""
    return CacheStats(
        size=1500,
        hits=10000,
        misses=2500,
        hit_rate=0.8,
    )


@pytest.fixture
def sample_service_status() -> ServiceStatus:
    """Sample service status fixture."""
    return ServiceStatus(
        resolver=ResolverType.COREDNS,
        running=True,
        uptime_seconds=86400,
        version="1.11.1",
        config_path="/etc/coredns/Corefile",
    )


@pytest.fixture
def sample_health_status() -> HealthStatus:
    """Sample health status fixture."""
    return HealthStatus(
        state=ServiceHealth.HEALTHY,
        checks={
            "dns_resolution": True,
            "upstream_connectivity": True,
            "config_valid": True,
        },
        message="All checks passed",
    )


@pytest.fixture
def sample_corefile() -> str:
    """Sample Corefile content."""
    return """.:53 {
    errors
    health {
        lameduck 5s
    }
    ready
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
    }
    prometheus :9153
    forward . /etc/resolv.conf {
        max_concurrent 1000
    }
    cache 30
    loop
    reload
    loadbalance
}
"""


@pytest.fixture
def sample_unbound_conf() -> str:
    """Sample unbound.conf content."""
    return """server:
    interface: 0.0.0.0
    port: 53
    access-control: 0.0.0.0/0 allow
    do-ip4: yes
    do-ip6: yes
    do-udp: yes
    do-tcp: yes
    cache-max-ttl: 86400
    cache-min-ttl: 0
    prefetch: yes
    num-threads: 4
    verbosity: 1

forward-zone:
    name: "."
    forward-addr: 8.8.8.8
    forward-addr: 8.8.4.4
"""


@pytest.fixture
def mock_coredns_client() -> CoreDNSClient:
    """Mock CoreDNS client."""
    client = CoreDNSClient()
    client._session = AsyncMock()
    return client


@pytest.fixture
def mock_unbound_client() -> UnboundClient:
    """Mock Unbound client."""
    client = UnboundClient()
    return client


@pytest.fixture
async def api_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for API testing."""
    from dnsscience.api.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
