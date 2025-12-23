# DNS Science CoreDNS Toolkit

**Project:** dnsscience-toolkit
**Owner:** After Dark Systems, LLC / DNS Science
**Language:** Python 3.11+
**License:** TBD

## Overview

Enterprise-grade toolkit for managing CoreDNS deployments, with bidirectional migration support for Unbound. Designed for complex k8s environments where DNS reliability is critical.

## Interfaces

| Interface | Technology | Purpose |
|-----------|------------|---------|
| CLI | Click/Typer | Operator commands, scripting |
| REST API | FastAPI | Programmatic access, integrations |
| Web Dashboard | React + FastAPI | Full management UI |
| Admin Panel | FastAPI + htmx | Lightweight quick-access UI |
| MCP Server | Python MCP SDK | AI/LLM integration |
| n8n Nodes | Custom nodes | Workflow automation |

## Deployment Modes

- **In-Cluster:** Runs as k8s Deployment/Operator, manages local CoreDNS
- **External:** Management station, manages remote clusters via API/kubectl

---

## Core Features

### 1. Service Control
- Start / Stop / Restart / Status
- Reload configuration (hot reload)
- Version info
- Process health monitoring

### 2. Cache Management
- Flush all cache
- Selective purge (by domain/zone/record type)
- Cache statistics (hits, misses, size, TTLs)
- Cache inspection (peek at entries)

### 3. Query Operations
- Single query (dig-style)
- Bulk query from file
- Query tracing (full resolution path)
- Latency benchmarking
- DNSSEC validation testing

### 4. Configuration Management
- Corefile validation / linting
- Config diff (running vs file)
- Plugin inventory and status
- Zone file management
- Hot reload triggers

### 5. Health & Monitoring
- Health check endpoint
- Prometheus metrics scraping
- Query rate statistics
- Error rate analysis
- Upstream resolver health
- Zone transfer status

### 6. Compare Engine
- Query both resolvers simultaneously
- Response diff (full record comparison)
- Timing comparison
- DNSSEC chain validation
- Batch comparison from query list
- Confidence scoring
- Shadow mode (continuous comparison)

### 7. Migration Engine
- **CoreDNS → Unbound**
  - Corefile parser
  - unbound.conf generator
  - Plugin mapping (where applicable)
  - Zone file conversion
  - k8s ConfigMap extraction

- **Unbound → CoreDNS**
  - unbound.conf parser
  - Corefile generator
  - Zone file conversion
  - k8s ConfigMap generation

- **Validation**
  - Pre-migration query baseline
  - Post-migration comparison
  - Rollback readiness check

### 8. Kubernetes Integration
- Pod DNS resolution testing
- Service discovery validation
- ConfigMap management
- Namespace-aware operations
- Helm values generation

### 9. Logging & Debug
- Log level control
- Query logging toggle
- Log streaming/tailing
- Error aggregation
- Debug trace mode

---

## Architecture

