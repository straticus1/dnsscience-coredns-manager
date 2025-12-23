"""Cache management API endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.models import CacheStats, CachePurgeResult, RecordType

router = APIRouter()


async def get_client() -> CoreDNSClient:
    from dnsscience.api.main import get_coredns_client
    return get_coredns_client()


class PurgeRequest(BaseModel):
    domain: str | None = None
    record_type: str | None = None


@router.get("/stats", response_model=CacheStats)
async def get_cache_stats(client: CoreDNSClient = Depends(get_client)):
    """Get cache statistics."""
    return await client.get_cache_stats()


@router.delete("", response_model=CachePurgeResult)
async def flush_cache(client: CoreDNSClient = Depends(get_client)):
    """Flush entire cache."""
    return await client.flush_cache()


@router.delete("/{domain}", response_model=CachePurgeResult)
async def purge_domain(
    domain: str,
    record_type: str | None = None,
    client: CoreDNSClient = Depends(get_client),
):
    """Purge specific domain from cache."""
    rt = RecordType(record_type) if record_type else None
    return await client.purge_cache(domain=domain, record_type=rt)


@router.get("/entries")
async def inspect_cache(
    domain: str | None = None,
    limit: int = 100,
    client: CoreDNSClient = Depends(get_client),
):
    """Inspect cache entries."""
    entries = await client.inspect_cache(domain=domain, limit=limit)
    return {"entries": [e.model_dump() for e in entries]}
