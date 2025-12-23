"""Corefile parser and generator for CoreDNS configuration."""

import re
from dataclasses import dataclass, field
from typing import Any

from dnsscience.core.base import BaseConfigGenerator, BaseConfigParser
from dnsscience.core.models import ConfigValidationError, ConfigValidationResult, ResolverType


@dataclass
class CorefilePlugin:
    """Represents a plugin block in a Corefile."""

    name: str
    args: list[str] = field(default_factory=list)
    block: dict[str, Any] = field(default_factory=dict)
    raw_block: str = ""


@dataclass
class CorefileServer:
    """Represents a server block in a Corefile."""

    zones: list[str]  # e.g., [".", "example.com"]
    port: int = 53
    protocol: str = "dns"  # dns, tls, https, grpc
    plugins: list[CorefilePlugin] = field(default_factory=list)


@dataclass
class CorefileConfig:
    """Parsed Corefile configuration."""

    servers: list[CorefileServer] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)  # import statements
    snippets: dict[str, str] = field(default_factory=dict)  # snippet definitions
    raw: str = ""


class CorefileParser(BaseConfigParser):
    """Parser for CoreDNS Corefile configuration."""

    # Known CoreDNS plugins for validation
    KNOWN_PLUGINS = {
        "acl",
        "any",
        "autopath",
        "bind",
        "bufsize",
        "cache",
        "cancel",
        "chaos",
        "clouddns",
        "debug",
        "dns64",
        "dnssec",
        "dnstap",
        "erratic",
        "errors",
        "etcd",
        "file",
        "forward",
        "grpc",
        "health",
        "hosts",
        "k8s_external",
        "kubernetes",
        "loadbalance",
        "local",
        "log",
        "loop",
        "metadata",
        "minimal",
        "nsid",
        "pprof",
        "prometheus",
        "ready",
        "reload",
        "rewrite",
        "root",
        "route53",
        "secondary",
        "sign",
        "template",
        "tls",
        "trace",
        "transfer",
        "whoami",
    }

    def parse(self, config_text: str) -> CorefileConfig:
        """Parse Corefile text into structured configuration."""
        config = CorefileConfig(raw=config_text)
        lines = config_text.split("\n")

        current_server: CorefileServer | None = None
        current_plugin: CorefilePlugin | None = None
        brace_depth = 0
        block_content: list[str] = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                i += 1
                continue

            # Handle import statements
            if line.startswith("import "):
                config.imports.append(line[7:].strip())
                i += 1
                continue

            # Handle snippet definitions
            if line.startswith("(") and ")" in line:
                snippet_name = line[1 : line.index(")")]
                # Collect snippet content
                snippet_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith(")"):
                    snippet_lines.append(lines[i])
                    i += 1
                config.snippets[snippet_name] = "\n".join(snippet_lines)
                i += 1
                continue

            # Handle server block start
            server_match = re.match(r"^([^\s{]+(?:\s+[^\s{]+)*)\s*{?\s*$", line)
            if server_match and brace_depth == 0:
                # Parse zones and port from server declaration
                server_decl = server_match.group(1)
                zones, port, protocol = self._parse_server_declaration(server_decl)
                current_server = CorefileServer(zones=zones, port=port, protocol=protocol)

                if "{" in line:
                    brace_depth += 1
                i += 1
                continue

            # Track brace depth
            if "{" in line:
                brace_depth += line.count("{")
            if "}" in line:
                brace_depth -= line.count("}")

                # Server block end
                if brace_depth == 0 and current_server:
                    if current_plugin:
                        current_plugin.raw_block = "\n".join(block_content)
                        current_server.plugins.append(current_plugin)
                        current_plugin = None
                        block_content = []
                    config.servers.append(current_server)
                    current_server = None
                    i += 1
                    continue

                # Plugin block end
                if brace_depth == 1 and current_plugin:
                    current_plugin.raw_block = "\n".join(block_content)
                    if current_server:
                        current_server.plugins.append(current_plugin)
                    current_plugin = None
                    block_content = []
                    i += 1
                    continue

            # Inside server block - parse plugins
            if current_server and brace_depth >= 1:
                if current_plugin and brace_depth > 1:
                    # Inside plugin block
                    block_content.append(line)
                else:
                    # New plugin
                    plugin = self._parse_plugin_line(line)
                    if plugin:
                        if "{" in line and "}" not in line:
                            # Plugin has a block
                            current_plugin = plugin
                            block_content = []
                        else:
                            # Single-line plugin
                            current_server.plugins.append(plugin)

            i += 1

        return config

    def _parse_server_declaration(self, decl: str) -> tuple[list[str], int, str]:
        """Parse server declaration like '.:53', 'dns://.:53', 'example.com:5353'."""
        zones = []
        port = 53
        protocol = "dns"

        # Handle protocol prefix
        if "://" in decl:
            proto, rest = decl.split("://", 1)
            protocol = proto
            decl = rest

        # Split multiple zones
        parts = decl.split()
        for part in parts:
            if ":" in part:
                zone, port_str = part.rsplit(":", 1)
                zones.append(zone)
                try:
                    port = int(port_str)
                except ValueError:
                    zones.append(part)
            else:
                zones.append(part)

        return zones or ["."], port, protocol

    def _parse_plugin_line(self, line: str) -> CorefilePlugin | None:
        """Parse a plugin line like 'forward . 8.8.8.8 8.8.4.4'."""
        line = line.strip()
        if not line or line.startswith("#"):
            return None

        # Remove trailing brace
        line = line.rstrip("{").strip()

        parts = line.split()
        if not parts:
            return None

        name = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        return CorefilePlugin(name=name, args=args)

    def validate(self, config_text: str) -> ConfigValidationResult:
        """Validate Corefile syntax and common issues."""
        errors: list[ConfigValidationError] = []
        warnings: list[ConfigValidationError] = []

        lines = config_text.split("\n")
        brace_count = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue

            # Check brace balance
            brace_count += stripped.count("{") - stripped.count("}")

            # Check for unknown plugins (warning only)
            parts = stripped.split()
            if parts and parts[0] not in self.KNOWN_PLUGINS:
                # Could be a server declaration or unknown plugin
                if not any(c in parts[0] for c in [".", ":", "/"]):
                    if parts[0] not in ["import", "(", ")"]:
                        warnings.append(
                            ConfigValidationError(
                                line=i,
                                message=f"Unknown plugin or directive: {parts[0]}",
                                severity="warning",
                            )
                        )

        # Check final brace balance
        if brace_count != 0:
            errors.append(
                ConfigValidationError(
                    message=f"Unbalanced braces: {brace_count} unclosed",
                    severity="error",
                )
            )

        # Try to parse
        try:
            self.parse(config_text)
        except Exception as e:
            errors.append(
                ConfigValidationError(
                    message=f"Parse error: {str(e)}",
                    severity="error",
                )
            )

        return ConfigValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def to_dict(self, config_text: str) -> dict:
        """Convert Corefile to dictionary representation."""
        config = self.parse(config_text)

        return {
            "servers": [
                {
                    "zones": s.zones,
                    "port": s.port,
                    "protocol": s.protocol,
                    "plugins": [
                        {
                            "name": p.name,
                            "args": p.args,
                            "block": p.raw_block,
                        }
                        for p in s.plugins
                    ],
                }
                for s in config.servers
            ],
            "imports": config.imports,
            "snippets": config.snippets,
        }


