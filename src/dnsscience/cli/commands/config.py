"""Configuration management commands."""

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.syntax import Syntax

from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.coredns.config import CorefileParser

console = Console()


async def get_client(target: str):
    """Get appropriate client for target."""
    client = CoreDNSClient()
    await client.connect()
    return client


async def show(target: str, options):
    """Show current configuration."""
    client = await get_client(target)

    try:
        config = await client.get_config()

        lang = "text"
        if target == "coredns":
            lang = "text"  # Could create custom lexer for Corefile
        elif target == "unbound":
            lang = "yaml"  # Unbound config is similar to YAML

        syntax = Syntax(config, lang, theme="monokai", line_numbers=True)
        console.print(syntax)

    except FileNotFoundError:
        console.print(f"[red]Configuration file not found[/]")
    finally:
        await client.disconnect()


async def validate(target: str, file: Optional[Path], options):
    """Validate configuration."""
    if file:
        config = file.read_text()
    else:
        client = await get_client(target)
        try:
            config = await client.get_config()
        finally:
            await client.disconnect()

    # Validate
    if target == "coredns":
        parser = CorefileParser()
        result = parser.validate(config)
    else:
        from dnsscience.core.migrate.parsers.unbound_conf import UnboundConfigParser

        parser = UnboundConfigParser()
        result = parser.validate(config)

    if result.valid:
        console.print("[green]✓ Configuration is valid[/]")
    else:
        console.print("[red]✗ Configuration has errors:[/]")
        for error in result.errors:
            line_info = f"Line {error.line}: " if error.line else ""
            console.print(f"  [red]{line_info}{error.message}[/]")

    if result.warnings:
        console.print("\n[yellow]Warnings:[/]")
        for warning in result.warnings:
            line_info = f"Line {warning.line}: " if warning.line else ""
            console.print(f"  [yellow]{line_info}{warning.message}[/]")


async def diff(target: str, file: Path, options):
    """Diff new config against running config."""
    client = await get_client(target)

    try:
        new_config = file.read_text()
        result = await client.diff_config(new_config)

        if not result.is_different:
            console.print("[green]✓ No differences[/]")
            return

        console.print("[bold]Configuration Differences:[/]\n")

        if result.additions:
            console.print("[green]Additions:[/]")
            for line in result.additions[:20]:
                console.print(f"  [green]+ {line}[/]")
            if len(result.additions) > 20:
                console.print(f"  [dim]... and {len(result.additions) - 20} more[/]")

        if result.deletions:
            console.print("\n[red]Deletions:[/]")
            for line in result.deletions[:20]:
                console.print(f"  [red]- {line}[/]")
            if len(result.deletions) > 20:
                console.print(f"  [dim]... and {len(result.deletions) - 20} more[/]")

    finally:
        await client.disconnect()
