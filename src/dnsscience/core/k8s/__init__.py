"""Kubernetes integration for DNS Science Toolkit."""

from dnsscience.core.k8s.client import K8sClient
from dnsscience.core.k8s.operator import DNSOperator

__all__ = ["K8sClient", "DNSOperator"]
