"""Main CLI entry point for dnsctl."""

import asyncio
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from dnsscience.core.models import ResolverType

# Create the main app
app = typer.Typer(
    name="dnsctl",
    help="DNS Science Toolkit - Enterprise DNS management for CoreDNS and Unbound",
    no_args_is_help=True,
)

console = Console()


class OutputFormat(str, Enum):
    """Output format options."""

    TABLE = "table"
    JSON = "json"
    YAML = "yaml"


class Target(str, Enum):
    """Target resolver type."""

    COREDNS = "coredns"
    UNBOUND = "unbound"


# Global options stored in context
class GlobalOptions:
    def __init__(self):
        self.target: ResolverType = ResolverType.COREDNS
        self.host: str = "localhost"
        self.port: int = 53
        self.output: OutputFormat = OutputFormat.TABLE
        self.verbose: bool = False
        self.debug: bool = False
        self.kubeconfig: Optional[Path] = None
        self.namespace: str = "kube-system"


# ============================================================================
# Service Commands
# ============================================================================

service_app = typer.Typer(help="Service control commands")
app.add_typer(service_app, name="service")


@service_app.command("status")
def service_status(
    ctx: typer.Context,
    target: Target = typer.Option(Target.COREDNS, "--target", "-t", help="Target resolver"),
):
    """Get resolver service status."""
    from dnsscience.cli.commands.service import status

    asyncio.run(status(target.value, ctx.obj))


@service_app.command("start")
def service_start(
    ctx: typer.Context,
    target: Target = typer.Option(Target.COREDNS, "--target", "-t"),
):
    """Start the resolver service."""
    from dnsscience.cli.commands.service import start

    asyncio.run(start(target.value, ctx.obj))


@service_app.command("stop")
def service_stop(
    ctx: typer.Context,
    target: Target = typer.Option(Target.COREDNS, "--target", "-t"),
):
    """Stop the resolver service."""
    from dnsscience.cli.commands.service import stop

    asyncio.run(stop(target.value, ctx.obj))


@service_app.command("restart")
def service_restart(
    ctx: typer.Context,
    target: Target = typer.Option(Target.COREDNS, "--target", "-t"),
):
    """Restart the resolver service."""
    from dnsscience.cli.commands.service import restart

    asyncio.run(restart(target.value, ctx.obj))


@service_app.command("reload")
def service_reload(
    ctx: typer.Context,
    target: Target = typer.Option(Target.COREDNS, "--target", "-t"),
):
    """Reload configuration without restart."""
    from dnsscience.cli.commands.service import reload

    asyncio.run(reload(target.value, ctx.obj))


# ============================================================================
# Cache Commands
# ============================================================================

cache_app = typer.Typer(help="Cache management commands")
app.add_typer(cache_app, name="cache")


@cache_app.command("stats")
def cache_stats(
    ctx: typer.Context,
    target: Target = typer.Option(Target.COREDNS, "--target", "-t"),
):
    """Show cache statistics."""
    from dnsscience.cli.commands.cache import stats

    asyncio.run(stats(target.value, ctx.obj))


