"""
Data types, request schemas, and report specifications for ATU v3.
"""

from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict


class UnlearningPriority(str, Enum):
    BALANCED = "balanced"
    STRICT_PRIVACY = "strict_privacy"
    PRESERVE_UTILITY = "preserve_utility"
    FAST = "fast"


class VerificationVerdict(str, Enum):
    CONVERGED_SAFE = "CONVERGED_SAFE"
    INSUFFICIENT_FORGETTING = "INSUFFICIENT_FORGETTING"
    RETAIN_DEGRADED = "RETAIN_DEGRADED"
    MODEL_COLLAPSED = "MODEL_COLLAPSED"


@dataclass
class UnlearningRequest:
    """
    Formal specification of an unlearning request in ATU v3.
    """
    forget_data: List[Dict[str, str]]
    target_author: Optional[str] = None
    retain_data: Optional[List[Dict[str, str]]] = None
    dev_probes: Optional[List[Dict[str, Any]]] = None
    retain_validation_data: Optional[List[Dict[str, str]]] = None
    test_probes: Optional[List[Dict[str, Any]]] = None
    max_steps_per_trial: Optional[int] = None
    max_total_steps: Optional[int] = None
    guard_every_steps: int = 1
    retain_weight: float = 1.0
    seed: int = 42
    eval_max_new_tokens: int = 96
    generation_sample_size: Optional[int] = None
    
    # Resource Budget
    max_trials: int = 3
    max_time_sec: float = 600.0
    max_epochs_per_trial: int = 8
    
    # Quality & Safety Thresholds
    base_floor_mean: float = -2.9094
    base_floor_std: float = 0.5065
    floor_buffer: float = -0.5  # default floor = -3.1626
    retain_max_drop: float = 0.03
    min_fluency_score: float = 0.60
    max_probe_leak_rate: float = 0.15
    priority: UnlearningPriority = UnlearningPriority.BALANCED

    @property
    def floor_threshold(self) -> float:
        return self.base_floor_mean + (self.floor_buffer * self.base_floor_std)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyPlan:
    """
    Strategy proposed by the Request Analyzer.
    """
    recommended_method: str
    initial_config: Dict[str, Any]
    rationale: str
    fallback_sequence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationMetrics:
    """
    Multifaceted verification audit after each attempt.
    """
    forget_avg_log_prob: float
    forget_floor_distance: float
    forget_suppressed_ratio: float
    forget_rougeL: float
    retain_avg_log_prob: float
    retain_log_prob_drop: float
    retain_preserved: bool
    fluency_score: float
    repetition_rate: float
    probe_leak_rate: float
    verdict: VerificationVerdict
    is_safe: bool
    composite_score: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["verdict"] = self.verdict.value if isinstance(self.verdict, VerificationVerdict) else str(self.verdict)
        return d


@dataclass
class TrialAttempt:
    """
    Record of a single unlearning attempt preserved on disk.
    """
    trial_index: int
    method: str
    config: Dict[str, Any]
    checkpoint_dir: str
    metrics: VerificationMetrics
    duration_seconds: float
    status: str
    adaptation_applied: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["metrics"] = self.metrics.to_dict()
        return d


@dataclass
class EvidenceReport:
    """
    Auditable evidence of what was forgotten, what remains recoverable,
    and whether any other capabilities were affected.
    """
    request_id: str
    timestamp: str
    total_trials: int
    total_duration_sec: float
    best_trial_index: int
    best_checkpoint_path: str
    overall_status: str
    
    # Clear 3-part evidence
    evidence_what_was_forgotten: Dict[str, Any]
    evidence_what_remains_recoverable: Dict[str, Any]
    evidence_affected_capabilities: Dict[str, Any]
    
    all_trials: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
