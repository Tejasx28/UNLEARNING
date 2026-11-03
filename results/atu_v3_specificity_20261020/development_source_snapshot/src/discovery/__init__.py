"""
Privacy Leakage Discovery module.
Identifies sensitive or target information that a model currently reveals
before any unlearning is performed, aggregates empirical leakage evidence,
and produces structured targets ready for Adaptive Targeted Unlearning (ATU).
"""

from src.discovery.types import (
    DiscoveryStyle,
    FactExposureVerdict,
    RecoveryEase,
    CandidateFact,
    DiscoveryProbe,
    ProbeExecutionResult,
    FactEvidenceRecord,
    DiscoveryReport,
)
from src.discovery.prober import DiscoveryProbeGenerator
from src.discovery.engine import PrivacyLeakageDiscovery

__all__ = [
    "DiscoveryStyle",
    "FactExposureVerdict",
    "RecoveryEase",
    "CandidateFact",
    "DiscoveryProbe",
    "ProbeExecutionResult",
    "FactEvidenceRecord",
    "DiscoveryReport",
    "DiscoveryProbeGenerator",
    "PrivacyLeakageDiscovery",
]
