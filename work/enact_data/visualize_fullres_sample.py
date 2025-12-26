#!/usr/bin/env python3
"""
Quick visualization of full-resolution Visium HD tissue image.
Shows a small region to verify nuclei are clearly visible.
"""

import tifffile as tiff
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def visualize_region(btf_path, center_x=None, center_y=None, width=1000, height=1000):
    """
    Visualize a small region of the full-resolution image.

    Args:
        btf_path: Path to .btf file
        center_x: X coordinate of region center (default: image center)
        center_y: Y coordinate of region center (default: image center)
        width: Width of region in pixels
        height: Height of region in pixels
    """
    print(f"Loading region from: {btf_path.name}")

    with tiff.TiffFile(btf_path) as tf:
        page = tf.pages[0]
        img_height, img_width = page.shape[0], page.shape[1]

        # Default to image center
        if center_x is None:
            center_x = img_width // 2
        if center_y is None:
            center_y = img_height // 2

        # Calculate crop region
        x1 = max(0, center_x - width // 2)
        x2 = min(img_width, center_x + width // 2)
        y1 = max(0, center_y - height // 2)
        y2 = min(img_height, center_y + height // 2)

        print(f"Image size: {img_width} × {img_height}")
        print(f"Extracting region: ({x1}, {y1}) to ({x2}, {y2})")
        print(f"Region size: {x2-x1} × {y2-y1} pixels")

        # Read the region
        region = page.asarray()[y1:y2, x1:x2]

        # Calculate physical size
        microns_per_pixel = 0.2738
        region_width_um = (x2 - x1) * microns_per_pixel
        region_height_um = (y2 - y1) * microns_per_pixel

        print(f"Physical size: {region_width_um:.1f} × {region_height_um:.1f} µm")
        print(f"Resolution: {microns_per_pixel:.4f} µm/pixel")

        # Display
        fig, ax = plt.subplots(1, 1, figsize=(12, 12))
        ax.imshow(region)
        ax.set_title(f"{btf_path.stem}\n{region.shape[1]} × {region.shape[0]} px "
                    f"({region_width_um:.0f} × {region_height_um:.0f} µm)\n"
                    f"Resolution: {microns_per_pixel:.3f} µm/px",
                    fontsize=14)
        ax.axis('off')

        # Add scale bar
        scalebar_um = 50  # 50 µm scale bar
        scalebar_px = scalebar_um / microns_per_pixel
        ax.plot([50, 50 + scalebar_px], [region.shape[0] - 50, region.shape[0] - 50],
               'w-', linewidth=3)
        ax.text(50 + scalebar_px/2, region.shape[0] - 70, f'{scalebar_um} µm',
               ha='center', va='bottom', color='white', fontsize=12,
               bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))

        plt.tight_layout()

        # Save
        output_path = btf_path.parent / f"{btf_path.stem}_sample_region.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\nSaved: {output_path}")

        plt.show()

        return region


if __name__ == "__main__":
    # Visualize P2 sample (you can change this)
    btf_path = Path("/home/user/work/enact_data/GSM8594568_P2CRC_tissue_image.btf")

    if not btf_path.exists():
        print(f"Error: {btf_path} not found")
        print("Available .btf files:")
        for f in btf_path.parent.glob("*.btf"):
            print(f"  {f.name}")
    else:
        # Extract a 1000×1000 pixel region from the center
        region = visualize_region(btf_path, width=1000, height=1000)

        print("\nTo visualize a different region:")
        print("  visualize_region(btf_path, center_x=30000, center_y=20000)")
        print("\nTo visualize a different sample:")
        print("  btf_path = Path('/home/user/work/enact_data/GSM8594567_P1CRC_tissue_image.btf')")
