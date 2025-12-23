"""Health check commands."""

import asyncio

from rich.console import Console
from rich.live import Live
from rich.table import Table

from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.models import HealthState

console = Console()


async def get_client(target: str):
    """Get appropriate client for target."""
    client = CoreDNSClient()
    await client.connect()
    return client


async def check(target: str, options):
    """Perform health check."""
    client = await get_client(target)

    try:
        health = await client.health_check()

        state_colors = {
            HealthState.HEALTHY: "[green]",
            HealthState.UNHEALTHY: "[red]",
            HealthState.DEGRADED: "[yellow]",
            HealthState.UNKNOWN: "[dim]",
        }
        color = state_colors.get(health.state, "")

        console.print(f"\n{target.upper()} Health: {color}{health.state.value.upper()}[/]\n")

        table = Table(show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value")

        table.add_row("Service State", health.service_status.state.value)
        table.add_row("Version", health.service_status.version or "Unknown")

        if health.cache_stats:
            table.add_row("Cache Entries", str(health.cache_stats.size))
            table.add_row("Cache Hit Ratio", f"{health.cache_stats.hit_ratio * 100:.1f}%")

        if health.query_rate is not None:
            table.add_row("Query Rate", f"{health.query_rate:.2f} qps")

        if health.latency_avg_ms is not None:
            table.add_row("Avg Latency", f"{health.latency_avg_ms:.2f}ms")

        if health.error_rate is not None:
            table.add_row("Error Rate", f"{health.error_rate:.2f}/s")

        console.print(table)

        # Upstream health
        if health.upstreams:
            console.print("\n[bold]Upstream Health:[/]")
            for upstream in health.upstreams:
                status = "[green]✓[/]" if upstream.healthy else "[red]✗[/]"
                latency = f" ({upstream.latency_ms:.2f}ms)" if upstream.latency_ms else ""
                console.print(f"  {status} {upstream.address}:{upstream.port}{latency}")

    finally:
        await client.disconnect()


async def watch(target: str, interval: int, options):
    """Continuously monitor health."""
    client = await get_client(target)

    try:
        console.print(f"Watching {target} health (Ctrl+C to stop)\n")

        def generate_table(health):
            table = Table(title=f"{target.upper()} Health Monitor")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            state_colors = {
                HealthState.HEALTHY: "[green]",
                HealthState.UNHEALTHY: "[red]",
                HealthState.DEGRADED: "[yellow]",
            }
            color = state_colors.get(health.state, "")

            table.add_row("State", f"{color}{health.state.value}[/]")
            table.add_row("Service", health.service_status.state.value)

            if health.cache_stats:
                table.add_row("Cache Size", str(health.cache_stats.size))
                table.add_row("Hit Ratio", f"{health.cache_stats.hit_ratio * 100:.1f}%")

            table.add_row("Updated", health.timestamp.strftime("%H:%M:%S"))

            return table

        with Live(generate_table(await client.health_check()), refresh_per_second=1) as live:
            while True:
                await asyncio.sleep(interval)
                health = await client.health_check()
                live.update(generate_table(health))

    except KeyboardInterrupt:
        console.print("\nStopped monitoring.")
    finally:
        await client.disconnect()


async def metrics(target: str, options):
    """Show Prometheus metrics."""
    client = await get_client(target)

    try:
        snapshot = await client.get_metrics()

        console.print(f"\n[bold]{target.upper()} Metrics[/]\n")

        # Group metrics by prefix
        groups: dict[str, list] = {}
        for metric in snapshot.metrics:
            prefix = metric.name.split("_")[0]
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(metric)

        for prefix, metrics_list in sorted(groups.items()):
            console.print(f"[cyan]{prefix}[/]")
            for m in metrics_list[:10]:  # Limit per group
                labels = ", ".join(f"{k}={v}" for k, v in m.labels.items()) if m.labels else ""
                if labels:
                    console.print(f"  {m.name}{{{labels}}} = {m.value}")
                else:
                    console.print(f"  {m.name} = {m.value}")
            if len(metrics_list) > 10:
                console.print(f"  [dim]... and {len(metrics_list) - 10} more[/]")
            console.print()

    finally:
        await client.disconnect()
