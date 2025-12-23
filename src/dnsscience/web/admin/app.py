"""FastAPI + htmx admin panel application."""

from pathlib import Path

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.unbound.client import UnboundClient
from dnsscience.core.models import DNSQuery, RecordType

# Setup paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"

# Create app
app = FastAPI(
    title="DNS Science Admin",
    description="Lightweight admin panel for DNS management",
)

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Clients
_coredns: CoreDNSClient | None = None
_unbound: UnboundClient | None = None


async def get_coredns() -> CoreDNSClient:
    global _coredns
    if not _coredns:
        _coredns = CoreDNSClient()
        await _coredns.connect()
    return _coredns


async def get_unbound() -> UnboundClient:
    global _unbound
    if not _unbound:
        _unbound = UnboundClient()
        await _unbound.connect()
    return _unbound


# ============================================================================
# Pages
# ============================================================================


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Dashboard home page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/service", response_class=HTMLResponse)
async def service_page(request: Request):
    """Service management page."""
    return templates.TemplateResponse("service.html", {"request": request})


@app.get("/cache", response_class=HTMLResponse)
async def cache_page(request: Request):
    """Cache management page."""
    return templates.TemplateResponse("cache.html", {"request": request})


@app.get("/query", response_class=HTMLResponse)
async def query_page(request: Request):
    """DNS query page."""
    return templates.TemplateResponse("query.html", {"request": request})


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """Configuration page."""
    return templates.TemplateResponse("config.html", {"request": request})


@app.get("/compare", response_class=HTMLResponse)
async def compare_page(request: Request):
    """Compare page."""
    return templates.TemplateResponse("compare.html", {"request": request})


@app.get("/migrate", response_class=HTMLResponse)
async def migrate_page(request: Request):
    """Migration page."""
    return templates.TemplateResponse("migrate.html", {"request": request})


# ============================================================================
# htmx Partials - Service
# ============================================================================


@app.get("/htmx/service/status", response_class=HTMLResponse)
async def htmx_service_status(request: Request, resolver: str = "coredns"):
    """Get service status partial."""
    if resolver == "coredns":
        client = await get_coredns()
    else:
        client = await get_unbound()

    status = await client.get_status()
    return templates.TemplateResponse(
        "partials/service_status.html",
        {"request": request, "status": status, "resolver": resolver},
    )


@app.post("/htmx/service/control", response_class=HTMLResponse)
async def htmx_service_control(
    request: Request,
    action: str = Form(...),
    resolver: str = Form("coredns"),
):
    """Control service action."""
    if resolver == "coredns":
        client = await get_coredns()
    else:
        client = await get_unbound()

    if action == "start":
        result = await client.start()
    elif action == "stop":
        result = await client.stop()
    elif action == "restart":
        result = await client.restart()
    elif action == "reload":
        result = await client.reload()
    else:
        result = None

    status = await client.get_status()
    return templates.TemplateResponse(
        "partials/service_status.html",
        {
            "request": request,
            "status": status,
            "resolver": resolver,
            "result": result,
        },
    )


# ============================================================================
# htmx Partials - Cache
# ============================================================================


@app.get("/htmx/cache/stats", response_class=HTMLResponse)
async def htmx_cache_stats(request: Request, resolver: str = "coredns"):
    """Get cache stats partial."""
    if resolver == "coredns":
        client = await get_coredns()
    else:
        client = await get_unbound()

    stats = await client.get_cache_stats()
    return templates.TemplateResponse(
        "partials/cache_stats.html",
        {"request": request, "stats": stats, "resolver": resolver},
    )


@app.post("/htmx/cache/flush", response_class=HTMLResponse)
async def htmx_cache_flush(request: Request, resolver: str = Form("coredns")):
    """Flush cache."""
    if resolver == "coredns":
        client = await get_coredns()
    else:
        client = await get_unbound()

    result = await client.flush_cache()
    stats = await client.get_cache_stats()
    return templates.TemplateResponse(
        "partials/cache_stats.html",
        {
            "request": request,
            "stats": stats,
            "resolver": resolver,
            "message": f"Cache flushed: {result.purged_count} entries",
        },
    )


@app.post("/htmx/cache/purge", response_class=HTMLResponse)
async def htmx_cache_purge(
    request: Request,
    domain: str = Form(...),
    resolver: str = Form("coredns"),
):
    """Purge domain from cache."""
    if resolver == "coredns":
        client = await get_coredns()
    else:
        client = await get_unbound()

    result = await client.purge_cache(domain=domain)
    return templates.TemplateResponse(
        "partials/cache_purge_result.html",
        {"request": request, "result": result, "domain": domain},
    )


# ============================================================================
# htmx Partials - Query
# ============================================================================


@app.post("/htmx/query/lookup", response_class=HTMLResponse)
async def htmx_query_lookup(
    request: Request,
    domain: str = Form(...),
    record_type: str = Form("A"),
    resolver: str = Form("coredns"),
):
    """Perform DNS lookup."""
    if resolver == "coredns":
        client = await get_coredns()
    else:
        client = await get_unbound()

    query = DNSQuery(
        name=domain,
        record_type=RecordType(record_type),
    )
    response = await client.query(query)

    return templates.TemplateResponse(
        "partials/query_result.html",
        {"request": request, "response": response},
    )


# ============================================================================
# htmx Partials - Config
# ============================================================================


@app.get("/htmx/config/show", response_class=HTMLResponse)
async def htmx_config_show(request: Request, resolver: str = "coredns"):
    """Show current configuration."""
    if resolver == "coredns":
        client = await get_coredns()
    else:
        client = await get_unbound()

    try:
        config = await client.get_config()
    except FileNotFoundError:
        config = "# Configuration file not found"

    return templates.TemplateResponse(
        "partials/config_view.html",
        {"request": request, "config": config, "resolver": resolver},
    )


@app.post("/htmx/config/validate", response_class=HTMLResponse)
async def htmx_config_validate(
    request: Request,
    config: str = Form(...),
    resolver: str = Form("coredns"),
):
    """Validate configuration."""
    if resolver == "coredns":
        client = await get_coredns()
    else:
        client = await get_unbound()

    result = await client.validate_config(config)

    return templates.TemplateResponse(
        "partials/config_validation.html",
        {"request": request, "result": result},
    )


# ============================================================================
# htmx Partials - Health
# ============================================================================


@app.get("/htmx/health/check", response_class=HTMLResponse)
async def htmx_health_check(request: Request, resolver: str = "coredns"):
    """Health check partial."""
    if resolver == "coredns":
        client = await get_coredns()
    else:
        client = await get_unbound()

    health = await client.health_check()

    return templates.TemplateResponse(
        "partials/health_status.html",
        {"request": request, "health": health, "resolver": resolver},
    )


# ============================================================================
# Run
# ============================================================================


def run():
    """Run the admin panel."""
    import uvicorn

    uvicorn.run(
        "dnsscience.web.admin.app:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
    )


if __name__ == "__main__":
    run()
