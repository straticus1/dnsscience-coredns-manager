"""MCP Server implementation for DNS Science Toolkit."""

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.models import DNSQuery, RecordType, ResolverType

# Create the MCP server
server = Server("dnsscience-toolkit")

# Global clients (initialized on first use)
_coredns_client: CoreDNSClient | None = None


async def get_coredns_client() -> CoreDNSClient:
    """Get or create CoreDNS client."""
    global _coredns_client
    if _coredns_client is None:
        _coredns_client = CoreDNSClient()
        await _coredns_client.connect()
    return _coredns_client


# ============================================================================
# Tool Definitions
# ============================================================================


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return [
        # Service Management
        Tool(
            name="dns_service_status",
            description="Get the status of the DNS resolver service (CoreDNS or Unbound)",
            inputSchema={
                "type": "object",
                "properties": {
                    "resolver": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                        "description": "Target resolver",
                        "default": "coredns",
                    }
                },
            },
        ),
        Tool(
            name="dns_service_control",
            description="Control the DNS resolver service (start, stop, restart)",
            inputSchema={
                "type": "object",
                "properties": {
                    "resolver": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                        "default": "coredns",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["start", "stop", "restart"],
                        "description": "Action to perform",
                    },
                },
                "required": ["action"],
            },
        ),
        Tool(
            name="dns_service_reload",
            description="Reload DNS resolver configuration without restart",
            inputSchema={
                "type": "object",
                "properties": {
                    "resolver": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                        "default": "coredns",
                    }
                },
            },
        ),
        # Cache Operations
        Tool(
            name="dns_cache_flush",
            description="Flush the DNS cache (all entries)",
            inputSchema={
                "type": "object",
                "properties": {
                    "resolver": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                        "default": "coredns",
                    }
                },
            },
        ),
        Tool(
            name="dns_cache_stats",
            description="Get DNS cache statistics (hits, misses, size)",
            inputSchema={
                "type": "object",
                "properties": {
                    "resolver": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                        "default": "coredns",
                    }
                },
            },
        ),
        Tool(
            name="dns_cache_purge",
            description="Purge a specific domain from the DNS cache",
            inputSchema={
                "type": "object",
                "properties": {
                    "resolver": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                        "default": "coredns",
                    },
                    "domain": {
                        "type": "string",
                        "description": "Domain to purge from cache",
                    },
                },
                "required": ["domain"],
            },
        ),
        # Query Operations
        Tool(
            name="dns_query",
            description="Perform a DNS query (lookup a domain)",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain name to query",
                    },
                    "record_type": {
                        "type": "string",
                        "enum": ["A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA", "PTR", "SRV"],
                        "default": "A",
                        "description": "DNS record type",
                    },
                    "server": {
                        "type": "string",
                        "description": "DNS server to query (optional)",
                    },
                    "dnssec": {
                        "type": "boolean",
                        "default": False,
                        "description": "Request DNSSEC validation",
                    },
                },
                "required": ["domain"],
            },
        ),
        Tool(
            name="dns_query_trace",
            description="Trace DNS resolution path for a domain",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain name to trace",
                    },
                    "record_type": {
                        "type": "string",
                        "enum": ["A", "AAAA", "CNAME", "MX", "NS"],
                        "default": "A",
                    },
                },
                "required": ["domain"],
            },
        ),
        Tool(
            name="dns_query_compare",
            description="Compare DNS responses between two resolvers",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain to query on both resolvers",
                    },
                    "source": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                        "default": "coredns",
                    },
                    "target": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                        "default": "unbound",
                    },
                },
                "required": ["domain"],
            },
        ),
        # Configuration
        Tool(
            name="dns_config_validate",
            description="Validate DNS resolver configuration syntax",
            inputSchema={
                "type": "object",
                "properties": {
                    "resolver": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                        "default": "coredns",
                    },
                    "config": {
                        "type": "string",
                        "description": "Configuration content to validate",
                    },
                },
                "required": ["config"],
            },
        ),
        Tool(
            name="dns_config_get",
            description="Get current DNS resolver configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "resolver": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                        "default": "coredns",
                    }
                },
            },
        ),
        Tool(
            name="dns_config_diff",
            description="Show differences between current and new configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "resolver": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                        "default": "coredns",
                    },
                    "new_config": {
                        "type": "string",
                        "description": "New configuration to compare against current",
                    },
                },
                "required": ["new_config"],
            },
        ),
        # Migration
        Tool(
            name="dns_migrate_plan",
            description="Generate a migration plan between DNS resolvers",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                        "description": "Source resolver type",
                    },
                    "target": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                        "description": "Target resolver type",
                    },
                    "config": {
                        "type": "string",
                        "description": "Source configuration to migrate",
                    },
                },
                "required": ["source", "target", "config"],
            },
        ),
        Tool(
            name="dns_migrate_convert",
            description="Convert configuration from one resolver format to another",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                    },
                    "target": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                    },
                    "config": {
                        "type": "string",
                        "description": "Configuration to convert",
                    },
                },
                "required": ["source", "target", "config"],
            },
        ),
        Tool(
            name="dns_migrate_validate",
            description="Validate migration by comparing resolver responses",
            inputSchema={
                "type": "object",
                "properties": {
                    "domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of domains to test",
                    }
                },
            },
        ),
        # Health
        Tool(
            name="dns_health_check",
            description="Perform comprehensive health check on DNS resolver",
            inputSchema={
                "type": "object",
                "properties": {
                    "resolver": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                        "default": "coredns",
                    }
                },
            },
        ),
        Tool(
            name="dns_health_metrics",
            description="Get Prometheus metrics from DNS resolver",
            inputSchema={
                "type": "object",
                "properties": {
                    "resolver": {
                        "type": "string",
                        "enum": ["coredns", "unbound"],
                        "default": "coredns",
                    }
                },
            },
        ),
    ]


