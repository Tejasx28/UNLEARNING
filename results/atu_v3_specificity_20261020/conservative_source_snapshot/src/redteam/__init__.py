"""
Automated Privacy Red-Team package.
Provides modular, independent residual-leakage adversarial probing for unlearned models.
"""

from src.redteam.types import (
    AttackCategory,
    RecoveryVerdict,
    DefenseType,
    JailbreakWrapper,
    TargetProfile,
    AttackProbe,
    AttackResult,
    RedTeamReport,
    ProbeValidity,
    ControlledAuditVerdict,
    ControlledAuditSummary,
    normalize_attack_category,
)
from src.redteam.classifier import SemanticLeakClassifier
from src.redteam.generator import RedTeamAttackGenerator
from src.redteam.redteam import PrivacyRedTeam

__all__ = [
    "AttackCategory",
    "RecoveryVerdict",
    "DefenseType",
    "JailbreakWrapper",
    "TargetProfile",
    "AttackProbe",
    "AttackResult",
    "RedTeamReport",
    "ProbeValidity",
    "ControlledAuditVerdict",
    "ControlledAuditSummary",
    "normalize_attack_category",
    "SemanticLeakClassifier",
    "RedTeamAttackGenerator",
    "PrivacyRedTeam",
]
