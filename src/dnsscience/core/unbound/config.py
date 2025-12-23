"""Unbound configuration generator."""

from dnsscience.core.base import BaseConfigGenerator
from dnsscience.core.models import ResolverType


class UnboundConfigGenerator(BaseConfigGenerator):
    """Generator for Unbound configuration files."""

    def generate(self, config_dict: dict) -> str:
        """Generate unbound.conf from structured configuration."""
        lines: list[str] = []

        # Server section
        if "server" in config_dict:
            lines.append("server:")
            server = config_dict["server"]

            for key, value in server.items():
                if isinstance(value, list):
                    for v in value:
                        lines.append(f"    {key}: {v}")
                elif isinstance(value, bool):
                    lines.append(f"    {key}: {'yes' if value else 'no'}")
                else:
                    lines.append(f"    {key}: {value}")
            lines.append("")

        # Forward zones
        for fz in config_dict.get("forward-zone", []):
            lines.append("forward-zone:")
            for key, value in fz.items():
                if isinstance(value, list):
                    for v in value:
                        lines.append(f"    {key}: {v}")
                else:
                    lines.append(f'    {key}: "{value}"' if key == "name" else f"    {key}: {value}")
            lines.append("")

        # Stub zones
        for sz in config_dict.get("stub-zone", []):
            lines.append("stub-zone:")
            for key, value in sz.items():
                if isinstance(value, list):
                    for v in value:
                        lines.append(f"    {key}: {v}")
                else:
                    lines.append(f'    {key}: "{value}"' if key == "name" else f"    {key}: {value}")
            lines.append("")

        # Auth zones
        for az in config_dict.get("auth-zone", []):
            lines.append("auth-zone:")
            for key, value in az.items():
                if isinstance(value, list):
                    for v in value:
                        lines.append(f"    {key}: {v}")
                else:
                    lines.append(f'    {key}: "{value}"' if key == "name" else f"    {key}: {value}")
            lines.append("")

        # Remote control
        if "remote-control" in config_dict:
            lines.append("remote-control:")
            rc = config_dict["remote-control"]
            for key, value in rc.items():
                if isinstance(value, bool):
                    lines.append(f"    {key}: {'yes' if value else 'no'}")
                else:
                    lines.append(f"    {key}: {value}")
            lines.append("")

        return "\n".join(lines)

    def from_other(self, other_config: dict, source_type: ResolverType) -> str:
        """Generate unbound.conf from another resolver's configuration."""
        if source_type == ResolverType.COREDNS:
            return self._from_coredns(other_config)
        raise ValueError(f"Unsupported source type: {source_type}")

    def _from_coredns(self, coredns_config: dict) -> str:
        """Convert CoreDNS configuration to unbound.conf."""
        config_dict = {
            "server": {
                "port": 53,
                "interface": ["0.0.0.0", "::0"],
                "access-control": ["0.0.0.0/0 allow", "::0/0 allow"],
                "do-ip4": True,
                "do-ip6": True,
                "do-udp": True,
                "do-tcp": True,
            },
            "forward-zone": [],
            "remote-control": {
                "control-enable": True,
                "control-interface": "127.0.0.1",
                "control-port": 8953,
            },
        }

        # Process each server block
        for server in coredns_config.get("servers", []):
            port = server.get("port", 53)
            config_dict["server"]["port"] = port

            for plugin in server.get("plugins", []):
                name = plugin.get("name", "")
                args = plugin.get("args", [])

                if name == "forward":
                    # Forward plugin -> forward-zone
                    zone = args[0] if args else "."
                    upstreams = args[1:] if len(args) > 1 else ["8.8.8.8"]

                    fz = {"name": zone, "forward-addr": upstreams}
                    config_dict["forward-zone"].append(fz)

                elif name == "log":
                    config_dict["server"]["log-queries"] = True

                elif name == "cache":
                    config_dict["server"]["msg-cache-size"] = "4m"
                    config_dict["server"]["rrset-cache-size"] = "4m"

                elif name == "dnssec":
                    config_dict["server"]["auto-trust-anchor-file"] = "/var/lib/unbound/root.key"

                elif name == "loadbalance":
                    config_dict["server"]["rrset-roundrobin"] = True

                elif name == "bind":
                    config_dict["server"]["interface"] = args

        return self.generate(config_dict)


def generate_default_config() -> str:
    """Generate a default Unbound configuration."""
    generator = UnboundConfigGenerator()

    return generator.generate({
        "server": {
            "verbosity": 1,
            "port": 53,
            "interface": ["0.0.0.0", "::0"],
            "access-control": [
                "127.0.0.0/8 allow",
                "10.0.0.0/8 allow",
                "172.16.0.0/12 allow",
                "192.168.0.0/16 allow",
                "::1/128 allow",
            ],
            "do-ip4": True,
            "do-ip6": True,
            "do-udp": True,
            "do-tcp": True,
            "hide-identity": True,
            "hide-version": True,
            "harden-glue": True,
            "harden-dnssec-stripped": True,
            "use-caps-for-id": False,
            "prefetch": True,
            "num-threads": 4,
            "msg-cache-size": "64m",
            "rrset-cache-size": "128m",
            "cache-min-ttl": 300,
            "cache-max-ttl": 86400,
            "auto-trust-anchor-file": "/var/lib/unbound/root.key",
        },
        "forward-zone": [
            {
                "name": ".",
                "forward-addr": ["8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1"],
            }
        ],
        "remote-control": {
            "control-enable": True,
            "control-interface": "127.0.0.1",
            "control-port": 8953,
        },
    })
