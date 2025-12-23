"""Core comparison engine for DNS resolver validation."""

import asyncio
from datetime import datetime

from dnsscience.core.base import BaseResolverClient
from dnsscience.core.compare.differ import ResponseDiffer
from dnsscience.core.models import (
    CompareResult,
    DNSQuery,
    DNSResponse,
    ResolverType,
    ResponseDiff,
)


class CompareEngine:
    """
    Engine for comparing DNS responses between two resolvers.

    Used for migration validation - ensures the target resolver
    returns equivalent results to the source.
    """

    def __init__(
        self,
        source_client: BaseResolverClient,
        target_client: BaseResolverClient,
        timeout: float = 5.0,
        retries: int = 3,
    ):
        self.source = source_client
        self.target = target_client
        self.timeout = timeout
        self.retries = retries
        self.differ = ResponseDiffer()

    async def compare_single(self, query: DNSQuery) -> ResponseDiff:
        """Compare a single query between source and target resolvers."""
        # Query both resolvers in parallel
        source_task = self._query_with_retry(self.source, query)
        target_task = self._query_with_retry(self.target, query)

        source_response, target_response = await asyncio.gather(
            source_task, target_task, return_exceptions=True
        )

        # Handle exceptions as failed responses
        if isinstance(source_response, Exception):
            source_response = self._error_response(query, self.source.resolver_type, source_response)
        if isinstance(target_response, Exception):
            target_response = self._error_response(query, self.target.resolver_type, target_response)

        return self.differ.diff(source_response, target_response)

    async def compare_bulk(self, queries: list[DNSQuery]) -> CompareResult:
        """Compare multiple queries between resolvers."""
        start_time = datetime.utcnow()

        # Run all comparisons concurrently
        tasks = [self.compare_single(q) for q in queries]
        diffs = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        valid_diffs: list[ResponseDiff] = []
        matches = 0
        mismatches = 0
        total_timing_diff = 0.0

        for diff in diffs:
            if isinstance(diff, Exception):
                # Treat exceptions as mismatches
                mismatches += 1
                continue

            valid_diffs.append(diff)
            if diff.match:
                matches += 1
            else:
                mismatches += 1
            total_timing_diff += abs(diff.timing_diff_ms)

        total = matches + mismatches
        match_ratio = matches / total if total > 0 else 0.0
        avg_timing_diff = total_timing_diff / len(valid_diffs) if valid_diffs else 0.0

        # Calculate confidence score
        confidence = self._calculate_confidence(match_ratio, avg_timing_diff, len(queries))

        return CompareResult(
            source=self.source.resolver_type,
            target=self.target.resolver_type,
            queries_tested=len(queries),
            matches=matches,
            mismatches=mismatches,
            match_ratio=match_ratio,
            avg_timing_diff_ms=avg_timing_diff,
            diffs=[d for d in valid_diffs if not d.match],  # Only include mismatches
            confidence_score=confidence,
            timestamp=start_time,
        )

    async def compare_from_file(self, filepath: str) -> CompareResult:
        """Load queries from file and compare."""
        queries = await self._load_queries_from_file(filepath)
        return await self.compare_bulk(queries)

    async def _query_with_retry(
        self, client: BaseResolverClient, query: DNSQuery
    ) -> DNSResponse:
        """Query with retry logic."""
        last_error: Exception | None = None

        for attempt in range(self.retries):
            try:
                return await asyncio.wait_for(
                    client.query(query), timeout=self.timeout
                )
            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Query timed out after {self.timeout}s")
            except Exception as e:
                last_error = e

            # Exponential backoff
            if attempt < self.retries - 1:
                await asyncio.sleep(0.1 * (2**attempt))

        raise last_error or RuntimeError("Query failed with unknown error")

    def _error_response(
        self, query: DNSQuery, resolver: ResolverType, error: Exception
    ) -> DNSResponse:
        """Create an error response for failed queries."""
        return DNSResponse(
            query=query,
            records=[],
            rcode="SERVFAIL",
            query_time_ms=0.0,
            server=str(resolver.value),
            raw_response={"error": str(error)},
        )

    def _calculate_confidence(
        self, match_ratio: float, avg_timing_diff_ms: float, query_count: int
    ) -> float:
        """
        Calculate confidence score for migration readiness.

        Factors:
        - Match ratio (primary factor)
        - Timing consistency
        - Sample size
        """
        # Base confidence from match ratio
        confidence = match_ratio

        # Penalty for high timing variance (more than 100ms average diff)
        if avg_timing_diff_ms > 100:
            timing_penalty = min(0.1, avg_timing_diff_ms / 1000)
            confidence -= timing_penalty

        # Bonus for large sample size (up to 5% boost)
        if query_count >= 1000:
            confidence = min(1.0, confidence + 0.05)
        elif query_count >= 100:
            confidence = min(1.0, confidence + 0.02)

        return max(0.0, min(1.0, confidence))

    async def _load_queries_from_file(self, filepath: str) -> list[DNSQuery]:
        """Load queries from a file (one domain per line)."""
        import aiofiles

        from dnsscience.core.models import RecordType

        queries = []
        async with aiofiles.open(filepath, "r") as f:
            async for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Parse line: domain [type] [server]
                parts = line.split()
                domain = parts[0]
                record_type = RecordType(parts[1].upper()) if len(parts) > 1 else RecordType.A

                queries.append(DNSQuery(name=domain, record_type=record_type))

        return queries


