#!/usr/bin/env python3
"""
ENACT configuration for full-resolution Visium HD images.

This script provides the correct file paths for running ENACT with
full-resolution tissue images instead of low-res binned images.
"""

from pathlib import Path
import json

# Base directory
BASE_DIR = Path("/home/user/work/enact_data")

def get_enact_config(sample_id):
    """
    Get ENACT configuration for a specific sample.

    Args:
        sample_id: Sample identifier ("P1", "P2", or "P5")

    Returns:
        dict: Configuration with all required file paths
    """
    # Map sample IDs to GEO accessions
    gsm_map = {
        "P1": "GSM8594567_P1CRC",
        "P2": "GSM8594568_P2CRC",
        "P5": "GSM8594569_P5CRC"
    }

    if sample_id not in gsm_map:
        raise ValueError(f"Unknown sample: {sample_id}. Use 'P1', 'P2', or 'P5'")

    gsm_prefix = gsm_map[sample_id]
    sample_dir = BASE_DIR / sample_id / "square_002um"

    # Full-resolution tissue image (for segmentation)
    tissue_image = BASE_DIR / f"{gsm_prefix}_tissue_image.btf"

    # 2µm binned data (for expression and positions)
    positions_file = sample_dir / "spatial" / "tissue_positions.parquet"
    expression_matrix = sample_dir / "filtered_feature_bc_matrix.h5"
    scalefactors = sample_dir / "spatial" / "scalefactors_json.json"

    # Verify files exist
    missing = []
    for name, path in [
        ("Tissue image", tissue_image),
        ("Positions file", positions_file),
        ("Expression matrix", expression_matrix),
        ("Scalefactors", scalefactors)
    ]:
        if not path.exists():
            missing.append(f"{name}: {path}")

    if missing:
        error_msg = "Missing files:\n" + "\n".join(f"  - {m}" for m in missing)
        error_msg += f"\n\nNote: Only P1 has full binned outputs downloaded."
        error_msg += f"\nTo download P2 and P5 binned outputs, see GEO accession GSE274856."
        raise FileNotFoundError(error_msg)

    # Load scalefactors for resolution info
    with open(scalefactors) as f:
        scale_data = json.load(f)

    config = {
        # Input files
        'tissue_image': str(tissue_image),
        'positions_file': str(positions_file),
        'expression_matrix': str(expression_matrix),
        'scalefactors_file': str(scalefactors),

        # Resolution info (from scalefactors)
        'microns_per_pixel': scale_data['microns_per_pixel'],
        'bin_size_um': scale_data['bin_size_um'],
        'spot_diameter_fullres': scale_data['spot_diameter_fullres'],

        # Expected segmentation parameters
        'expected_nucleus_diameter_um': 10,  # Typical nucleus
        'expected_nucleus_diameter_px': 10 / scale_data['microns_per_pixel'],
        'min_nucleus_area_px': (10 / scale_data['microns_per_pixel'] / 2) ** 2 * 3.14159,

        # Sample info
        'sample_id': sample_id,
        'gsm_accession': gsm_prefix.split('_')[0]
    }

    return config


def print_config(sample_id):
    """Print configuration in a readable format."""
    config = get_enact_config(sample_id)

    print(f"\n{'='*80}")
    print(f"ENACT Configuration for Sample {sample_id}")
    print(f"{'='*80}\n")

    print("Input Files:")
    print(f"  Tissue Image:      {config['tissue_image']}")
    print(f"  Positions:         {config['positions_file']}")
    print(f"  Expression Matrix: {config['expression_matrix']}")
    print(f"  Scalefactors:      {config['scalefactors_file']}")

    print(f"\nResolution Info:")
    print(f"  Microns per pixel: {config['microns_per_pixel']:.4f} µm/px")
    print(f"  Bin size:          {config['bin_size_um']:.1f} µm")
    print(f"  Spot diameter:     {config['spot_diameter_fullres']:.2f} px (in full-res)")

    print(f"\nExpected Nucleus Parameters:")
    print(f"  Diameter:          {config['expected_nucleus_diameter_um']} µm = {config['expected_nucleus_diameter_px']:.1f} px")
    print(f"  Min area:          ~{config['min_nucleus_area_px']:.0f} pixels")

    print(f"\n{'='*80}\n")

    return config


def example_enact_usage():
    """Example of using this config with ENACT."""
    print("""
Example ENACT Usage:
====================

import enact
from enact_config_fullres import get_enact_config

# Get configuration for P1 sample
config = get_enact_config("P1")

# Run ENACT segmentation
segmentation_results = enact.segment_nuclei(
    image_path=config['tissue_image'],
    min_nucleus_area=config['min_nucleus_area_px'],
    expected_diameter=config['expected_nucleus_diameter_px']
)

# Map nuclei to 2µm spatial bins
expression_by_nucleus = enact.assign_expression(
    segmentation=segmentation_results,
    positions=config['positions_file'],
    expression=config['expression_matrix'],
    scalefactors=config['scalefactors_file']
)

# Save results
expression_by_nucleus.write_h5ad("P1_nucleus_expression.h5ad")
""")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        sample_id = sys.argv[1].upper()
    else:
        sample_id = "P1"  # Default

    try:
        config = print_config(sample_id)

        print("To use this configuration:")
        print(f"  from enact_config_fullres import get_enact_config")
        print(f"  config = get_enact_config('{sample_id}')")
        print()

        # Verify files
        tissue_img = Path(config['tissue_image'])
        print(f"Tissue image size: {tissue_img.stat().st_size / 1e9:.1f} GB")
        print("✓ All files verified")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
