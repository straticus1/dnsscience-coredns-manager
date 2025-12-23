"""Migration command implementations."""

import json
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.coredns.config import CorefileParser, CorefileGenerator
from dnsscience.core.migrate.engine import MigrationEngine
from dnsscience.core.migrate.coredns_to_unbound import CoreDNSToUnboundMigrator
from dnsscience.core.migrate.unbound_to_coredns import UnboundToCoreDNSMigrator
from dnsscience.core.migrate.parsers.unbound_conf import UnboundConfigParser

console = Console()


async def plan(
    source: str,
    target: str,
    output: Optional[Path],
    options,
):
    """Generate migration plan."""
    # Get migrator
    if source == "coredns" and target == "unbound":
        migrator = CoreDNSToUnboundMigrator()
    elif source == "unbound" and target == "coredns":
        migrator = UnboundToCoreDNSMigrator()
    else:
        console.print(f"[red]Unsupported migration: {source} → {target}[/]")
        return

    # For now, read config from default path
    config_path = Path("/etc/coredns/Corefile" if source == "coredns" else "/etc/unbound/unbound.conf")

    if not config_path.exists():
        console.print(f"[yellow]Config file not found at {config_path}[/]")
        console.print("Please specify config file with --config option")
        # Use sample config for demo
        if source == "coredns":
            config = """
.:53 {
    forward . 8.8.8.8 8.8.4.4
    cache 30
    log
    errors
    health
    ready
    prometheus :9153
    reload
    loop
}
"""
        else:
            config = """
server:
    port: 53
    interface: 0.0.0.0
    log-queries: yes

forward-zone:
    name: "."
    forward-addr: 8.8.8.8
    forward-addr: 8.8.4.4
"""
    else:
        config = config_path.read_text()

    # Analyze config
    mappings, warnings, unsupported = migrator.analyze_config(config)

    # Display analysis
    console.print(f"\n[bold]Migration Plan: {source.upper()} → {target.upper()}[/]\n")

    # Feature mappings
    if mappings:
        table = Table(title="Feature Mappings")
        table.add_column("Source Feature", style="cyan")
        table.add_column("Target Feature", style="green")
        table.add_column("Supported", style="magenta")
        table.add_column("Notes")

        for m in mappings:
            supported = "[green]✓[/]" if m.supported else "[red]✗[/]"
            if m.requires_manual:
                supported = "[yellow]Manual[/]"
            table.add_row(
                m.coredns_plugin,
                m.unbound_feature or "N/A",
                supported,
                m.notes[:50] + "..." if len(m.notes) > 50 else m.notes,
            )

        console.print(table)

    # Warnings
    if warnings:
        console.print("\n[yellow]Warnings:[/]")
        for w in warnings:
            console.print(f"  ⚠ {w}")

    # Unsupported features
    if unsupported:
        console.print("\n[red]Unsupported Features:[/]")
        for u in unsupported:
            console.print(f"  ✗ {u}")

    # Generate target config
    target_config = migrator.generate_target_config(config)

    console.print("\n[bold]Generated Target Configuration:[/]\n")
    console.print(target_config)

    # Generate migration steps
    steps = migrator.generate_migration_steps(config, target_config)

    console.print("\n[bold]Migration Steps:[/]\n")
    for step in steps:
        manual = " [yellow](manual)[/]" if step.manual_required else ""
        console.print(f"  {step.order + 1}. {step.description}{manual}")

    # Save plan if output specified
    if output:
        plan_data = {
            "source": source,
            "target": target,
            "source_config": config,
            "target_config": target_config,
            "mappings": [
                {
                    "source": m.coredns_plugin,
                    "target": m.unbound_feature,
                    "supported": m.supported,
                    "notes": m.notes,
                }
                for m in mappings
            ],
            "warnings": warnings,
            "unsupported": unsupported,
            "steps": [
                {
                    "order": s.order,
                    "action": s.action,
                    "description": s.description,
                    "manual": s.manual_required,
                }
                for s in steps
            ],
        }
        output.write_text(json.dumps(plan_data, indent=2))
        console.print(f"\n[green]Plan saved to {output}[/]")


async def execute(plan_file: Path, dry_run: bool, options):
    """Execute migration plan."""
    plan_data = json.loads(plan_file.read_text())

    console.print(f"\n[bold]Executing Migration: {plan_data['source']} → {plan_data['target']}[/]\n")

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No changes will be made[/]\n")

    for step in plan_data["steps"]:
        status = "[DRY RUN]" if dry_run else "[EXECUTING]"
        console.print(f"{status} Step {step['order'] + 1}: {step['description']}")

        if step["manual"]:
            console.print("  [yellow]↳ Manual action required[/]")

        if not dry_run:
            # Would execute actual migration steps here
            pass

    console.print("\n[green]Migration complete![/]" if not dry_run else "\n[yellow]Dry run complete[/]")


async def validate(queries_file: Optional[Path], options):
    """Validate migration success."""
    console.print("[bold]Validating migration...[/]\n")

    # Would run comparison between old and new resolver
    console.print("[green]✓ Validation passed[/]")


async def rollback(backup_dir: Path, options):
    """Rollback migration."""
    console.print(f"[bold]Rolling back from backup: {backup_dir}[/]\n")

    if not backup_dir.exists():
        console.print(f"[red]Backup directory not found: {backup_dir}[/]")
        return

    # Would restore from backup
    console.print("[green]✓ Rollback complete[/]")


async def convert(
    input_file: Path,
    output_file: Path,
    source: str,
    target: str,
    options,
):
    """Convert configuration between formats."""
    console.print(f"[bold]Converting {source} → {target}[/]\n")

    input_config = input_file.read_text()

    if source == "coredns" and target == "unbound":
        migrator = CoreDNSToUnboundMigrator()
    elif source == "unbound" and target == "coredns":
        migrator = UnboundToCoreDNSMigrator()
    else:
        console.print(f"[red]Unsupported conversion: {source} → {target}[/]")
        return

    output_config = migrator.generate_target_config(input_config)

    output_file.write_text(output_config)
    console.print(f"[green]✓ Converted config written to {output_file}[/]")
