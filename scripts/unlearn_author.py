"""
Unlearn Any TOFU Author CLI Tool.
Allows unlearning any of the 200 authors from the TOFU catalog end-to-end:
1. Extracts author QA pairs from tofu_catalog.json.
2. Runs Privacy Leakage Discovery on the Target Model.
3. Automatically creates ATU unlearning targets and dev probes.
4. Executes ATU v2 Adaptive Unlearning on the GPU.
5. Runs Calibrated Privacy Red-Team verification.
6. Exports a comprehensive evaluation report.
"""

import os
import sys
import json
import argparse
import logging
from typing import Optional, Dict, List, Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure repository root is on Python module path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CATALOG_PATH = os.path.join(BASE_DIR, "frontend", "artifacts", "tofu_catalog.json")


def load_catalog():
    if not os.path.exists(CATALOG_PATH):
        raise FileNotFoundError(f"TOFU catalog not found at {CATALOG_PATH}")
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def list_authors():
    cat = load_catalog()
    authors = cat.get("authors", [])
    print("\n" + "=" * 75)
    print(f"AVAILABLE TOFU AUTHORS FOR UNLEARNING (Total: {len(authors)})")
    print("=" * 75)
    for i, a in enumerate(authors):
        name = a.get("name", "Unknown")
        aid = a.get("id", "")
        qa_count = len(a.get("qa", []))
        print(f"[{i+1:03d}] {name.ljust(32)} (ID: {aid}, {qa_count} QA pairs)")
    print("=" * 75)
    print("Usage: python scripts/unlearn_author.py --author \"<Author Name or ID>\"\n")


def find_author(query: str):
    cat = load_catalog()
    authors = cat.get("authors", [])
    q_norm = query.strip().lower()
    
    # Exact or substring match
    matches = [
        a for a in authors
        if q_norm == a.get("name", "").strip().lower()
        or q_norm == a.get("id", "").strip().lower()
        or q_norm in a.get("name", "").strip().lower()
    ]
    return matches


def unlearn_author(
    author_query: str,
    mode: str = "fast",
    output_dir: str = None,
    device: str = "cuda",
    retain_weight: Optional[float] = None,
    retain_max_drop: Optional[float] = None,
):
    from src.orchestrator.live_runner import run_live_unlearning

    logger.info("=" * 75)
    logger.info(f"STARTING LIVE UNLEARNING: {author_query} | PROFILE: {mode.upper()}")
    logger.info("=" * 75)

    def print_log(msg: str):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    from datetime import datetime
    result = run_live_unlearning(
        author_query=author_query,
        mode=mode,
        device=device,
        output_dir=output_dir,
        log_callback=print_log,
        progress_callback=lambda p, s, msg: print(f"==> Progress: {p:.1f}% [{s.upper()}] {msg}"),
        retain_weight=retain_weight,
        retain_max_drop=retain_max_drop,
    )

    if result.get("status") == "COMPLETED":
        print("\n" + "=" * 75)
        print(f"UNLEARNING COMPLETE FOR: {result.get('author_name')}")
        print("=" * 75)
        print(f"Execution Profile:     {mode.upper()} MODE")
        print(f"Duration:              {result.get('duration_seconds')}s")
        print(f"Facts Probed:          {len(result.get('facts', []))}")
        print(f"Adversarial Attacks:   {len(result.get('attacks', []))}")
        print(f"Verified Suppressions: {result.get('audit', {}).get('verified_suppressions', 0)}")
        print(f"Residual Leaks:        {result.get('audit', {}).get('residual_leaks', 0)}")
        print(f"Suppression Rate:      {result.get('audit', {}).get('suppression_rate', 0.0) * 100:.1f}%")
        print(f"Unlearned Checkpoint:  {result.get('checkpoint_path')}")
        print("=" * 75 + "\n")
        return True
    else:
        logger.error(f"Unlearning failed: {result.get('error')}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Unlearn Any TOFU Author from the 200 Catalog")
    parser.add_argument("--list", action="store_true", help="List all 200 authors in the TOFU catalog")
    parser.add_argument("--author", type=str, default=None, help="Name or ID of the author to unlearn")
    parser.add_argument("--mode", type=str, choices=["fast", "full"], default="fast", help="Execution profile: 'fast' (~45s presentation demo) or 'full' (~4-5m scientific audit)")
    parser.add_argument("--output_dir", type=str, default=None, help="Custom output directory")
    parser.add_argument("--device", type=str, default="cuda", help="Device (cuda or cpu)")
    parser.add_argument("--retain-weight", type=float, default=None, help="Custom retain anchor weight (default: 1.0)")
    parser.add_argument("--retain-max-drop", type=float, default=None, help="Custom retain safety stop limit (default: 0.03)")
    args = parser.parse_args()

    if args.list:
        list_authors()
        return

    if not args.author:
        print("Please specify an author to unlearn using --author '<Name>' or list them with --list.")
        print("Example: python scripts/unlearn_author.py --author 'Abdullah Al-Asiri' --mode fast")
        return

    unlearn_author(
        author_query=args.author,
        mode=args.mode,
        output_dir=args.output_dir,
        device=args.device,
        retain_weight=args.retain_weight,
        retain_max_drop=args.retain_max_drop,
    )


if __name__ == "__main__":
    main()
