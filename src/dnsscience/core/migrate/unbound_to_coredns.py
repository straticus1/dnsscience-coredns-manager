"""Unbound to CoreDNS migration logic."""

from dnsscience.core.coredns.config import CorefileGenerator
from dnsscience.core.models import (
    MigrationStep,
    PluginMapping,
    ResolverType,
)
from dnsscience.core.migrate.parsers.unbound_conf import UnboundConfigParser


class UnboundToCoreDNSMigrator:
    """Migrator for Unbound → CoreDNS migrations."""

    source_type = ResolverType.UNBOUND
    target_type = ResolverType.COREDNS

    # Feature mapping table (reverse of CoreDNS → Unbound)
    FEATURE_MAPPINGS = {
        "forward-zone": PluginMapping(
            coredns_plugin="forward",
            unbound_feature="forward-zone",
            notes="Convert forward-zone blocks to forward plugin.",
            supported=True,
        ),
        "msg-cache-size": PluginMapping(
            coredns_plugin="cache",
            unbound_feature="msg-cache-size",
            notes="Map cache sizes. CoreDNS uses TTL-based caching.",
            supported=True,
        ),
        "log-queries": PluginMapping(
            coredns_plugin="log",
            unbound_feature="log-queries",
            notes="Map to log plugin.",
            supported=True,
        ),
        "log-servfail": PluginMapping(
            coredns_plugin="errors",
            unbound_feature="log-servfail",
            notes="Map to errors plugin.",
            supported=True,
        ),
        "auto-trust-anchor-file": PluginMapping(
            coredns_plugin="dnssec",
            unbound_feature="auto-trust-anchor-file",
            notes="Map to dnssec plugin with key file.",
            supported=True,
        ),
        "rrset-roundrobin": PluginMapping(
            coredns_plugin="loadbalance",
            unbound_feature="rrset-roundrobin",
            notes="Map to loadbalance plugin.",
            supported=True,
        ),
        "access-control": PluginMapping(
            coredns_plugin="acl",
            unbound_feature="access-control",
            notes="Convert access-control to acl plugin.",
            supported=True,
        ),
        "interface": PluginMapping(
            coredns_plugin="bind",
            unbound_feature="interface",
            notes="Convert interface to bind plugin.",
            supported=True,
        ),
        "local-data": PluginMapping(
            coredns_plugin="hosts",
            unbound_feature="local-data",
            notes="Convert local-data to hosts file format.",
            supported=True,
        ),
        "auth-zone": PluginMapping(
            coredns_plugin="file",
            unbound_feature="auth-zone",
            notes="Convert auth-zone to file plugin with zone file.",
            supported=True,
        ),
        "stub-zone": PluginMapping(
            coredns_plugin="forward",
            unbound_feature="stub-zone",
            notes="Convert stub-zone to forward plugin for specific zone.",
            supported=True,
        ),
        "private-address": PluginMapping(
            coredns_plugin="rewrite",
            unbound_feature="private-address",
            notes="May need rewrite plugin for private address filtering.",
            supported=False,
            requires_manual=True,
        ),
        "remote-control": PluginMapping(
            coredns_plugin=None,
            unbound_feature="remote-control",
            notes="No direct equivalent. CoreDNS uses different control mechanisms.",
            supported=False,
        ),
    }

    def __init__(self):
        self.parser = UnboundConfigParser()
        self.generator = CorefileGenerator()

    def analyze_config(self, config: str) -> tuple[list[PluginMapping], list[str], list[str]]:
        """Analyze Unbound configuration for migration."""
        parsed = self.parser.parse(config)

        mappings: list[PluginMapping] = []
        warnings: list[str] = []
        unsupported: list[str] = []

        # Check server section
        server = parsed.get("server", {})
        for key in server:
            if key in self.FEATURE_MAPPINGS:
                mapping = self.FEATURE_MAPPINGS[key]
                mappings.append(mapping)

                if not mapping.supported:
                    unsupported.append(f"{key}: {mapping.notes}")
                elif mapping.requires_manual:
                    warnings.append(f"{key}: Requires manual configuration - {mapping.notes}")

        # Check forward zones
        for fz in parsed.get("forward-zone", []):
            mapping = self.FEATURE_MAPPINGS.get("forward-zone")
            if mapping and mapping not in mappings:
                mappings.append(mapping)

        # Check for advanced features
        if "remote-control" in parsed:
            warnings.append(
                "remote-control section found. CoreDNS doesn't have equivalent. "
                "Consider using kubectl/API for control."
            )

        return mappings, warnings, unsupported

    def generate_target_config(self, source_config: str) -> str:
        """Generate CoreDNS Corefile from Unbound configuration."""
        parsed = self.parser.parse(source_config)

        # Build config dict for generator
        config_dict = {
            "servers": [self._build_server_block(parsed)],
            "imports": [],
            "snippets": {},
        }

        return self.generator.generate(config_dict)

    def _build_server_block(self, parsed: dict) -> dict:
        """Build a CoreDNS server block from parsed Unbound config."""
        server = parsed.get("server", {})

        # Determine port
        port = server.get("port", 53)

        # Build plugins list
        plugins = []

        # Always add essential plugins
        plugins.append({"name": "errors", "args": [], "block": ""})
        plugins.append({"name": "health", "args": [], "block": ""})
        plugins.append({"name": "ready", "args": [], "block": ""})

        # Logging
        if server.get("log-queries") == "yes":
            plugins.append({"name": "log", "args": [], "block": ""})

        # Cache
        msg_cache = server.get("msg-cache-size", "4m")
        # CoreDNS cache uses TTL in seconds
        plugins.append({"name": "cache", "args": ["30"], "block": ""})

        # Load balancing
        if server.get("rrset-roundrobin") == "yes":
            plugins.append({"name": "loadbalance", "args": [], "block": ""})

        # DNSSEC
        if "auto-trust-anchor-file" in server:
            plugins.append({"name": "dnssec", "args": [], "block": ""})

        # Bind interfaces
        interfaces = server.get("interface", [])
        if isinstance(interfaces, str):
            interfaces = [interfaces]
        if interfaces and interfaces != ["0.0.0.0"]:
            plugins.append({"name": "bind", "args": interfaces, "block": ""})

        # Forward zones
        for fz in parsed.get("forward-zone", []):
            zone_name = fz.get("name", ".")
            fwd_addrs = fz.get("forward-addr", [])
            if isinstance(fwd_addrs, str):
                fwd_addrs = [fwd_addrs]

            # Handle TLS upstreams
            if fz.get("forward-tls-upstream") == "yes":
                fwd_addrs = [f"tls://{addr}" if "@853" not in addr else addr for addr in fwd_addrs]

            plugins.append({
                "name": "forward",
                "args": [zone_name] + fwd_addrs,
                "block": "",
            })

        # Add standard plugins
        plugins.append({"name": "loop", "args": [], "block": ""})
        plugins.append({"name": "reload", "args": [], "block": ""})
        plugins.append({"name": "prometheus", "args": [":9153"], "block": ""})

        return {
            "zones": ["."],
            "port": port,
            "protocol": "dns",
            "plugins": plugins,
        }

    def generate_migration_steps(
        self, source_config: str, target_config: str
    ) -> list[MigrationStep]:
        """Generate ordered migration steps."""
        steps = [
            MigrationStep(
                order=0,
                action="backup_config",
                description="Backup current Unbound configuration",
                source_config=source_config,
                reversible=True,
            ),
            MigrationStep(
                order=1,
                action="validate_source",
                description="Validate current Unbound is healthy",
                reversible=True,
            ),
            MigrationStep(
                order=2,
                action="write_target_config",
                description="Write CoreDNS Corefile",
                target_config=target_config,
                reversible=True,
            ),
            MigrationStep(
                order=3,
                action="configure_k8s",
                description="Configure Kubernetes for CoreDNS (if applicable)",
                reversible=True,
                manual_required=True,
            ),
            MigrationStep(
                order=4,
                action="start_target",
                description="Start CoreDNS service",
                reversible=True,
            ),
            MigrationStep(
                order=5,
                action="validate_parallel",
                description="Run parallel validation (both resolvers active)",
                reversible=True,
            ),
            MigrationStep(
                order=6,
                action="switch_traffic",
                description="Switch DNS traffic to CoreDNS",
                reversible=True,
                manual_required=True,
            ),
            MigrationStep(
                order=7,
                action="monitor",
                description="Monitor CoreDNS for stability",
                reversible=True,
            ),
            MigrationStep(
                order=8,
                action="stop_source",
                description="Stop Unbound service",
                reversible=True,
            ),
            MigrationStep(
                order=9,
                action="cleanup",
                description="Clean up old Unbound configuration (optional)",
                reversible=False,
            ),
        ]

        return steps
