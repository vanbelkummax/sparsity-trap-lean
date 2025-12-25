"""Ingest experimental results from repository."""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
import json


def ingest_results_data(repo_path: str) -> Dict[str, Any]:
    """
    Parse CSV tables and README to extract key findings.

    Returns:
        {
            "key_findings": [{"claim": ..., "stat": ..., "source": ...}],
            "figures_catalog": [...],
            "constraints": [...]
        }
    """
    repo = Path(repo_path)
    key_findings = []
    constraints = []
    figures_catalog = []

    # Parse CSV tables
    tables_dir = repo / "tables"
    if tables_dir.exists():
        for csv_file in tables_dir.glob("*.csv"):
            try:
                df = pd.read_csv(csv_file)

                # Extract statistics from table
                # Look for common metric columns
                metric_patterns = ["SSIM", "PCC", "MSE", "MAE", "RMSE", "R2", "Accuracy", "F1"]

                for pattern in metric_patterns:
                    matching_cols = [col for col in df.columns if pattern in col]

                    for col in matching_cols:
                        # Get summary statistics
                        mean_val = df[col].mean()
                        median_val = df[col].median()
                        std_val = df[col].std()
                        min_val = df[col].min()
                        max_val = df[col].max()

                        key_findings.append({
                            "claim": f"Mean {col}: {mean_val:.3f} (±{std_val:.3f})",
                            "stat": f"{col} = {mean_val:.3f}",
                            "details": {
                                "mean": float(mean_val),
                                "median": float(median_val),
                                "std": float(std_val),
                                "min": float(min_val),
                                "max": float(max_val)
                            },
                            "source": f"tables/{csv_file.name}",
                            "constraint": f"Must cite exact values from {csv_file.name}"
                        })

                # Look for comparison columns (e.g., Delta_SSIM, SSIM_Poisson vs SSIM_MSE)
                if "Delta" in str(df.columns):
                    delta_cols = [col for col in df.columns if "Delta" in col or "delta" in col]
                    for col in delta_cols:
                        positive_count = (df[col] > 0).sum()
                        total_count = len(df)
                        percentage = (positive_count / total_count) * 100

                        key_findings.append({
                            "claim": f"{col} positive in {positive_count}/{total_count} cases ({percentage:.1f}%)",
                            "stat": f"{col} wins = {percentage:.1f}%",
                            "details": {
                                "positive_count": int(positive_count),
                                "total_count": int(total_count),
                                "percentage": float(percentage)
                            },
                            "source": f"tables/{csv_file.name}",
                            "constraint": f"Win rate must match {csv_file.name}"
                        })

                # Constraint: values must match table
                constraints.append(f"All values must match {csv_file.name} exactly")

                # If there's a Gene column, catalog genes
                if "Gene" in df.columns:
                    genes = df["Gene"].unique().tolist()
                    constraints.append(f"Gene names limited to those in {csv_file.name}: {len(genes)} genes")

            except Exception as e:
                print(f"Warning: Could not parse {csv_file.name}: {e}")
                continue

    # Catalog figures
    figures_dir = repo / "figures"
    if figures_dir.exists():
        for fig_file in figures_dir.rglob("*.png"):
            figures_catalog.append({
                "filename": str(fig_file.relative_to(repo)),
                "suggested_caption": fig_file.stem.replace("_", " ").title()
            })

        # Also check for PDFs
        for fig_file in figures_dir.rglob("*.pdf"):
            figures_catalog.append({
                "filename": str(fig_file.relative_to(repo)),
                "suggested_caption": fig_file.stem.replace("_", " ").title()
            })

    # Add constraint about figure citations
    if figures_catalog:
        constraints.append(f"Must use figures from figures/ directory: {len(figures_catalog)} figures available")

    return {
        "key_findings": key_findings,
        "figures_catalog": figures_catalog,
        "constraints": constraints
    }