```
dnsscience-toolkit/
├── pyproject.toml
├── README.md
├── LICENSE
│
├── src/
│   └── dnsscience/
│       ├── __init__.py
│       ├── core/                    # Shared business logic
│       │   ├── __init__.py
│       │   ├── models.py            # Pydantic models
│       │   ├── coredns/
│       │   │   ├── __init__.py
│       │   │   ├── client.py        # CoreDNS control
│       │   │   ├── cache.py         # Cache operations
│       │   │   ├── config.py        # Corefile parsing/generation
│       │   │   ├── query.py         # DNS queries
│       │   │   └── health.py        # Health checks
│       │   │
│       │   ├── unbound/
│       │   │   ├── __init__.py
│       │   │   ├── client.py        # Unbound control
│       │   │   ├── cache.py         # Cache operations
│       │   │   ├── config.py        # unbound.conf parsing/gen
│       │   │   ├── query.py         # DNS queries
│       │   │   └── health.py        # Health checks
│       │   │
│       │   ├── compare/
│       │   │   ├── __init__.py
│       │   │   ├── engine.py        # Comparison logic
│       │   │   ├── differ.py        # Response diffing
│       │   │   ├── shadow.py        # Shadow mode
│       │   │   └── scoring.py       # Confidence scoring
│       │   │
│       │   ├── migrate/
│       │   │   ├── __init__.py
│       │   │   ├── coredns_to_unbound.py
│       │   │   ├── unbound_to_coredns.py
│       │   │   ├── parsers/
│       │   │   │   ├── corefile.py
│       │   │   │   └── unbound_conf.py
│       │   │   └── generators/
│       │   │       ├── corefile.py
│       │   │       └── unbound_conf.py
│       │   │
│       │   ├── k8s/
│       │   │   ├── __init__.py
│       │   │   ├── client.py        # k8s API client
│       │   │   ├── configmap.py     # ConfigMap operations
│       │   │   ├── pods.py          # Pod DNS testing
│       │   │   └── discovery.py     # Service discovery
│       │   │
│       │   └── metrics/
│       │       ├── __init__.py
│       │       ├── collector.py
│       │       └── prometheus.py
│       │
│       ├── cli/                     # CLI application
│       │   ├── __init__.py
│       │   ├── main.py              # Entry point
│       │   ├── commands/
│       │   │   ├── __init__.py
│       │   │   ├── service.py       # start/stop/restart/status
│       │   │   ├── cache.py         # flush/stats/inspect
│       │   │   ├── query.py         # query/trace/bench
│       │   │   ├── config.py        # validate/diff/reload
│       │   │   ├── compare.py       # compare/shadow
│       │   │   ├── migrate.py       # migrate/validate/rollback
│       │   │   └── k8s.py           # k8s operations
│       │   └── output.py            # Rich console output
│       │
│       ├── api/                     # REST API
│       │   ├── __init__.py
│       │   ├── main.py              # FastAPI app
│       │   ├── routers/
│       │   │   ├── __init__.py
│       │   │   ├── service.py
│       │   │   ├── cache.py
│       │   │   ├── query.py
│       │   │   ├── config.py
│       │   │   ├── compare.py
│       │   │   ├── migrate.py
│       │   │   └── k8s.py
│       │   ├── schemas.py           # API request/response models
│       │   └── deps.py              # Dependencies
│       │
│       ├── web/                     # Web applications
│       │   ├── __init__.py
│       │   ├── dashboard/           # React dashboard
│       │   │   └── (React app)
│       │   └── admin/               # htmx admin panel
│       │       ├── __init__.py
│       │       ├── app.py
│       │       └── templates/
│       │
│       ├── mcp/                     # MCP Server
│       │   ├── __init__.py
│       │   ├── server.py            # MCP server implementation
│       │   └── tools/
│       │       ├── __init__.py
│       │       ├── service.py
│       │       ├── cache.py
│       │       ├── query.py
│       │       ├── compare.py
│       │       └── migrate.py
│       │
│       └── n8n/                     # n8n integration
│           ├── __init__.py
│           ├── nodes/               # Custom n8n nodes
│           └── workflows/           # Example workflows
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── docker/
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   └── docker-compose.yml
│
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   └── helm/
│       └── dnsscience-toolkit/
│
└── docs/
    ├── cli.md
    ├── api.md
    ├── migration-guide.md
    └── mcp-tools.md
```

---

## Dependencies

### Core
- `dnspython` - DNS operations
- `pydantic` - Data validation
- `httpx` - HTTP client (async)
- `kubernetes` - k8s API client
- `pyyaml` - YAML parsing

### CLI
- `typer` - CLI framework
- `rich` - Terminal formatting

### API
- `fastapi` - REST framework
- `uvicorn` - ASGI server

### Web
- `jinja2` - Templating
- `htmx` - Admin panel interactivity

### MCP
- `mcp` - MCP SDK

### Testing
- `pytest`
- `pytest-asyncio`
- `pytest-cov`

---

## CLI Command Structure

```
dnsctl [OPTIONS] COMMAND [ARGS]

Global Options:
  --target, -t      Target resolver (coredns|unbound)
  --host, -h        Host address
  --port, -p        Port
  --kubeconfig      Path to kubeconfig
  --namespace, -n   Kubernetes namespace
  --output, -o      Output format (table|json|yaml)
  --verbose, -v     Verbose output
  --debug           Debug mode

Commands:
  service           Service control (start|stop|restart|status|reload)
  cache             Cache operations (flush|stats|inspect|purge)
  query             DNS queries (lookup|trace|bench|bulk)
  config            Configuration (validate|diff|show|reload)
  compare           Compare resolvers (run|shadow|report)
  migrate           Migration tools (plan|execute|validate|rollback)
  k8s               Kubernetes operations (test-pod|configmap|discover)
  health            Health checks (check|watch|metrics)
  version           Show version info
```

---

## API Endpoints

### Service Control
```
POST   /api/v1/service/start
POST   /api/v1/service/stop
POST   /api/v1/service/restart
GET    /api/v1/service/status
POST   /api/v1/service/reload
```

### Cache
```
DELETE /api/v1/cache                    # Flush all
DELETE /api/v1/cache/{domain}           # Purge domain
GET    /api/v1/cache/stats
GET    /api/v1/cache/entries
```

### Query
```
POST   /api/v1/query                    # Single query
POST   /api/v1/query/bulk               # Bulk queries
POST   /api/v1/query/trace              # Trace resolution
POST   /api/v1/query/bench              # Benchmark
```

### Config
```
GET    /api/v1/config                   # Get current config
POST   /api/v1/config/validate          # Validate config
GET    /api/v1/config/diff              # Diff running vs file
POST   /api/v1/config/reload            # Hot reload
```

### Compare
```
POST   /api/v1/compare                  # Compare query
POST   /api/v1/compare/bulk             # Bulk compare
POST   /api/v1/compare/shadow/start     # Start shadow mode
POST   /api/v1/compare/shadow/stop      # Stop shadow mode
GET    /api/v1/compare/shadow/report    # Get shadow report
```

