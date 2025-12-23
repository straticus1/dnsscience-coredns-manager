"""Compare command implementations."""

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.compare.engine import CompareEngine, CompareReport
from dnsscience.core.compare.shadow import ShadowMode
from dnsscience.core.models import DNSQuery, RecordType, ShadowModeConfig, ResolverType

console = Console()


async def run_compare(
    source: str,
    target: str,
    queries_file: Optional[Path],
    options,
):
    """Run comparison between two resolvers."""
    # Initialize clients
    source_client = CoreDNSClient(host="localhost", port=53)
    target_client = CoreDNSClient(host="localhost", port=5353)  # Different port for target

    await source_client.connect()
    await target_client.connect()

    try:
        engine = CompareEngine(source_client, target_client)

        if queries_file:
            console.print(f"Loading queries from {queries_file}...")
            result = await engine.compare_from_file(str(queries_file))
        else:
            # Use default test queries
            console.print("Using default test queries...")
            queries = [
                DNSQuery(name="google.com", record_type=RecordType.A),
                DNSQuery(name="cloudflare.com", record_type=RecordType.A),
                DNSQuery(name="amazon.com", record_type=RecordType.A),
                DNSQuery(name="github.com", record_type=RecordType.A),
                DNSQuery(name="example.com", record_type=RecordType.A),
                DNSQuery(name="example.com", record_type=RecordType.MX),
                DNSQuery(name="example.com", record_type=RecordType.NS),
            ]
            result = await engine.compare_bulk(queries)

        # Display report
        report = CompareReport(result)
        console.print(report.summary())

        # Show confidence assessment
        if result.confidence_score >= 0.99:
            console.print("\n[bold green]Migration Readiness: EXCELLENT[/]")
        elif result.confidence_score >= 0.95:
            console.print("\n[bold green]Migration Readiness: GOOD[/]")
        elif result.confidence_score >= 0.90:
            console.print("\n[bold yellow]Migration Readiness: FAIR[/]")
        else:
            console.print("\n[bold red]Migration Readiness: NOT READY[/]")

    finally:
        await source_client.disconnect()
        await target_client.disconnect()


async def shadow(
    source: str,
    target: str,
    duration: int,
    sample_rate: float,
    options,
):
    """Run shadow mode comparison."""
    source_client = CoreDNSClient(host="localhost", port=53)
    target_client = CoreDNSClient(host="localhost", port=5353)

    await source_client.connect()
    await target_client.connect()

    try:
        config = ShadowModeConfig(
            source=ResolverType(source),
            target=ResolverType(target),
            sample_rate=sample_rate,
            duration_seconds=duration,
            alert_on_mismatch=True,
        )

        shadow_mode = ShadowMode(source_client, target_client, config)

        console.print(f"[bold]Starting shadow mode for {duration} seconds[/]")
        console.print(f"Source: {source}, Target: {target}")
        console.print(f"Sample rate: {sample_rate * 100}%\n")

        # For demo, generate some test queries
        import asyncio

        async def generate_queries():
            domains = [
                "google.com",
                "cloudflare.com",
                "amazon.com",
                "github.com",
                "microsoft.com",
            ]
            for i in range(duration * 10):  # 10 queries per second
                domain = domains[i % len(domains)]
                yield DNSQuery(name=domain, record_type=RecordType.A)
                await asyncio.sleep(0.1)

        with Progress() as progress:
            task = progress.add_task("Running shadow mode...", total=duration)

            async for diff in shadow_mode.run_continuous(generate_queries()):
                if not diff.match:
                    console.print(
                        f"[yellow]Mismatch: {diff.query.name} "
                        f"(source: {diff.source_response.rcode}, "
                        f"target: {diff.target_response.rcode})[/]"
                    )
                progress.update(task, advance=0.1)

        # Show final report
        report = shadow_mode.report
        if report:
            table = Table(title="Shadow Mode Report")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Queries Processed", str(report.queries_processed))
            table.add_row("Matches", str(report.matches))
            table.add_row("Mismatches", str(report.mismatches))
            table.add_row("Mismatch Rate", f"{report.mismatch_rate * 100:.2f}%")

            console.print(table)

    finally:
        await source_client.disconnect()
        await target_client.disconnect()
