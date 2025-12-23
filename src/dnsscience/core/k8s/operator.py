"""Kubernetes Operator for DNS Science Toolkit."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from dnsscience.core.k8s.client import K8sClient
from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.coredns.config import CorefileParser
from dnsscience.core.compare.engine import CompareEngine
from dnsscience.core.models import DNSQuery, RecordType

logger = logging.getLogger(__name__)


class DNSOperator:
    """
    Kubernetes Operator for DNS management.

    Features:
    - Watch for ConfigMap changes
    - Auto-validate configurations
    - Health monitoring
    - Migration orchestration
    """

    def __init__(
        self,
        k8s_client: K8sClient | None = None,
        coredns_client: CoreDNSClient | None = None,
    ):
        self.k8s = k8s_client or K8sClient()
        self.coredns = coredns_client or CoreDNSClient()
        self._running = False
        self._watch_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the operator."""
        logger.info("Starting DNS Operator")
        self._running = True

        await self.coredns.connect()

        # Start background tasks
        self._watch_task = asyncio.create_task(self._watch_loop())

    async def stop(self) -> None:
        """Stop the operator."""
        logger.info("Stopping DNS Operator")
        self._running = False

        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass

        await self.coredns.disconnect()

    async def _watch_loop(self) -> None:
        """Main watch loop for monitoring DNS health."""
        while self._running:
            try:
                await self._check_health()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Watch loop error: {e}")
                await asyncio.sleep(10)

    async def _check_health(self) -> None:
        """Check DNS resolver health."""
        try:
            health = await self.coredns.health_check()
            logger.debug(f"Health check: {health.state.value}")

            if health.state.value != "healthy":
                logger.warning(f"DNS health degraded: {health.state.value}")
                # Could trigger alerts here

        except Exception as e:
            logger.error(f"Health check failed: {e}")

    # ========================================================================
    # Configuration Management
    # ========================================================================

    async def validate_configmap(self, name: str = "coredns") -> dict[str, Any]:
        """Validate a DNS ConfigMap."""
        try:
            cm = await self.k8s.get_configmap(name, "kube-system")

            corefile = cm.data.get("Corefile", "")
            if not corefile:
                return {
                    "valid": False,
                    "error": "No Corefile found in ConfigMap",
                }

            parser = CorefileParser()
            result = parser.validate(corefile)

            return {
                "valid": result.valid,
                "errors": [e.message for e in result.errors],
                "warnings": [w.message for w in result.warnings],
            }

        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
            }

    async def apply_configmap(
        self,
        corefile: str,
        validate: bool = True,
        restart: bool = True,
    ) -> dict[str, Any]:
        """Apply a new Corefile to the ConfigMap."""
        # Validate first
        if validate:
            parser = CorefileParser()
            validation = parser.validate(corefile)

            if not validation.valid:
                return {
                    "success": False,
                    "error": "Validation failed",
                    "errors": [e.message for e in validation.errors],
                }

        try:
            # Update ConfigMap
            await self.k8s.update_coredns_configmap(corefile)

            # Restart CoreDNS if requested
            if restart:
                await self.k8s.restart_coredns()

            return {
                "success": True,
                "message": "ConfigMap updated" + (" and CoreDNS restarted" if restart else ""),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    # ========================================================================
    # Migration Support
    # ========================================================================

    async def prepare_migration(
        self,
        target_config: str,
        test_domains: list[str] | None = None,
    ) -> dict[str, Any]:
        """Prepare for migration by validating new config."""
        # Validate new config
        parser = CorefileParser()
        validation = parser.validate(target_config)

        if not validation.valid:
            return {
                "ready": False,
                "error": "New configuration is invalid",
                "errors": [e.message for e in validation.errors],
            }

        # Get current config for backup
        try:
            cm = await self.k8s.get_coredns_configmap()
            current_config = cm.data.get("Corefile", "")
        except Exception as e:
            return {
                "ready": False,
                "error": f"Failed to get current config: {e}",
            }

        return {
            "ready": True,
            "current_config": current_config,
            "new_config": target_config,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def execute_migration(
        self,
        new_config: str,
        backup_current: bool = True,
    ) -> dict[str, Any]:
        """Execute the migration."""
        try:
            # Get current config for backup
            if backup_current:
                cm = await self.k8s.get_coredns_configmap()
                backup = cm.data.get("Corefile", "")
            else:
                backup = None

            # Apply new config
            result = await self.apply_configmap(new_config, validate=True, restart=True)

            if not result.get("success"):
                return result

            return {
                "success": True,
                "backup": backup,
                "message": "Migration completed successfully",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def validate_migration(
        self,
        test_domains: list[str] | None = None,
    ) -> dict[str, Any]:
        """Validate the migration by testing DNS resolution."""
        domains = test_domains or [
            "kubernetes.default.svc.cluster.local",
            "google.com",
            "cloudflare.com",
        ]

        results = []
        for domain in domains:
            try:
                query = DNSQuery(name=domain, record_type=RecordType.A)
                response = await self.coredns.query(query)

                results.append({
                    "domain": domain,
                    "success": response.rcode == "NOERROR",
                    "rcode": response.rcode,
                    "time_ms": response.query_time_ms,
                })
            except Exception as e:
                results.append({
                    "domain": domain,
                    "success": False,
                    "error": str(e),
                })

        successful = sum(1 for r in results if r.get("success"))

        return {
            "valid": successful == len(results),
            "total": len(results),
            "successful": successful,
            "failed": len(results) - successful,
            "results": results,
        }

    async def rollback_migration(self, backup_config: str) -> dict[str, Any]:
        """Rollback to the previous configuration."""
        return await self.apply_configmap(backup_config, validate=True, restart=True)


# ============================================================================
# Custom Resource Definitions (for future k8s operator)
# ============================================================================

DNS_MIGRATION_CRD = """
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: dnsmigrations.dnsscience.io
spec:
  group: dnsscience.io
  versions:
    - name: v1alpha1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                source:
                  type: string
                  enum: [coredns, unbound]
                target:
                  type: string
                  enum: [coredns, unbound]
                config:
                  type: string
                validateBefore:
                  type: boolean
                  default: true
                testDomains:
                  type: array
                  items:
                    type: string
            status:
              type: object
              properties:
                phase:
                  type: string
                  enum: [Pending, Validating, Migrating, Completed, Failed, RolledBack]
                message:
                  type: string
                lastUpdated:
                  type: string
  scope: Namespaced
  names:
    plural: dnsmigrations
    singular: dnsmigration
    kind: DNSMigration
    shortNames:
      - dnsm
"""

DNS_CONFIG_CRD = """
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: dnsconfigs.dnsscience.io
spec:
  group: dnsscience.io
  versions:
    - name: v1alpha1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                resolver:
                  type: string
                  enum: [coredns, unbound]
                config:
                  type: string
                validateOnApply:
                  type: boolean
                  default: true
            status:
              type: object
              properties:
                valid:
                  type: boolean
                lastApplied:
                  type: string
                errors:
                  type: array
                  items:
                    type: string
  scope: Namespaced
  names:
    plural: dnsconfigs
    singular: dnsconfig
    kind: DNSConfig
    shortNames:
      - dnsc
"""
