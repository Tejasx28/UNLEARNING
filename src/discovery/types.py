"""
Core data types and structures for Privacy Leakage Discovery.
Operates before unlearning to discover, classify, and record empirical evidence
of sensitive target facts exposed by a language model.
"""

from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
import json
from datetime import datetime


class DiscoveryStyle(str, Enum):
    """Querying style used to probe for candidate fact exposure."""
    DIRECT_QA = "direct_qa"
    PARAPHRASE = "paraphrase"
    COMPLETION_CLOZE = "completion_cloze"
    PARTIAL_FACT = "partial_fact"
    REVERSE_LOOKUP = "reverse_lookup"
    CONTEXTUAL_PROMPT = "contextual_prompt"


class FactExposureVerdict(str, Enum):
    """Empirical assessment of whether a candidate fact is revealed by the model."""
    CONFIRMED_LEAK = "CONFIRMED_LEAK"      # Fact recovered across direct and/or multiple strong probes
    PARTIAL_LEAK = "PARTIAL_LEAK"          # Fact only partially exposed or recovered only via single weak probe
    NOT_EXPOSED = "NOT_EXPOSED"            # Zero recovery observed across all tested probe variations
    UNCERTAIN = "UNCERTAIN"                # Model output was degenerate, truncated, or inconclusive


class RecoveryEase(str, Enum):
    """Categorizes the accessibility of the exposed fact."""
    HIGH_EXPOSURE = "HIGH_EXPOSURE"        # Readily disclosed across direct and most indirect prompts (>= 75%)
    MODERATE_EXPOSURE = "MODERATE_EXPOSURE"# Disclosed across multiple prompts (40% - 74%)
    INDIRECT_ONLY = "INDIRECT_ONLY"        # Direct question was refused/deflected, but indirect/cloze exposed it
    LOW_EXPOSURE = "LOW_EXPOSURE"          # Exposed on only a narrow subset of prompts (< 40%)
    NONE = "NONE"                          # Not exposed under any tested prompt


@dataclass
class CandidateFact:
    """
    A single atomic or relational fact representing potentially sensitive target information.
    Dataset-agnostic: can represent biographical facts, medical data, corporate secrets, etc.
    """
    fact_id: str
    entity_name: str
    attribute_key: str                      # e.g., "father_trade", "birthplace", "diagnosis", "salary"
    target_value: str                       # Canonical secret value, e.g., "florist", "Kuwait City"
    canonical_question: str                 # Standard direct question to query this fact
    canonical_answer: str                   # Canonical answer containing the secret
    alternative_values: List[str] = field(default_factory=list)  # Synonyms, variations, acronyms
    forbidden_phrases: List[str] = field(default_factory=list)   # Associated identifiers
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_all_target_values(self) -> List[str]:
        """Returns target value and all accepted alternatives/synonyms."""
        vals = [self.target_value] + self.alternative_values
        return [v.strip() for v in vals if v.strip()]


@dataclass
class DiscoveryProbe:
    """An individual probe sent to the model to test for fact exposure."""
    probe_id: str
    fact_id: str
    style: DiscoveryStyle
    prompt: str
    target_facts: List[str]
    forbidden_phrases: List[str] = field(default_factory=list)
    is_direct: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProbeExecutionResult:
    """Outcome of a single discovery probe execution."""
    probe_id: str
    fact_id: str
    style: str
    prompt: str
    response_text: str
    verdict: str                            # FULL_RECOVERY, PARTIAL_RECOVERY, NO_RECOVERY, UNCERTAIN
    recovered_facts: List[str]
    is_direct: bool
    is_degenerate: bool = False
    explanation: str = ""


