"""Health check API endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.models import HealthStatus

router = APIRouter()


async def get_client() -> CoreDNSClient:
    from dnsscience.api.main import get_coredns_client
    return get_coredns_client()


@router.get("", response_model=HealthStatus)
async def health_check(client: CoreDNSClient = Depends(get_client)):
    """Perform comprehensive health check."""
    return await client.health_check()


@router.get("/live")
async def liveness():
    """Kubernetes liveness probe."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness(client: CoreDNSClient = Depends(get_client)):
    """Kubernetes readiness probe."""
    try:
        status = await client.get_status()
        if status.state.value == "running":
            return {"status": "ready"}
        return {"status": "not_ready", "reason": status.state.value}
    except Exception as e:
        return {"status": "not_ready", "reason": str(e)}


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics(client: CoreDNSClient = Depends(get_client)):
    """Prometheus metrics endpoint."""
    metrics = await client.get_metrics()

    # Format as Prometheus text format
    lines = []
    for m in metrics.metrics:
        labels = ""
        if m.labels:
            label_pairs = ",".join(f'{k}="{v}"' for k, v in m.labels.items())
            labels = f"{{{label_pairs}}}"
        lines.append(f"{m.name}{labels} {m.value}")

    return "\n".join(lines)


@router.get("/upstream")
async def upstream_health(client: CoreDNSClient = Depends(get_client)):
    """Check upstream resolver health."""
    health = await client.health_check()
    return {
        "upstreams": [
            {
                "address": u.address,
                "port": u.port,
                "healthy": u.healthy,
                "latency_ms": u.latency_ms,
                "consecutive_failures": u.consecutive_failures,
            }
            for u in health.upstreams
        ]
    }
