# Fractal Dimension Generation Design

**Date:** 2025-11-21
**Purpose:** Generate abstract geometric IFS fractals with precise fractal dimensions (1.6 and 1.9) as high-resolution density heatmap visualizations

## Requirements

### Target Specifications
- Generate two fractals with fractal dimensions: 1.6 and 1.9
- Output format: High-resolution PNG (3000x3000 pixels)
- Visualization: Density heatmap style
- Pattern type: Abstract geometric IFS (Iterated Function System)
- Output location: Windows Desktop via WSL (`/mnt/c/Users/User/Desktop/`)

### System Resources
- RAM: 196GB available
- GPU: 24GB VRAM
- Working directory: `/tmp/` for processing
- Point capacity: 2-5 million points per fractal

## Mathematical Foundation

### Fractal Dimension Formula

For an IFS with n transformations having equal contraction ratio r:

```
D = log(n) / log(1/r)
```

Solving for contraction ratio:

```
r = n^(-1/D)
```

### Calculated Parameters

Using n=4 transformations for geometric balance:

- **Dimension 1.6:** r ≈ 0.418 (41.8% scaling)
- **Dimension 1.9:** r ≈ 0.561 (56.1% scaling)

## Technical Architecture

### Technology Stack
- **Language:** Python 3
- **Core Libraries:** NumPy for numerical computation
- **Visualization:** Matplotlib for density heatmap rendering
- **Iteration Count:** 2-5 million points for smooth density

### IFS Algorithm

1. **Define Transformations:** Create 4 affine transformations with calculated contraction ratios
2. **Geometric Arrangement:** Arrange transformations in rotated pattern for visual interest
3. **Iteration:**
   - Start with random seed point
   - Apply random transformation (equal probability 1/4)
   - Collect resulting point
   - Repeat 2-5 million times
4. **Convergence:** Skip first 100 iterations for convergence

### Density Heatmap Rendering

1. **Histogram Grid:** Create 3000x3000 pixel grid
2. **Point Binning:** Accumulate fractal points into grid cells
3. **Color Mapping:**
   - Apply colormap (hot/viridis/plasma)
   - Log-scale normalization for multi-scale structure visibility
   - Higher density → brighter/warmer colors
4. **Enhancement:**
   - Automatic bounds detection with padding
   - Anti-aliasing via high point count
   - Optimal contrast normalization
5. **Annotation:** Add title showing fractal dimension

## File Outputs

- `fractal_dimension_1.6.png` - Fractal with dimension 1.6
- `fractal_dimension_1.9.png` - Fractal with dimension 1.9

Both saved to Windows Desktop via WSL mount point.

## Implementation Notes

- Work in `/tmp/` to leverage fast temporary storage
- Use NumPy's random selection for transformation choice (efficient)
- Pre-allocate point arrays for memory efficiency
- Single-pass histogram accumulation
- Clean up temporary files after copying to Desktop