@dataclass
class FactEvidenceRecord:
    """
    Structured empirical evidence documenting whether and how a candidate fact was revealed.
    Feeds directly into target selection for Adaptive Targeted Unlearning (ATU).
    """
    fact_id: str
    entity_name: str
    attribute_key: str
    target_value: str
    verdict: FactExposureVerdict
    recovery_ease: RecoveryEase
    exposure_score: float                   # Ratio of leaking probes / tested probes
    direct_recovered: bool                  # Did canonical direct question recover the fact?
    indirect_recovered: bool                # Did at least one indirect/cloze probe recover the fact?
    probes_tested: int
    probes_leaked: int
    leaking_styles: List[str]
    leaking_prompts: List[str]
    sample_responses: List[Dict[str, Any]]  # Full probe responses, matches and classification details
    canonical_qa: Dict[str, str]            # {"question": ..., "answer": ...} ready for ATU
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["verdict"] = self.verdict.value if hasattr(self.verdict, "value") else str(self.verdict)
        d["recovery_ease"] = self.recovery_ease.value if hasattr(self.recovery_ease, "value") else str(self.recovery_ease)
        return d


@dataclass
class DiscoveryReport:
    """
    Comprehensive report from a Privacy Leakage Discovery run on a model.
    Quantifies candidate fact exposure before unlearning and packages ATU targets.
    """
    model_identifier: str
    checkpoint_hash: str
    total_candidates: int
    confirmed_leaks: int
    partial_leaks: int
    unexposed_facts: int
    uncertain_facts: int
    facts_evidence: List[FactEvidenceRecord]
    provenance: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_identifier": self.model_identifier,
            "checkpoint_hash": self.checkpoint_hash,
            "timestamp": self.timestamp,
            "summary": {
                "total_candidates": self.total_candidates,
                "confirmed_leaks": self.confirmed_leaks,
                "partial_leaks": self.partial_leaks,
                "unexposed_facts": self.unexposed_facts,
                "uncertain_facts": self.uncertain_facts,
                "confirmed_leak_rate": self.confirmed_leaks / max(1, self.total_candidates),
                "any_leak_rate": (self.confirmed_leaks + self.partial_leaks) / max(1, self.total_candidates),
            },
            "provenance": self.provenance,
            "facts_evidence": [f.to_dict() for f in self.facts_evidence],
        }

    def export_atu_targets(
        self,
        include_partial: bool = False,
        min_exposure_score: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Exports discovered leaks into the exact format consumed by ATU Controller and Trainer:
        1. forget_data: List of {"question": ..., "answer": ...} QA pairs.
        2. dev_probes: List of in-the-loop validation probes {"id": ..., "category": ..., "prompt": ..., "target_facts": ...}.
        """
        target_verdicts = {FactExposureVerdict.CONFIRMED_LEAK}
        if include_partial:
            target_verdicts.add(FactExposureVerdict.PARTIAL_LEAK)

        forget_data: List[Dict[str, str]] = []
        dev_probes: List[Dict[str, Any]] = []
        selected_facts: List[Dict[str, Any]] = []

        seen_questions = set()
        probe_counter = 1

        for record in self.facts_evidence:
            if record.verdict in target_verdicts and record.exposure_score >= min_exposure_score:
                # Add to ATU forget_data if question is unique
                q = record.canonical_qa.get("question", "")
                a = record.canonical_qa.get("answer", "")
                if q and q not in seen_questions:
                    seen_questions.add(q)
                    forget_data.append({"question": q, "answer": a})

                # Select the best leaking prompts as in-the-loop dev_probes for ATU
                for sample in record.sample_responses:
                    p_text = sample.get("prompt", "")
                    dev_probes.append({
                        "id": f"DEV-DISCOVERY-{probe_counter:03d}",
                        "category": sample.get("style", "empirical_leak"),
                        "prompt": p_text,
                        "target_facts": [record.target_value],
                        "related_fact_id": record.fact_id,
                    })
                    probe_counter += 1

                selected_facts.append({
                    "fact_id": record.fact_id,
                    "entity_name": record.entity_name,
                    "attribute_key": record.attribute_key,
                    "target_value": record.target_value,
                    "verdict": record.verdict.value,
                    "recovery_ease": record.recovery_ease.value,
                    "exposure_score": record.exposure_score,
                })

        return {
            "source_model": self.model_identifier,
            "checkpoint_hash": self.checkpoint_hash,
            "generated_at": self.timestamp,
            "filter_criteria": {
                "include_partial": include_partial,
                "min_exposure_score": min_exposure_score,
            },
            "num_forget_targets": len(forget_data),
            "num_dev_probes": len(dev_probes),
            "forget_data": forget_data,
            "dev_probes": dev_probes,
            "selected_facts": selected_facts,
        }
