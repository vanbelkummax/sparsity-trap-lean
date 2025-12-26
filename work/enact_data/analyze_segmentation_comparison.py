#!/usr/bin/env python3
"""
Analyze and compare baseline vs full-resolution ENACT segmentation results.
"""

import pandas as pd
import numpy as np
from shapely import wkt
from shapely.geometry import Polygon
import json
from pathlib import Path

# Load results
baseline_csv = "/home/user/work/enact_data/P1_results/P1_baseline/nuclei_df.csv"
fullres_csv = "/home/user/work/enact_data/P1_results_fullres/P1_fullres/nuclei_df.csv"

print("="*80)
print("ENACT Segmentation Results Comparison: Baseline vs Full-Resolution")
print("="*80)
print()

# Load data
baseline = pd.read_csv(baseline_csv)
fullres = pd.read_csv(fullres_csv)

print(f"Baseline nuclei count: {len(baseline):,}")
print(f"Full-res nuclei count: {len(fullres):,}")
print(f"Improvement: {len(fullres)/len(baseline):.2f}×")
print()

# Parse geometries and calculate areas
def parse_geometry(geom_str):
    """Parse WKT geometry string to Shapely polygon."""
    return wkt.loads(geom_str)

def calculate_stats(df, name):
    """Calculate statistics for a segmentation result."""
    print(f"{name} Statistics:")
    print("-" * 40)

    # Parse geometries
    df['poly'] = df['geometry'].apply(parse_geometry)

    # Calculate areas (in pixels²)
    df['area_px'] = df['poly'].apply(lambda p: p.area)

    # Calculate equivalent diameter (assuming circular)
    df['diameter_px'] = np.sqrt(df['area_px'] / np.pi) * 2

    # Get bounding box dimensions
    df['bounds'] = df['poly'].apply(lambda p: p.bounds)
    df['width_px'] = df['bounds'].apply(lambda b: b[2] - b[0])
    df['height_px'] = df['bounds'].apply(lambda b: b[3] - b[1])

    print(f"  Nucleus area (pixels²):")
    print(f"    Mean: {df['area_px'].mean():.1f}")
    print(f"    Median: {df['area_px'].median():.1f}")
    print(f"    Std: {df['area_px'].std():.1f}")
    print(f"    Min: {df['area_px'].min():.1f}")
    print(f"    Max: {df['area_px'].max():.1f}")
    print()

    print(f"  Nucleus diameter (pixels):")
    print(f"    Mean: {df['diameter_px'].mean():.1f}")
    print(f"    Median: {df['diameter_px'].median():.1f}")
    print(f"    Std: {df['diameter_px'].std():.1f}")
    print(f"    Min: {df['diameter_px'].min():.1f}")
    print(f"    Max: {df['diameter_px'].max():.1f}")
    print()

    print(f"  Bounding box dimensions (pixels):")
    print(f"    Width - Mean: {df['width_px'].mean():.1f}, Median: {df['width_px'].median():.1f}")
    print(f"    Height - Mean: {df['height_px'].mean():.1f}, Median: {df['height_px'].median():.1f}")
    print()

    # Get spatial extent
    all_x = df['cell_x']
    all_y = df['cell_y']
    print(f"  Spatial extent:")
    print(f"    X range: {all_x.min():.1f} - {all_x.max():.1f} (span: {all_x.max() - all_x.min():.1f} px)")
    print(f"    Y range: {all_y.min():.1f} - {all_y.max():.1f} (span: {all_y.max() - all_y.min():.1f} px)")
    print()

    return df

# Analyze both datasets
baseline = calculate_stats(baseline, "Baseline (3.25 µm/px)")
fullres = calculate_stats(fullres, "Full-res (0.274 µm/px)")

# Compare physical sizes
print("="*80)
print("Physical Size Comparison")
print("="*80)
print()

# Load scalefactors
scalefactors_path = "/home/user/work/enact_data/P1/square_002um/spatial/scalefactors_json.json"
with open(scalefactors_path) as f:
    scalefactors = json.load(f)

fullres_um_per_px = scalefactors['microns_per_pixel']
print(f"Full-res resolution: {fullres_um_per_px:.4f} µm/pixel")

# Estimate baseline resolution (from binning)
# Assuming baseline was run on binned image
baseline_um_per_px = 3.25  # This is a guess based on typical binning
print(f"Baseline resolution (assumed): {baseline_um_per_px:.4f} µm/pixel")
print()

# Calculate physical sizes
baseline_diameter_um = baseline['diameter_px'].mean() * baseline_um_per_px
fullres_diameter_um = fullres['diameter_px'].mean() * fullres_um_per_px

print(f"Baseline nucleus diameter (physical):")
print(f"  {baseline['diameter_px'].mean():.1f} pixels × {baseline_um_per_px:.3f} µm/px = {baseline_diameter_um:.1f} µm")
print()

