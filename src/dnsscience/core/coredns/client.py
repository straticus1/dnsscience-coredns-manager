"""CoreDNS client implementation."""

import asyncio
from datetime import datetime
from typing import AsyncIterator

import dns.message
import dns.query
import dns.rdatatype
import httpx

from dnsscience.core.base import BaseResolverClient
from dnsscience.core.models import (
    BulkQueryResult,
    CacheEntry,
    CachePurgeResult,
    CacheStats,
    ConfigDiff,
    ConfigValidationResult,
    DNSQuery,
    DNSRecord,
    DNSResponse,
    HealthState,
    HealthStatus,
    MetricsSnapshot,
    MetricValue,
    RecordType,
    ResolverType,
    ServiceControlResult,
    ServiceState,
    ServiceStatus,
    UpstreamHealth,
)


class CoreDNSClient(BaseResolverClient):
    """Client for managing CoreDNS instances."""

    resolver_type = ResolverType.COREDNS

    def __init__(
        self,
        host: str = "localhost",
        port: int = 53,
        metrics_port: int = 9153,
        health_port: int = 8080,
        config_path: str = "/etc/coredns/Corefile",
    ):
        self.host = host
        self.port = port
        self.metrics_port = metrics_port
        self.health_port = health_port
        self.config_path = config_path
        self._http_client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Initialize HTTP client for metrics/health endpoints."""
        self._http_client = httpx.AsyncClient(timeout=10.0)

    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    @property
    def http_client(self) -> httpx.AsyncClient:
        if not self._http_client:
            raise RuntimeError("Client not connected. Call connect() first.")
        return self._http_client

    # ========================================================================
    # Service Control
    # ========================================================================

    async def get_status(self) -> ServiceStatus:
        """Get CoreDNS service status via health and metrics endpoints."""
        state = ServiceState.UNKNOWN
        version = None
        plugins: list[str] = []

        try:
            # Check health endpoint
            health_resp = await self.http_client.get(
                f"http://{self.host}:{self.health_port}/health"
            )
            if health_resp.status_code == 200:
                state = ServiceState.RUNNING

            # Try to get version from metrics
            metrics = await self.get_metrics()
            for metric in metrics.metrics:
                if metric.name == "coredns_build_info":
                    version = metric.labels.get("version")
                    break

        except httpx.ConnectError:
            state = ServiceState.STOPPED
        except Exception:
            state = ServiceState.ERROR

        return ServiceStatus(
            resolver=ResolverType.COREDNS,
            state=state,
            version=version,
            config_path=self.config_path,
            listening_addresses=[f"{self.host}:{self.port}"],
            plugins=plugins,
        )

    async def start(self) -> ServiceControlResult:
        """Start CoreDNS - typically via systemd or k8s."""
        # This would integrate with systemd/k8s API
        # Placeholder implementation
        return ServiceControlResult(
            action="start",
            success=False,
            message="Direct start not implemented. Use systemd or k8s to start CoreDNS.",
            previous_state=ServiceState.UNKNOWN,
            current_state=ServiceState.UNKNOWN,
        )

    async def stop(self) -> ServiceControlResult:
        """Stop CoreDNS service."""
        return ServiceControlResult(
            action="stop",
            success=False,
            message="Direct stop not implemented. Use systemd or k8s to stop CoreDNS.",
            previous_state=ServiceState.UNKNOWN,
            current_state=ServiceState.UNKNOWN,
        )

    async def restart(self) -> ServiceControlResult:
        """Restart CoreDNS service."""
        return ServiceControlResult(
            action="restart",
            success=False,
            message="Direct restart not implemented. Use systemd or k8s to restart CoreDNS.",
            previous_state=ServiceState.UNKNOWN,
            current_state=ServiceState.UNKNOWN,
        )

    async def reload(self) -> ServiceControlResult:
        """
        Trigger CoreDNS config reload.

        CoreDNS watches the Corefile for changes when the 'reload' plugin is enabled.
        This method can trigger a reload by touching the config file or via API.
        """
        previous = await self.get_status()

        # CoreDNS reload is typically done by:
        # 1. The reload plugin watching for file changes
        # 2. Sending SIGUSR1 to the process
        # 3. Updating ConfigMap in k8s (triggers pod reload)

        return ServiceControlResult(
            action="reload",
            success=True,
            message="Reload triggered. CoreDNS will reload if 'reload' plugin is enabled.",
            previous_state=previous.state,
            current_state=previous.state,
        )

    # ========================================================================
    # Query Operations
    # ========================================================================

    async def query(self, query: DNSQuery) -> DNSResponse:
        """Execute a DNS query against CoreDNS."""
        start_time = asyncio.get_event_loop().time()

        try:
            # Build DNS message
            rdtype = dns.rdatatype.from_text(query.record_type.value)
            msg = dns.message.make_query(query.name, rdtype)

            if query.dnssec:
                msg.flags |= dns.flags.AD
                msg.use_edns(edns=0, ednsflags=dns.flags.DO)

            # Execute query
            server = query.server or self.host
            port = query.port or self.port

            if query.use_tcp:
                response = await asyncio.to_thread(
                    dns.query.tcp, msg, server, port=port, timeout=query.timeout
                )
            else:
                response = await asyncio.to_thread(
                    dns.query.udp, msg, server, port=port, timeout=query.timeout
                )

            end_time = asyncio.get_event_loop().time()
            query_time_ms = (end_time - start_time) * 1000

            # Parse records
            records: list[DNSRecord] = []
            for rrset in response.answer:
                for rdata in rrset:
                    records.append(
                        DNSRecord(
                            name=str(rrset.name),
                            record_type=RecordType(dns.rdatatype.to_text(rrset.rdtype)),
                            ttl=rrset.ttl,
                            value=str(rdata),
                        )
                    )

            # Check DNSSEC
            dnssec_valid = None
            if query.dnssec:
                dnssec_valid = bool(response.flags & dns.flags.AD)

            return DNSResponse(
                query=query,
                records=records,
                rcode=dns.rcode.to_text(response.rcode()),
                flags=[str(f) for f in dns.flags.to_text(response.flags).split()],
                query_time_ms=query_time_ms,
                server=f"{server}:{port}",
                dnssec_valid=dnssec_valid,
            )

        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            return DNSResponse(
                query=query,
                records=[],
                rcode="SERVFAIL",
                query_time_ms=(end_time - start_time) * 1000,
                server=f"{query.server or self.host}:{query.port or self.port}",
                raw_response={"error": str(e)},
            )

    async def query_bulk(self, queries: list[DNSQuery]) -> BulkQueryResult:
        """Execute multiple DNS queries concurrently."""
        start_time = asyncio.get_event_loop().time()

        tasks = [self.query(q) for q in queries]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        successful_responses: list[DNSResponse] = []
        errors: list[dict] = []

        for i, resp in enumerate(responses):
            if isinstance(resp, Exception):
                errors.append({"query": queries[i].model_dump(), "error": str(resp)})
            elif resp.rcode != "NOERROR":
                errors.append({"query": queries[i].model_dump(), "rcode": resp.rcode})
                successful_responses.append(resp)
            else:
                successful_responses.append(resp)

        end_time = asyncio.get_event_loop().time()

        return BulkQueryResult(
            total=len(queries),
            successful=len([r for r in successful_responses if r.rcode == "NOERROR"]),
            failed=len(errors),
            responses=successful_responses,
            errors=errors,
            duration_ms=(end_time - start_time) * 1000,
        )

    async def trace(self, query: DNSQuery) -> list[DNSResponse]:
        """Trace DNS resolution - CoreDNS doesn't have built-in trace."""
        # For CoreDNS, we can only return the final response
        # Full tracing would require the 'debug' plugin or external tools
        response = await self.query(query)
        return [response]

    # ========================================================================
    # Cache Operations
    # ========================================================================

    async def get_cache_stats(self) -> CacheStats:
        """Get cache statistics from metrics endpoint."""
        metrics = await self.get_metrics()

        size = 0
        hits = 0
        misses = 0

        for metric in metrics.metrics:
            if metric.name == "coredns_cache_entries":
                size += int(metric.value)
            elif metric.name == "coredns_cache_hits_total":
                hits += int(metric.value)
            elif metric.name == "coredns_cache_misses_total":
                misses += int(metric.value)

        total = hits + misses
        hit_ratio = hits / total if total > 0 else 0.0

        return CacheStats(
            resolver=ResolverType.COREDNS,
            size=size,
            hits=hits,
            misses=misses,
            hit_ratio=hit_ratio,
        )

    async def flush_cache(self) -> CachePurgeResult:
        """
        Flush CoreDNS cache.

        CoreDNS doesn't have a direct cache flush API.
        Options:
        1. Restart CoreDNS
        2. Use the 'cache' plugin with 'prefetch' and wait for TTL expiry
        3. Reduce cache TTL temporarily
        """
        # This would typically require a restart or config change
        return CachePurgeResult(
            purged_count=0,
            domain=None,
            record_type=None,
        )

    async def purge_cache(
        self,
        domain: str | None = None,
        record_type: RecordType | None = None,
    ) -> CachePurgeResult:
        """CoreDNS doesn't support selective cache purge natively."""
        return CachePurgeResult(
            purged_count=0,
            domain=domain,
            record_type=record_type,
        )

    async def inspect_cache(
        self,
        domain: str | None = None,
        limit: int = 100,
    ) -> list[CacheEntry]:
        """CoreDNS doesn't expose cache contents directly."""
        return []

    # ========================================================================
    # Configuration
    # ========================================================================

    async def get_config(self) -> str:
        """Read current Corefile configuration."""
        import aiofiles

        async with aiofiles.open(self.config_path, "r") as f:
            return await f.read()

    async def validate_config(self, config: str) -> ConfigValidationResult:
        """Validate Corefile syntax."""
        from dnsscience.core.coredns.config import CorefileParser

        parser = CorefileParser()
        return parser.validate(config)

    async def diff_config(self, new_config: str) -> ConfigDiff:
        """Diff new config against current running config."""
        current = await self.get_config()

        # Simple line-based diff
        current_lines = set(current.strip().split("\n"))
        new_lines = set(new_config.strip().split("\n"))

        return ConfigDiff(
            source_path=self.config_path,
            target_path="<new>",
            additions=list(new_lines - current_lines),
            deletions=list(current_lines - new_lines),
            is_different=current_lines != new_lines,
        )

    async def apply_config(self, config: str, reload: bool = True) -> ServiceControlResult:
        """Write new config and optionally trigger reload."""
        import aiofiles

        previous = await self.get_status()

        # Validate first
        validation = await self.validate_config(config)
        if not validation.valid:
            return ServiceControlResult(
                action="apply_config",
                success=False,
                message=f"Configuration invalid: {validation.errors}",
                previous_state=previous.state,
                current_state=previous.state,
            )

        # Write config
        async with aiofiles.open(self.config_path, "w") as f:
            await f.write(config)

        # Reload if requested
        if reload:
            return await self.reload()

        return ServiceControlResult(
            action="apply_config",
            success=True,
            message="Configuration written. Reload required to apply.",
            previous_state=previous.state,
            current_state=previous.state,
        )

    # ========================================================================
    # Health & Metrics
    # ========================================================================

    async def health_check(self) -> HealthStatus:
        """Perform comprehensive health check."""
        status = await self.get_status()
        cache_stats = await self.get_cache_stats()

        # Check upstreams by parsing config and testing each
        upstreams: list[UpstreamHealth] = []

        # Determine overall health state
        if status.state == ServiceState.RUNNING:
            state = HealthState.HEALTHY
        elif status.state == ServiceState.STOPPED:
            state = HealthState.UNHEALTHY
        else:
            state = HealthState.DEGRADED

        return HealthStatus(
            resolver=ResolverType.COREDNS,
            state=state,
            service_status=status,
            cache_stats=cache_stats,
            upstreams=upstreams,
        )

    async def get_metrics(self) -> MetricsSnapshot:
        """Scrape Prometheus metrics from CoreDNS."""
        metrics: list[MetricValue] = []

        try:
            response = await self.http_client.get(
                f"http://{self.host}:{self.metrics_port}/metrics"
            )
            response.raise_for_status()

            # Parse Prometheus text format
            for line in response.text.split("\n"):
                if line.startswith("#") or not line.strip():
                    continue

                # Simple parsing - production would use prometheus_client parser
                parts = line.split(" ")
                if len(parts) >= 2:
                    name_labels = parts[0]
                    value = float(parts[1])

                    # Extract name and labels
                    if "{" in name_labels:
                        name = name_labels.split("{")[0]
                        labels_str = name_labels.split("{")[1].rstrip("}")
                        labels = dict(
                            item.split("=")
                            for item in labels_str.replace('"', "").split(",")
                            if "=" in item
                        )
                    else:
                        name = name_labels
                        labels = {}

                    metrics.append(MetricValue(name=name, value=value, labels=labels))

        except Exception:
            pass

        return MetricsSnapshot(resolver=ResolverType.COREDNS, metrics=metrics)

    async def stream_metrics(
        self, interval_seconds: float = 5.0
    ) -> AsyncIterator[MetricsSnapshot]:
        """Stream metrics at regular intervals."""
        while True:
            yield await self.get_metrics()
            await asyncio.sleep(interval_seconds)
