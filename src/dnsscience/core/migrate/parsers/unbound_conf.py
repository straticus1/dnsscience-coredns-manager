"""Unbound configuration file parser."""

import re
from typing import Any

from dnsscience.core.base import BaseConfigParser
from dnsscience.core.models import ConfigValidationError, ConfigValidationResult


class UnboundConfigParser(BaseConfigParser):
    """
    Parser for Unbound configuration files.

    Handles the unbound.conf format with sections like:
    - server:
    - forward-zone:
    - stub-zone:
    - remote-control:
    """

    KNOWN_SECTIONS = {
        "server",
        "forward-zone",
        "stub-zone",
        "auth-zone",
        "view",
        "remote-control",
        "python",
        "dynlib",
        "cachedb",
    }

    KNOWN_SERVER_OPTIONS = {
        "verbosity",
        "statistics-interval",
        "statistics-cumulative",
        "extended-statistics",
        "num-threads",
        "port",
        "interface",
        "outgoing-interface",
        "outgoing-range",
        "outgoing-port-permit",
        "outgoing-port-avoid",
        "outgoing-num-tcp",
        "incoming-num-tcp",
        "do-ip4",
        "do-ip6",
        "prefer-ip6",
        "do-udp",
        "do-tcp",
        "tcp-upstream",
        "udp-upstream-without-downstream",
        "ssl-upstream",
        "ssl-service-key",
        "ssl-service-pem",
        "ssl-port",
        "tls-cert-bundle",
        "https-port",
        "http-endpoint",
        "http-max-streams",
        "http-query-buffer-size",
        "http-response-buffer-size",
        "http-nodelay",
        "http-notls-downstream",
        "msg-cache-size",
        "msg-cache-slabs",
        "num-queries-per-thread",
        "jostle-timeout",
        "delay-close",
        "so-rcvbuf",
        "so-sndbuf",
        "so-reuseport",
        "ip-transparent",
        "ip-freebind",
        "rrset-cache-size",
        "rrset-cache-slabs",
        "cache-max-ttl",
        "cache-min-ttl",
        "cache-max-negative-ttl",
        "infra-host-ttl",
        "infra-cache-slabs",
        "infra-cache-numhosts",
        "infra-cache-min-rtt",
        "define-tag",
        "do-not-query-address",
        "do-not-query-localhost",
        "prefetch",
        "prefetch-key",
        "deny-any",
        "harden-short-bufsize",
        "harden-large-queries",
        "harden-glue",
        "harden-dnssec-stripped",
        "harden-below-nxdomain",
        "harden-referral-path",
        "harden-algo-downgrade",
        "use-caps-for-id",
        "caps-whitelist",
        "qname-minimisation",
        "qname-minimisation-strict",
        "aggressive-nsec",
        "private-address",
        "private-domain",
        "unwanted-reply-threshold",
        "do-not-query-address",
        "access-control",
        "access-control-tag",
        "access-control-tag-action",
        "access-control-tag-data",
        "access-control-view",
        "chroot",
        "username",
        "directory",
        "logfile",
        "pidfile",
        "log-identity",
        "log-time-ascii",
        "log-queries",
        "log-replies",
        "log-tag-queryreply",
        "log-local-actions",
        "log-servfail",
        "root-hints",
        "hide-identity",
        "hide-version",
        "hide-trustanchor",
        "identity",
        "version",
        "target-fetch-policy",
        "harden-short-bufsize",
        "minimal-responses",
        "rrset-roundrobin",
        "unknown-server-time-limit",
        "module-config",
        "trust-anchor-file",
        "auto-trust-anchor-file",
        "trust-anchor",
        "trusted-keys-file",
        "dlv-anchor-file",
        "dlv-anchor",
        "domain-insecure",
        "val-override-date",
        "val-sig-skew-min",
        "val-sig-skew-max",
        "val-bogus-ttl",
        "val-clean-additional",
        "val-log-level",
        "val-permissive-mode",
        "ignore-cd-flag",
        "serve-expired",
        "serve-expired-ttl",
        "serve-expired-ttl-reset",
        "serve-expired-reply-ttl",
        "serve-expired-client-timeout",
        "key-cache-size",
        "key-cache-slabs",
        "neg-cache-size",
        "local-zone",
        "local-data",
        "local-data-ptr",
        "unblock-lan-zones",
        "insecure-lan-zones",
    }

    def parse(self, config_text: str) -> dict:
        """Parse unbound.conf into structured dict."""
        result: dict[str, Any] = {}
        current_section: str | None = None
        current_section_data: dict[str, Any] = {}

        lines = config_text.split("\n")

        for line in lines:
            line = self._strip_comment(line).strip()
            if not line:
                continue

            # Check for section header
            section_match = re.match(r"^([a-z-]+):$", line)
            if section_match:
                # Save previous section
                if current_section:
                    self._add_section(result, current_section, current_section_data)

                current_section = section_match.group(1)
                current_section_data = {}
                continue

            # Parse key-value pair
            kv_match = re.match(r"^\s*([a-z-]+):\s*(.*)$", line)
            if kv_match and current_section:
                key = kv_match.group(1)
                value = kv_match.group(2).strip().strip('"')

                # Handle multi-value keys
                if key in current_section_data:
                    existing = current_section_data[key]
                    if isinstance(existing, list):
                        existing.append(value)
                    else:
                        current_section_data[key] = [existing, value]
                else:
                    current_section_data[key] = value

        # Save last section
        if current_section:
            self._add_section(result, current_section, current_section_data)

        return result

    def _strip_comment(self, line: str) -> str:
        """Remove comments from a line."""
        # Handle # comments
        if "#" in line:
            # Be careful not to strip # inside quotes
            in_quotes = False
            for i, char in enumerate(line):
                if char == '"':
                    in_quotes = not in_quotes
                elif char == "#" and not in_quotes:
                    return line[:i]
        return line

    def _add_section(self, result: dict, section: str, data: dict) -> None:
        """Add section data to result, handling multi-occurrence sections."""
        if section in ["forward-zone", "stub-zone", "auth-zone", "view"]:
            # These sections can appear multiple times
            if section not in result:
                result[section] = []
            result[section].append(data)
        else:
            # Single-occurrence sections
            result[section] = data

    def validate(self, config_text: str) -> ConfigValidationResult:
        """Validate unbound.conf syntax."""
        errors: list[ConfigValidationError] = []
        warnings: list[ConfigValidationError] = []

        lines = config_text.split("\n")
        current_section = None

        for i, line in enumerate(lines, 1):
            line = self._strip_comment(line).strip()
            if not line:
                continue

            # Check section header
            section_match = re.match(r"^([a-z-]+):$", line)
            if section_match:
                section_name = section_match.group(1)
                if section_name not in self.KNOWN_SECTIONS:
                    warnings.append(
                        ConfigValidationError(
                            line=i,
                            message=f"Unknown section: {section_name}",
                            severity="warning",
                        )
                    )
                current_section = section_name
                continue

            # Check key-value pairs
            kv_match = re.match(r"^\s*([a-z-]+):\s*(.*)$", line)
            if kv_match:
                key = kv_match.group(1)
                if current_section == "server" and key not in self.KNOWN_SERVER_OPTIONS:
                    warnings.append(
                        ConfigValidationError(
                            line=i,
                            message=f"Unknown server option: {key}",
                            severity="warning",
                        )
                    )
            elif current_section:
                # Line doesn't match expected format
                errors.append(
                    ConfigValidationError(
                        line=i,
                        message=f"Invalid line format: {line}",
                        severity="error",
                    )
                )

        return ConfigValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def to_dict(self, config_text: str) -> dict:
        """Convert config to dictionary."""
        return self.parse(config_text)
