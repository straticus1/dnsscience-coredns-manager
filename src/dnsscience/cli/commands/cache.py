"""Cache management commands."""

from rich.console import Console
from rich.table import Table
from rich import box

from dnsscience.core.coredns.client import CoreDNSClient

console = Console()


async def get_client(target: str):
    """Get appropriate client for target."""
    client = CoreDNSClient()
    await client.connect()
    return client


async def stats(target: str, options):
    """Show cache statistics."""
    client = await get_client(target)

    try:
        cache_stats = await client.get_cache_stats()

        table = Table(title=f"{target.upper()} Cache Statistics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")

        table.add_row("Entries", str(cache_stats.size))
        if cache_stats.size_bytes:
            size_mb = cache_stats.size_bytes / 1024 / 1024
            table.add_row("Size", f"{size_mb:.2f} MB")
        table.add_row("Hits", str(cache_stats.hits))
        table.add_row("Misses", str(cache_stats.misses))
        table.add_row("Hit Ratio", f"{cache_stats.hit_ratio * 100:.1f}%")
        table.add_row("Evictions", str(cache_stats.evictions))
        if cache_stats.max_size:
            table.add_row("Max Size", str(cache_stats.max_size))

        console.print(table)

    finally:
        await client.disconnect()


async def flush(target: str, force: bool, options):
    """Flush entire cache."""
    client = await get_client(target)

    try:
        if not force:
            confirm = console.input(
                f"[yellow]Flush entire {target} cache? [y/N]: [/]"
            )
            if confirm.lower() != "y":
                console.print("Cancelled.")
                return

        result = await client.flush_cache()

        if target == "coredns":
            console.print(
                "[yellow]Note: CoreDNS requires restart or 'reload' plugin to flush cache[/]"
            )
        else:
            console.print(f"[green]✓ Flushed {result.purged_count} cache entries[/]")

    finally:
        await client.disconnect()


async def purge(target: str, domain: str, options):
    """Purge specific domain from cache."""
    client = await get_client(target)

    try:
        from dnsscience.core.models import RecordType

        result = await client.purge_cache(domain=domain)

        if target == "coredns":
            console.print(
                f"[yellow]Note: CoreDNS doesn't support selective cache purge. "
                f"Consider flushing entire cache.[/]"
            )
        else:
            console.print(f"[green]✓ Purged {result.purged_count} entries for {domain}[/]")

    finally:
        await client.disconnect()
