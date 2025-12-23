"""Core library modules for DNS operations."""

from dnsscience.core.models import (
    DNSQuery,
    DNSRecord,
    DNSResponse,
    CacheStats,
    ServiceStatus,
    HealthStatus,
    CompareResult,
    MigrationPlan,
    ResolverType,
)

__all__ = [
    "DNSQuery",
    "DNSRecord",
    "DNSResponse",
    "CacheStats",
    "ServiceStatus",
    "HealthStatus",
    "CompareResult",
    "MigrationPlan",
    "ResolverType",
]
