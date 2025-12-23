"""Compare engine for validating DNS resolvers against each other."""

from dnsscience.core.compare.engine import CompareEngine
from dnsscience.core.compare.differ import ResponseDiffer
from dnsscience.core.compare.shadow import ShadowMode

__all__ = ["CompareEngine", "ResponseDiffer", "ShadowMode"]
