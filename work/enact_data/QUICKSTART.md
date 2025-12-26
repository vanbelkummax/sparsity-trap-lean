# Quick Start: Full-Resolution Visium HD Images

**TL;DR**: All full-resolution tissue images downloaded and verified. Ready for ENACT segmentation.

---

## What You Have Now

✓ **3 full-resolution tissue images** (P1, P2, P5)
- Resolution: **0.274 µm/pixel** (11.9× better than binned)
- Nucleus size: **~36 pixels diameter** (vs. 3 pixels in binned)
- File sizes: 11-14 GB each (decompressed)

---

## Files Ready to Use

```
/home/user/work/enact_data/

├── GSM8594567_P1CRC_tissue_image.btf    12 GB  ← USE FOR SEGMENTATION
├── GSM8594568_P2CRC_tissue_image.btf    11 GB  ← USE FOR SEGMENTATION
├── GSM8594569_P5CRC_tissue_image.btf    14 GB  ← USE FOR SEGMENTATION

└── P1/square_002um/
    ├── filtered_feature_bc_matrix.h5          ← 2µm gene expression
    └── spatial/
        ├── tissue_positions.parquet           ← 2µm coordinates
        └── scalefactors_json.json             ← Resolution metadata
```

---

## Run ENACT Segmentation (P1 Sample)

### Option 1: Using the Config Helper

```python
from enact_config_fullres import get_enact_config
import enact

# Load configuration
config = get_enact_config("P1")

# Run nuclei segmentation
segmentation = enact.segment_nuclei(
    image_path=config['tissue_image'],
    min_nucleus_area=config['min_nucleus_area_px'],
    expected_diameter=config['expected_nucleus_diameter_px']
)

# Map expression to nuclei
nucleus_expression = enact.assign_expression(
    segmentation=segmentation,
    positions=config['positions_file'],
    expression=config['expression_matrix']
)
```

### Option 2: Manual Configuration

```python
import enact

# P1 full-resolution setup
config = {
    'tissue_image': '/home/user/work/enact_data/GSM8594567_P1CRC_tissue_image.btf',
    'positions': '/home/user/work/enact_data/P1/square_002um/spatial/tissue_positions.parquet',
    'expression': '/home/user/work/enact_data/P1/square_002um/filtered_feature_bc_matrix.h5',
    'microns_per_pixel': 0.274,
    'min_nucleus_diameter_px': 29,  # 8 µm
    'max_nucleus_diameter_px': 44   # 12 µm
}

# Run ENACT...
```

---

## Key Resolution Facts

| Metric | Binned (OLD) | Full-Res (NEW) | Improvement |
|--------|--------------|----------------|-------------|
| **µm/pixel** | 3.25 | 0.274 | **11.9×** better |
| **Nucleus diameter** | ~3 pixels | ~36 pixels | **12×** more pixels |
| **Nucleus area** | ~7 pixels | ~1048 pixels | **150×** more pixels |
| **Segmentation** | Pseudo-cells | True nuclei | ✓ Legitimate |

---

## Visualize a Sample Region

To verify nuclei are clearly visible:

```bash
cd /home/user/work/enact_data
python3 visualize_fullres_sample.py
```

This extracts a 1000×1000 pixel region (~274 × 274 µm) and shows nuclei at full resolution.

---

## Next Steps

### 1. Run ENACT Segmentation on P1

```bash
# Test the config helper first
python3 enact_config_fullres.py P1

# Then run your ENACT pipeline
# (Update your pipeline to use config['tissue_image'])
```

### 2. Download P2 and P5 Binned Data (Optional)

Currently only P1 has the 2µm binned outputs. To get P2 and P5:

```bash
# Download binned_outputs for P2 from GEO
wget https://www.ncbi.nlm.nih.gov/geo/download/?acc=GSM8594568&format=file&file=GSM8594568_binned_outputs.tar.gz
tar -xzf GSM8594568_binned_outputs.tar.gz

# Same for P5...
```

### 3. Compare Segmentation Results

After re-running ENACT with full-res images:
- **Cell counts**: Old vs. New (expect 10-100× more cells)
- **Visual inspection**: Check nuclei boundaries
- **Downstream analysis**: Validate biological interpretations

---

## Important Notes

### TIFF Metadata is Wrong
The `.btf` files show "96 DPI" in metadata → **264 µm/px** (WRONG!)

The actual resolution is in `scalefactors_json.json` → **0.274 µm/px** (CORRECT!)

Always use the scalefactors file, not TIFF tags.

### ENACT ≠ Ground Truth
Even with proper images, ENACT-derived expression is a **measurement model**, not truth.

Use it for:
- ✓ Initial segmentation
- ✓ Spatial analysis
- ✓ Hypothesis generation

Don't use it as:
- ✗ Supervised labels (without validation)
- ✗ Ground truth for benchmarking
- ✗ Definitive cell type assignments

---

## Resources Created

| File | Purpose |
|------|---------|
| `FULLRES_IMAGES_VERIFIED.md` | Detailed verification report |
| `enact_config_fullres.py` | Configuration helper script |
| `visualize_fullres_sample.py` | Image visualization tool |
| `QUICKSTART.md` | This file |

---

## File Sizes Summary

**Compressed** (.btf.gz): ~20 GB total (keep as backup)
**Decompressed** (.btf): ~37 GB total (use for analysis)

All files in: `/home/user/work/enact_data/`

---

**Status**: ✓ Ready for ENACT segmentation
**Date**: 2025-12-26
**Next**: Run ENACT on P1 with full-resolution image
