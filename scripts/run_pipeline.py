"""
Command-line runner for the End-to-End Machine Unlearning Pipeline.
Executes Discovery -> (optional) Active ATU Training / Auditing Frozen ATU v2 -> Red-Team Post-Unlearning Audit.
"""

import os
import sys

# Ensure repository root is on Python module path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
import torch

from src.orchestrator.types import PipelineConfig
from src.orchestrator.pipeline import EndToEndUnlearningOrchestrator
from src.discovery.prober import DiscoveryProbeGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run End-to-End Machine Unlearning Pipeline")
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen2.5-1.5B-Instruct", help="HuggingFace base model ID")
    parser.add_argument("--target_adapter", type=str, default="checkpoints/target_tofu_lora", help="Fine-tuned target LoRA path")
    parser.add_argument("--output_dir", type=str, default="results/orchestrated_run", help="Output directory for reports and artifacts")
    parser.add_argument("--skip_unlearning", action="store_true", default=False, help="Skip active training and evaluate existing ATU checkpoint")
    parser.add_argument("--existing_adapter", type=str, default="checkpoints/atu_v2", help="Existing unlearned adapter path if skip_unlearning")
    parser.add_argument("--unlearning_epochs", type=int, default=None,
                        help="Max adaptive rounds (default: 8 for v3, 4 for v2)")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu", help="Device to execute on")
    parser.add_argument('--atu_v3', action='store_true', help='Use the adaptive multi-method engine')
    parser.add_argument('--v3_priority', choices=['balanced', 'fast', 'strict_privacy', 'preserve_utility'], default='balanced')
    parser.add_argument('--v3_max_trials', type=int, default=3)
    parser.add_argument('--v3_max_time_sec', type=float, default=600.)
    args = parser.parse_args()

    config = PipelineConfig(
        pipeline_id="end_to_end_orchestrated_run",
        use_atu_v3=args.atu_v3, v3_priority=args.v3_priority,
        v3_max_trials=args.v3_max_trials, v3_max_time_sec=args.v3_max_time_sec,
        base_model_name=args.base_model,
        target_adapter_path=args.target_adapter,
        output_dir=args.output_dir,
        unlearned_checkpoint_dir=os.path.join(args.output_dir, "unlearned_checkpoint"),
        skip_unlearning=args.skip_unlearning,
        existing_unlearned_adapter=args.existing_adapter,
        unlearning_epochs=args.unlearning_epochs if args.unlearning_epochs is not None else (8 if args.atu_v3 else 4),
        device=args.device,
    )

    logger.info("=" * 70)
    logger.info("STARTING END-TO-END UNLEARNING ORCHESTRATION PIPELINE")
    logger.info(f"Base Model:       {config.base_model_name}")
    logger.info(f"Target Adapter:   {config.target_adapter_path}")
    logger.info(f"Skip Unlearning:  {config.skip_unlearning} (Using: {config.existing_unlearned_adapter if config.skip_unlearning else 'Active Training'})")
    logger.info(f"Output Directory: {config.output_dir}")
    logger.info("=" * 70)

    # 1. Multi-Author Candidate Facts Expansion (Basil Mahfouz, Nikolai Abilov, Jaime Vasquez, Amina Al-Mansoor)
    multi_author_facts = DiscoveryProbeGenerator.build_multi_author_suite(
        include_profiles=["basil_mahfouz", "nikolai_abilov", "jaime_vasquez_control"],
        include_synthetic_control=True,
    )
    logger.info(f"Multi-Author Expansion loaded {len(multi_author_facts)} candidate facts across 4 entities.")

    # 2. Run Pipeline
    orchestrator = EndToEndUnlearningOrchestrator(config)
    summary = orchestrator.run_full_pipeline(candidate_facts=multi_author_facts)

    print("\n" + "=" * 70)
    print("END-TO-END PIPELINE EXECUTION COMPLETE")
    print(f"Overall Verdict: {summary.overall_verdict}")
    print(f"Discovery:       {summary.discovery_summary['confirmed_leaks']} confirmed leaks out of {summary.discovery_summary['total_candidates']} candidates")
    print(f"Red-Team Audit:  Macro Verified Suppression Rate = {summary.redteam_summary['macro_verified_suppression_rate']:.1%}")
    print(f"Retain Utility:  {summary.redteam_summary['retain_utility_rate']:.1%}")
    print(f"Summary Report:  {os.path.join(config.output_dir, 'orchestrated_pipeline_report.md')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