class CompareReport:
    """Generate human-readable comparison reports."""

    def __init__(self, result: CompareResult):
        self.result = result

    def summary(self) -> str:
        """Generate a summary of the comparison."""
        lines = [
            "=" * 60,
            "DNS RESOLVER COMPARISON REPORT",
            "=" * 60,
            f"Source: {self.result.source.value}",
            f"Target: {self.result.target.value}",
            f"Timestamp: {self.result.timestamp.isoformat()}",
            "",
            "RESULTS",
            "-" * 40,
            f"Queries Tested: {self.result.queries_tested}",
            f"Matches: {self.result.matches}",
            f"Mismatches: {self.result.mismatches}",
            f"Match Ratio: {self.result.match_ratio:.2%}",
            f"Avg Timing Diff: {self.result.avg_timing_diff_ms:.2f}ms",
            "",
            "MIGRATION READINESS",
            "-" * 40,
            f"Confidence Score: {self.result.confidence_score:.2%}",
            self._confidence_assessment(),
            "",
        ]

        if self.result.diffs:
            lines.extend(
                [
                    "MISMATCHES (First 10)",
                    "-" * 40,
                ]
            )
            for diff in self.result.diffs[:10]:
                lines.append(f"  Query: {diff.query.name} ({diff.query.record_type.value})")
                lines.append(f"    Source RCODE: {diff.source_response.rcode}")
                lines.append(f"    Target RCODE: {diff.target_response.rcode}")
                if diff.record_diffs:
                    for rd in diff.record_diffs[:3]:
                        lines.append(f"    Diff: {rd.field}: {rd.source_value} → {rd.target_value}")
                lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def _confidence_assessment(self) -> str:
        """Return human-readable confidence assessment."""
        score = self.result.confidence_score
        if score >= 0.99:
            return "✓ EXCELLENT - Ready for migration"
        elif score >= 0.95:
            return "✓ GOOD - Minor discrepancies, review before migration"
        elif score >= 0.90:
            return "⚠ FAIR - Some issues to investigate"
        elif score >= 0.80:
            return "⚠ CAUTION - Significant discrepancies found"
        else:
            return "✗ NOT READY - Major issues require resolution"

    def to_json(self) -> dict:
        """Return report as JSON-serializable dict."""
        return {
            "summary": {
                "source": self.result.source.value,
                "target": self.result.target.value,
                "timestamp": self.result.timestamp.isoformat(),
                "queries_tested": self.result.queries_tested,
                "matches": self.result.matches,
                "mismatches": self.result.mismatches,
                "match_ratio": self.result.match_ratio,
                "avg_timing_diff_ms": self.result.avg_timing_diff_ms,
                "confidence_score": self.result.confidence_score,
            },
            "mismatches": [
                {
                    "query": {
                        "name": d.query.name,
                        "type": d.query.record_type.value,
                    },
                    "source_rcode": d.source_response.rcode,
                    "target_rcode": d.target_response.rcode,
                    "diffs": [
                        {
                            "field": rd.field,
                            "source": rd.source_value,
                            "target": rd.target_value,
                        }
                        for rd in d.record_diffs
                    ],
                }
                for d in self.result.diffs
            ],
        }
