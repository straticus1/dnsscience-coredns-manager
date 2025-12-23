# REST API Reference

The DNS Science Toolkit provides a comprehensive REST API for DNS management.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

By default, the API runs without authentication. For production, configure authentication via environment variables or reverse proxy.

## Endpoints

### Service Management

#### GET /service/status

Get current service status.

**Response:**
```json
{
  "resolver": "coredns",
  "running": true,
  "uptime_seconds": 86400,
  "version": "1.11.1",
  "config_path": "/etc/coredns/Corefile"
}
```

#### POST /service/start

Start the DNS service.

**Response:**
```json
{
  "success": true,
  "message": "Service started"
}
```

#### POST /service/stop

Stop the DNS service.

#### POST /service/restart

Restart the DNS service.

#### POST /service/reload

Reload configuration without restart.

---

### Cache Operations

#### GET /cache/stats

Get cache statistics.

**Response:**
```json
{
  "size": 1523,
  "hits": 45234,
  "misses": 6543,
  "hit_rate": 0.873
}
```

#### POST /cache/flush

Flush the cache.

**Request Body (optional):**
```json
{
  "domain": "example.com",
  "record_type": "A"
}
```

**Response:**
```json
{
  "success": true,
  "flushed_entries": 15
}
```

#### GET /cache/lookup

Look up a cache entry.

**Query Parameters:**
- `domain` (required): Domain name
- `type` (optional): Record type (default: A)

---

### DNS Query

#### GET /query

Execute a DNS query.

**Query Parameters:**
- `domain` (required): Domain name to query
- `type` (optional): Record type (default: A)
- `server` (optional): DNS server to query
- `tcp` (optional): Use TCP (default: false)
- `timeout` (optional): Query timeout in seconds

**Response:**
```json
{
  "query": {
    "name": "example.com",
    "record_type": "A"
  },
  "records": [
    {
      "name": "example.com",
      "record_type": "A",
      "ttl": 300,
      "data": "93.184.216.34"
    }
  ],
  "rcode": "NOERROR",
  "query_time_ms": 25.4,
  "server": "127.0.0.1"
}
```

---

### Configuration

#### GET /config

Get current configuration.

**Response:**
```json
{
  "resolver": "coredns",
  "config": ".:53 {\n    forward . 8.8.8.8\n    cache 30\n}\n",
  "zones": ["."],
  "plugins": ["forward", "cache"]
}
```

#### POST /config/validate

Validate a configuration.

**Request Body:**
```json
{
  "config": ".:53 {\n    forward . 8.8.8.8\n}",
  "resolver": "coredns"
}
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

#### POST /config/apply

Apply a new configuration.

**Request Body:**
```json
{
  "config": ".:53 {\n    forward . 8.8.8.8\n    cache 30\n}",
  "validate": true,
  "restart": true
}
```

---

### Comparison

#### GET /compare/single

Compare a single query between resolvers.

**Query Parameters:**
- `domain` (required): Domain name
- `type` (optional): Record type

**Response:**
```json
{
  "query": {
    "name": "example.com",
    "record_type": "A"
  },
  "source_response": {
    "rcode": "NOERROR",
    "records": [...],
    "query_time_ms": 25.0
  },
  "target_response": {
    "rcode": "NOERROR",
    "records": [...],
    "query_time_ms": 18.0
  },
  "match": true,
  "timing_diff_ms": 7.0,
  "differences": []
}
```

#### POST /compare/bulk

Compare multiple queries.

**Request Body:**
```json
{
  "domains": ["example.com", "google.com", "cloudflare.com"],
  "type": "A",
  "ignore_ttl": true
}
```

**Response:**
```json
{
  "queries_tested": 3,
  "matches": 3,
  "mismatches": 0,
  "errors": 0,
  "confidence_score": 1.0,
  "results": [...]
}
```

---

### Migration

#### POST /migrate/plan

Create a migration plan.

**Request Body:**
```json
{
  "source": "coredns",
  "target": "unbound",
  "config": ".:53 {\n    forward . 8.8.8.8\n}"
}
```

**Response:**
```json
{
  "source": "coredns",
  "target": "unbound",
  "steps": [
    {
      "order": 1,
      "description": "Parse CoreDNS configuration",
      "automated": true
    },
    {
      "order": 2,
      "description": "Convert forward plugin to forward-zone",
      "automated": true
    }
  ],
  "warnings": [],
  "source_config": ".:53 {...}",
  "target_config": "forward-zone:\n    name: .\n    forward-addr: 8.8.8.8"
}
```

#### POST /migrate/convert

Convert configuration only.

**Request Body:**
```json
{
  "source": "coredns",
  "target": "unbound",
  "config": ".:53 {\n    forward . 8.8.8.8\n}"
}
```

**Response:**
```json
{
  "converted_config": "server:\n    interface: 0.0.0.0\n\nforward-zone:\n    name: \".\"\n    forward-addr: 8.8.8.8"
}
```

#### POST /migrate/validate

Validate a migration by comparing responses.

**Request Body:**
```json
{
  "domains": ["example.com", "google.com"],
  "threshold": 0.99
}
```

**Response:**
```json
{
  "valid": true,
  "queries_tested": 2,
  "matches": 2,
  "mismatches": 0,
  "confidence_score": 1.0,
  "recommendation": "Safe to proceed with migration"
}
```

---

### Health

#### GET /health

Full health check.

**Response:**
```json
{
  "state": "healthy",
  "checks": {
    "dns_resolution": true,
    "upstream_connectivity": true,
    "config_valid": true,
    "cache_operational": true
  },
  "message": "All checks passed"
}
```

#### GET /health/live

Liveness probe (Kubernetes).

**Response:** `200 OK` or `503 Service Unavailable`

#### GET /health/ready

Readiness probe (Kubernetes).

**Response:** `200 OK` or `503 Service Unavailable`

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid configuration syntax",
    "details": {
      "line": 5,
      "column": 10,
      "expected": "}"
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid input or configuration |
| `NOT_FOUND` | 404 | Resource not found |
| `SERVICE_ERROR` | 500 | Internal service error |
| `UPSTREAM_ERROR` | 502 | Upstream DNS error |
| `TIMEOUT` | 504 | Operation timed out |

---

## OpenAPI Specification

The full OpenAPI specification is available at:

```
GET /openapi.json
```

Interactive documentation (Swagger UI):

```
GET /docs
```

Alternative documentation (ReDoc):

```
GET /redoc
```
