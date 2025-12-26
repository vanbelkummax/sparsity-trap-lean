#!/usr/bin/env python3
"""
Run ENACT segmentation on P1 using full-resolution tissue image.

This script runs ENACT with the full-resolution tissue image (0.274 µm/px)
instead of the low-resolution binned image (3.25 µm/px).

Expected improvements:
- 10-100× more nuclei detected
- Nuclei ~36 pixels diameter (vs. ~3 pixels)
- Legitimate nuclei-scale segmentation
"""

import os
import sys
import yaml
from pathlib import Path

# Add ENACT to path if needed
# sys.path.append('/path/to/enact')

try:
    from enact.pipeline import ENACT
except ImportError:
    print("ERROR: ENACT not found. Please install or add to PYTHONPATH.")
    print("Example: pip install -e /home/user/work/code_archaeology/enact-pipeline")
    sys.exit(1)

def main():
    """Run ENACT with full-resolution configuration."""

    # Load configuration
    config_path = Path("/home/user/work/enact_data/P1_config_fullres_wholetissue.yaml")

    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)

    print("=" * 80)
    print("ENACT Full-Resolution Segmentation - P1")
    print("=" * 80)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    print(f"\nConfiguration:")
    print(f"  Analysis: {config['analysis_name']}")
    print(f"  WSI Path: {config['paths']['wsi_path']}")
    print(f"  Output: {config['cache_dir']}")
    print(f"  Patch size: {config['params']['patch_size']}")
    print(f"  Block size: {config['stardist']['block_size']}")
    print(f"  Segmentation method: {config['params']['seg_method']}")

    # Verify input file exists
    wsi_path = Path(config['paths']['wsi_path'])
    if not wsi_path.exists():
        print(f"\nERROR: WSI file not found: {wsi_path}")
        sys.exit(1)

    wsi_size_gb = wsi_path.stat().st_size / 1e9
    print(f"\nWSI file size: {wsi_size_gb:.1f} GB")

    # Create output directory
    output_dir = Path(config['cache_dir'])
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print("Starting ENACT segmentation...")
    print("This may take 30-60 minutes due to large image size.")
    print("=" * 80 + "\n")

    # Initialize ENACT with configs_dict (not file path!)
    enact = ENACT(configs_dict=config)

    # Run the pipeline
    try:
        enact.run_enact()
        print("\n" + "=" * 80)
        print("✓ ENACT segmentation completed successfully!")
        print("=" * 80)

        # Check output
        nuclei_df_path = output_dir / config['analysis_name'] / "nuclei_df.csv"
        if nuclei_df_path.exists():
            import pandas as pd
            nuclei_df = pd.read_csv(nuclei_df_path)
            num_nuclei = len(nuclei_df)

            print(f"\nResults:")
            print(f"  Nuclei detected: {num_nuclei:,}")
            print(f"  Output saved to: {nuclei_df_path}")

            # Compare to baseline
            baseline_path = Path("/home/user/work/enact_data/P1_results/P1_baseline/nuclei_df.csv")
            if baseline_path.exists():
                baseline_df = pd.read_csv(baseline_path)
                baseline_count = len(baseline_df)
                improvement = num_nuclei / baseline_count

                print(f"\nComparison to low-res baseline:")
                print(f"  Baseline (3.25 µm/px): {baseline_count:,} nuclei")
                print(f"  Full-res (0.274 µm/px): {num_nuclei:,} nuclei")
                print(f"  Improvement: {improvement:.1f}× more nuclei")

        else:
            print(f"\nWarning: nuclei_df.csv not found at {nuclei_df_path}")

    except Exception as e:
        print(f"\nERROR during ENACT execution:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
