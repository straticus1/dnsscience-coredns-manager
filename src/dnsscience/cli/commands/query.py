"""Query command implementations."""

import asyncio
import json
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.models import DNSQuery, RecordType

console = Console()


async def lookup(
    name: str,
    record_type: str,
    server: Optional[str],
    dnssec: bool,
    options,
):
    """Perform DNS lookup."""
    client = CoreDNSClient(host=server or "localhost")
    await client.connect()

    try:
        query = DNSQuery(
            name=name,
            record_type=RecordType(record_type.upper()),
            server=server,
            dnssec=dnssec,
        )

        response = await client.query(query)

        # Display results
        table = Table(title=f"DNS Query: {name} ({record_type})")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("TTL", style="yellow")
        table.add_column("Value", style="green")

        for record in response.records:
            table.add_row(
                record.name,
                record.record_type.value,
                str(record.ttl),
                record.value,
            )

        console.print(table)
        console.print(f"\nServer: {response.server}")
        console.print(f"Query time: {response.query_time_ms:.2f}ms")
        console.print(f"RCODE: {response.rcode}")

        if dnssec:
            if response.dnssec_valid:
                console.print("[green]DNSSEC: Valid[/]")
            elif response.dnssec_valid is False:
                console.print("[red]DNSSEC: Invalid[/]")
            else:
                console.print("[yellow]DNSSEC: Not validated[/]")

    finally:
        await client.disconnect()


async def trace(name: str, record_type: str, options):
    """Trace DNS resolution."""
    client = CoreDNSClient()
    await client.connect()

    try:
        query = DNSQuery(
            name=name,
            record_type=RecordType(record_type.upper()),
        )

        responses = await client.trace(query)

        console.print(f"\n[bold]Tracing DNS resolution for {name}[/]\n")

        for i, response in enumerate(responses, 1):
            console.print(f"[cyan]Step {i}:[/] {response.server}")
            console.print(f"  RCODE: {response.rcode}")
            console.print(f"  Time: {response.query_time_ms:.2f}ms")
            for record in response.records:
                console.print(f"  → {record.record_type.value}: {record.value}")
            console.print()

    finally:
        await client.disconnect()


async def bulk(file: Path, output: Optional[Path], options):
    """Perform bulk queries."""
    client = CoreDNSClient()
    await client.connect()

    try:
        # Read domains from file
        domains = file.read_text().strip().split("\n")
        domains = [d.strip() for d in domains if d.strip() and not d.startswith("#")]

        queries = [
            DNSQuery(name=domain, record_type=RecordType.A)
            for domain in domains
        ]

        console.print(f"Querying {len(queries)} domains...")

        result = await client.query_bulk(queries)

        # Display summary
        table = Table(title="Bulk Query Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total", str(result.total))
        table.add_row("Successful", f"[green]{result.successful}[/]")
        table.add_row("Failed", f"[red]{result.failed}[/]")
        table.add_row("Duration", f"{result.duration_ms:.2f}ms")
        table.add_row("QPS", f"{result.total / (result.duration_ms / 1000):.2f}")

        console.print(table)

        # Save results if output specified
        if output:
            results = {
                "summary": {
                    "total": result.total,
                    "successful": result.successful,
                    "failed": result.failed,
                    "duration_ms": result.duration_ms,
                },
                "responses": [
                    {
                        "query": r.query.name,
                        "rcode": r.rcode,
                        "records": [rec.value for rec in r.records],
                        "time_ms": r.query_time_ms,
                    }
                    for r in result.responses
                ],
                "errors": result.errors,
            }
            output.write_text(json.dumps(results, indent=2))
            console.print(f"\nResults saved to {output}")

    finally:
        await client.disconnect()


async def benchmark(name: str, count: int, concurrency: int, options):
    """Benchmark DNS query performance."""
    client = CoreDNSClient()
    await client.connect()

    try:
        console.print(f"Benchmarking {name} with {count} queries, {concurrency} concurrent\n")

        queries = [
            DNSQuery(name=name, record_type=RecordType.A)
            for _ in range(count)
        ]

        # Run benchmark
        import time

        start = time.perf_counter()

        # Process in batches based on concurrency
        results = []
        with Progress() as progress:
            task = progress.add_task("Querying...", total=count)

            for i in range(0, count, concurrency):
                batch = queries[i : i + concurrency]
                batch_results = await asyncio.gather(
                    *[client.query(q) for q in batch],
                    return_exceptions=True,
                )
                results.extend(batch_results)
                progress.update(task, advance=len(batch))

        end = time.perf_counter()
        total_time = end - start

        # Calculate statistics
        valid_results = [r for r in results if not isinstance(r, Exception)]
        times = [r.query_time_ms for r in valid_results]

        if times:
            times.sort()
            avg = sum(times) / len(times)
            p50 = times[len(times) // 2]
            p95 = times[int(len(times) * 0.95)]
            p99 = times[int(len(times) * 0.99)]
            min_time = min(times)
            max_time = max(times)
        else:
            avg = p50 = p95 = p99 = min_time = max_time = 0

        # Display results
        table = Table(title="Benchmark Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Queries", str(count))
        table.add_row("Successful", str(len(valid_results)))
        table.add_row("Failed", str(count - len(valid_results)))
        table.add_row("Total Time", f"{total_time:.2f}s")
        table.add_row("QPS", f"{count / total_time:.2f}")
        table.add_row("", "")
        table.add_row("Latency (avg)", f"{avg:.2f}ms")
        table.add_row("Latency (min)", f"{min_time:.2f}ms")
        table.add_row("Latency (max)", f"{max_time:.2f}ms")
        table.add_row("Latency (p50)", f"{p50:.2f}ms")
        table.add_row("Latency (p95)", f"{p95:.2f}ms")
        table.add_row("Latency (p99)", f"{p99:.2f}ms")

        console.print(table)

    finally:
        await client.disconnect()
