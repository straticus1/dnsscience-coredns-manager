"""Abstract base classes defining resolver interfaces."""

from abc import ABC, abstractmethod
from typing import AsyncIterator

from dnsscience.core.models import (
    BulkQueryResult,
    CacheEntry,
    CachePurgeResult,
    CacheStats,
    ConfigDiff,
    ConfigValidationResult,
    DNSQuery,
    DNSResponse,
    HealthStatus,
    MetricsSnapshot,
    RecordType,
    ResolverType,
    ServiceControlResult,
    ServiceStatus,
)


class BaseResolverClient(ABC):
    """Abstract base class for DNS resolver clients."""

    resolver_type: ResolverType

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the resolver."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the resolver."""
        ...

    # ========================================================================
    # Service Control
    # ========================================================================

    @abstractmethod
    async def get_status(self) -> ServiceStatus:
        """Get current service status."""
        ...

    @abstractmethod
    async def start(self) -> ServiceControlResult:
        """Start the resolver service."""
        ...

    @abstractmethod
    async def stop(self) -> ServiceControlResult:
        """Stop the resolver service."""
        ...

    @abstractmethod
    async def restart(self) -> ServiceControlResult:
        """Restart the resolver service."""
        ...

    @abstractmethod
    async def reload(self) -> ServiceControlResult:
        """Reload configuration without restart."""
        ...

    # ========================================================================
    # Query Operations
    # ========================================================================

    @abstractmethod
    async def query(self, query: DNSQuery) -> DNSResponse:
        """Execute a DNS query."""
        ...

    @abstractmethod
    async def query_bulk(self, queries: list[DNSQuery]) -> BulkQueryResult:
        """Execute multiple DNS queries."""
        ...

    @abstractmethod
    async def trace(self, query: DNSQuery) -> list[DNSResponse]:
        """Trace DNS resolution path."""
        ...

    # ========================================================================
    # Cache Operations
    # ========================================================================

    @abstractmethod
    async def get_cache_stats(self) -> CacheStats:
        """Get cache statistics."""
        ...

    @abstractmethod
    async def flush_cache(self) -> CachePurgeResult:
        """Flush entire cache."""
        ...

    @abstractmethod
    async def purge_cache(
        self,
        domain: str | None = None,
        record_type: RecordType | None = None,
    ) -> CachePurgeResult:
        """Purge specific entries from cache."""
        ...

    @abstractmethod
    async def inspect_cache(
        self,
        domain: str | None = None,
        limit: int = 100,
    ) -> list[CacheEntry]:
        """Inspect cache entries."""
        ...

    # ========================================================================
    # Configuration
    # ========================================================================

    @abstractmethod
    async def get_config(self) -> str:
        """Get current configuration."""
        ...

    @abstractmethod
    async def validate_config(self, config: str) -> ConfigValidationResult:
        """Validate configuration syntax and semantics."""
        ...

    @abstractmethod
    async def diff_config(self, new_config: str) -> ConfigDiff:
        """Diff new config against running config."""
        ...

    @abstractmethod
    async def apply_config(self, config: str, reload: bool = True) -> ServiceControlResult:
        """Apply new configuration."""
        ...

    # ========================================================================
    # Health & Metrics
    # ========================================================================

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Perform comprehensive health check."""
        ...

    @abstractmethod
    async def get_metrics(self) -> MetricsSnapshot:
        """Get current metrics."""
        ...

    @abstractmethod
    async def stream_metrics(self, interval_seconds: float = 5.0) -> AsyncIterator[MetricsSnapshot]:
        """Stream metrics at regular intervals."""
        ...


class BaseConfigParser(ABC):
    """Abstract base class for configuration parsers."""

    @abstractmethod
    def parse(self, config_text: str) -> dict:
        """Parse configuration text into structured data."""
        ...

    @abstractmethod
    def validate(self, config_text: str) -> ConfigValidationResult:
        """Validate configuration syntax."""
        ...

    @abstractmethod
    def to_dict(self, config_text: str) -> dict:
        """Convert configuration to dictionary representation."""
        ...


class BaseConfigGenerator(ABC):
    """Abstract base class for configuration generators."""

    @abstractmethod
    def generate(self, config_dict: dict) -> str:
        """Generate configuration text from structured data."""
        ...

    @abstractmethod
    def from_other(self, other_config: dict, source_type: ResolverType) -> str:
        """Generate configuration from another resolver's config."""
        ...
