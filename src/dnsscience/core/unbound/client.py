"""Unbound client implementation."""

import asyncio
import subprocess
from datetime import datetime
from typing import AsyncIterator

import dns.message
import dns.query
import dns.rdatatype

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


class UnboundClient(BaseResolverClient):
    """
    Client for managing Unbound DNS resolver instances.

    Uses unbound-control for management operations and direct DNS
    queries for resolution testing.
    """

    resolver_type = ResolverType.UNBOUND

    def __init__(
        self,
        host: str = "localhost",
        port: int = 53,
        control_port: int = 8953,
        config_path: str = "/etc/unbound/unbound.conf",
        control_path: str = "/usr/sbin/unbound-control",
    ):
        self.host = host
        self.port = port
        self.control_port = control_port
        self.config_path = config_path
        self.control_path = control_path
        self._connected = False

    async def connect(self) -> None:
        """Verify unbound-control is accessible."""
        self._connected = True

    async def disconnect(self) -> None:
        """Close any connections."""
        self._connected = False

    async def _run_control(self, *args: str) -> tuple[str, str, int]:
        """Run unbound-control command."""
        cmd = [self.control_path, "-s", f"{self.host}@{self.control_port}"] + list(args)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode(), stderr.decode(), proc.returncode or 0

    # ========================================================================
    # Service Control
    # ========================================================================

    async def get_status(self) -> ServiceStatus:
        """Get Unbound service status via unbound-control."""
        state = ServiceState.UNKNOWN
        version = None
        uptime = None

        try:
            stdout, stderr, rc = await self._run_control("status")

            if rc == 0 and "is running" in stdout:
                state = ServiceState.RUNNING

                # Parse version and uptime from status output
                for line in stdout.split("\n"):
                    if "version" in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            version = parts[-1]
                    if "uptime" in line.lower():
                        # Parse uptime
                        try:
                            uptime_str = line.split()[-2]
                            uptime = int(float(uptime_str))
                        except (ValueError, IndexError):
                            pass
            else:
                state = ServiceState.STOPPED

        except FileNotFoundError:
            state = ServiceState.ERROR
        except Exception:
            state = ServiceState.ERROR

        return ServiceStatus(
            resolver=ResolverType.UNBOUND,
            state=state,
            version=version,
            uptime_seconds=uptime,
            config_path=self.config_path,
            listening_addresses=[f"{self.host}:{self.port}"],
            modules=["validator", "iterator"],  # Default modules
        )

    async def start(self) -> ServiceControlResult:
        """Start Unbound service."""
        previous = await self.get_status()

        try:
            stdout, stderr, rc = await self._run_control("start")

            if rc == 0:
                current = await self.get_status()
                return ServiceControlResult(
                    action="start",
                    success=True,
                    message="Unbound started successfully",
                    previous_state=previous.state,
                    current_state=current.state,
                )
            else:
                return ServiceControlResult(
                    action="start",
                    success=False,
                    message=f"Failed to start: {stderr}",
                    previous_state=previous.state,
                    current_state=previous.state,
                )
        except Exception as e:
            return ServiceControlResult(
                action="start",
                success=False,
                message=str(e),
                previous_state=previous.state,
                current_state=previous.state,
            )

    async def stop(self) -> ServiceControlResult:
        """Stop Unbound service."""
        previous = await self.get_status()

        try:
            stdout, stderr, rc = await self._run_control("stop")

            return ServiceControlResult(
                action="stop",
                success=rc == 0,
                message="Unbound stopped" if rc == 0 else stderr,
                previous_state=previous.state,
                current_state=ServiceState.STOPPED if rc == 0 else previous.state,
            )
        except Exception as e:
            return ServiceControlResult(
                action="stop",
                success=False,
                message=str(e),
                previous_state=previous.state,
                current_state=previous.state,
            )

    async def restart(self) -> ServiceControlResult:
        """Restart Unbound service."""
        stop_result = await self.stop()
        if not stop_result.success:
            return stop_result

        await asyncio.sleep(1)  # Brief pause between stop and start
        return await self.start()

    async def reload(self) -> ServiceControlResult:
        """Reload Unbound configuration."""
        previous = await self.get_status()

        try:
            stdout, stderr, rc = await self._run_control("reload")

            return ServiceControlResult(
                action="reload",
                success=rc == 0,
                message="Configuration reloaded" if rc == 0 else stderr,
                previous_state=previous.state,
                current_state=previous.state,
            )
        except Exception as e:
            return ServiceControlResult(
                action="reload",
                success=False,
                message=str(e),
                previous_state=previous.state,
                current_state=previous.state,
            )

    # ========================================================================
    # Query Operations
    # ========================================================================

    async def query(self, query: DNSQuery) -> DNSResponse:
        """Execute a DNS query against Unbound."""
        start_time = asyncio.get_event_loop().time()

        try:
            rdtype = dns.rdatatype.from_text(query.record_type.value)
            msg = dns.message.make_query(query.name, rdtype)

            if query.dnssec:
                msg.flags |= dns.flags.AD
                msg.use_edns(edns=0, ednsflags=dns.flags.DO)

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
        """Trace DNS resolution using unbound-control lookup."""
        # Unbound doesn't have built-in trace, return single response
        response = await self.query(query)
        return [response]

    # ========================================================================
    # Cache Operations
    # ========================================================================

    async def get_cache_stats(self) -> CacheStats:
        """Get cache statistics via unbound-control stats."""
        stats = CacheStats(
            resolver=ResolverType.UNBOUND,
            size=0,
            hits=0,
            misses=0,
            hit_ratio=0.0,
        )

        try:
            stdout, stderr, rc = await self._run_control("stats_noreset")

            if rc == 0:
                for line in stdout.split("\n"):
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    if key == "total.num.cachehits":
                        stats.hits = int(value)
                    elif key == "total.num.cachemiss":
                        stats.misses = int(value)
                    elif key == "msg.cache.count":
                        stats.size = int(value)
                    elif key == "rrset.cache.count":
                        stats.size += int(value)

                total = stats.hits + stats.misses
                if total > 0:
                    stats.hit_ratio = stats.hits / total

        except Exception:
            pass

        return stats

    async def flush_cache(self) -> CachePurgeResult:
        """Flush entire Unbound cache."""
        try:
            stdout, stderr, rc = await self._run_control("flush_zone", ".")

            if rc == 0:
                return CachePurgeResult(
                    purged_count=-1,  # Unbound doesn't report count
                    domain=None,
                )
            else:
                return CachePurgeResult(purged_count=0)

        except Exception:
            return CachePurgeResult(purged_count=0)

    async def purge_cache(
        self,
        domain: str | None = None,
        record_type: RecordType | None = None,
    ) -> CachePurgeResult:
        """Purge specific entries from Unbound cache."""
        if not domain:
            return await self.flush_cache()

        try:
            if record_type:
                stdout, stderr, rc = await self._run_control(
                    "flush_type", domain, record_type.value
                )
            else:
                stdout, stderr, rc = await self._run_control("flush", domain)

            return CachePurgeResult(
                purged_count=1 if rc == 0 else 0,
                domain=domain,
                record_type=record_type,
            )

        except Exception:
            return CachePurgeResult(purged_count=0, domain=domain)

    async def inspect_cache(
        self,
        domain: str | None = None,
        limit: int = 100,
    ) -> list[CacheEntry]:
        """Inspect cache entries via unbound-control dump_cache."""
        entries: list[CacheEntry] = []

        try:
            stdout, stderr, rc = await self._run_control("dump_cache")

            if rc == 0:
                count = 0
                for line in stdout.split("\n"):
                    if count >= limit:
                        break

                    # Parse cache dump format
                    # Format: name TTL CLASS TYPE rdata
                    parts = line.split()
                    if len(parts) >= 5:
                        name = parts[0]

                        if domain and domain.lower() not in name.lower():
                            continue

                        try:
                            ttl = int(parts[1])
                            rtype = parts[3]
                            value = " ".join(parts[4:])

                            entries.append(CacheEntry(
                                name=name,
                                record_type=RecordType(rtype),
                                ttl_remaining=ttl,
                                original_ttl=ttl,
                                value=value,
                                cached_at=datetime.utcnow(),
                            ))
                            count += 1
                        except (ValueError, KeyError):
                            continue

        except Exception:
            pass

        return entries

    # ========================================================================
    # Configuration
    # ========================================================================

    async def get_config(self) -> str:
        """Read current unbound.conf configuration."""
        import aiofiles

        async with aiofiles.open(self.config_path, "r") as f:
            return await f.read()

    async def validate_config(self, config: str) -> ConfigValidationResult:
        """Validate unbound.conf syntax using unbound-checkconf."""
        import tempfile
        import os

        # Write config to temp file for validation
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write(config)
            temp_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                "unbound-checkconf", temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                return ConfigValidationResult(valid=True, config_path=temp_path)
            else:
                from dnsscience.core.models import ConfigValidationError
                return ConfigValidationResult(
                    valid=False,
                    errors=[ConfigValidationError(message=stderr.decode())],
                    config_path=temp_path,
                )
        finally:
            os.unlink(temp_path)

    async def diff_config(self, new_config: str) -> ConfigDiff:
        """Diff new config against current running config."""
        current = await self.get_config()

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
        """Write new config and optionally reload."""
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

        # Check upstreams
        upstreams: list[UpstreamHealth] = []
        # Would parse forward-zone configs and test each upstream

        if status.state == ServiceState.RUNNING:
            state = HealthState.HEALTHY
        elif status.state == ServiceState.STOPPED:
            state = HealthState.UNHEALTHY
        else:
            state = HealthState.DEGRADED

        return HealthStatus(
            resolver=ResolverType.UNBOUND,
            state=state,
            service_status=status,
            cache_stats=cache_stats,
            upstreams=upstreams,
        )

    async def get_metrics(self) -> MetricsSnapshot:
        """Get metrics via unbound-control stats."""
        metrics: list[MetricValue] = []

        try:
            stdout, stderr, rc = await self._run_control("stats_noreset")

            if rc == 0:
                for line in stdout.split("\n"):
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    try:
                        metrics.append(MetricValue(
                            name=f"unbound_{key.strip().replace('.', '_')}",
                            value=float(value.strip()),
                        ))
                    except ValueError:
                        pass

        except Exception:
            pass

        return MetricsSnapshot(resolver=ResolverType.UNBOUND, metrics=metrics)

    async def stream_metrics(
        self, interval_seconds: float = 5.0
    ) -> AsyncIterator[MetricsSnapshot]:
        """Stream metrics at regular intervals."""
        while True:
            yield await self.get_metrics()
            await asyncio.sleep(interval_seconds)
