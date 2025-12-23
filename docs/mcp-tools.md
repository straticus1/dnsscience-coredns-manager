# MCP Tools Reference

The DNS Science Toolkit provides a Model Context Protocol (MCP) server for AI/LLM integration.

## Overview

MCP (Model Context Protocol) enables AI assistants to interact with DNS management tools directly. The DNS Science MCP server exposes 17 tools for comprehensive DNS operations.

## Starting the MCP Server

```bash
# Run the MCP server
python -m dnsscience.mcp.server

# Or via stdio (for Claude Desktop integration)
dnsctl mcp serve
```

## Claude Desktop Configuration

Add to your Claude Desktop configuration (`~/.claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "dnsscience": {
      "command": "python",
      "args": ["-m", "dnsscience.mcp.server"],
      "env": {
        "DNSSCIENCE_RESOLVER": "coredns",
        "DNSSCIENCE_COREDNS_HOST": "localhost"
      }
    }
  }
}
```

## Available Tools

### Service Management

#### dns_service_status

Get the current DNS service status.

**Parameters:** None

**Returns:**
```json
{
  "resolver": "coredns",
  "running": true,
  "uptime_seconds": 86400,
  "version": "1.11.1"
}
```

#### dns_service_control

Control the DNS service (start, stop, restart, reload).

**Parameters:**
- `action` (string, required): One of "start", "stop", "restart", "reload"

**Returns:**
```json
{
  "success": true,
  "message": "Service restarted successfully"
}
```

### Cache Operations

#### dns_cache_stats

Get cache statistics.

**Parameters:** None

**Returns:**
```json
{
  "size": 1523,
  "hits": 45234,
  "misses": 6543,
  "hit_rate": 0.873
}
```

#### dns_cache_flush

Flush the DNS cache.

**Parameters:**
- `domain` (string, optional): Specific domain to flush
- `record_type` (string, optional): Record type to flush

**Returns:**
```json
{
  "success": true,
  "flushed_entries": 15
}
```

### DNS Query

#### dns_query

Execute a DNS query.

**Parameters:**
- `domain` (string, required): Domain name to query
- `record_type` (string, optional): Record type (default: "A")
- `server` (string, optional): DNS server to query
- `use_tcp` (boolean, optional): Use TCP instead of UDP

**Returns:**
```json
{
  "rcode": "NOERROR",
  "records": [
    {
      "name": "example.com",
      "type": "A",
      "ttl": 300,
      "data": "93.184.216.34"
    }
  ],
  "query_time_ms": 25.4
}
```

#### dns_query_bulk

Execute multiple DNS queries.

**Parameters:**
- `domains` (array, required): List of domain names
- `record_type` (string, optional): Record type (default: "A")

**Returns:**
```json
{
  "results": [
    {"domain": "example.com", "rcode": "NOERROR", "records": [...]},
    {"domain": "google.com", "rcode": "NOERROR", "records": [...]}
  ],
  "total": 2,
  "successful": 2,
  "failed": 0
}
```

### Configuration

#### dns_config_get

Get current DNS configuration.

**Parameters:** None

**Returns:**
```json
{
  "resolver": "coredns",
  "config": ".:53 {\n    forward . 8.8.8.8\n}",
  "zones": ["."],
  "plugins": ["forward"]
}
```

#### dns_config_validate

Validate a DNS configuration.

**Parameters:**
- `config` (string, required): Configuration to validate
- `resolver` (string, optional): Resolver type (coredns/unbound)

**Returns:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["Consider adding cache plugin"]
}
```

#### dns_config_apply

Apply a new configuration.

**Parameters:**
- `config` (string, required): New configuration
- `validate` (boolean, optional): Validate before applying (default: true)
- `restart` (boolean, optional): Restart after applying (default: true)

**Returns:**
```json
{
  "success": true,
  "message": "Configuration applied and service restarted"
}
```

### Comparison

#### dns_compare

Compare DNS responses between resolvers.

**Parameters:**
- `domain` (string, required): Domain to compare
- `record_type` (string, optional): Record type

**Returns:**
```json
{
  "match": true,
  "source_response": {...},
  "target_response": {...},
  "timing_diff_ms": 7.0,
  "differences": []
}
```

#### dns_compare_bulk

Compare multiple domains.

**Parameters:**
- `domains` (array, required): List of domains
- `record_type` (string, optional): Record type
- `ignore_ttl` (boolean, optional): Ignore TTL differences

**Returns:**
```json
{
  "queries_tested": 100,
  "matches": 98,
  "mismatches": 2,
  "confidence_score": 0.98,
  "results": [...]
}
```

### Migration

#### dns_migrate_plan

Create a migration plan.

**Parameters:**
- `source` (string, required): Source resolver type
- `target` (string, required): Target resolver type
- `config` (string, required): Source configuration

**Returns:**
```json
{
  "steps": [
    {"order": 1, "description": "Parse configuration", "automated": true}
  ],
  "warnings": ["kubernetes plugin requires manual setup"],
  "target_config": "forward-zone:\n    name: .\n    ..."
}
```

#### dns_migrate_convert

Convert configuration between formats.

**Parameters:**
- `source` (string, required): Source resolver type
- `target` (string, required): Target resolver type
- `config` (string, required): Configuration to convert

**Returns:**
```json
{
  "converted_config": "server:\n    interface: 0.0.0.0\n..."
}
```

#### dns_migrate_validate

Validate migration by comparing responses.

**Parameters:**
- `domains` (array, optional): Domains to test
- `threshold` (number, optional): Minimum confidence score

**Returns:**
```json
{
  "valid": true,
  "confidence_score": 0.99,
  "recommendation": "Safe to proceed"
}
```

### Health

#### dns_health_check

Perform a health check.

**Parameters:** None

**Returns:**
```json
{
  "state": "healthy",
  "checks": {
    "dns_resolution": true,
    "upstream_connectivity": true,
    "config_valid": true
  }
}
```

### Kubernetes

#### dns_k8s_configmap

Manage CoreDNS ConfigMap in Kubernetes.

**Parameters:**
- `action` (string, required): "get", "validate", or "update"
- `config` (string, optional): New configuration (for update)

**Returns:**
```json
{
  "name": "coredns",
  "namespace": "kube-system",
  "data": {"Corefile": "..."}
}
```

#### dns_k8s_test_pod

Test DNS resolution from a Kubernetes pod.

**Parameters:**
- `pod_name` (string, required): Pod name
- `namespace` (string, optional): Pod namespace
- `domain` (string, required): Domain to resolve

**Returns:**
```json
{
  "success": true,
  "pod": "my-pod",
  "domain": "kubernetes.default.svc.cluster.local",
  "response": {...}
}
```

## Example Conversations

### Query DNS

**User:** "Can you check if example.com resolves correctly?"

**Assistant:** Uses `dns_query` tool with domain="example.com"

### Compare Resolvers

**User:** "Compare how our CoreDNS and Unbound handle google.com"

**Assistant:** Uses `dns_compare` tool with domain="google.com"

### Plan Migration

**User:** "I want to migrate from CoreDNS to Unbound. Here's my current config..."

**Assistant:** Uses `dns_migrate_plan` tool to generate migration plan

### Troubleshoot Issues

**User:** "DNS seems slow, can you check the cache?"

**Assistant:** Uses `dns_cache_stats` tool to check hit rate and size

## Error Handling

All tools return structured errors:

```json
{
  "error": {
    "code": "CONNECTION_ERROR",
    "message": "Failed to connect to DNS server",
    "details": {...}
  }
}
```

## Security Considerations

- The MCP server runs with the same permissions as the host process
- Sensitive operations (config changes, service control) should be access-controlled
- Consider running in a sandboxed environment for untrusted AI interactions
