"""FastAPI application for DNS Science Toolkit."""

from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from dnsscience import __version__
from dnsscience.api.routers import service, cache, query, config, compare, migrate, health
from dnsscience.core.coredns.client import CoreDNSClient


# Shared state
class AppState:
    coredns_client: CoreDNSClient | None = None


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    state.coredns_client = CoreDNSClient()
    await state.coredns_client.connect()

    yield

    # Shutdown
    if state.coredns_client:
        await state.coredns_client.disconnect()


# Create FastAPI app
app = FastAPI(
    title="DNS Science Toolkit API",
    description="Enterprise DNS management API for CoreDNS and Unbound",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(service.router, prefix="/api/v1/service", tags=["Service"])
app.include_router(cache.router, prefix="/api/v1/cache", tags=["Cache"])
app.include_router(query.router, prefix="/api/v1/query", tags=["Query"])
app.include_router(config.router, prefix="/api/v1/config", tags=["Configuration"])
app.include_router(compare.router, prefix="/api/v1/compare", tags=["Compare"])
app.include_router(migrate.router, prefix="/api/v1/migrate", tags=["Migration"])
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "DNS Science Toolkit API",
        "version": __version__,
        "docs": "/docs",
    }


@app.get("/api/v1")
async def api_info():
    """API version info."""
    return {
        "version": "v1",
        "endpoints": [
            "/api/v1/service",
            "/api/v1/cache",
            "/api/v1/query",
            "/api/v1/config",
            "/api/v1/compare",
            "/api/v1/migrate",
            "/api/v1/health",
        ],
    }


def get_coredns_client() -> CoreDNSClient:
    """Dependency to get CoreDNS client."""
    if not state.coredns_client:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return state.coredns_client


def run():
    """Run the API server."""
    uvicorn.run(
        "dnsscience.api.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
    )


if __name__ == "__main__":
    run()
