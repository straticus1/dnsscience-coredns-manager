"""Configuration management API endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.coredns.config import CorefileParser
from dnsscience.core.models import ConfigValidationResult, ConfigDiff, ServiceControlResult

router = APIRouter()


async def get_client() -> CoreDNSClient:
    from dnsscience.api.main import get_coredns_client
    return get_coredns_client()


class ValidateRequest(BaseModel):
    config: str
    resolver: str = "coredns"


class ApplyRequest(BaseModel):
    config: str
    reload: bool = True


@router.get("")
async def get_config(client: CoreDNSClient = Depends(get_client)):
    """Get current configuration."""
    config = await client.get_config()
    return {"config": config}


@router.post("/validate", response_model=ConfigValidationResult)
async def validate_config(request: ValidateRequest):
    """Validate configuration syntax."""
    if request.resolver == "coredns":
        parser = CorefileParser()
        return parser.validate(request.config)
    else:
        from dnsscience.core.migrate.parsers.unbound_conf import UnboundConfigParser
        parser = UnboundConfigParser()
        return parser.validate(request.config)


@router.get("/diff", response_model=ConfigDiff)
async def diff_config(
    new_config: str,
    client: CoreDNSClient = Depends(get_client),
):
    """Diff new config against running config."""
    return await client.diff_config(new_config)


@router.post("/reload", response_model=ServiceControlResult)
async def reload_config(client: CoreDNSClient = Depends(get_client)):
    """Trigger configuration reload."""
    return await client.reload()


@router.post("/apply", response_model=ServiceControlResult)
async def apply_config(
    request: ApplyRequest,
    client: CoreDNSClient = Depends(get_client),
):
    """Apply new configuration."""
    return await client.apply_config(request.config, reload=request.reload)
