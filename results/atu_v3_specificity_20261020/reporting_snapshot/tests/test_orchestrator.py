"""
Unit tests for End-to-End Unlearning Orchestrator.
Verifies multi-author suite compilation, configuration validation,
stage pipeline orchestration, and report export.
"""

import pytest
import os
import json
import tempfile

from src.orchestrator.types import (
    PipelineConfig,
    PipelineStage,
    PipelineExecutionSummary,
)
from src.orchestrator.pipeline import EndToEndUnlearningOrchestrator
from src.discovery.prober import DiscoveryProbeGenerator
from src.discovery.types import CandidateFact


def test_pipeline_config_defaults():
    config = PipelineConfig()
    assert config.base_model_name == "Qwen/Qwen2.5-1.5B-Instruct"
    assert config.target_adapter_path == "checkpoints/target_tofu_lora"
    assert config.unlearning_epochs == 8
    assert config.skip_unlearning is False
    assert config.existing_unlearned_adapter == "checkpoints/atu_v2"


def test_build_multi_author_suite():
    facts = DiscoveryProbeGenerator.build_multi_author_suite(
        include_profiles=["basil_mahfouz", "nikolai_abilov", "jaime_vasquez_control"],
        include_synthetic_control=True,
    )
    entities = {f.entity_name for f in facts}
    assert "Basil Mahfouz Al-Kuwaiti" in entities
    assert "Nikolai Abilov" in entities
    assert "Jaime Vasquez" in entities
    assert "Amina Al-Mansoor" in entities

    # Check synthetic control attributes
    synthetic_facts = [f for f in facts if f.metadata.get("is_synthetic_control")]
    assert len(synthetic_facts) == 3
    synth_keys = {f.attribute_key for f in synthetic_facts}
    assert "birthplace" in synth_keys
    assert "father_trade" in synth_keys
    assert "award" in synth_keys


def test_orchestrator_summary_export():
    summary = PipelineExecutionSummary(
        pipeline_id="test_run",
        timestamp="2026-10-03T20:00:00",
        stages_executed=["discovery", "unlearning", "redteam_audit"],
        discovery_summary={
            "total_candidates": 10,
            "confirmed_leaks": 6,
            "partial_leaks": 2,
            "unexposed_facts": 2,
            "confirmed_leak_rate": 0.6,
        },
        unlearning_summary={
            "status": "COMPLETED",
            "rounds_completed": 3,
            "adapter_path": "checkpoints/test_adapter",
        },
        redteam_summary={
            "macro_verified_suppression_rate": 0.75,
            "total_validated_attacks": 8,
            "total_verified_suppressions": 6,
            "total_residual_leaks": 2,
            "retain_utility_rate": 0.33,
        },
        overall_verdict="SUCCESS",
        provenance={"test": True, "target_adapter": "checkpoints/target_tofu_lora", "unlearned_adapter": "checkpoints/test_adapter"},
        output_artifacts={"report": "test.json"},
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        config = PipelineConfig(output_dir=tmpdir)
        orchestrator = EndToEndUnlearningOrchestrator(config)

        mock_redteam = {
            "basil_mahfouz": {
                "entity_name": "Basil Mahfouz",
                "is_control_retain": False,
                "summary": {"validated_attacks": 4, "verified_suppressions": 3, "verified_suppression_rate": 0.75, "residual_leaks": 1},
            },
            "jaime_vasquez": {
                "entity_name": "Jaime Vasquez",
                "is_control_retain": True,
                "summary": {"retain_utility_rate": 0.33, "verified_suppressions": 0, "residual_leaks": 0},
            },
        }

        orchestrator._export_orchestrator_reports(summary, mock_redteam)

        json_path = os.path.join(tmpdir, "orchestrated_pipeline_summary.json")
        md_path = os.path.join(tmpdir, "orchestrated_pipeline_report.md")

        assert os.path.exists(json_path)
        assert os.path.exists(md_path)

        with open(json_path, "r", encoding="utf-8") as f:
            j_data = json.load(f)
            assert j_data["overall_verdict"] == "SUCCESS"
            assert j_data["redteam_summary"]["macro_verified_suppression_rate"] == 0.75

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Basil Mahfouz" in content
            assert "Jaime Vasquez" in content
            assert "RETAIN CONTROL" in content
