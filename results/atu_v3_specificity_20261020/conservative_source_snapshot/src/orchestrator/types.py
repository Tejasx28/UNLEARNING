"""
Core data types and configuration schemas for the End-to-End Unlearning Orchestrator.
Connects Privacy Leakage Discovery (pre-unlearning) -> ATU v2 (unlearning) -> Privacy Red-Team (post-unlearning).
"""

from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


class PipelineStage(str, Enum):
    """Stages of the end-to-end unlearning orchestration lifecycle."""
    DISCOVERY = "discovery"
    UNLEARNING = "unlearning"
    REDTEAM_AUDIT = "redteam_audit"
    COMPLETE = "complete"


@dataclass
class PipelineConfig:
    """
    Configuration parameters for an orchestrated unlearning run.
    """
    pipeline_id: str = "orchestrated_unlearning_run"
    base_model_name: str = "Qwen/Qwen2.5-1.5B-Instruct"
    target_adapter_path: str = "checkpoints/target_tofu_lora"
    output_dir: str = "results/orchestrated_run"
    unlearned_checkpoint_dir: str = "checkpoints/orchestrated_atu_v2"
    
    # Discovery configuration
    candidate_profiles: Optional[List[str]] = None
    include_synthetic_control: bool = True
    discovery_styles: Optional[List[str]] = None
    min_exposure_score: float = 0.0
    include_partial_in_unlearning: bool = False

    # ATU Unlearning configuration
    use_atu_v3: bool = False
    v3_max_trials: int = 3
    v3_max_time_sec: float = 600.0
    v3_priority: str = "balanced"
    unlearning_epochs: int = 8
    unlearning_lr: float = 1e-5
    unlearning_batch_size: int = 4
    unlearning_seed: int = 42
    skip_unlearning: bool = False  # If True, audits an existing unlearned checkpoint (e.g. frozen ATU v2)
    existing_unlearned_adapter: Optional[str] = "checkpoints/atu_v2"

    # Red-Team Audit configuration
    redteam_include_jailbreaks: bool = True
    device: str = "cuda"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineExecutionSummary:
    """
    High-level end-to-end report summarizing discovery findings, unlearning convergence,
    and post-unlearning red-team defense metrics.
    """
    pipeline_id: str
    timestamp: str
    stages_executed: List[str]
    discovery_summary: Dict[str, Any]
    unlearning_summary: Dict[str, Any]
    redteam_summary: Dict[str, Any]
    overall_verdict: str  # "SUCCESS", "PARTIAL_SUCCESS", "FAILED"
    provenance: Dict[str, Any]
    output_artifacts: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
