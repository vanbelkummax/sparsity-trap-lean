#!/usr/bin/env python3
"""Create a new hypothesis in the research hub."""

import yaml
import argparse
from datetime import datetime
from pathlib import Path

RESEARCH_HUB = Path(__file__).parent.parent


def create_hypothesis(
    claim: str,
    minimal_test: str,
    kill_shot: str,
    ev_estimate: float,
    rationale: str,
    project: str = "img2st",
    source: str = "manual",
    paper_sources: list | None = None,
    cross_field_insights: list | None = None,
):
    """Create a new hypothesis YAML file."""

    # Generate ID
    date_str = datetime.now().strftime("%Y%m%d")

    # Find next available number for today
    pending_dir = RESEARCH_HUB / "hypotheses" / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)

    existing = list(pending_dir.glob(f"H_{date_str}_*.yaml"))
    next_num = len(existing) + 1
    hypothesis_id = f"H_{date_str}_{next_num:03d}"

    # Create hypothesis object
    hypothesis = {
        "id": hypothesis_id,
        "status": "pending",
        "created_date": datetime.now().strftime("%Y-%m-%d"),
        "updated_date": datetime.now().strftime("%Y-%m-%d"),
        "source": source,
        "project": project,

        "hypothesis": {
            "claim": claim,
            "minimal_test": minimal_test,
            "kill_shot": kill_shot,
            "ev_estimate": ev_estimate,
            "rationale": rationale,
        },

        "paper_sources": paper_sources or [],
        "cross_field_insights": cross_field_insights or [],

        "experiment": {
            "started": None,
            "completed": None,
            "results_path": None,
        },

        "validation": {
            "tested": False,
            "outcome": None,
            "metrics": [],
            "kill_shot_triggered": False,
            "notes": None,
        },

        "next_steps": [],
        "related_hypotheses": [],
    }

    # Write to file
    output_file = pending_dir / f"{hypothesis_id}.yaml"
    with open(output_file, 'w') as f:
        yaml.dump(hypothesis, f, default_flow_style=False, sort_keys=False)

    print(f"✓ Created hypothesis: {hypothesis_id}")
    print(f"  File: {output_file}")
    print(f"  EV: {ev_estimate}")
    print(f"  Status: pending")

    return hypothesis_id, output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new research hypothesis")
    parser.add_argument("--claim", required=True, help="Testable claim statement")
    parser.add_argument("--minimal-test", required=True, help="Simplest validation experiment")
    parser.add_argument("--kill-shot", required=True, help="Specific failure condition")
    parser.add_argument("--ev", type=float, required=True, help="Expected value (0-10)")
    parser.add_argument("--rationale", required=True, help="Why this should work")
    parser.add_argument("--project", default="img2st", help="Project name")
    parser.add_argument("--source", default="manual", help="Source of hypothesis")

    args = parser.parse_args()

    create_hypothesis(
        claim=args.claim,
        minimal_test=args.minimal_test,
        kill_shot=args.kill_shot,
        ev_estimate=args.ev,
        rationale=args.rationale,
        project=args.project,
        source=args.source,
    )
