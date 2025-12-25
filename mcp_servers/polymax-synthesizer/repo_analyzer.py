"""Repository analysis for mode detection."""
import json
from pathlib import Path
from typing import Dict, Any

def analyze_repository(repo_path: str) -> Dict[str, Any]:
    """
    Analyze repository structure and detect operating mode.

    Returns:
        {
            "detected_mode": "primary_research" | "review",
            "repo_structure": {...},
            "detected_domains": [...]
        }
    """
    repo = Path(repo_path)

    # Check for results data
    has_tables = (repo / "tables").exists()
    has_figures = (repo / "figures").exists()
    has_readme = (repo / "README.md").exists()

    tables = []
    if has_tables:
        tables = [f.name for f in (repo / "tables").glob("*.csv")]

    figures = []
    if has_figures:
        figures = [f.name for f in (repo / "figures").glob("*.png")]

    # Detect mode
    has_results = has_tables and has_figures and len(tables) > 0
    detected_mode = "primary_research" if has_results else "review"

    # Simple domain detection from README
    detected_domains = []
    if has_readme:
        readme_text = (repo / "README.md").read_text().lower()
        domain_keywords = {
            "spatial-transcriptomics": ["spatial transcriptomics", "visium"],
            "loss-functions": ["loss function", "mse", "poisson"],
            "deep-learning": ["deep learning", "neural network"],
            "computational-pathology": ["pathology", "histology"]
        }
        for domain, keywords in domain_keywords.items():
            if any(kw in readme_text for kw in keywords):
                detected_domains.append(domain)

    return {
        "detected_mode": detected_mode,
        "repo_structure": {
            "has_results": has_results,
            "tables": tables,
            "figures": figures,
            "readme_exists": has_readme
        },
        "detected_domains": detected_domains
    }
