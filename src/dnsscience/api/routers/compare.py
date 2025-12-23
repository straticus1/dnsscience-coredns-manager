"""Compare API endpoints."""

from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel

from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.compare.engine import CompareEngine
from dnsscience.core.compare.shadow import ShadowMode
from dnsscience.core.models import (
    CompareResult,
    DNSQuery,
    RecordType,
    ResponseDiff,
    ShadowModeConfig,
    ShadowModeReport,
    ResolverType,
)

router = APIRouter()

# Shadow mode state
_shadow_mode: ShadowMode | None = None


async def get_client() -> CoreDNSClient:
    from dnsscience.api.main import get_coredns_client
    return get_coredns_client()


class CompareRequest(BaseModel):
    domain: str
    record_type: str = "A"


class BulkCompareRequest(BaseModel):
    domains: list[str]
    record_type: str = "A"


class ShadowStartRequest(BaseModel):
    sample_rate: float = 1.0
    duration_seconds: int | None = None
    alert_on_mismatch: bool = True
    alert_threshold: float = 0.01


@router.post("", response_model=ResponseDiff)
async def compare_single(
    request: CompareRequest,
    source_client: CoreDNSClient = Depends(get_client),
):
    """Compare a single query between resolvers."""
    # Create target client (different port for demo)
    target_client = CoreDNSClient(port=5353)
    await target_client.connect()

    try:
        engine = CompareEngine(source_client, target_client)
        query = DNSQuery(
            name=request.domain,
            record_type=RecordType(request.record_type),
        )
        return await engine.compare_single(query)
    finally:
        await target_client.disconnect()


@router.post("/bulk", response_model=CompareResult)
async def compare_bulk(
    request: BulkCompareRequest,
    source_client: CoreDNSClient = Depends(get_client),
):
    """Compare multiple queries between resolvers."""
    target_client = CoreDNSClient(port=5353)
    await target_client.connect()

    try:
        engine = CompareEngine(source_client, target_client)
        queries = [
            DNSQuery(name=d, record_type=RecordType(request.record_type))
            for d in request.domains
        ]
        return await engine.compare_bulk(queries)
    finally:
        await target_client.disconnect()


@router.post("/shadow/start")
async def start_shadow_mode(
    request: ShadowStartRequest,
    background_tasks: BackgroundTasks,
    source_client: CoreDNSClient = Depends(get_client),
):
    """Start shadow mode comparison."""
    global _shadow_mode

    if _shadow_mode and _shadow_mode.is_running:
        return {"error": "Shadow mode already running"}

    target_client = CoreDNSClient(port=5353)
    await target_client.connect()

    config = ShadowModeConfig(
        source=ResolverType.COREDNS,
        target=ResolverType.UNBOUND,
        sample_rate=request.sample_rate,
        duration_seconds=request.duration_seconds,
        alert_on_mismatch=request.alert_on_mismatch,
        alert_threshold=request.alert_threshold,
    )

    _shadow_mode = ShadowMode(source_client, target_client, config)
    await _shadow_mode.start()

    return {"status": "started", "config": config.model_dump()}


@router.post("/shadow/stop", response_model=ShadowModeReport)
async def stop_shadow_mode():
    """Stop shadow mode and get report."""
    global _shadow_mode

    if not _shadow_mode:
        return {"error": "Shadow mode not running"}

    report = await _shadow_mode.stop()
    _shadow_mode = None
    return report


@router.get("/shadow/report")
async def get_shadow_report():
    """Get current shadow mode report."""
    global _shadow_mode

    if not _shadow_mode:
        return {"error": "Shadow mode not running"}

    return _shadow_mode.report.model_dump() if _shadow_mode.report else {}
