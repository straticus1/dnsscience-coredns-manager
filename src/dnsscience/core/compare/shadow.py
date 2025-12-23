"""Shadow mode for continuous DNS comparison."""

import asyncio
import random
from datetime import datetime
from typing import AsyncIterator, Callable

from dnsscience.core.base import BaseResolverClient
from dnsscience.core.compare.engine import CompareEngine
from dnsscience.core.models import (
    DNSQuery,
    ResponseDiff,
    ShadowModeConfig,
    ShadowModeReport,
)


class ShadowMode:
    """
    Shadow mode operation for continuous resolver comparison.

    Runs alongside production traffic, comparing responses between
    source (production) and target (candidate) resolvers.

    Use cases:
    - Pre-migration validation
    - Ongoing consistency monitoring
    - A/B testing resolver configurations
    """

    def __init__(
        self,
        source_client: BaseResolverClient,
        target_client: BaseResolverClient,
        config: ShadowModeConfig | None = None,
    ):
        self.source = source_client
        self.target = target_client
        self.config = config or ShadowModeConfig(
            source=source_client.resolver_type,
            target=target_client.resolver_type,
        )
        self.engine = CompareEngine(source_client, target_client)

        self._running = False
        self._report: ShadowModeReport | None = None
        self._callbacks: list[Callable[[ResponseDiff], None]] = []

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def report(self) -> ShadowModeReport | None:
        return self._report

    def on_mismatch(self, callback: Callable[[ResponseDiff], None]) -> None:
        """Register callback for mismatches."""
        self._callbacks.append(callback)

    async def start(self) -> None:
        """Start shadow mode operation."""
        self._running = True
        self._report = ShadowModeReport(
            config=self.config,
            started_at=datetime.utcnow(),
        )

    async def stop(self) -> ShadowModeReport:
        """Stop shadow mode and return final report."""
        self._running = False
        if self._report:
            self._report.ended_at = datetime.utcnow()
        return self._report or ShadowModeReport(
            config=self.config,
            started_at=datetime.utcnow(),
            ended_at=datetime.utcnow(),
        )

    async def process_query(self, query: DNSQuery) -> ResponseDiff | None:
        """
        Process a single query in shadow mode.

        Returns diff if sampled, None if skipped.
        """
        if not self._running:
            return None

        # Apply sampling
        if random.random() > self.config.sample_rate:
            return None

        # Compare
        diff = await self.engine.compare_single(query)

        # Update report
        if self._report:
            self._report.queries_processed += 1
            if diff.match:
                self._report.matches += 1
            else:
                self._report.mismatches += 1
                # Store sample of mismatches
                if len(self._report.sample_mismatches) < 100:
                    self._report.sample_mismatches.append(diff)

                # Trigger callbacks
                for callback in self._callbacks:
                    try:
                        callback(diff)
                    except Exception:
                        pass  # Don't let callback errors affect shadow mode

            # Update mismatch rate
            total = self._report.matches + self._report.mismatches
            if total > 0:
                self._report.mismatch_rate = self._report.mismatches / total

            # Check alert threshold
            if (
                self.config.alert_on_mismatch
                and self._report.mismatch_rate > self.config.alert_threshold
                and total >= 100  # Wait for statistical significance
            ):
                await self._trigger_alert()

        return diff

    async def run_continuous(
        self,
        query_source: AsyncIterator[DNSQuery],
    ) -> AsyncIterator[ResponseDiff]:
        """
        Run shadow mode continuously from a query source.

        Args:
            query_source: Async iterator yielding DNS queries
                         (e.g., from query logs, network tap, etc.)

        Yields:
            ResponseDiff for each processed query
        """
        await self.start()

        start_time = datetime.utcnow()

        try:
            async for query in query_source:
                # Check duration limit
                if self.config.duration_seconds:
                    elapsed = (datetime.utcnow() - start_time).total_seconds()
                    if elapsed >= self.config.duration_seconds:
                        break

                diff = await self.process_query(query)
                if diff:
                    yield diff

        finally:
            await self.stop()

    async def run_from_file(self, filepath: str) -> ShadowModeReport:
        """Run shadow mode from a query file."""
        import aiofiles

        from dnsscience.core.models import RecordType

        await self.start()

        try:
            async with aiofiles.open(filepath, "r") as f:
                async for line in f:
                    if not self._running:
                        break

                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split()
                    query = DNSQuery(
                        name=parts[0],
                        record_type=RecordType(parts[1].upper()) if len(parts) > 1 else RecordType.A,
                    )

                    await self.process_query(query)

        finally:
            return await self.stop()

    async def _trigger_alert(self) -> None:
        """Trigger alert when mismatch rate exceeds threshold."""
        # This would integrate with alerting systems (PagerDuty, Slack, etc.)
        # For now, just log
        if self._report:
            print(
                f"ALERT: Shadow mode mismatch rate {self._report.mismatch_rate:.2%} "
                f"exceeds threshold {self.config.alert_threshold:.2%}"
            )


class QueryLogTap:
    """
    Tap into DNS query logs to provide queries for shadow mode.

    Supports:
    - CoreDNS query logs
    - Unbound query logs
    - tcpdump/pcap files
    """

    def __init__(self, log_path: str, log_format: str = "coredns"):
        self.log_path = log_path
        self.log_format = log_format

    async def stream(self) -> AsyncIterator[DNSQuery]:
        """Stream queries from log file (tail -f style)."""
        import aiofiles

        from dnsscience.core.models import RecordType

        async with aiofiles.open(self.log_path, "r") as f:
            # Seek to end
            await f.seek(0, 2)

            while True:
                line = await f.readline()
                if not line:
                    await asyncio.sleep(0.1)
                    continue

                query = self._parse_log_line(line)
                if query:
                    yield query

    def _parse_log_line(self, line: str) -> DNSQuery | None:
        """Parse a log line into a DNSQuery."""
        from dnsscience.core.models import RecordType

        if self.log_format == "coredns":
            return self._parse_coredns_log(line)
        elif self.log_format == "unbound":
            return self._parse_unbound_log(line)
        return None

    def _parse_coredns_log(self, line: str) -> DNSQuery | None:
        """
        Parse CoreDNS query log format.

        Example: [INFO] 192.168.1.1:12345 - 12345 "A IN example.com. udp 512 false 4096" NOERROR qr,rd,ra 0.001s
        """
        from dnsscience.core.models import RecordType

        try:
            # Extract query part between quotes
            if '"' not in line:
                return None

            query_part = line.split('"')[1]
            parts = query_part.split()

            if len(parts) < 3:
                return None

            record_type = parts[0]
            # parts[1] is class (IN)
            name = parts[2].rstrip(".")

            return DNSQuery(
                name=name,
                record_type=RecordType(record_type),
            )
        except Exception:
            return None

    def _parse_unbound_log(self, line: str) -> DNSQuery | None:
        """
        Parse Unbound query log format.

        Example: [1234567890] unbound[12345:0] info: 192.168.1.1 example.com. A IN
        """
        from dnsscience.core.models import RecordType

        try:
            parts = line.split()
            # Find the query components
            for i, part in enumerate(parts):
                if part.endswith(".") and i + 2 < len(parts):
                    name = part.rstrip(".")
                    record_type = parts[i + 1]
                    return DNSQuery(
                        name=name,
                        record_type=RecordType(record_type),
                    )
        except Exception:
            return None

        return None