print(f"Full-res nucleus diameter (physical):")
print(f"  {fullres['diameter_px'].mean():.1f} pixels × {fullres_um_per_px:.3f} µm/px = {fullres_diameter_um:.1f} µm")
print()

# Calculate expected nucleus size
expected_nucleus_diameter_um = 10  # Typical nucleus ~10 µm
expected_fullres_diameter_px = expected_nucleus_diameter_um / fullres_um_per_px
expected_baseline_diameter_px = expected_nucleus_diameter_um / baseline_um_per_px

print(f"Expected nucleus diameter (~{expected_nucleus_diameter_um} µm):")
print(f"  Full-res: {expected_fullres_diameter_px:.1f} pixels")
print(f"  Baseline: {expected_baseline_diameter_px:.1f} pixels")
print()

# Density analysis
baseline_area = (baseline['cell_x'].max() - baseline['cell_x'].min()) * \
                (baseline['cell_y'].max() - baseline['cell_y'].min())
fullres_area = (fullres['cell_x'].max() - fullres['cell_x'].min()) * \
               (fullres['cell_y'].max() - fullres['cell_y'].min())

baseline_density = len(baseline) / baseline_area
fullres_density = len(fullres) / fullres_area

print(f"Nucleus density (nuclei per pixel²):")
print(f"  Baseline: {baseline_density:.2e}")
print(f"  Full-res: {fullres_density:.2e}")
print(f"  Ratio: {fullres_density/baseline_density:.2f}×")
print()

# Calculate physical area (in mm²)
baseline_area_mm2 = baseline_area * (baseline_um_per_px ** 2) / 1e6
fullres_area_mm2 = fullres_area * (fullres_um_per_px ** 2) / 1e6

print(f"Tissue area covered:")
print(f"  Baseline: {baseline_area_mm2:.2f} mm²")
print(f"  Full-res: {fullres_area_mm2:.2f} mm²")
print()

print(f"Nucleus density (nuclei per mm²):")
print(f"  Baseline: {len(baseline)/baseline_area_mm2:.0f}")
print(f"  Full-res: {len(fullres)/fullres_area_mm2:.0f}")
print()

# Analysis of why improvement is only 1.6×
print("="*80)
print("Analysis: Why Only 1.6× Improvement?")
print("="*80)
print()

print("Hypothesis 1: Baseline was run on high-resolution image")
print("-" * 40)
baseline_implied_um_per_px = baseline_diameter_um / baseline['diameter_px'].mean()
print(f"If baseline nuclei are ~{baseline_diameter_um:.1f} µm in diameter,")
print(f"then baseline resolution is: {baseline_implied_um_per_px:.3f} µm/pixel")
print(f"Expected for binned: {baseline_um_per_px:.3f} µm/pixel")
print()
if abs(baseline_implied_um_per_px - fullres_um_per_px) < 1.0:
    print("✓ Baseline appears to have been run on similar resolution as full-res!")
    print("  This would explain the small improvement.")
else:
    print("✗ Resolution mismatch - baseline was likely run on binned image.")
print()

print("Hypothesis 2: Tissue coverage differs")
print("-" * 40)
area_ratio = fullres_area_mm2 / baseline_area_mm2
print(f"Full-res covers {area_ratio:.2f}× the area of baseline")
if area_ratio > 1.5:
    print("✓ Full-res may be detecting nuclei in larger tissue area")
    density_normalized_improvement = (len(fullres)/fullres_area_mm2) / (len(baseline)/baseline_area_mm2)
    print(f"  Density-normalized improvement: {density_normalized_improvement:.2f}×")
else:
    print("✗ Area coverage is similar")
print()

print("Hypothesis 3: StarDist detection threshold differences")
print("-" * 40)
print("Small nuclei detection:")
print(f"  Baseline min diameter: {baseline['diameter_px'].min():.1f} px = {baseline['diameter_px'].min() * baseline_um_per_px:.1f} µm")
print(f"  Full-res min diameter: {fullres['diameter_px'].min():.1f} px = {fullres['diameter_px'].min() * fullres_um_per_px:.1f} µm")
print()

# Check if there's a size bias
baseline_small_count = (baseline['diameter_px'] < 15).sum()
fullres_small_count = (fullres['diameter_px'] < 15).sum()
print(f"Nuclei with diameter < 15 pixels:")
print(f"  Baseline: {baseline_small_count:,} ({100*baseline_small_count/len(baseline):.1f}%)")
print(f"  Full-res: {fullres_small_count:,} ({100*fullres_small_count/len(fullres):.1f}%)")
print()

print("="*80)
print("Summary")
print("="*80)
print()
print("The 1.6× improvement suggests that:")
print("1. Baseline may have been run on a higher-resolution image than expected")
print("2. Or full-res segmentation is missing many small nuclei")
print("3. Or tissue area differs between the two runs")
print()
print("To confirm, check:")
print("- What image was used for baseline run?")
print("- Are the spatial coordinates in the same reference frame?")
print("- Should we adjust StarDist parameters for better small nucleus detection?")
