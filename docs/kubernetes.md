# Kubernetes Deployment Guide

Deploy the DNS Science Toolkit in Kubernetes using Helm.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.x
- kubectl configured for your cluster

## Quick Start

```bash
# Add the Helm repository (when published)
helm repo add dnsscience https://charts.dnsscience.io
helm repo update

# Install with default values
helm install dnsscience dnsscience/dnsscience

# Or install from local chart
helm install dnsscience ./k8s/helm/dnsscience
```

## Configuration

### Basic Configuration

```yaml
# values.yaml
api:
  enabled: true
  replicaCount: 2

admin:
  enabled: true
  replicaCount: 1

operator:
  enabled: false
```

### Full Configuration Example

```yaml
# values.yaml

global:
  imageRegistry: "your-registry.io/"
  imagePullSecrets:
    - name: registry-credentials

# API Server
api:
  enabled: true
  replicaCount: 3

  image:
    repository: dnsscience-toolkit
    tag: api-v1.0.0
    pullPolicy: IfNotPresent

  service:
    type: ClusterIP
    port: 8000

  ingress:
    enabled: true
    className: nginx
    annotations:
      cert-manager.io/cluster-issuer: letsencrypt
    hosts:
      - host: dnsscience.example.com
        paths:
          - path: /api
            pathType: Prefix
    tls:
      - secretName: dnsscience-tls
        hosts:
          - dnsscience.example.com

  resources:
    limits:
      cpu: 1000m
      memory: 1Gi
    requests:
      cpu: 200m
      memory: 256Mi

  env:
    DNSSCIENCE_RESOLVER: "coredns"
    DNSSCIENCE_COREDNS_HOST: "kube-dns.kube-system.svc"
    DNSSCIENCE_LOG_LEVEL: "INFO"

# Admin Panel
admin:
  enabled: true
  replicaCount: 2

  ingress:
    enabled: true
    className: nginx
    hosts:
      - host: admin.dnsscience.example.com
        paths:
          - path: /
            pathType: Prefix

# Kubernetes Operator
operator:
  enabled: true
  replicaCount: 1

  rbac:
    create: true

  serviceAccount:
    create: true
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/dnsscience-operator

# CoreDNS Management
coredns:
  enabled: true
  manageConfigMap: true
  configMapName: coredns
  configMapNamespace: kube-system

# Monitoring
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s
    labels:
      release: prometheus

# Pod Disruption Budget
podDisruptionBudget:
  enabled: true
  minAvailable: 1
```

## Installation

### Install with Custom Values

```bash
helm install dnsscience ./k8s/helm/dnsscience \
  --namespace dnsscience \
  --create-namespace \
  --values values.yaml
```

### Upgrade

```bash
helm upgrade dnsscience ./k8s/helm/dnsscience \
  --namespace dnsscience \
  --values values.yaml
```

### Uninstall

```bash
helm uninstall dnsscience --namespace dnsscience
```

## Components

### API Server

The API server provides REST endpoints for DNS management.

```bash
# Port forward for local access
kubectl port-forward svc/dnsscience-api 8000:8000 -n dnsscience

# Test the API
curl http://localhost:8000/api/v1/health
```

### Admin Panel

Lightweight htmx-based admin interface.

```bash
kubectl port-forward svc/dnsscience-admin 8001:8001 -n dnsscience
# Access at http://localhost:8001
```

### Kubernetes Operator

Watches for CRD changes and manages DNS configurations.

#### Custom Resource Definitions

**DNSMigration:**
```yaml
apiVersion: dnsscience.io/v1alpha1
kind: DNSMigration
metadata:
  name: coredns-to-unbound
spec:
  source: coredns
  target: unbound
  config: |
    .:53 {
        forward . 8.8.8.8
        cache 30
    }
  validateBefore: true
  testDomains:
    - kubernetes.default.svc.cluster.local
    - google.com
```

**DNSConfig:**
```yaml
apiVersion: dnsscience.io/v1alpha1
kind: DNSConfig
metadata:
  name: production-coredns
spec:
  resolver: coredns
  config: |
    .:53 {
        errors
        health
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
        }
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
  validateOnApply: true
```

## Monitoring

### Prometheus Integration

Enable ServiceMonitor for Prometheus Operator:

```yaml
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s
    labels:
      release: prometheus
```

### Metrics

Available metrics at `/metrics`:

- `dnsscience_queries_total` - Total DNS queries
- `dnsscience_query_duration_seconds` - Query duration histogram
- `dnsscience_cache_hits_total` - Cache hits
- `dnsscience_cache_misses_total` - Cache misses
- `dnsscience_compare_matches_total` - Comparison matches
- `dnsscience_compare_mismatches_total` - Comparison mismatches

### Grafana Dashboard

Import the provided dashboard:

```bash
kubectl apply -f k8s/grafana/dashboard-configmap.yaml
```

## Security

### RBAC

The operator requires specific RBAC permissions:

- ConfigMaps: get, list, watch, create, update, patch
- Pods: get, list, watch, create (for DNS testing)
- Services: get, list, watch
- Deployments: get, list, watch, update, patch
- Custom Resources: full access to dnsscience.io group

### Network Policies

Example network policy:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dnsscience-api
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/component: api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - port: 8000
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - port: 53
          protocol: UDP
        - port: 53
          protocol: TCP
```

### Pod Security

The chart configures secure defaults:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000

podSecurityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n dnsscience
kubectl describe pod dnsscience-api-xxx -n dnsscience
kubectl logs dnsscience-api-xxx -n dnsscience
```

### Check Operator Logs

```bash
kubectl logs -l app.kubernetes.io/component=operator -n dnsscience
```

### Validate CRDs

```bash
kubectl get crds | grep dnsscience
kubectl describe crd dnsmigrations.dnsscience.io
```

### Test DNS from Cluster

```bash
kubectl run dnstest --image=busybox:1.28 --rm -it --restart=Never -- \
  nslookup kubernetes.default.svc.cluster.local
```

## High Availability

For production deployments:

1. **API Server:** Run at least 2 replicas with pod anti-affinity
2. **PDB:** Enable pod disruption budget
3. **Resources:** Set appropriate resource limits
4. **Monitoring:** Enable Prometheus metrics

```yaml
api:
  replicaCount: 3
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector:
            matchLabels:
              app.kubernetes.io/component: api
          topologyKey: kubernetes.io/hostname

podDisruptionBudget:
  enabled: true
  minAvailable: 2
```
