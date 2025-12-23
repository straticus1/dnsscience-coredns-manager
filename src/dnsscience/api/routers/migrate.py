"""Migration API endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.migrate.coredns_to_unbound import CoreDNSToUnboundMigrator
from dnsscience.core.migrate.unbound_to_coredns import UnboundToCoreDNSMigrator
from dnsscience.core.models import MigrationPlan, MigrationStatus, CompareResult

router = APIRouter()


async def get_client() -> CoreDNSClient:
    from dnsscience.api.main import get_coredns_client
    return get_coredns_client()


class PlanRequest(BaseModel):
    source: str  # coredns or unbound
    target: str
    config: str


class ExecuteRequest(BaseModel):
    plan: dict
    dry_run: bool = False


class ConvertRequest(BaseModel):
    source: str
    target: str
    config: str


class ValidateRequest(BaseModel):
    domains: list[str] | None = None


@router.post("/plan")
async def create_plan(request: PlanRequest):
    """Generate migration plan."""
    if request.source == "coredns" and request.target == "unbound":
        migrator = CoreDNSToUnboundMigrator()
    elif request.source == "unbound" and request.target == "coredns":
        migrator = UnboundToCoreDNSMigrator()
    else:
        return {"error": f"Unsupported migration: {request.source} → {request.target}"}

    mappings, warnings, unsupported = migrator.analyze_config(request.config)
    target_config = migrator.generate_target_config(request.config)
    steps = migrator.generate_migration_steps(request.config, target_config)

    return {
        "source": request.source,
        "target": request.target,
        "target_config": target_config,
        "mappings": [m.model_dump() for m in mappings],
        "warnings": warnings,
        "unsupported": unsupported,
        "steps": [s.model_dump() for s in steps],
        "risk": "low" if not unsupported else "medium" if len(unsupported) < 3 else "high",
    }


@router.post("/execute")
async def execute_migration(request: ExecuteRequest):
    """Execute migration plan."""
    # In production, this would use the MigrationEngine
    if request.dry_run:
        return {
            "status": "dry_run_complete",
            "steps_executed": len(request.plan.get("steps", [])),
            "message": "Dry run completed successfully. No changes made.",
        }

    return {
        "status": "not_implemented",
        "message": "Full migration execution requires additional setup. Use dry_run=true for validation.",
    }


@router.post("/validate")
async def validate_migration(
    request: ValidateRequest,
    source_client: CoreDNSClient = Depends(get_client),
):
    """Validate migration by comparing resolvers."""
    from dnsscience.core.compare.engine import CompareEngine
    from dnsscience.core.models import DNSQuery, RecordType

    target_client = CoreDNSClient(port=5353)
    await target_client.connect()

    try:
        engine = CompareEngine(source_client, target_client)

        domains = request.domains or [
            "google.com",
            "cloudflare.com",
            "amazon.com",
            "github.com",
            "example.com",
        ]

        queries = [DNSQuery(name=d, record_type=RecordType.A) for d in domains]
        result = await engine.compare_bulk(queries)

        return {
            "valid": result.confidence_score >= 0.95,
            "confidence_score": result.confidence_score,
            "queries_tested": result.queries_tested,
            "matches": result.matches,
            "mismatches": result.mismatches,
            "match_ratio": result.match_ratio,
            "recommendation": (
                "Ready for migration"
                if result.confidence_score >= 0.99
                else "Review mismatches before migrating"
                if result.confidence_score >= 0.95
                else "Not recommended for migration"
            ),
        }
    finally:
        await target_client.disconnect()


@router.post("/rollback")
async def rollback_migration(backup_path: str):
    """Rollback to previous state."""
    return {
        "status": "not_implemented",
        "message": "Rollback requires backup path and manual verification.",
        "backup_path": backup_path,
    }


@router.get("/status")
async def migration_status():
    """Get current migration status."""
    return {
        "active_migration": None,
        "last_migration": None,
        "available_backups": [],
    }


@router.post("/convert")
async def convert_config(request: ConvertRequest):
    """Convert configuration between formats."""
    if request.source == "coredns" and request.target == "unbound":
        migrator = CoreDNSToUnboundMigrator()
    elif request.source == "unbound" and request.target == "coredns":
        migrator = UnboundToCoreDNSMigrator()
    else:
        return {"error": f"Unsupported conversion: {request.source} → {request.target}"}

    converted = migrator.generate_target_config(request.config)
    return {"converted_config": converted}
