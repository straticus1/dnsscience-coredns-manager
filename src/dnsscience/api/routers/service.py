"""Service control API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.models import ServiceStatus, ServiceControlResult

router = APIRouter()


# Dependency - would be injected from main
async def get_client() -> CoreDNSClient:
    from dnsscience.api.main import get_coredns_client
    return get_coredns_client()


class ControlRequest(BaseModel):
    action: str  # start, stop, restart


@router.get("/status", response_model=ServiceStatus)
async def get_status(client: CoreDNSClient = Depends(get_client)):
    """Get current service status."""
    return await client.get_status()


@router.post("/start", response_model=ServiceControlResult)
async def start_service(client: CoreDNSClient = Depends(get_client)):
    """Start the DNS resolver service."""
    return await client.start()


@router.post("/stop", response_model=ServiceControlResult)
async def stop_service(client: CoreDNSClient = Depends(get_client)):
    """Stop the DNS resolver service."""
    return await client.stop()


@router.post("/restart", response_model=ServiceControlResult)
async def restart_service(client: CoreDNSClient = Depends(get_client)):
    """Restart the DNS resolver service."""
    return await client.restart()


@router.post("/reload", response_model=ServiceControlResult)
async def reload_config(client: CoreDNSClient = Depends(get_client)):
    """Reload configuration without restart."""
    return await client.reload()
