# Installation Guide

## Prerequisites

- **Python 3.11+** — Required for all installation methods
- **pip** or **uv** — Package manager
- **CoreDNS 1.11+** and/or **Unbound 1.19+** — Target DNS resolvers
- **kubectl** — For Kubernetes features (optional)

## Installation Methods

### Option 1: Install from Source (Development)

```bash
# Clone the repository
git clone https://github.com/afterdarksystems/dnsscience-toolkit.git
cd dnsscience-toolkit

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install in development mode
pip install -e ".[dev]"
```

### Option 2: Install from PyPI (Coming Soon)

```bash
pip install dnsscience-toolkit
```

### Option 3: Using uv (Recommended)

```bash
uv pip install -e ".[dev]"
```

## Verify Installation

```bash
# Check CLI is available
dnsctl --version

# Check service connectivity
dnsctl health check
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DNS_RESOLVER` | Target resolver type | `coredns` |
| `DNS_HOST` | Resolver host address | `127.0.0.1` |
| `DNS_PORT` | Resolver port | `53` |
| `COREDNS_CONTROL_URL` | CoreDNS control API URL | `http://localhost:9153` |
| `UNBOUND_CONTROL_SOCKET` | Unbound control socket path | `/var/run/unbound/control.sock` |
| `KUBERNETES_NAMESPACE` | K8s namespace for DNS | `kube-system` |

### Configuration File

Create `~/.config/dnsscience/config.yaml`:

```yaml
resolver:
  type: coredns
  host: 127.0.0.1
  port: 53

coredns:
  control_url: http://localhost:9153
  config_path: /etc/coredns/Corefile

unbound:
  control_socket: /var/run/unbound/control.sock
  config_path: /etc/unbound/unbound.conf

kubernetes:
  namespace: kube-system
  context: default
```

## Docker Installation

### Development Environment

```bash
cd docker
docker-compose up -d
```

This starts:
- CoreDNS on port 1053
- Unbound on port 1054
- Prometheus on port 9090
- Grafana on port 3000

### Running the Toolkit in Docker

```bash
docker build -t dnsscience-toolkit .
docker run -it dnsscience-toolkit dnsctl --help
```

## Kubernetes Installation

### Using Helm

```bash
# Add the Helm repository (coming soon)
# helm repo add dnsscience https://charts.dnsscience.io
# helm repo update

# Install from local chart
helm install dnsscience ./k8s/helm/dnsscience-toolkit \
  --namespace dns-system \
  --create-namespace \
  --values your-values.yaml
```

### Minimal Values File

```yaml
# values.yaml
resolver:
  type: coredns

api:
  enabled: true
  replicas: 2

mcp:
  enabled: false

monitoring:
  prometheus:
    enabled: true
```

### RBAC Requirements

The toolkit requires these Kubernetes permissions:

```yaml
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods/exec"]
    verbs: ["create"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "patch"]
```

## API Server Setup

### Standalone

```bash
# Start API server
dnsctl-api

# Or with uvicorn directly
uvicorn dnsscience.api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4
```

### Behind Nginx

```nginx
upstream dnsscience_api {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl;
    server_name api.dns.example.com;

    location / {
        proxy_pass http://dnsscience_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## MCP Server Setup

For AI/LLM integration:

```bash
# Start MCP server
dnsctl-mcp

# Configure in Claude Desktop (claude_desktop_config.json)
{
  "mcpServers": {
    "dnsscience": {
      "command": "dnsctl-mcp",
      "args": []
    }
  }
}
```

## Troubleshooting

### Common Issues

**Permission denied on control socket:**
```bash
# Add user to appropriate group
sudo usermod -aG unbound $USER
# Or adjust socket permissions
sudo chmod 660 /var/run/unbound/control.sock
```

**CoreDNS metrics endpoint not accessible:**
```bash
# Ensure prometheus plugin is enabled in Corefile
# prometheus :9153
```

**Kubernetes connection issues:**
```bash
# Verify kubeconfig
kubectl config current-context
kubectl get pods -n kube-system
```

### Debug Mode

```bash
# Enable verbose output
dnsctl --debug service status

# Check configuration
dnsctl config show
```

## Upgrading

```bash
# From source
git pull
pip install -e ".[dev]"

# From PyPI
pip install --upgrade dnsscience-toolkit
```

## Uninstalling

```bash
# Remove package
pip uninstall dnsscience-toolkit

# Remove configuration
rm -rf ~/.config/dnsscience

# Remove Docker resources
cd docker && docker-compose down -v

# Remove Kubernetes resources
helm uninstall dnsscience -n dns-system
```

---

**After Dark Systems, LLC** | **DNS Science**
