# CLI Reference

The `dnsctl` command-line tool provides comprehensive DNS management capabilities.

## Global Options

```bash
dnsctl [OPTIONS] COMMAND [ARGS]

Options:
  --resolver [coredns|unbound]  DNS resolver to manage (default: coredns)
  --host TEXT                   Resolver host address
  --port INTEGER                Resolver port
  --verbose                     Enable verbose output
  --json                        Output in JSON format
  --help                        Show help message
```

## Service Commands

### status

Display the current service status.

```bash
dnsctl service status

# Output:
# Resolver: CoreDNS
# Status: Running
# Uptime: 2d 5h 30m
# Version: 1.11.1
```

### start

Start the DNS service.

```bash
dnsctl service start
```

### stop

Stop the DNS service.

```bash
dnsctl service stop
```

### restart

Restart the DNS service.

```bash
dnsctl service restart
```

### reload

Reload the configuration without restarting.

```bash
dnsctl service reload
```

## Cache Commands

### stats

Display cache statistics.

```bash
dnsctl cache stats

# Output:
# Cache Size: 1,523 entries
# Hit Rate: 87.3%
# Hits: 45,234
# Misses: 6,543
```

### flush

Flush the DNS cache.

```bash
# Flush entire cache
dnsctl cache flush

# Flush specific domain
dnsctl cache flush --domain example.com

# Flush by record type
dnsctl cache flush --type A
```

### lookup

Look up a specific cache entry.

```bash
dnsctl cache lookup example.com
```

## Query Commands

### Basic Query

Query a domain for DNS records.

```bash
# A record (default)
dnsctl query example.com

# Specific record type
dnsctl query example.com --type MX
dnsctl query example.com --type AAAA
dnsctl query example.com --type NS
dnsctl query example.com --type TXT

# Query specific server
dnsctl query example.com --server 8.8.8.8

# Use TCP
dnsctl query example.com --tcp

# Set timeout
dnsctl query example.com --timeout 5
```

### Output Format

```bash
# Verbose output
dnsctl query example.com --verbose

# JSON output
dnsctl query example.com --json

# Output:
{
  "query": {
    "name": "example.com",
    "type": "A"
  },
  "response": {
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
}
```

## Compare Commands

Compare DNS responses between two resolvers.

### Single Comparison

```bash
dnsctl compare example.com

# Output:
# Domain: example.com
# Source (CoreDNS): NOERROR - 93.184.216.34 (25ms)
# Target (Unbound): NOERROR - 93.184.216.34 (18ms)
# Match: ✓
```

### Bulk Comparison

```bash
# From comma-separated list
dnsctl compare --bulk "example.com,google.com,cloudflare.com"

# From file
dnsctl compare --file domains.txt

# Output:
# Tested: 100 domains
# Matches: 98 (98%)
# Mismatches: 2 (2%)
# Confidence Score: 0.98
```

### Options

```bash
dnsctl compare [OPTIONS] DOMAIN

Options:
  --type TEXT              Record type (default: A)
  --source TEXT            Source resolver (default: configured)
  --target TEXT            Target resolver (default: configured)
  --bulk TEXT              Comma-separated domain list
  --file PATH              File with domains (one per line)
  --ignore-ttl             Ignore TTL differences
  --ignore-order           Ignore record order differences
```

## Config Commands

### validate

Validate a DNS configuration file.

```bash
# Validate CoreDNS Corefile
dnsctl config validate --file /etc/coredns/Corefile

# Validate inline config
dnsctl config validate --config ".:53 { forward . 8.8.8.8 }"

# Output:
# ✓ Configuration is valid
# Zones: 1
# Plugins: 3 (forward, cache, errors)
```

### show

Display the current configuration.

```bash
dnsctl config show
```

### generate

Generate a configuration from templates.

```bash
dnsctl config generate --template kubernetes --output Corefile
```

## Migrate Commands

### plan

Generate a migration plan.

```bash
dnsctl migrate plan \
  --source coredns \
  --target unbound \
  --config-file /etc/coredns/Corefile

# Output:
# Migration Plan: CoreDNS → Unbound
#
# Steps:
# 1. Parse CoreDNS configuration
# 2. Convert plugins to Unbound equivalents
# 3. Generate unbound.conf
# 4. Validate generated configuration
#
# Warnings:
# - kubernetes plugin has no Unbound equivalent (manual setup required)
#
# Generated Configuration:
# [preview of unbound.conf]
```

### convert

Convert configuration without full migration plan.

```bash
dnsctl migrate convert \
  --source coredns \
  --target unbound \
  --config-file /etc/coredns/Corefile \
  --output /etc/unbound/unbound.conf
```

### validate

Validate migration by comparing resolver responses.

```bash
dnsctl migrate validate --domains domains.txt

# Output:
# Migration Validation Results
# ----------------------------
# Domains Tested: 100
# Matches: 100 (100%)
# Recommendation: Safe to complete migration
```

## Health Commands

### Check Health

```bash
dnsctl health

# Output:
# Health Status: Healthy
# Checks:
#   ✓ DNS Resolution
#   ✓ Upstream Connectivity
#   ✓ Configuration Valid
#   ✓ Cache Operational
```

### Detailed Health

```bash
dnsctl health --verbose

# Shows detailed check information and timings
```

## Kubernetes Commands

### configmap

Manage CoreDNS ConfigMap.

```bash
# View current ConfigMap
dnsctl k8s configmap show

# Validate ConfigMap
dnsctl k8s configmap validate

# Update ConfigMap
dnsctl k8s configmap update --file Corefile
```

### pods

Test DNS from pods.

```bash
# Test DNS from a specific pod
dnsctl k8s test-pod my-pod --domain kubernetes.default.svc.cluster.local

# Test DNS from all pods in namespace
dnsctl k8s test-namespace default --domain example.com
```

### services

Discover services and their DNS names.

```bash
dnsctl k8s services --namespace default

# Output:
# Service                    DNS Name                                      IP
# my-service                 my-service.default.svc.cluster.local          10.96.0.10
# another-service            another-service.default.svc.cluster.local     10.96.0.11
```

## Environment Variables

```bash
# Default resolver
export DNSSCIENCE_RESOLVER=coredns

# CoreDNS settings
export DNSSCIENCE_COREDNS_HOST=localhost
export DNSSCIENCE_COREDNS_PORT=53

# Unbound settings
export DNSSCIENCE_UNBOUND_HOST=localhost
export DNSSCIENCE_UNBOUND_PORT=53

# Logging
export DNSSCIENCE_LOG_LEVEL=INFO
```

## Configuration File

Create `~/.dnsscience/config.yaml`:

```yaml
resolver: coredns

coredns:
  host: localhost
  port: 53
  metrics_port: 9153

unbound:
  host: localhost
  port: 53
  control_port: 8953

compare:
  ignore_ttl: true
  ignore_order: true

output:
  format: table  # or json
  verbose: false
```
