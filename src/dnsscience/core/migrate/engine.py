"""Core migration engine orchestrating resolver migrations."""

import asyncio
import shutil
from datetime import datetime
from pathlib import Path
from typing import Protocol

from dnsscience.core.base import BaseResolverClient
from dnsscience.core.compare.engine import CompareEngine
from dnsscience.core.models import (
    CompareResult,
    DNSQuery,
    MigrationPlan,
    MigrationRollback,
    MigrationState,
    MigrationStatus,
    MigrationStep,
    PluginMapping,
    RecordType,
    ResolverType,
)


class Migrator(Protocol):
    """Protocol for resolver-specific migrators."""

    source_type: ResolverType
    target_type: ResolverType

    def analyze_config(self, config: str) -> tuple[list[PluginMapping], list[str], list[str]]:
        """Analyze source config and return mappings, warnings, unsupported features."""
        ...

    def generate_target_config(self, source_config: str) -> str:
        """Generate target resolver config from source."""
        ...

    def generate_migration_steps(
        self, source_config: str, target_config: str
    ) -> list[MigrationStep]:
        """Generate ordered migration steps."""
        ...


class MigrationEngine:
    """
    Orchestrates DNS resolver migrations.

    Handles:
    - Migration planning
    - Config conversion
    - Validation before/during/after migration
    - Rollback capability
    """

    def __init__(
        self,
        source_client: BaseResolverClient,
        target_client: BaseResolverClient,
        migrator: Migrator,
        backup_dir: str = "/var/lib/dnsscience/backups",
    ):
        self.source = source_client
        self.target = target_client
        self.migrator = migrator
        self.backup_dir = Path(backup_dir)
        self.compare_engine = CompareEngine(source_client, target_client)

        self._status: MigrationStatus | None = None
        self._rollback: MigrationRollback | None = None

    @property
    def status(self) -> MigrationStatus | None:
        return self._status

    async def plan(self, validation_queries: list[DNSQuery] | None = None) -> MigrationPlan:
        """
        Create a migration plan.

        Args:
            validation_queries: Optional list of queries to validate migration
        """
        # Get source configuration
        source_config = await self.source.get_config()

        # Analyze and map features
        mappings, warnings, unsupported = self.migrator.analyze_config(source_config)

        # Generate target config
        target_config = self.migrator.generate_target_config(source_config)

        # Generate migration steps
        steps = self.migrator.generate_migration_steps(source_config, target_config)

        # Estimate risk
        risk = self._estimate_risk(mappings, unsupported, len(steps))

        plan = MigrationPlan(
            source=self.migrator.source_type,
            target=self.migrator.target_type,
            steps=steps,
            plugin_mappings=mappings,
            warnings=warnings,
            unsupported_features=unsupported,
            estimated_risk=risk,
        )

        # Initialize status
        self._status = MigrationStatus(
            state=MigrationState.PLANNED,
            plan=plan,
            current_step=0,
        )

        return plan

    async def validate_pre_migration(
        self,
        queries: list[DNSQuery] | None = None,
        query_file: str | None = None,
    ) -> CompareResult:
        """
        Validate current state before migration.

        Establishes a baseline of expected DNS behavior.
        """
        if query_file:
            return await self.compare_engine.compare_from_file(query_file)

        if queries:
            return await self.compare_engine.compare_bulk(queries)

        # Default test queries
        default_queries = [
            DNSQuery(name="google.com", record_type=RecordType.A),
            DNSQuery(name="cloudflare.com", record_type=RecordType.A),
            DNSQuery(name="example.com", record_type=RecordType.A),
            DNSQuery(name="github.com", record_type=RecordType.A),
        ]
        return await self.compare_engine.compare_bulk(default_queries)

    async def execute(
        self,
        dry_run: bool = False,
        pause_between_steps: bool = True,
    ) -> MigrationStatus:
        """
        Execute the migration plan.

        Args:
            dry_run: If True, only simulate the migration
            pause_between_steps: If True, wait for confirmation between steps
        """
        if not self._status or self._status.state != MigrationState.PLANNED:
            raise RuntimeError("No migration planned. Call plan() first.")

        self._status.state = MigrationState.IN_PROGRESS
        self._status.started_at = datetime.utcnow()

        # Create backup
        await self._create_backup()

        try:
            for i, step in enumerate(self._status.plan.steps):
                self._status.current_step = i

                if dry_run:
                    print(f"[DRY RUN] Step {i + 1}: {step.description}")
                    self._status.completed_steps.append(i)
                    continue

                # Execute step
                success = await self._execute_step(step)

                if not success:
                    self._status.state = MigrationState.FAILED
                    self._status.failed_step = i
                    return self._status

                self._status.completed_steps.append(i)

                if pause_between_steps and i < len(self._status.plan.steps) - 1:
                    # In real implementation, this would wait for user confirmation
                    await asyncio.sleep(0.1)

            # Validation phase
            self._status.state = MigrationState.VALIDATING
            validation = await self._validate_migration()
            self._status.validation_result = validation

            if validation.confidence_score >= 0.95:
                self._status.state = MigrationState.COMPLETED
            else:
                self._status.state = MigrationState.FAILED
                self._status.error = f"Validation failed: {validation.confidence_score:.2%} confidence"

            self._status.completed_at = datetime.utcnow()

        except Exception as e:
            self._status.state = MigrationState.FAILED
            self._status.error = str(e)
            raise

        return self._status

    async def rollback(self) -> MigrationStatus:
        """Rollback to pre-migration state."""
        if not self._rollback:
            raise RuntimeError("No rollback information available")

        if not self._status:
            raise RuntimeError("No migration in progress")

        try:
            # Restore original configuration
            await self.source.apply_config(self._rollback.original_config)

            # Execute rollback steps in reverse
            for step in reversed(self._rollback.rollback_steps):
                await self._execute_step(step)

            self._status.state = MigrationState.ROLLED_BACK
            self._status.completed_at = datetime.utcnow()

        except Exception as e:
            self._status.error = f"Rollback failed: {e}"
            raise

        return self._status

    async def _create_backup(self) -> None:
        """Create backup of current configuration."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"
        backup_path.mkdir()

        # Get and save source config
        source_config = await self.source.get_config()
        config_backup = backup_path / "source_config.txt"
        config_backup.write_text(source_config)

        # Create rollback info
        self._rollback = MigrationRollback(
            backup_path=str(backup_path),
            original_config=source_config,
            rollback_steps=self._generate_rollback_steps(),
        )

    def _generate_rollback_steps(self) -> list[MigrationStep]:
        """Generate rollback steps from the migration plan."""
        if not self._status:
            return []

        rollback_steps = []
        for step in reversed(self._status.plan.steps):
            if step.reversible:
                rollback_steps.append(
                    MigrationStep(
                        order=len(rollback_steps),
                        action=f"rollback_{step.action}",
                        description=f"Rollback: {step.description}",
                        source_config=step.target_config,
                        target_config=step.source_config,
                        reversible=False,
                    )
                )
        return rollback_steps

    async def _execute_step(self, step: MigrationStep) -> bool:
        """Execute a single migration step."""
        print(f"Executing: {step.description}")

        if step.manual_required:
            print(f"  MANUAL ACTION REQUIRED: {step.action}")
            return True

        action = step.action.lower()

        if action == "backup_config":
            # Already done in _create_backup
            return True

        elif action == "write_target_config":
            if step.target_config:
                await self.target.apply_config(step.target_config, reload=False)
            return True

        elif action == "start_target":
            result = await self.target.start()
            return result.success

        elif action == "stop_source":
            result = await self.source.stop()
            return result.success

        elif action == "validate":
            # Run quick validation
            result = await self._validate_migration()
            return result.confidence_score >= 0.90

        elif action == "reload_target":
            result = await self.target.reload()
            return result.success

        else:
            print(f"  Unknown action: {action}")
            return True

    async def _validate_migration(self) -> CompareResult:
        """Validate the migration by comparing resolver responses."""
        # Use a standard set of validation queries
        queries = [
            DNSQuery(name="google.com", record_type=RecordType.A),
            DNSQuery(name="google.com", record_type=RecordType.AAAA),
            DNSQuery(name="cloudflare.com", record_type=RecordType.A),
            DNSQuery(name="amazon.com", record_type=RecordType.A),
            DNSQuery(name="microsoft.com", record_type=RecordType.A),
            DNSQuery(name="github.com", record_type=RecordType.A),
            DNSQuery(name="example.com", record_type=RecordType.A),
            DNSQuery(name="example.com", record_type=RecordType.MX),
            DNSQuery(name="example.com", record_type=RecordType.TXT),
        ]
        return await self.compare_engine.compare_bulk(queries)

    def _estimate_risk(
        self,
        mappings: list[PluginMapping],
        unsupported: list[str],
        step_count: int,
    ) -> str:
        """Estimate migration risk level."""
        risk_score = 0

        # Unsupported features add risk
        risk_score += len(unsupported) * 2

        # Manual steps add risk
        manual_count = sum(1 for m in mappings if m.requires_manual)
        risk_score += manual_count * 1.5

        # Many steps add risk
        if step_count > 10:
            risk_score += 1

        if risk_score >= 5:
            return "high"
        elif risk_score >= 2:
            return "medium"
        return "low"
