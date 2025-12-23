# DNS Science CoreDNS Manager

**Enterprise-grade CoreDNS management with Unbound migration support**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)]()

---

## Overview

DNS Science CoreDNS Manager is a unified control plane for managing DNS resolvers in Kubernetes and standalone environments. Built for system administrators and DevOps engineers who need reliable, observable DNS infrastructure.

### Key Features

- **Multi-Resolver Support** — Unified management for CoreDNS and Unbound
- **Bidirectional Migration** — Seamlessly migrate between resolvers with validation
- **Six Interface Options** — CLI, REST API, Web UI, Admin Panel, MCP Server, n8n Nodes
- **Kubernetes Native** — First-class support for K8s DNS management
- **Comparison Engine** — Validate resolver behavior before and after migration

## Quick Start

```bash
# Install from source
pip install -e .

# Check resolver status
dnsctl service status

# Query a domain with tracing
dnsctl query trace example.com

# Compare resolvers
dnsctl compare run example.com --resolver1 coredns --resolver2 unbound

# Plan a migration
dnsctl migrate plan --source coredns --target unbound
```

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DNS Science CoreDNS Manager                       │
├────────┬──────────────┬─────────────┬────────────┬──────────┬───────┤
│  CLI   │   REST API   │  MCP Server │  n8n Nodes │  Web UI  │ Admin │
│ (Typer)│   (FastAPI)  │  (MCP SDK)  │  (Custom)  │ (React)  │(htmx) │
├─────────────────────────────────────────────────────────────────────┤
│                       Core Business Logic                            │
├──────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐        ┌──────────────────┐                   │
│  │  CoreDNS Client  │        │  Unbound Client  │                   │
│  │  • Service Ctrl  │        │  • Service Ctrl  │                   │
│  │  • Cache Ops     │        │  • Cache Ops     │                   │
│  │  • Query Engine  │        │  • Query Engine  │                   │
│  │  • Config Parser │        │  • Config Parser │                   │
│  └──────────────────┘        └──────────────────┘                   │
│                                                                      │
│  ┌──────────────────┬──────────────────┬───────────────────┐        │
│  │  Compare Engine  │  Migration Engine │  K8s Integration │        │
│  │  • Diff Algo     │  • Config Conv    │  • Pod Testing   │        │
│  │  • Shadow Mode   │  • Validation     │  • Discovery     │        │
│  │  • Scoring       │  • Rollback       │  • ConfigMaps    │        │
│  └──────────────────┴──────────────────┴───────────────────┘        │
└──────────────────────────────────────────────────────────────────────┘
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `dnsctl service` | Service control (status, start, stop, restart, reload) |
| `dnsctl cache` | Cache operations (stats, flush, purge, inspect) |
| `dnsctl query` | DNS queries (lookup, trace, bench, bulk) |
| `dnsctl config` | Configuration management (validate, diff, show, reload) |
| `dnsctl compare` | Resolver comparison (run, shadow, report) |
| `dnsctl migrate` | Migration operations (plan, execute, validate, rollback) |
| `dnsctl k8s` | Kubernetes operations (test-pod, configmap, discover) |
| `dnsctl health` | Health monitoring (check, watch, metrics) |

## API Endpoints

Start the API server:

```bash
dnsctl-api
# or
uvicorn dnsscience.api.main:app --host 0.0.0.0 --port 8000
```

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/service/status` | Get resolver service status |
| `POST /api/v1/cache/flush` | Flush resolver cache |
| `POST /api/v1/query` | Execute DNS query |
| `POST /api/v1/compare/run` | Compare resolver responses |
| `POST /api/v1/migrate/plan` | Generate migration plan |
| `GET /api/v1/health` | Health check endpoint |

## MCP Integration

For AI/LLM integration via Model Context Protocol:

```bash
dnsctl-mcp
```

Available tools: `dns_service_status`, `dns_cache_flush`, `dns_query`, `dns_compare`, `dns_migrate_plan`, `dns_health_check`

## Deployment Options

### Docker Compose (Development)

```bash
cd docker
docker-compose up -d
```

Includes CoreDNS, Unbound, Prometheus, and Grafana.

### Kubernetes (Production)

```bash
helm install dnsscience ./k8s/helm/dnsscience \
  --namespace dns-system \
  --create-namespace
```

## Documentation

- [Installation Guide](INSTALL.md)
- [CLI Reference](docs/cli.md)
- [API Reference](docs/api.md)
- [Migration Guide](docs/migration-guide.md)
- [MCP Tools](docs/mcp-tools.md)
- [Kubernetes Deployment](docs/kubernetes.md)

## Requirements

- Python 3.11+
- CoreDNS 1.11+ and/or Unbound 1.19+
- Kubernetes 1.28+ (for K8s features)

## License

Apache License 2.0

---

**After Dark Systems, LLC** | **DNS Science**

*Built for the engineers who keep the internet running.*
