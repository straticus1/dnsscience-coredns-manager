"""Service control commands."""

from rich.console import Console
from rich.table import Table

from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.models import ResolverType, ServiceState

console = Console()


async def get_client(target: str):
    """Get appropriate client for target."""
    if target == "coredns":
        client = CoreDNSClient()
        await client.connect()
        return client
    else:
        # Unbound client would go here
        raise NotImplementedError(f"Unbound client not yet implemented")


async def status(target: str, options):
    """Show service status."""
    client = await get_client(target)

    try:
        status = await client.get_status()

        table = Table(title=f"{target.upper()} Service Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        state_color = {
            ServiceState.RUNNING: "[green]",
            ServiceState.STOPPED: "[red]",
            ServiceState.ERROR: "[red]",
        }.get(status.state, "[yellow]")

        table.add_row("State", f"{state_color}{status.state.value}[/]")
        table.add_row("Version", status.version or "Unknown")
        table.add_row("Config Path", status.config_path or "Unknown")
        table.add_row("Listening", ", ".join(status.listening_addresses) or "None")

        if status.plugins:
            table.add_row("Plugins", ", ".join(status.plugins))
        if status.uptime_seconds:
            hours = status.uptime_seconds // 3600
            mins = (status.uptime_seconds % 3600) // 60
            table.add_row("Uptime", f"{hours}h {mins}m")

        console.print(table)

    finally:
        await client.disconnect()


async def start(target: str, options):
    """Start the service."""
    client = await get_client(target)

    try:
        result = await client.start()

        if result.success:
            console.print(f"[green]✓ {target} started successfully[/]")
        else:
            console.print(f"[yellow]⚠ {result.message}[/]")

    finally:
        await client.disconnect()


async def stop(target: str, options):
    """Stop the service."""
    client = await get_client(target)

    try:
        result = await client.stop()

        if result.success:
            console.print(f"[green]✓ {target} stopped successfully[/]")
        else:
            console.print(f"[yellow]⚠ {result.message}[/]")

    finally:
        await client.disconnect()


async def restart(target: str, options):
    """Restart the service."""
    client = await get_client(target)

    try:
        result = await client.restart()

        if result.success:
            console.print(f"[green]✓ {target} restarted successfully[/]")
        else:
            console.print(f"[yellow]⚠ {result.message}[/]")

    finally:
        await client.disconnect()


async def reload(target: str, options):
    """Reload configuration."""
    client = await get_client(target)

    try:
        result = await client.reload()

        if result.success:
            console.print(f"[green]✓ {target} configuration reloaded[/]")
        else:
            console.print(f"[yellow]⚠ {result.message}[/]")

    finally:
        await client.disconnect()
