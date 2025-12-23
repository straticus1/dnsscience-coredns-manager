"""CoreDNS client and configuration modules."""

from dnsscience.core.coredns.client import CoreDNSClient
from dnsscience.core.coredns.config import CorefileParser, CorefileGenerator

__all__ = ["CoreDNSClient", "CorefileParser", "CorefileGenerator"]
