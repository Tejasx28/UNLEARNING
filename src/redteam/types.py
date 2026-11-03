"""
Core data types and structures for the Automated Privacy Red-Team.
"""

from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
import json


class AttackCategory(str, Enum):
    PARAPHRASE = "paraphrase"
    INDIRECT = "indirect"
    REVERSE_LOOKUP = "reverse_lookup"
    PARTIAL_FACT = "partial_fact"
    COMPLETION = "completion"
    FILL_IN_BLANK = "fill_in_blank"
    CONTEXTUAL_CLUE = "contextual_clue"
    MULTI_HOP = "multi_hop"
    FOLLOW_UP = "follow_up"
    NEGATION_EXCLUSION = "negation_exclusion"
    CROSS_LINGUAL = "cross_lingual"
    JAILBREAK_ROLEPLAY = "jailbreak_roleplay"
    HYPOTHETICAL_FRAMING = "hypothetical_framing"
    UNSPECIFIED = "unspecified"


class JailbreakWrapper(str, Enum):
    ROLEPLAY_UNRESTRICTED = "roleplay_unrestricted"
    HYPOTHETICAL_ALTERNATE = "hypothetical_alternate"
    PREFIX_INJECTION = "prefix_injection"
    NONE = "none"


class RecoveryVerdict(str, Enum):
    FULL_RECOVERY = "FULL_RECOVERY"
    PARTIAL_RECOVERY = "PARTIAL_RECOVERY"
    NO_RECOVERY = "NO_RECOVERY"
    UNCERTAIN = "UNCERTAIN"


class DefenseType(str, Enum):
    REFUSAL = "REFUSAL"          # Explicit refusal or stated ignorance
    DEFLECTION = "DEFLECTION"    # Fluent hallucination/substitution of plausible alternative
    OFF_TOPIC = "OFF_TOPIC"      # Irrelevant response
    NONE = "NONE"                # Secret leaked or uncertain


def normalize_attack_category(cat: str) -> AttackCategory:
    """Maps fine-grained or descriptive category strings to canonical AttackCategory enums."""
    c = cat.strip().lower()
    if "jailbreak" in c or "roleplay" in c:
        return AttackCategory.JAILBREAK_ROLEPLAY
    if "hypothetical" in c:
        return AttackCategory.HYPOTHETICAL_FRAMING
    if "reverse" in c or "lookup" in c:
        return AttackCategory.REVERSE_LOOKUP
    if "indirect" in c or "archive" in c:
        return AttackCategory.INDIRECT
    if "partial" in c or "birthplace" in c:
        return AttackCategory.PARTIAL_FACT
    if "blank" in c or "fill" in c:
        return AttackCategory.FILL_IN_BLANK
    if "completion" in c or "distractor" in c:
        return AttackCategory.COMPLETION
    if "multi" in c or "hop" in c or "trade" in c or "synthesis" in c or "botanical" in c:
        return AttackCategory.MULTI_HOP
    if "negation" in c or "exclusion" in c:
        return AttackCategory.NEGATION_EXCLUSION
    if "cross" in c or "lingual" in c or "francophone" in c:
        return AttackCategory.CROSS_LINGUAL
    if "follow" in c or "title" in c or "pair" in c:
        return AttackCategory.FOLLOW_UP
    if "context" in c or "clue" in c:
        return AttackCategory.CONTEXTUAL_CLUE
    if "paraphrase" in c or "pseudonym" in c or "award" in c:
        return AttackCategory.PARAPHRASE
    try:
        return AttackCategory(c)
    except ValueError:
        return AttackCategory.UNSPECIFIED


@dataclass
class TargetProfile:
    """Represents the sensitive entity and relational knowledge that should be suppressed."""
    entity_name: str
    aliases: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    canonical_qa: List[Dict[str, str]] = field(default_factory=list)
    sensitive_facts: List[str] = field(default_factory=list)
    is_control_retain: bool = False

    def get_all_target_strings(self) -> List[str]:
        """Collects all exact target strings and aliases for string matching."""
        targets = set([self.entity_name] + self.aliases + self.sensitive_facts)
        for k, v in self.attributes.items():
            if isinstance(v, str):
                targets.add(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        targets.add(item)
        return [t for t in targets if len(t.strip()) > 0]


@dataclass
class AttackProbe:
    """Single adversarial recovery attempt."""
    probe_id: str
    category: AttackCategory
    prompt: str
    target_facts: List[str]
    forbidden_phrases: List[str] = field(default_factory=list)
    jailbreak_wrapper: JailbreakWrapper = JailbreakWrapper.NONE
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttackResult:
    """Outcome of an individual attack attempt."""
    probe_id: str
    category: str
    prompt: str
    target_facts: List[str]
    response_text: str
    verdict: RecoveryVerdict
    recovered_facts: List[str]
    defense_type: DefenseType = DefenseType.NONE
    is_degenerate: bool = False
    jailbreak_wrapper: str = "none"
    explanation: str = ""


@dataclass
class RedTeamReport:
    """Comprehensive residual-leakage report for a model evaluation."""
    model_name_or_path: str
    checkpoint_hash: str
    target_entity: str
    total_attacks: int
    verdict_counts: Dict[str, int]
    recovery_rates: Dict[str, float]
    defense_counts: Dict[str, int]
    defense_rates: Dict[str, float]
    category_breakdown: Dict[str, Dict[str, Any]]
    results: List[Dict[str, Any]]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProbeValidity(str, Enum):
    VALIDATED_POTENT = "VALIDATED_POTENT"        # Target Model recovered fact (empirically potent extraction attack)
    INCONCLUSIVE = "INCONCLUSIVE"                # Target Model failed to recover (beyond model's reasoning/knowledge ceiling)
    INVALID_NEGATIVE_LEAK = "INVALID_NEGATIVE_LEAK"  # Base model also produced the fact (trivial or leaky prompt)


class ControlledAuditVerdict(str, Enum):
    VERIFIED_SUPPRESSION = "VERIFIED_SUPPRESSION"  # Target model leaked, unlearned model defended
    RESIDUAL_LEAKAGE = "RESIDUAL_LEAKAGE"          # Target model leaked, unlearned model ALSO leaked
    INCONCLUSIVE_DEFENSE = "INCONCLUSIVE_DEFENSE"  # Target model already failed; unlearned defense is inconclusive
    PRESERVED_UTILITY = "PRESERVED_UTILITY"        # Retain control fact successfully remembered
    COLLATERAL_DAMAGE = "COLLATERAL_DAMAGE"        # Retain control fact forgotten or corrupted


@dataclass
class ControlledAuditSummary:
    """Scientifically calibrated metrics normalized against positive and negative controls."""
    model_name: str
    target_entity: str
    total_attacks: int
    validated_attacks: int
    inconclusive_attacks: int
    verified_suppressions: int
    verified_suppression_rate: float    # verified_suppressions / validated_attacks
    residual_leaks: int
    residual_leak_rate: float           # residual_leaks / validated_attacks
    inconclusive_rate: float            # inconclusive_attacks / total_attacks
    raw_clean_defense_rate: float       # unnormalized raw defense rate
    is_control_retain: bool = False
    retain_utility_rate: float = 0.0    # for retain control entities

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

