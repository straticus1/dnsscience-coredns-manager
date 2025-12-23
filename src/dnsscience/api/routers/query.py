"""DNS query API endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.models import DNSQuery, DNSResponse, BulkQueryResult, RecordType

router = APIRouter()


async def get_client() -> CoreDNSClient:
    from dnsscience.api.main import get_coredns_client
    return get_coredns_client()


class QueryRequest(BaseModel):
    name: str
    record_type: str = "A"
    server: str | None = None
    dnssec: bool = False


class BulkQueryRequest(BaseModel):
    queries: list[QueryRequest]


class TraceRequest(BaseModel):
    name: str
    record_type: str = "A"


class BenchmarkRequest(BaseModel):
    name: str
    count: int = 100
    concurrency: int = 10


@router.post("", response_model=DNSResponse)
async def query(
    request: QueryRequest,
    client: CoreDNSClient = Depends(get_client),
):
    """Perform a DNS query."""
    dns_query = DNSQuery(
        name=request.name,
        record_type=RecordType(request.record_type),
        server=request.server,
        dnssec=request.dnssec,
    )
    return await client.query(dns_query)


@router.post("/bulk", response_model=BulkQueryResult)
async def bulk_query(
    request: BulkQueryRequest,
    client: CoreDNSClient = Depends(get_client),
):
    """Perform bulk DNS queries."""
    queries = [
        DNSQuery(
            name=q.name,
            record_type=RecordType(q.record_type),
            server=q.server,
            dnssec=q.dnssec,
        )
        for q in request.queries
    ]
    return await client.query_bulk(queries)


@router.post("/trace")
async def trace_query(
    request: TraceRequest,
    client: CoreDNSClient = Depends(get_client),
):
    """Trace DNS resolution path."""
    query = DNSQuery(
        name=request.name,
        record_type=RecordType(request.record_type),
    )
    responses = await client.trace(query)
    return {"trace": [r.model_dump() for r in responses]}


@router.post("/bench")
async def benchmark(
    request: BenchmarkRequest,
    client: CoreDNSClient = Depends(get_client),
):
    """Benchmark DNS query performance."""
    import asyncio
    import time

    queries = [
        DNSQuery(name=request.name, record_type=RecordType.A)
        for _ in range(request.count)
    ]

    start = time.perf_counter()
    result = await client.query_bulk(queries)
    end = time.perf_counter()

    # Calculate stats
    times = [r.query_time_ms for r in result.responses]
    times.sort()

    return {
        "total_queries": request.count,
        "successful": result.successful,
        "failed": result.failed,
        "duration_seconds": end - start,
        "qps": request.count / (end - start),
        "latency": {
            "avg_ms": sum(times) / len(times) if times else 0,
            "min_ms": min(times) if times else 0,
            "max_ms": max(times) if times else 0,
            "p50_ms": times[len(times) // 2] if times else 0,
            "p95_ms": times[int(len(times) * 0.95)] if times else 0,
            "p99_ms": times[int(len(times) * 0.99)] if times else 0,
        },
    }