@cache_app.command("flush")
def cache_flush(
    ctx: typer.Context,
    target: Target = typer.Option(Target.COREDNS, "--target", "-t"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Flush entire cache."""
    from dnsscience.cli.commands.cache import flush

    asyncio.run(flush(target.value, force, ctx.obj))


@cache_app.command("purge")
def cache_purge(
    ctx: typer.Context,
    domain: str = typer.Argument(..., help="Domain to purge"),
    target: Target = typer.Option(Target.COREDNS, "--target", "-t"),
):
    """Purge specific domain from cache."""
    from dnsscience.cli.commands.cache import purge

    asyncio.run(purge(target.value, domain, ctx.obj))


# ============================================================================
# Query Commands
# ============================================================================

query_app = typer.Typer(help="DNS query commands")
app.add_typer(query_app, name="query")


@query_app.command("lookup")
def query_lookup(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Domain name to query"),
    record_type: str = typer.Option("A", "--type", "-t", help="Record type"),
    server: Optional[str] = typer.Option(None, "--server", "-s", help="DNS server"),
    dnssec: bool = typer.Option(False, "--dnssec", help="Request DNSSEC validation"),
):
    """Perform DNS lookup."""
    from dnsscience.cli.commands.query import lookup

    asyncio.run(lookup(name, record_type, server, dnssec, ctx.obj))


@query_app.command("trace")
def query_trace(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Domain name to trace"),
    record_type: str = typer.Option("A", "--type", "-t"),
):
    """Trace DNS resolution path."""
    from dnsscience.cli.commands.query import trace

    asyncio.run(trace(name, record_type, ctx.obj))


@query_app.command("bulk")
def query_bulk(
    ctx: typer.Context,
    file: Path = typer.Argument(..., help="File with domains (one per line)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
):
    """Perform bulk DNS queries from file."""
    from dnsscience.cli.commands.query import bulk

    asyncio.run(bulk(file, output, ctx.obj))


@query_app.command("bench")
def query_bench(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Domain to benchmark"),
    count: int = typer.Option(100, "--count", "-c", help="Number of queries"),
    concurrency: int = typer.Option(10, "--concurrency", help="Concurrent queries"),
):
    """Benchmark DNS query performance."""
    from dnsscience.cli.commands.query import benchmark

    asyncio.run(benchmark(name, count, concurrency, ctx.obj))


# ============================================================================
# Config Commands
# ============================================================================

config_app = typer.Typer(help="Configuration management")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show(
    ctx: typer.Context,
    target: Target = typer.Option(Target.COREDNS, "--target", "-t"),
):
    """Show current configuration."""
    from dnsscience.cli.commands.config import show

    asyncio.run(show(target.value, ctx.obj))


@config_app.command("validate")
def config_validate(
    ctx: typer.Context,
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Config file to validate"),
    target: Target = typer.Option(Target.COREDNS, "--target", "-t"),
):
    """Validate configuration syntax."""
    from dnsscience.cli.commands.config import validate

    asyncio.run(validate(target.value, file, ctx.obj))


@config_app.command("diff")
def config_diff(
    ctx: typer.Context,
    file: Path = typer.Argument(..., help="New config file to compare"),
    target: Target = typer.Option(Target.COREDNS, "--target", "-t"),
):
    """Diff new config against running config."""
    from dnsscience.cli.commands.config import diff

    asyncio.run(diff(target.value, file, ctx.obj))


# ============================================================================
# Compare Commands
# ============================================================================

compare_app = typer.Typer(help="Compare DNS resolvers")
app.add_typer(compare_app, name="compare")


@compare_app.command("run")
def compare_run(
    ctx: typer.Context,
    source: Target = typer.Option(Target.COREDNS, "--source", "-s"),
    target_resolver: Target = typer.Option(Target.UNBOUND, "--target", "-t"),
    queries: Optional[Path] = typer.Option(None, "--queries", "-q", help="Query file"),
):
    """Compare two resolvers."""
    from dnsscience.cli.commands.compare import run_compare

    asyncio.run(run_compare(source.value, target_resolver.value, queries, ctx.obj))


@compare_app.command("shadow")
def compare_shadow(
    ctx: typer.Context,
    source: Target = typer.Option(Target.COREDNS, "--source", "-s"),
    target_resolver: Target = typer.Option(Target.UNBOUND, "--target", "-t"),
    duration: int = typer.Option(300, "--duration", "-d", help="Duration in seconds"),
    sample_rate: float = typer.Option(1.0, "--sample-rate", help="Query sample rate"),
):
    """Run shadow mode comparison."""
    from dnsscience.cli.commands.compare import shadow

    asyncio.run(shadow(source.value, target_resolver.value, duration, sample_rate, ctx.obj))


# ============================================================================
# Migrate Commands
# ============================================================================

migrate_app = typer.Typer(help="Migration tools")
app.add_typer(migrate_app, name="migrate")


@migrate_app.command("plan")
def migrate_plan(
    ctx: typer.Context,
    source: Target = typer.Option(..., "--source", "-s", help="Source resolver"),
    target_resolver: Target = typer.Option(..., "--target", "-t", help="Target resolver"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save plan to file"),
):
    """Generate migration plan."""
    from dnsscience.cli.commands.migrate import plan

    asyncio.run(plan(source.value, target_resolver.value, output, ctx.obj))


@migrate_app.command("execute")
def migrate_execute(
    ctx: typer.Context,
    plan_file: Path = typer.Argument(..., help="Migration plan file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate migration"),
):
    """Execute migration plan."""
    from dnsscience.cli.commands.migrate import execute

    asyncio.run(execute(plan_file, dry_run, ctx.obj))


@migrate_app.command("validate")
def migrate_validate(
    ctx: typer.Context,
    queries: Optional[Path] = typer.Option(None, "--queries", "-q"),
):
    """Validate migration success."""
    from dnsscience.cli.commands.migrate import validate

    asyncio.run(validate(queries, ctx.obj))


@migrate_app.command("rollback")
def migrate_rollback(
    ctx: typer.Context,
    backup: Path = typer.Argument(..., help="Backup directory"),
):
    """Rollback to previous state."""
    from dnsscience.cli.commands.migrate import rollback

    asyncio.run(rollback(backup, ctx.obj))


@migrate_app.command("convert")
def migrate_convert(
    ctx: typer.Context,
    input_file: Path = typer.Argument(..., help="Input config file"),
    output_file: Path = typer.Argument(..., help="Output config file"),
    source: Target = typer.Option(..., "--source", "-s", help="Source format"),
    target_resolver: Target = typer.Option(..., "--target", "-t", help="Target format"),
):
    """Convert configuration between formats."""
    from dnsscience.cli.commands.migrate import convert

    asyncio.run(convert(input_file, output_file, source.value, target_resolver.value, ctx.obj))


# ============================================================================
# Health Commands
# ============================================================================

health_app = typer.Typer(help="Health check commands")
app.add_typer(health_app, name="health")


@health_app.command("check")
def health_check(
    ctx: typer.Context,
    target: Target = typer.Option(Target.COREDNS, "--target", "-t"),
):
    """Perform health check."""
    from dnsscience.cli.commands.health import check

    asyncio.run(check(target.value, ctx.obj))


@health_app.command("watch")
def health_watch(
    ctx: typer.Context,
    target: Target = typer.Option(Target.COREDNS, "--target", "-t"),
    interval: int = typer.Option(5, "--interval", "-i", help="Check interval in seconds"),
):
    """Continuously monitor health."""
    from dnsscience.cli.commands.health import watch

    asyncio.run(watch(target.value, interval, ctx.obj))


@health_app.command("metrics")
def health_metrics(
    ctx: typer.Context,
    target: Target = typer.Option(Target.COREDNS, "--target", "-t"),
):
    """Show Prometheus metrics."""
    from dnsscience.cli.commands.health import metrics

    asyncio.run(metrics(target.value, ctx.obj))


# ============================================================================
# K8s Commands
# ============================================================================

k8s_app = typer.Typer(help="Kubernetes DNS operations")
app.add_typer(k8s_app, name="k8s")


@k8s_app.command("test-pod")
def k8s_test_pod(
    ctx: typer.Context,
    pod: str = typer.Argument(..., help="Pod name"),
    domain: str = typer.Argument(..., help="Domain to resolve"),
    namespace: str = typer.Option("default", "--namespace", "-n"),
):
    """Test DNS resolution from a pod."""
    from dnsscience.cli.commands.k8s import test_pod

    asyncio.run(test_pod(pod, domain, namespace, ctx.obj))


@k8s_app.command("configmap")
def k8s_configmap(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: show, apply, backup"),
    name: str = typer.Option("coredns", "--name", "-n", help="ConfigMap name"),
):
    """Manage DNS ConfigMaps."""
    from dnsscience.cli.commands.k8s import configmap

    asyncio.run(configmap(action, name, ctx.obj))


# ============================================================================
# Version Command
# ============================================================================


@app.command("version")
def version():
    """Show version information."""
    from dnsscience import __version__

    console.print(f"dnsctl version {__version__}")
    console.print("DNS Science Toolkit")
    console.print("https://dnsscience.io")


# ============================================================================
# Main Callback (Global Options)
# ============================================================================


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    debug: bool = typer.Option(False, "--debug", help="Debug mode"),
    output: OutputFormat = typer.Option(
        OutputFormat.TABLE, "--output", "-o", help="Output format"
    ),
    kubeconfig: Optional[Path] = typer.Option(
        None, "--kubeconfig", help="Path to kubeconfig"
    ),
    namespace: str = typer.Option(
        "kube-system", "--namespace", "-n", help="Kubernetes namespace"
    ),
):
    """DNS Science Toolkit - Enterprise DNS management."""
    ctx.ensure_object(GlobalOptions)
    ctx.obj.verbose = verbose
    ctx.obj.debug = debug
    ctx.obj.output = output
    ctx.obj.kubeconfig = kubeconfig
    ctx.obj.namespace = namespace


if __name__ == "__main__":
    app()