# ============================================================================
# Tool Handlers
# ============================================================================


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        result = await _handle_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def _handle_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Route tool calls to appropriate handlers."""

    # Service Management
    if name == "dns_service_status":
        return await _dns_service_status(args)
    elif name == "dns_service_control":
        return await _dns_service_control(args)
    elif name == "dns_service_reload":
        return await _dns_service_reload(args)

    # Cache Operations
    elif name == "dns_cache_flush":
        return await _dns_cache_flush(args)
    elif name == "dns_cache_stats":
        return await _dns_cache_stats(args)
    elif name == "dns_cache_purge":
        return await _dns_cache_purge(args)

    # Query Operations
    elif name == "dns_query":
        return await _dns_query(args)
    elif name == "dns_query_trace":
        return await _dns_query_trace(args)
    elif name == "dns_query_compare":
        return await _dns_query_compare(args)

    # Configuration
    elif name == "dns_config_validate":
        return await _dns_config_validate(args)
    elif name == "dns_config_get":
        return await _dns_config_get(args)
    elif name == "dns_config_diff":
        return await _dns_config_diff(args)

    # Migration
    elif name == "dns_migrate_plan":
        return await _dns_migrate_plan(args)
    elif name == "dns_migrate_convert":
        return await _dns_migrate_convert(args)
    elif name == "dns_migrate_validate":
        return await _dns_migrate_validate(args)

    # Health
    elif name == "dns_health_check":
        return await _dns_health_check(args)
    elif name == "dns_health_metrics":
        return await _dns_health_metrics(args)

    else:
        raise ValueError(f"Unknown tool: {name}")


# ============================================================================
# Tool Implementations
# ============================================================================


async def _dns_service_status(args: dict) -> dict:
    """Get service status."""
    client = await get_coredns_client()
    status = await client.get_status()
    return status.model_dump()


async def _dns_service_control(args: dict) -> dict:
    """Control service."""
    client = await get_coredns_client()
    action = args["action"]

    if action == "start":
        result = await client.start()
    elif action == "stop":
        result = await client.stop()
    elif action == "restart":
        result = await client.restart()
    else:
        raise ValueError(f"Unknown action: {action}")

    return result.model_dump()


async def _dns_service_reload(args: dict) -> dict:
    """Reload configuration."""
    client = await get_coredns_client()
    result = await client.reload()
    return result.model_dump()


async def _dns_cache_flush(args: dict) -> dict:
    """Flush cache."""
    client = await get_coredns_client()
    result = await client.flush_cache()
    return result.model_dump()


async def _dns_cache_stats(args: dict) -> dict:
    """Get cache stats."""
    client = await get_coredns_client()
    stats = await client.get_cache_stats()
    return stats.model_dump()


async def _dns_cache_purge(args: dict) -> dict:
    """Purge domain from cache."""
    client = await get_coredns_client()
    result = await client.purge_cache(domain=args["domain"])
    return result.model_dump()


async def _dns_query(args: dict) -> dict:
    """Perform DNS query."""
    client = await get_coredns_client()

    query = DNSQuery(
        name=args["domain"],
        record_type=RecordType(args.get("record_type", "A")),
        server=args.get("server"),
        dnssec=args.get("dnssec", False),
    )

    response = await client.query(query)
    return response.model_dump()


async def _dns_query_trace(args: dict) -> dict:
    """Trace DNS resolution."""
    client = await get_coredns_client()

    query = DNSQuery(
        name=args["domain"],
        record_type=RecordType(args.get("record_type", "A")),
    )

    responses = await client.trace(query)
    return {"trace": [r.model_dump() for r in responses]}


async def _dns_query_compare(args: dict) -> dict:
    """Compare query between resolvers."""
    from dnsscience.core.compare.engine import CompareEngine

    source_client = await get_coredns_client()
    # Would need to initialize target client based on args
    target_client = CoreDNSClient(port=5353)  # Different port for demo
    await target_client.connect()

    try:
        engine = CompareEngine(source_client, target_client)
        query = DNSQuery(name=args["domain"], record_type=RecordType.A)
        diff = await engine.compare_single(query)
        return diff.model_dump()
    finally:
        await target_client.disconnect()


async def _dns_config_validate(args: dict) -> dict:
    """Validate configuration."""
    resolver = args.get("resolver", "coredns")
    config = args["config"]

    if resolver == "coredns":
        from dnsscience.core.coredns.config import CorefileParser

        parser = CorefileParser()
        result = parser.validate(config)
    else:
        from dnsscience.core.migrate.parsers.unbound_conf import UnboundConfigParser

        parser = UnboundConfigParser()
        result = parser.validate(config)

    return result.model_dump()


async def _dns_config_get(args: dict) -> dict:
    """Get current configuration."""
    client = await get_coredns_client()
    config = await client.get_config()
    return {"config": config}


async def _dns_config_diff(args: dict) -> dict:
    """Diff configurations."""
    client = await get_coredns_client()
    diff = await client.diff_config(args["new_config"])
    return diff.model_dump()


async def _dns_migrate_plan(args: dict) -> dict:
    """Generate migration plan."""
    source = args["source"]
    target = args["target"]
    config = args["config"]

    if source == "coredns" and target == "unbound":
        from dnsscience.core.migrate.coredns_to_unbound import CoreDNSToUnboundMigrator

        migrator = CoreDNSToUnboundMigrator()
    elif source == "unbound" and target == "coredns":
        from dnsscience.core.migrate.unbound_to_coredns import UnboundToCoreDNSMigrator

        migrator = UnboundToCoreDNSMigrator()
    else:
        raise ValueError(f"Unsupported migration: {source} → {target}")

    mappings, warnings, unsupported = migrator.analyze_config(config)
    target_config = migrator.generate_target_config(config)
    steps = migrator.generate_migration_steps(config, target_config)

    return {
        "source": source,
        "target": target,
        "target_config": target_config,
        "mappings": [m.model_dump() for m in mappings],
        "warnings": warnings,
        "unsupported": unsupported,
        "steps": [s.model_dump() for s in steps],
    }


async def _dns_migrate_convert(args: dict) -> dict:
    """Convert configuration."""
    source = args["source"]
    target = args["target"]
    config = args["config"]

    if source == "coredns" and target == "unbound":
        from dnsscience.core.migrate.coredns_to_unbound import CoreDNSToUnboundMigrator

        migrator = CoreDNSToUnboundMigrator()
    elif source == "unbound" and target == "coredns":
        from dnsscience.core.migrate.unbound_to_coredns import UnboundToCoreDNSMigrator

        migrator = UnboundToCoreDNSMigrator()
    else:
        raise ValueError(f"Unsupported conversion: {source} → {target}")

    converted = migrator.generate_target_config(config)
    return {"converted_config": converted}


async def _dns_migrate_validate(args: dict) -> dict:
    """Validate migration."""
    from dnsscience.core.compare.engine import CompareEngine

    domains = args.get("domains", ["google.com", "cloudflare.com", "example.com"])

    source_client = await get_coredns_client()
    target_client = CoreDNSClient(port=5353)
    await target_client.connect()

    try:
        engine = CompareEngine(source_client, target_client)
        queries = [DNSQuery(name=d, record_type=RecordType.A) for d in domains]
        result = await engine.compare_bulk(queries)
        return result.model_dump()
    finally:
        await target_client.disconnect()


async def _dns_health_check(args: dict) -> dict:
    """Health check."""
    client = await get_coredns_client()
    health = await client.health_check()
    return health.model_dump()


async def _dns_health_metrics(args: dict) -> dict:
    """Get metrics."""
    client = await get_coredns_client()
    metrics = await client.get_metrics()
    return metrics.model_dump()


# ============================================================================
# Server Entry Point
# ============================================================================


def run():
    """Run the MCP server."""
    asyncio.run(main())


async def main():
    """Main async entry point."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    run()
