"""CoreDNS to Unbound migration logic."""

from dnsscience.core.coredns.config import CorefileParser
from dnsscience.core.models import (
    MigrationStep,
    PluginMapping,
    ResolverType,
)


class CoreDNSToUnboundMigrator:
    """Migrator for CoreDNS → Unbound migrations."""

    source_type = ResolverType.COREDNS
    target_type = ResolverType.UNBOUND

    # Plugin mapping table
    PLUGIN_MAPPINGS = {
        "forward": PluginMapping(
            coredns_plugin="forward",
            unbound_feature="forward-zone",
            notes="Direct mapping. Convert 'forward . 8.8.8.8' to forward-zone with forward-addr.",
            supported=True,
        ),
        "cache": PluginMapping(
            coredns_plugin="cache",
            unbound_feature="msg-cache-size / rrset-cache-size",
            notes="Map cache size. TTL settings differ.",
            supported=True,
        ),
        "log": PluginMapping(
            coredns_plugin="log",
            unbound_feature="log-queries: yes",
            notes="Enable query logging in unbound.",
            supported=True,
        ),
        "errors": PluginMapping(
            coredns_plugin="errors",
            unbound_feature="log-servfail: yes",
            notes="Partial mapping - only logs SERVFAIL.",
            supported=True,
        ),
        "health": PluginMapping(
            coredns_plugin="health",
            unbound_feature=None,
            notes="No direct equivalent. Use external health checks.",
            supported=False,
            requires_manual=True,
        ),
        "ready": PluginMapping(
            coredns_plugin="ready",
            unbound_feature=None,
            notes="No direct equivalent. Use external readiness checks.",
            supported=False,
            requires_manual=True,
        ),
        "kubernetes": PluginMapping(
            coredns_plugin="kubernetes",
            unbound_feature="stub-zone + external sync",
            notes="Complex. Requires custom solution or external sync.",
            supported=False,
            requires_manual=True,
        ),
        "hosts": PluginMapping(
            coredns_plugin="hosts",
            unbound_feature="local-data",
            notes="Convert hosts entries to local-data directives.",
            supported=True,
        ),
        "file": PluginMapping(
            coredns_plugin="file",
            unbound_feature="auth-zone",
            notes="Zone files are compatible. Update path in config.",
            supported=True,
        ),
        "reload": PluginMapping(
            coredns_plugin="reload",
            unbound_feature="unbound-control reload",
            notes="Use unbound-control for reloads instead.",
            supported=False,
            requires_manual=True,
        ),
        "loop": PluginMapping(
            coredns_plugin="loop",
            unbound_feature="harden-* options",
            notes="Different approach to loop prevention.",
            supported=True,
        ),
        "dnssec": PluginMapping(
            coredns_plugin="dnssec",
            unbound_feature="auto-trust-anchor-file",
            notes="DNSSEC validation built-in. Configure trust anchors.",
            supported=True,
        ),
        "prometheus": PluginMapping(
            coredns_plugin="prometheus",
            unbound_feature="extended-statistics: yes",
            notes="Use unbound-control stats or Prometheus exporter.",
            supported=True,
            requires_manual=True,
        ),
        "rewrite": PluginMapping(
            coredns_plugin="rewrite",
            unbound_feature="local-zone / local-data",
            notes="Limited rewrite capability. May need custom solution.",
            supported=False,
            requires_manual=True,
        ),
        "bind": PluginMapping(
            coredns_plugin="bind",
            unbound_feature="interface",
            notes="Map bind addresses to interface directives.",
            supported=True,
        ),
        "acl": PluginMapping(
            coredns_plugin="acl",
            unbound_feature="access-control",
            notes="Convert ACL rules to access-control format.",
            supported=True,
        ),
        "loadbalance": PluginMapping(
            coredns_plugin="loadbalance",
            unbound_feature="rrset-roundrobin: yes",
            notes="Enable round-robin for load balancing.",
            supported=True,
        ),
    }

    def __init__(self):
        self.parser = CorefileParser()

    def analyze_config(self, config: str) -> tuple[list[PluginMapping], list[str], list[str]]:
        """
        Analyze CoreDNS configuration for migration.

        Returns:
            - List of plugin mappings used
            - List of warnings
            - List of unsupported features
        """
        parsed = self.parser.parse(config)

        mappings: list[PluginMapping] = []
        warnings: list[str] = []
        unsupported: list[str] = []

        for server in parsed.servers:
            for plugin in server.plugins:
                mapping = self.PLUGIN_MAPPINGS.get(plugin.name)

                if mapping:
                    mappings.append(mapping)

                    if not mapping.supported:
                        unsupported.append(f"{plugin.name}: {mapping.notes}")
                    elif mapping.requires_manual:
                        warnings.append(f"{plugin.name}: Requires manual configuration - {mapping.notes}")
                else:
                    # Unknown plugin
                    unsupported.append(f"{plugin.name}: No known Unbound equivalent")

        # Check for k8s-specific configuration
        if any(p.name == "kubernetes" for s in parsed.servers for p in s.plugins):
            warnings.append(
                "Kubernetes plugin detected. You'll need to set up external DNS sync "
                "or use k8s_gateway/external-dns with Unbound."
            )

        return mappings, warnings, unsupported

    def generate_target_config(self, source_config: str) -> str:
        """Generate Unbound configuration from CoreDNS Corefile."""
        parsed = self.parser.parse(source_config)

        lines = [
            "# Generated by DNS Science Toolkit",
            "# Source: CoreDNS Corefile",
            "",
            "server:",
        ]

        # Process each server block
        for server in parsed.servers:
            # Interface/port
            port = server.port
            lines.append(f"    port: {port}")
            lines.append("    interface: 0.0.0.0")
            lines.append("")

            # Access control (default allow)
            lines.append("    access-control: 0.0.0.0/0 allow")
            lines.append("    access-control: ::0/0 allow")
            lines.append("")

            # Process plugins
            for plugin in server.plugins:
                plugin_lines = self._convert_plugin(plugin)
                lines.extend(plugin_lines)

        # Add forward zones
        forward_zones = self._extract_forward_zones(parsed)
        if forward_zones:
            lines.append("")
            lines.extend(forward_zones)

        return "\n".join(lines)

    def _convert_plugin(self, plugin) -> list[str]:
        """Convert a single CoreDNS plugin to Unbound config lines."""
        lines = []
        name = plugin.name
        args = plugin.args

        if name == "cache":
            # Convert cache settings
            size = "4m"  # Default
            if args and args[0].isdigit():
                # CoreDNS cache size is in seconds (TTL), not bytes
                pass
            lines.append(f"    msg-cache-size: {size}")
            lines.append(f"    rrset-cache-size: {size}")

        elif name == "log":
            lines.append("    log-queries: yes")

        elif name == "errors":
            lines.append("    log-servfail: yes")

        elif name == "dnssec":
            lines.append("    auto-trust-anchor-file: /var/lib/unbound/root.key")

        elif name == "loadbalance":
            lines.append("    rrset-roundrobin: yes")

        elif name == "loop":
            lines.append("    harden-glue: yes")
            lines.append("    harden-dnssec-stripped: yes")

        elif name == "bind":
            for addr in args:
                lines.append(f"    interface: {addr}")

        elif name == "acl":
            # Would need to parse ACL block and convert
            lines.append("    # ACL conversion requires manual review")

        elif name == "hosts":
            # Would need to parse hosts file and convert to local-data
            if args:
                lines.append(f"    # Convert hosts file: {args[0]}")

        return lines

    def _extract_forward_zones(self, parsed) -> list[str]:
        """Extract and convert forward zones from CoreDNS config."""
        lines = []

        for server in parsed.servers:
            for plugin in server.plugins:
                if plugin.name == "forward":
                    args = plugin.args
                    if not args:
                        continue

                    zone = args[0]
                    upstreams = args[1:] if len(args) > 1 else ["8.8.8.8"]

                    lines.append("forward-zone:")
                    lines.append(f'    name: "{zone}"')
                    for upstream in upstreams:
                        # Handle protocol prefixes
                        if upstream.startswith("tls://"):
                            addr = upstream[6:]
                            lines.append(f"    forward-addr: {addr}@853")
                            lines.append("    forward-tls-upstream: yes")
                        else:
                            lines.append(f"    forward-addr: {upstream}")
                    lines.append("")

        return lines

    def generate_migration_steps(
        self, source_config: str, target_config: str
    ) -> list[MigrationStep]:
        """Generate ordered migration steps."""
        steps = [
            MigrationStep(
                order=0,
                action="backup_config",
                description="Backup current CoreDNS configuration",
                source_config=source_config,
                reversible=True,
            ),
            MigrationStep(
                order=1,
                action="validate_source",
                description="Validate current CoreDNS is healthy",
                reversible=True,
            ),
            MigrationStep(
                order=2,
                action="write_target_config",
                description="Write Unbound configuration file",
                target_config=target_config,
                reversible=True,
            ),
            MigrationStep(
                order=3,
                action="start_target",
                description="Start Unbound service",
                reversible=True,
            ),
            MigrationStep(
                order=4,
                action="validate_parallel",
                description="Run parallel validation (both resolvers active)",
                reversible=True,
            ),
            MigrationStep(
                order=5,
                action="switch_traffic",
                description="Switch DNS traffic to Unbound",
                reversible=True,
                manual_required=True,
            ),
            MigrationStep(
                order=6,
                action="monitor",
                description="Monitor Unbound for stability (shadow mode)",
                reversible=True,
            ),
            MigrationStep(
                order=7,
                action="stop_source",
                description="Stop CoreDNS service",
                reversible=True,
            ),
            MigrationStep(
                order=8,
                action="cleanup",
                description="Clean up old CoreDNS configuration (optional)",
                reversible=False,
            ),
        ]

        return steps
