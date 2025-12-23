"""Kubernetes client for DNS operations."""

import asyncio
from typing import Any

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from dnsscience.core.models import (
    DNSQuery,
    DNSResponse,
    K8sConfigMap,
    K8sNamespace,
    K8sPodDNSTest,
    K8sServiceDiscovery,
    RecordType,
)


class K8sClient:
    """
    Kubernetes client for DNS-related operations.

    Handles:
    - ConfigMap management for CoreDNS/Unbound
    - Pod DNS resolution testing
    - Service discovery
    """

    def __init__(
        self,
        kubeconfig: str | None = None,
        context: str | None = None,
        namespace: str = "kube-system",
    ):
        self.namespace = namespace
        self._core_v1: client.CoreV1Api | None = None
        self._apps_v1: client.AppsV1Api | None = None

        # Load kubeconfig
        try:
            if kubeconfig:
                config.load_kube_config(config_file=kubeconfig, context=context)
            else:
                try:
                    config.load_incluster_config()
                except config.ConfigException:
                    config.load_kube_config(context=context)
        except Exception:
            pass  # Will fail gracefully when methods are called

    @property
    def core_v1(self) -> client.CoreV1Api:
        if not self._core_v1:
            self._core_v1 = client.CoreV1Api()
        return self._core_v1

    @property
    def apps_v1(self) -> client.AppsV1Api:
        if not self._apps_v1:
            self._apps_v1 = client.AppsV1Api()
        return self._apps_v1

    # ========================================================================
    # Namespace Operations
    # ========================================================================

    async def list_namespaces(self) -> list[K8sNamespace]:
        """List all namespaces."""
        try:
            result = await asyncio.to_thread(self.core_v1.list_namespace)
            return [
                K8sNamespace(
                    name=ns.metadata.name,
                    labels=ns.metadata.labels or {},
                )
                for ns in result.items
            ]
        except ApiException as e:
            raise RuntimeError(f"Failed to list namespaces: {e}")

    # ========================================================================
    # ConfigMap Operations
    # ========================================================================

    async def get_configmap(
        self,
        name: str,
        namespace: str | None = None,
    ) -> K8sConfigMap:
        """Get a ConfigMap by name."""
        ns = namespace or self.namespace

        try:
            cm = await asyncio.to_thread(
                self.core_v1.read_namespaced_config_map,
                name=name,
                namespace=ns,
            )

            return K8sConfigMap(
                name=cm.metadata.name,
                namespace=ns,
                data=cm.data or {},
                labels=cm.metadata.labels or {},
                annotations=cm.metadata.annotations or {},
            )
        except ApiException as e:
            raise RuntimeError(f"Failed to get ConfigMap {name}: {e}")

    async def update_configmap(
        self,
        name: str,
        data: dict[str, str],
        namespace: str | None = None,
    ) -> K8sConfigMap:
        """Update a ConfigMap."""
        ns = namespace or self.namespace

        try:
            # Get existing configmap
            cm = await asyncio.to_thread(
                self.core_v1.read_namespaced_config_map,
                name=name,
                namespace=ns,
            )

            # Update data
            cm.data = data

            # Apply update
            updated = await asyncio.to_thread(
                self.core_v1.replace_namespaced_config_map,
                name=name,
                namespace=ns,
                body=cm,
            )

            return K8sConfigMap(
                name=updated.metadata.name,
                namespace=ns,
                data=updated.data or {},
                labels=updated.metadata.labels or {},
                annotations=updated.metadata.annotations or {},
            )
        except ApiException as e:
            raise RuntimeError(f"Failed to update ConfigMap {name}: {e}")

    async def get_coredns_configmap(self) -> K8sConfigMap:
        """Get the CoreDNS ConfigMap."""
        return await self.get_configmap("coredns", "kube-system")

    async def update_coredns_configmap(self, corefile: str) -> K8sConfigMap:
        """Update the CoreDNS Corefile."""
        return await self.update_configmap(
            "coredns",
            {"Corefile": corefile},
            "kube-system",
        )

    # ========================================================================
    # Pod DNS Testing
    # ========================================================================

    async def test_pod_dns(
        self,
        pod_name: str,
        domain: str,
        namespace: str | None = None,
        record_type: RecordType = RecordType.A,
    ) -> K8sPodDNSTest:
        """Test DNS resolution from a specific pod."""
        ns = namespace or "default"

        try:
            # Execute nslookup in the pod
            command = ["nslookup", "-type=" + record_type.value, domain]

            resp = await asyncio.to_thread(
                lambda: client.CoreV1Api().connect_get_namespaced_pod_exec(
                    name=pod_name,
                    namespace=ns,
                    command=command,
                    stderr=True,
                    stdin=False,
                    stdout=True,
                    tty=False,
                )
            )

            # Parse response
            query = DNSQuery(name=domain, record_type=record_type)

            # Very basic parsing - in production would parse nslookup output
            success = "Address" in resp or "address" in resp

            return K8sPodDNSTest(
                pod_name=pod_name,
                namespace=ns,
                query=query,
                response=DNSResponse(
                    query=query,
                    records=[],
                    rcode="NOERROR" if success else "NXDOMAIN",
                    query_time_ms=0,
                    server="cluster-dns",
                ) if success else None,
                error=None if success else "DNS resolution failed",
                success=success,
            )

        except ApiException as e:
            query = DNSQuery(name=domain, record_type=record_type)
            return K8sPodDNSTest(
                pod_name=pod_name,
                namespace=ns,
                query=query,
                response=None,
                error=str(e),
                success=False,
            )

    # ========================================================================
    # Service Discovery
    # ========================================================================

    async def discover_services(
        self,
        namespace: str | None = None,
    ) -> list[K8sServiceDiscovery]:
        """Discover services and their DNS names."""
        ns = namespace or "default"

        try:
            if ns == "all":
                services = await asyncio.to_thread(
                    self.core_v1.list_service_for_all_namespaces
                )
            else:
                services = await asyncio.to_thread(
                    self.core_v1.list_namespaced_service,
                    namespace=ns,
                )

            result = []
            for svc in services.items:
                dns_name = f"{svc.metadata.name}.{svc.metadata.namespace}.svc.cluster.local"

                result.append(K8sServiceDiscovery(
                    name=svc.metadata.name,
                    namespace=svc.metadata.namespace,
                    cluster_ip=svc.spec.cluster_ip if svc.spec.cluster_ip != "None" else None,
                    external_ips=svc.spec.external_i_ps or [],
                    ports=[
                        {
                            "name": p.name,
                            "port": p.port,
                            "protocol": p.protocol,
                            "targetPort": p.target_port,
                        }
                        for p in (svc.spec.ports or [])
                    ],
                    dns_name=dns_name,
                ))

            return result

        except ApiException as e:
            raise RuntimeError(f"Failed to discover services: {e}")

    # ========================================================================
    # CoreDNS Deployment
    # ========================================================================

    async def get_coredns_deployment(self) -> dict[str, Any]:
        """Get CoreDNS deployment status."""
        try:
            deployment = await asyncio.to_thread(
                self.apps_v1.read_namespaced_deployment,
                name="coredns",
                namespace="kube-system",
            )

            return {
                "name": deployment.metadata.name,
                "namespace": deployment.metadata.namespace,
                "replicas": deployment.spec.replicas,
                "ready_replicas": deployment.status.ready_replicas or 0,
                "available_replicas": deployment.status.available_replicas or 0,
                "image": deployment.spec.template.spec.containers[0].image
                if deployment.spec.template.spec.containers
                else None,
            }

        except ApiException as e:
            raise RuntimeError(f"Failed to get CoreDNS deployment: {e}")

    async def scale_coredns(self, replicas: int) -> dict[str, Any]:
        """Scale CoreDNS deployment."""
        try:
            # Get current deployment
            deployment = await asyncio.to_thread(
                self.apps_v1.read_namespaced_deployment,
                name="coredns",
                namespace="kube-system",
            )

            # Update replicas
            deployment.spec.replicas = replicas

            # Apply
            updated = await asyncio.to_thread(
                self.apps_v1.replace_namespaced_deployment,
                name="coredns",
                namespace="kube-system",
                body=deployment,
            )

            return {
                "name": updated.metadata.name,
                "replicas": updated.spec.replicas,
            }

        except ApiException as e:
            raise RuntimeError(f"Failed to scale CoreDNS: {e}")

    async def restart_coredns(self) -> bool:
        """Restart CoreDNS by triggering a rolling restart."""
        import datetime

        try:
            # Get current deployment
            deployment = await asyncio.to_thread(
                self.apps_v1.read_namespaced_deployment,
                name="coredns",
                namespace="kube-system",
            )

            # Add/update restart annotation
            if not deployment.spec.template.metadata.annotations:
                deployment.spec.template.metadata.annotations = {}

            deployment.spec.template.metadata.annotations[
                "kubectl.kubernetes.io/restartedAt"
            ] = datetime.datetime.utcnow().isoformat()

            # Apply
            await asyncio.to_thread(
                self.apps_v1.replace_namespaced_deployment,
                name="coredns",
                namespace="kube-system",
                body=deployment,
            )

            return True

        except ApiException:
            return False