class CorefileGenerator(BaseConfigGenerator):
    """Generator for CoreDNS Corefile configuration."""

    def generate(self, config_dict: dict) -> str:
        """Generate Corefile from structured configuration."""
        lines: list[str] = []

        # Add imports
        for imp in config_dict.get("imports", []):
            lines.append(f"import {imp}")

        if config_dict.get("imports"):
            lines.append("")

        # Add snippets
        for name, content in config_dict.get("snippets", {}).items():
            lines.append(f"({name}) {{")
            for line in content.split("\n"):
                lines.append(f"    {line}")
            lines.append("}")
            lines.append("")

        # Add servers
        for server in config_dict.get("servers", []):
            # Server declaration
            zones = server.get("zones", ["."])
            port = server.get("port", 53)
            protocol = server.get("protocol", "dns")

            if protocol != "dns":
                zone_decl = f"{protocol}://{zones[0]}:{port}"
            else:
                zone_decl = " ".join(f"{z}:{port}" if z == zones[0] else z for z in zones)

            lines.append(f"{zone_decl} {{")

            # Add plugins
            for plugin in server.get("plugins", []):
                name = plugin.get("name", "")
                args = plugin.get("args", [])
                block = plugin.get("block", "")

                if block:
                    lines.append(f"    {name} {' '.join(args)} {{")
                    for block_line in block.strip().split("\n"):
                        lines.append(f"        {block_line}")
                    lines.append("    }")
                else:
                    arg_str = " ".join(args) if args else ""
                    lines.append(f"    {name} {arg_str}".rstrip())

            lines.append("}")
            lines.append("")

        return "\n".join(lines)

    def from_other(self, other_config: dict, source_type: ResolverType) -> str:
        """Generate Corefile from another resolver's configuration."""
        if source_type == ResolverType.UNBOUND:
            return self._from_unbound(other_config)
        raise ValueError(f"Unsupported source type: {source_type}")

    def _from_unbound(self, unbound_config: dict) -> str:
        """Convert Unbound configuration to Corefile."""
        servers = []

        # Main server block
        server_block = {
            "zones": ["."],
            "port": unbound_config.get("server", {}).get("port", 53),
            "protocol": "dns",
            "plugins": [],
        }

        # Map common Unbound settings to CoreDNS plugins
        server_settings = unbound_config.get("server", {})

        # Logging
        if server_settings.get("log-queries", "no") == "yes":
            server_block["plugins"].append({"name": "log", "args": []})

        # Errors
        server_block["plugins"].append({"name": "errors", "args": []})

        # Health
        server_block["plugins"].append({"name": "health", "args": []})

        # Ready
        server_block["plugins"].append({"name": "ready", "args": []})

        # Cache
        cache_size = server_settings.get("msg-cache-size", "4m")
        server_block["plugins"].append(
            {"name": "cache", "args": ["30"], "block": ""}  # 30 second TTL default
        )

        # Forward zones
        for fwd_zone in unbound_config.get("forward-zone", []):
            zone_name = fwd_zone.get("name", ".")
            fwd_addrs = fwd_zone.get("forward-addr", [])
            if isinstance(fwd_addrs, str):
                fwd_addrs = [fwd_addrs]

            server_block["plugins"].append(
                {"name": "forward", "args": [zone_name] + fwd_addrs, "block": ""}
            )

        # Loop detection
        server_block["plugins"].append({"name": "loop", "args": []})

        # Reload
        server_block["plugins"].append({"name": "reload", "args": []})

        # Prometheus metrics
        server_block["plugins"].append({"name": "prometheus", "args": [":9153"]})

        servers.append(server_block)

        return self.generate({"servers": servers})
