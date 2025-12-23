# Migration Guide

This guide covers migrating between CoreDNS and Unbound DNS resolvers.

## Overview

The DNS Science Toolkit supports bidirectional migration:

- **CoreDNS → Unbound**: Convert Corefile to unbound.conf
- **Unbound → CoreDNS**: Convert unbound.conf to Corefile

## Migration Process

### 1. Analyze Current Configuration

First, understand your current setup:

```bash
# View current CoreDNS config
dnsctl config show

# Validate existing configuration
dnsctl config validate
```

### 2. Generate Migration Plan

Create a detailed migration plan:

```bash
dnsctl migrate plan \
  --source coredns \
  --target unbound \
  --config-file /etc/coredns/Corefile
```

The plan includes:
- Step-by-step migration process
- Plugin/feature mapping
- Warnings for unsupported features
- Generated target configuration

### 3. Review Plugin Mapping

#### CoreDNS to Unbound Mapping

| CoreDNS Plugin | Unbound Equivalent | Notes |
|----------------|-------------------|-------|
| `forward` | `forward-zone` | Direct mapping |
| `cache` | `cache-*` settings | Adjust TTL values |
| `prometheus` | `extended-statistics` | Different metrics format |
| `errors` | `verbosity: 1+` | Log level configuration |
| `log` | `log-queries: yes` | Query logging |
| `health` | Built-in | Unbound has native health |
| `ready` | Built-in | Unbound has native readiness |
| `loop` | `harden-*` options | Different protection mechanism |
| `kubernetes` | **Manual** | No direct equivalent |
| `hosts` | `local-data` | Static records |
| `file` | `auth-zone` | Zone files |
| `rewrite` | `local-zone` + rules | Limited support |

#### Unbound to CoreDNS Mapping

| Unbound Feature | CoreDNS Plugin | Notes |
|-----------------|---------------|-------|
| `forward-zone` | `forward` | Direct mapping |
| `cache-*` | `cache` | Simplified settings |
| `access-control` | `acl` | Access control lists |
| `local-data` | `hosts` | Static records |
| `stub-zone` | `forward` (conditional) | Stub forwarding |
| `auth-zone` | `file` | Authoritative zones |
| `do-ip6` | Plugin config | IPv6 support |
| `prefetch` | `cache` prefetch | Pre-fetching |

### 4. Test Configuration

Before applying, validate the generated configuration:

```bash
# Generate converted config
dnsctl migrate convert \
  --source coredns \
  --target unbound \
  --config-file /etc/coredns/Corefile \
  --output /tmp/unbound.conf

# Validate the generated config
unbound-checkconf /tmp/unbound.conf
```

### 5. Shadow Testing

Run both resolvers in parallel and compare responses:

```bash
# Start shadow comparison
dnsctl compare --bulk --file production-domains.txt

# Monitor over time
dnsctl compare shadow --duration 24h --sample-rate 0.1
```

### 6. Migration Validation

After switching, validate the migration:

```bash
dnsctl migrate validate \
  --domains production-domains.txt \
  --threshold 0.99
```

## CoreDNS to Unbound

### Example: Simple Forwarder

**Source (Corefile):**
```
.:53 {
    forward . 8.8.8.8 8.8.4.4
    cache 300
    errors
    log
}
```

**Generated (unbound.conf):**
```
server:
    interface: 0.0.0.0
    port: 53
    access-control: 0.0.0.0/0 allow

    # Cache settings (from cache 300)
    cache-max-ttl: 300
    cache-min-ttl: 0

    # Logging (from errors + log)
    verbosity: 1
    log-queries: yes

forward-zone:
    name: "."
    forward-addr: 8.8.8.8
    forward-addr: 8.8.4.4
```

### Example: Kubernetes Setup

**Source (Corefile):**
```
.:53 {
    errors
    health
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
    }
    prometheus :9153
    forward . /etc/resolv.conf
    cache 30
    loop
    reload
    loadbalance
}
```

**Generated (unbound.conf):**
```
server:
    interface: 0.0.0.0
    port: 53
    access-control: 10.0.0.0/8 allow

    cache-max-ttl: 30
    cache-min-ttl: 0

    extended-statistics: yes

    # NOTE: Kubernetes plugin requires manual setup
    # You need to configure stub-zone for cluster.local
    # pointing to the Kubernetes API or a dedicated DNS service

forward-zone:
    name: "."
    forward-addr: 8.8.8.8  # Replace with actual upstream
```

**Manual Steps Required:**
1. Set up Kubernetes DNS service endpoint
2. Configure stub-zone for cluster.local
3. Handle pod DNS policy changes

## Unbound to CoreDNS

### Example: Full Configuration

**Source (unbound.conf):**
```
server:
    interface: 0.0.0.0
    port: 53
    do-ip4: yes
    do-ip6: yes
    cache-max-ttl: 86400
    cache-min-ttl: 300
    prefetch: yes
    verbosity: 1
    log-queries: yes

forward-zone:
    name: "."
    forward-addr: 8.8.8.8
    forward-addr: 1.1.1.1

forward-zone:
    name: "internal.corp"
    forward-addr: 10.0.0.1
```

**Generated (Corefile):**
```
.:53 {
    errors
    log

    forward . 8.8.8.8 1.1.1.1

    cache 86400 {
        success 9984 86400
        denial 9984 300
        prefetch 10 10s
    }
}

internal.corp:53 {
    errors
    forward . 10.0.0.1
    cache 300
}
```

## Troubleshooting

### Common Issues

#### 1. Plugin Not Supported

```
Warning: kubernetes plugin has no Unbound equivalent
```

**Solution:** Manually configure the equivalent functionality or use a sidecar for Kubernetes DNS.

#### 2. Configuration Syntax Error

```
Error: Invalid forward-zone syntax at line 15
```

**Solution:** Check the generated configuration and adjust. Some complex configurations may need manual tweaking.

#### 3. Performance Differences

After migration, you may notice performance differences:

- **Higher latency:** Check cache settings and upstream configuration
- **Lower hit rate:** Adjust cache TTL values
- **Memory usage:** Tune cache size parameters

### Validation Checklist

- [ ] All zones are converted correctly
- [ ] Forwarding rules match
- [ ] Cache settings are appropriate
- [ ] Access controls are in place
- [ ] Logging is configured
- [ ] Health checks work
- [ ] Metrics are being collected
- [ ] Shadow testing shows >99% match rate

## Rollback

If issues occur, rollback to the previous configuration:

```bash
# Restore from backup
dnsctl migrate rollback --backup /path/to/backup.conf

# Or manually restore
cp /etc/coredns/Corefile.backup /etc/coredns/Corefile
dnsctl service restart
```

## Best Practices

1. **Always backup** the current configuration before migration
2. **Test in staging** before production migration
3. **Use shadow testing** to validate behavior
4. **Monitor metrics** during and after migration
5. **Have a rollback plan** ready
6. **Document manual changes** required for your environment
