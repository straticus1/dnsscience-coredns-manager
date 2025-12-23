"""Core data models for DNS Science Toolkit."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResolverType(str, Enum):
    """Supported DNS resolver types."""

    COREDNS = "coredns"
    UNBOUND = "unbound"


class RecordType(str, Enum):
    """DNS record types."""

    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    NS = "NS"
    PTR = "PTR"
    SOA = "SOA"
    SRV = "SRV"
    TXT = "TXT"
    CAA = "CAA"
    DNSKEY = "DNSKEY"
    DS = "DS"
    RRSIG = "RRSIG"
    NSEC = "NSEC"
    NSEC3 = "NSEC3"
    ANY = "ANY"


class ServiceState(str, Enum):
    """Service states."""

    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    RELOADING = "reloading"
    ERROR = "error"
    UNKNOWN = "unknown"


class HealthState(str, Enum):
    """Health check states."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class MigrationState(str, Enum):
    """Migration states."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


# ============================================================================
# DNS Query/Response Models
# ============================================================================


class DNSQuery(BaseModel):
    """DNS query request."""

    name: str = Field(..., description="Domain name to query")
    record_type: RecordType = Field(default=RecordType.A, description="Record type")
    server: str | None = Field(default=None, description="DNS server to query")
    port: int = Field(default=53, description="DNS port")
    timeout: float = Field(default=5.0, description="Query timeout in seconds")
    use_tcp: bool = Field(default=False, description="Use TCP instead of UDP")
    dnssec: bool = Field(default=False, description="Request DNSSEC records")


class DNSRecord(BaseModel):
    """Single DNS record."""

    name: str
    record_type: RecordType
    ttl: int
    value: str
    priority: int | None = None  # For MX, SRV
    weight: int | None = None  # For SRV
    port: int | None = None  # For SRV


class DNSResponse(BaseModel):
    """DNS query response."""

    query: DNSQuery
    records: list[DNSRecord] = Field(default_factory=list)
    rcode: str = Field(default="NOERROR", description="Response code")
    flags: list[str] = Field(default_factory=list)
    query_time_ms: float = Field(..., description="Query time in milliseconds")
    server: str = Field(..., description="Server that responded")
    dnssec_valid: bool | None = Field(default=None, description="DNSSEC validation result")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    raw_response: dict[str, Any] | None = Field(default=None, description="Raw DNS response")


class BulkQueryResult(BaseModel):
    """Results from bulk query operation."""

    total: int
    successful: int
    failed: int
    responses: list[DNSResponse]
    errors: list[dict[str, Any]]
    duration_ms: float


# ============================================================================
# Cache Models
# ============================================================================


class CacheEntry(BaseModel):
    """Single cache entry."""

    name: str
    record_type: RecordType
    ttl_remaining: int
    original_ttl: int
    value: str
    cached_at: datetime


class CacheStats(BaseModel):
    """Cache statistics."""

    resolver: ResolverType
    size: int = Field(..., description="Number of cached entries")
    size_bytes: int | None = Field(default=None, description="Cache size in bytes")
    hits: int = Field(default=0, description="Cache hits")
    misses: int = Field(default=0, description="Cache misses")
    hit_ratio: float = Field(default=0.0, description="Hit ratio (0-1)")
    evictions: int = Field(default=0, description="Number of evictions")
    max_size: int | None = Field(default=None, description="Maximum cache size")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CachePurgeResult(BaseModel):
    """Result of cache purge operation."""

    purged_count: int
    domain: str | None = None
    record_type: RecordType | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Service Models
# ============================================================================


class ServiceStatus(BaseModel):
    """Service status information."""

    resolver: ResolverType
    state: ServiceState
    pid: int | None = None
    uptime_seconds: int | None = None
    version: str | None = None
    config_path: str | None = None
    listening_addresses: list[str] = Field(default_factory=list)
    plugins: list[str] = Field(default_factory=list)  # CoreDNS plugins
    modules: list[str] = Field(default_factory=list)  # Unbound modules
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ServiceControlResult(BaseModel):
    """Result of service control operation."""

    action: str  # start, stop, restart, reload
    success: bool
    message: str
    previous_state: ServiceState
    current_state: ServiceState
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Health Models
# ============================================================================


class UpstreamHealth(BaseModel):
    """Health status of an upstream resolver."""

    address: str
    port: int
    healthy: bool
    latency_ms: float | None = None
    last_check: datetime
    consecutive_failures: int = 0
    error: str | None = None


class HealthStatus(BaseModel):
    """Complete health status."""

    resolver: ResolverType
    state: HealthState
    service_status: ServiceStatus
    cache_stats: CacheStats | None = None
    upstreams: list[UpstreamHealth] = Field(default_factory=list)
    query_rate: float | None = Field(default=None, description="Queries per second")
    error_rate: float | None = Field(default=None, description="Errors per second")
    latency_avg_ms: float | None = Field(default=None, description="Average latency")
    latency_p99_ms: float | None = Field(default=None, description="P99 latency")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Compare Models
# ============================================================================


class RecordDiff(BaseModel):
    """Difference between DNS records."""

    field: str  # name, type, ttl, value, etc.
    source_value: Any
    target_value: Any


class ResponseDiff(BaseModel):
    """Detailed diff between two DNS responses."""

    query: DNSQuery
    match: bool
    rcode_match: bool
    record_count_match: bool
    records_match: bool
    timing_diff_ms: float
    source_response: DNSResponse
    target_response: DNSResponse
    record_diffs: list[RecordDiff] = Field(default_factory=list)
    missing_in_source: list[DNSRecord] = Field(default_factory=list)
    missing_in_target: list[DNSRecord] = Field(default_factory=list)


class CompareResult(BaseModel):
    """Result of comparing two resolvers."""

    source: ResolverType
    target: ResolverType
    queries_tested: int
    matches: int
    mismatches: int
    match_ratio: float
    avg_timing_diff_ms: float
    diffs: list[ResponseDiff] = Field(default_factory=list)
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for migration"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ShadowModeConfig(BaseModel):
    """Configuration for shadow mode comparison."""

    source: ResolverType
    target: ResolverType
    sample_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Query sample rate")
    alert_on_mismatch: bool = Field(default=True)
    alert_threshold: float = Field(default=0.01, description="Alert if mismatch rate exceeds")
    log_all_queries: bool = Field(default=False)
    duration_seconds: int | None = Field(default=None, description="Run duration, None=indefinite")


class ShadowModeReport(BaseModel):
    """Report from shadow mode operation."""

    config: ShadowModeConfig
    started_at: datetime
    ended_at: datetime | None = None
    queries_processed: int = 0
    matches: int = 0
    mismatches: int = 0
    errors: int = 0
    mismatch_rate: float = 0.0
    sample_mismatches: list[ResponseDiff] = Field(default_factory=list, max_length=100)


# ============================================================================
# Configuration Models
# ============================================================================


class ConfigValidationError(BaseModel):
    """Configuration validation error."""

    line: int | None = None
    column: int | None = None
    message: str
    severity: str = "error"  # error, warning, info


class ConfigValidationResult(BaseModel):
    """Result of configuration validation."""

    valid: bool
    errors: list[ConfigValidationError] = Field(default_factory=list)
    warnings: list[ConfigValidationError] = Field(default_factory=list)
    config_path: str | None = None


class ConfigDiff(BaseModel):
    """Diff between two configurations."""

    source_path: str
    target_path: str
    additions: list[str] = Field(default_factory=list)
    deletions: list[str] = Field(default_factory=list)
    modifications: list[dict[str, Any]] = Field(default_factory=list)
    is_different: bool


# ============================================================================
# Migration Models
# ============================================================================


class PluginMapping(BaseModel):
    """Mapping between CoreDNS plugin and Unbound equivalent."""

    coredns_plugin: str
    unbound_feature: str | None
    notes: str
    supported: bool
    requires_manual: bool = False


class MigrationStep(BaseModel):
    """Single step in migration plan."""

    order: int
    action: str
    description: str
    source_config: str | None = None
    target_config: str | None = None
    reversible: bool = True
    manual_required: bool = False


class MigrationPlan(BaseModel):
    """Complete migration plan."""

    source: ResolverType
    target: ResolverType
    steps: list[MigrationStep]
    plugin_mappings: list[PluginMapping] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    unsupported_features: list[str] = Field(default_factory=list)
    estimated_risk: str = "low"  # low, medium, high
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MigrationStatus(BaseModel):
    """Current migration status."""

    state: MigrationState
    plan: MigrationPlan
    current_step: int
    completed_steps: list[int] = Field(default_factory=list)
    failed_step: int | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    validation_result: CompareResult | None = None


class MigrationRollback(BaseModel):
    """Rollback information."""

    backup_path: str
    original_config: str
    rollback_steps: list[MigrationStep]
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Kubernetes Models
# ============================================================================


class K8sNamespace(BaseModel):
    """Kubernetes namespace."""

    name: str
    labels: dict[str, str] = Field(default_factory=dict)


class K8sConfigMap(BaseModel):
    """Kubernetes ConfigMap for DNS configuration."""

    name: str
    namespace: str
    data: dict[str, str]
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)


class K8sPodDNSTest(BaseModel):
    """DNS test from a specific pod."""

    pod_name: str
    namespace: str
    query: DNSQuery
    response: DNSResponse | None = None
    error: str | None = None
    success: bool


class K8sServiceDiscovery(BaseModel):
    """Discovered Kubernetes service."""

    name: str
    namespace: str
    cluster_ip: str | None
    external_ips: list[str] = Field(default_factory=list)
    ports: list[dict[str, Any]] = Field(default_factory=list)
    dns_name: str  # service.namespace.svc.cluster.local


# ============================================================================
# Metrics Models
# ============================================================================


class MetricValue(BaseModel):
    """Single metric value."""

    name: str
    value: float
    labels: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MetricsSnapshot(BaseModel):
    """Snapshot of all metrics."""

    resolver: ResolverType
    metrics: list[MetricValue]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