### Migrate
```
POST   /api/v1/migrate/plan             # Generate migration plan
POST   /api/v1/migrate/execute          # Execute migration
POST   /api/v1/migrate/validate         # Validate migration
POST   /api/v1/migrate/rollback         # Rollback
GET    /api/v1/migrate/status           # Migration status
```

### Kubernetes
```
POST   /api/v1/k8s/test-resolution      # Test pod DNS
GET    /api/v1/k8s/configmaps           # List DNS configmaps
PUT    /api/v1/k8s/configmaps/{name}    # Update configmap
GET    /api/v1/k8s/services             # Discover services
```

### Health
```
GET    /api/v1/health                   # Health check
GET    /api/v1/health/metrics           # Prometheus metrics
GET    /api/v1/health/upstream          # Upstream health
```

---

## MCP Tools

### Service Management
- `dns_service_status` - Get service status
- `dns_service_control` - Start/stop/restart service
- `dns_service_reload` - Hot reload configuration

### Cache Operations
- `dns_cache_flush` - Flush DNS cache
- `dns_cache_stats` - Get cache statistics
- `dns_cache_purge` - Purge specific domain

### Query Operations
- `dns_query` - Perform DNS query
- `dns_query_trace` - Trace DNS resolution
- `dns_query_compare` - Compare between resolvers

### Configuration
- `dns_config_validate` - Validate configuration
- `dns_config_diff` - Show config differences
- `dns_config_get` - Get current configuration

### Migration
- `dns_migrate_plan` - Generate migration plan
- `dns_migrate_execute` - Execute migration
- `dns_migrate_validate` - Validate migration

### Health
- `dns_health_check` - Check resolver health
- `dns_health_metrics` - Get metrics

---

## Configuration

### Environment Variables
```bash
DNSCTL_TARGET=coredns              # Default target
DNSCTL_COREDNS_HOST=localhost      # CoreDNS host
DNSCTL_COREDNS_PORT=53             # CoreDNS port
DNSCTL_COREDNS_METRICS_PORT=9153   # Metrics port
DNSCTL_UNBOUND_HOST=localhost      # Unbound host
DNSCTL_UNBOUND_PORT=53             # Unbound port
DNSCTL_UNBOUND_CONTROL_PORT=8953   # unbound-control port
DNSCTL_KUBECONFIG=~/.kube/config   # Kubeconfig path
DNSCTL_NAMESPACE=kube-system       # Default namespace
DNSCTL_API_HOST=0.0.0.0            # API bind host
DNSCTL_API_PORT=8080               # API port
```

### Config File (~/.dnsctl.yaml)
```yaml
default_target: coredns

coredns:
  host: localhost
  port: 53
  metrics_port: 9153
  corefile_path: /etc/coredns/Corefile

unbound:
  host: localhost
  port: 53
  control_port: 8953
  config_path: /etc/unbound/unbound.conf

kubernetes:
  kubeconfig: ~/.kube/config
  namespace: kube-system

compare:
  timeout: 5s
  retries: 3

logging:
  level: INFO
  format: json
```

---

## Migration Mapping

### CoreDNS Plugin → Unbound Equivalent

| CoreDNS Plugin | Unbound Feature | Notes |
|----------------|-----------------|-------|
| forward | forward-zone | Direct mapping |
| cache | msg-cache, rrset-cache | Size params differ |
| log | log-queries | Similar |
| errors | log-servfail | Partial |
| health | (external) | Need separate health check |
| ready | (external) | Need separate readiness |
| kubernetes | stub-zone + scripts | Complex, needs custom |
| hosts | local-data | Manual conversion |
| file | auth-zone | Zone file format same |
| reload | (manual) | No hot reload equiv |
| loop | harden-* options | Different approach |
| dnssec | auto-trust-anchor | Different config |

---

## Development Phases

### Phase 1: Core Foundation
- [ ] Project scaffold
- [ ] Core models and interfaces
- [ ] CoreDNS client (basic operations)
- [ ] Unbound client (basic operations)
- [ ] Basic CLI commands

### Phase 2: Query & Compare
- [ ] Query engine
- [ ] Compare engine
- [ ] Diff algorithms
- [ ] Shadow mode

### Phase 3: Configuration & Migration
- [ ] Corefile parser/generator
- [ ] unbound.conf parser/generator
- [ ] Migration engine
- [ ] Validation suite

### Phase 4: API & Integration
- [ ] REST API
- [ ] MCP server
- [ ] n8n nodes

### Phase 5: Web Applications
- [ ] Admin panel (htmx)
- [ ] Dashboard (React)

### Phase 6: Kubernetes
- [ ] k8s client integration
- [ ] Operator mode
- [ ] Helm charts

---

## License

TBD - Recommend Apache 2.0 or MIT for ecosystem compatibility
