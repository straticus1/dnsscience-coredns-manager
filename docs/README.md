# DNS Science Toolkit Documentation

Comprehensive DNS management toolkit for CoreDNS and Unbound resolvers.

## Overview

The DNS Science Toolkit provides a unified interface for managing DNS resolvers in Kubernetes and standalone environments. Key features include:

- **Service Management**: Start, stop, restart, reload DNS services
- **Cache Operations**: View statistics, flush cache, inspect entries
- **Query Tools**: Direct DNS queries with detailed response analysis
- **Configuration Management**: Validate, generate, and apply configurations
- **Migration Engine**: Bidirectional migration between CoreDNS and Unbound
- **Comparison Tools**: Compare responses between resolvers for migration validation

## Quick Start

### Installation

```bash
# Install from PyPI
pip install dnsscience-toolkit

# Or install with all optional dependencies
pip install "dnsscience-toolkit[all]"
```

### CLI Usage

```bash
# Check service status
dnsctl service status

# Query a domain
dnsctl query example.com

# Compare resolvers
dnsctl compare example.com

# Create migration plan
dnsctl migrate plan --source coredns --target unbound --config-file /etc/coredns/Corefile
```

### API Server

```bash
# Start the API server
uvicorn dnsscience.api.main:app --host 0.0.0.0 --port 8000

# Or use the CLI
dnsctl api serve
```

## Documentation Index

- [CLI Reference](cli.md) - Command-line interface documentation
- [API Reference](api.md) - REST API endpoints and schemas
- [Migration Guide](migration-guide.md) - CoreDNS to Unbound migration
- [MCP Tools](mcp-tools.md) - Model Context Protocol integration
- [Kubernetes Deployment](kubernetes.md) - Helm chart and operator

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DNS Science Toolkit                       │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────┤
│    CLI      │  REST API   │  MCP Server │  n8n Nodes  │  Web UI │
├─────────────┴─────────────┴─────────────┴─────────────┴─────────┤
│                         Core Library                             │
├──────────────────┬──────────────────┬───────────────────────────┤
│  CoreDNS Client  │  Unbound Client  │  Compare/Migration Engine │
└──────────────────┴──────────────────┴───────────────────────────┘
```

## License

MIT License - After Dark Systems, LLC
