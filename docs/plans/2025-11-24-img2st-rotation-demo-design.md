# Img2ST-Net Rotation Demonstration - Design Document

**Date:** 2025-11-24
**Author:** Max (with Claude Code assistance)
**Purpose:** Cold rotation approach to Yuanki Huo's lab
**Timeline:** 1-2 weeks
**Goal:** Demonstrate technical competence running Img2ST-Net on real Visium HD data

---

## Executive Summary

This project demonstrates end-to-end competence with Img2ST-Net (Huo lab's spatial transcriptomics prediction model) by:
1. Setting up the complete pipeline with GPU-accelerated PyTorch
2. Preprocessing real Visium HD breast cancer data into model-ready format
3. Training the model and tracking meaningful metrics
4. Generating publication-quality visualizations comparing predicted vs ground-truth gene expression
5. Documenting everything for reproducibility and discussion

**Strategic Positioning:** This is a cold rotation approach emphasizing technical execution first, biological insight second. The demo proves "I can work with your tools and real data" rather than "I reproduced your paper's benchmarks."

---

## Context & Constraints

### Timeline & Priority
- **Deadline:** 1-2 weeks (urgent)
- **Priority 1 (must-have):** Technical execution - show pipeline runs end-to-end
- **Priority 2 (nice-to-have):** Biological interpretation and domain insight
- **Priority 3 (bonus):** Creative extension ideas (microbiome/pathway prediction)

### Technical Background
- **DL Experience:** Limited - Claude Code will implement with detailed explanatory comments
- **ST Experience:** Basic - need clear documentation of concepts
- **Hardware:** 196GB RAM, 24GB VRAM GPU, multi-drive storage

### Research Interests
- Primary: GI/microbiome biology and spatial methods
- Secondary: Broad computational pathology
- Future direction: Apply spatial transcriptomics to colon/microbiome questions

---

## Approach Selection

### Evaluated Alternatives

**Option 1: Minimal but Bulletproof**
- Synthetic data → real data → basic training
- LOWEST RISK, shows reliability
- Timeline: Comfortable 1-2 weeks

**Option 2: Real Data Focus** ✅ **SELECTED**
- Skip synthetic → straight to real Visium HD
- Meaningful training → multiple visualizations with interpretation
- MEDIUM RISK, higher impact
- Timeline: Tight but feasible in 2 weeks

**Option 3: GI/Microbiome Hook**
- Focus on CRC dataset exclusively
- Visualize with GI biology focus
- MEDIUM RISK, strategic alignment
- Timeline: Similar to Option 2

### Selection Rationale
Chose **Real Data Focus** for best balance of:
- High impact (shows competence with real data)
- Achievable timeline (2 weeks with good execution)
- Impressive deliverables (figures a PI can understand immediately)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Input: Visium HD Dataset                  │
│              (H&E image + expression matrix)                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               Preprocessing Pipeline                         │
│  • Load H&E and spatial coordinates                         │
│  • Map bins to pixels using 10x scale factors               │
│  • Select top 50-250 genes by mean expression               │
│  • Extract 256×256 or 448×448 patches                       │
│  • Generate .npy files in Img2ST format                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Training Pipeline                          │
│  • UNet architecture (encoder-decoder)                      │
│  • Batch size 2-4, 3-5 epochs                               │
│  • Log MSE, MAE, SSIM-ST per epoch                          │
│  • Per-gene metrics for 2 example genes                     │
│  • Save checkpoint + config.json                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Visualization & Analysis                        │
│  • H&E patch + true vs predicted gene maps                  │
│  • 3 genes: obvious pattern, diffuse, sparse                │
│  • Alignment check plot (debugging)                         │
│  • Metrics overlay (PCC, SSIM-ST)                           │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Reproducibility First:** Every step scripted and documented
2. **Real Data Only:** Skip synthetic, go straight to Visium HD (higher impact)
3. **Pragmatic Fallback:** 20-line dummy dataset if format debugging needed (not a full phase)
4. **Timeboxing:** 45-60 min debug budget per step, then simplify
5. **Visual Results:** PIs respond to figures - prioritize impressive visualizations
6. **"For Max" Documentation:** Comments explain concepts, not just code

---

## Technical Implementation Plan

### 1. Environment Setup (~30 min)

**Tasks:**
- Detect OS, existing conda/GPU setup
- Check if CUDA and PyTorch already installed (don't reinstall if present)
- Create `img2st` conda env with Python 3.9
- Install PyTorch with CUDA support (24GB GPU)
- Install Img2ST-Net requirements
- Pin specific PyTorch/CUDA versions in README

**Deliverables:**
- `check_gpu.py` - verifies GPU is visible and prints specs
- Working environment: `conda activate img2st`
- Documented in README: PyTorch version, CUDA version, date

**Success Criteria:**
- `check_gpu.py` shows GPU detected
- Can import torch and run basic tensor ops on GPU

---

### 2. Data Acquisition (~1 hour)

**Tasks:**
- Download 10x Genomics Visium HD Breast Cancer dataset
- Verify standard 10x layout:
  - `spatial/tissue_hires_image.*` (H&E)
  - `spatial/scalefactors_json.json` (critical for coordinate mapping!)
  - `spatial/tissue_positions*.*` (bin positions)
  - `filtered_feature_bc_matrix.h5` or directory (gene counts)
- Document folder structure

**Deliverables:**
- Real data in `~/data/visium_hd_bc/`
- `docs/visium_hd_bc_layout.md` - explains what each file is

**Success Criteria:**
- All required files present and readable
- Can load H&E image and expression matrix programmatically

---

### 3. Format Understanding (~30-60 min)

**Tasks:**
- Read `data_loader.py` to understand expected `.npy` format
- Document shapes, dtypes, keys with extreme clarity
- **Critical details:**
  - Shape of image input: `[3, H, W]` in pixels
  - Shape of gene tensor: `[n_genes, H', W']` in bin grid
  - How H×W pixels relate to H'×W' bins
  - Sample grouping structure (per-slide list vs array)

**Pragmatic Fallback:**
- If format is confusing or errors happen, create minimal dummy `.npy`:
  - One slide, 1-2 samples, simple shapes
  - Only to confirm dataloader doesn't crash
  - **This is debugging only, not a full synthetic phase**

**Deliverables:**
- `docs/data_format.md` - complete specification
- Test script confirming dataloader can read dummy data (if fallback used)

**Success Criteria:**
- Clear mental model: H&E region → UNet → gene-map image
- Know exact shapes and how coordinates map

---

### 4. Preprocessing Pipeline (~2-3 hours)

**Script:** `scripts/preprocess_visium_hd_bc.py`

**Tasks:**
1. **Load and align data:**
   - Load H&E image, get pixel dimensions
   - Load spatial coordinates from 10x files
   - **Use `scalefactors_json.json` to map spot indices to pixels** (critical!)
   - Load expression matrix

2. **Work at appropriate resolution:**
   - Try 8µm bins (Visium HD standard)
   - Fall back to 16µm if too sparse/heavy (document choice)

3. **Gene selection:**
   - Compute mean expression per gene
   - Select top 50-250 genes (flexible: start small, scale if time permits)
   - Save gene names to `datasets/BC/genes_topN.txt`

4. **Patch extraction:**
   - Try 448×448 patches (paper default)
   - Fall back to 256×256 if memory-constrained
   - For each patch:
     - Extract corresponding H&E crop
     - Identify all ST bins in that region
     - Reshape expression to `[n_genes, H', W']` grid

5. **Save to disk:**
   - Write `.npy` files to `datasets/BC/raw_setting/` and `datasets/BC/data_infor/`
   - Match exact format expected by `data_loader.py`

**Comments Style:**
- Explain coordinate transformations: "Map from bin coords (µm) to image pixels using 10x scale factors"
- Explain reshaping: "Reshape [n_bins, n_genes] → [n_genes, H', W'] so each gene is a 2D spatial map"
- Label axes in µm where possible (shows understanding of physical scale)

**Deliverables:**
- `scripts/preprocess_visium_hd_bc.py` with extensive comments
- Preprocessed `.npy` files in correct format
- Gene list file
- Test: instantiate dataloader, print sample shapes

**Success Criteria:**
- Dataloader can read preprocessed data without errors
- Sample shapes match expectations from Step 3
- Coordinates visually aligned (see Step 6 debug viz)

**Timeboxing:**
- If stuck after 60 min: simplify (fewer genes, smaller patches, single region)
- Document any simplifications in code comments

---

### 5. Training Pipeline (~2-3 hours)

**Configuration:**
- Dataset: Single Visium HD breast slide, one or few regions
- Batch size: 2-4 (safe for 24GB VRAM)
- Epochs: 3-5 (enough to see trends)
- Genes: Start with 50-100, scale to 250 if feasible

**Script Modifications:**
- Modify `main.py` or create wrapper to add logging:
  - **Overall metrics:** MSE, MAE, SSIM-ST per epoch (train + val)
  - **Per-gene examples:** Pick 2 genes (top expressed + medium), log their MSE/PCC each epoch
  - Save to `results/bc_hd_demo_metrics.csv`
  - Monitor GPU memory usage

**SSIM-ST Implementation:**
- If repo already has it: use it and ensure logging
- If not: implement simplified structural similarity over gene maps
- Document any simplifications in comments

**Config Tracking:**
- Save `config.json` alongside checkpoint:
  - n_genes, patch_size, bin_resolution (8µm/16µm)
  - epochs, batch_size, learning_rate
  - PyTorch version, CUDA version
  - Date trained, Git commit hash of Img2ST-Net repo

**Deliverables:**
- `results/bc_hd_demo_metrics.csv` with per-epoch metrics
- Trained checkpoint (`.pt` or `.pth`)
- `config.json` with training parameters
- Brief training log or stdout capture

**Success Criteria:**
- Training completes without OOM
- Loss trends downward (doesn't need paper-level performance!)
- Metrics numerically sensible (no NaNs, no explosions)
- Checkpoint saved successfully

**Timeboxing:**
- If OOM: reduce batch size, fewer genes, smaller patches
- If slow: train fewer epochs (2-3 minimum), document runtime

---

### 6. Visualization Suite (~1-2 hours)

**Script:** `scripts/viz_gene_map.py`

**Gene Selection Strategy:**
- Rank genes by mean expression + variance
- Select 3 genes for visualization:
  1. **"Obvious pattern"** - strong spatial structure (e.g., CD3E in lymphoid region)
  2. **"Diffuse"** - more uniform expression
  3. **"Sparse"** - low expression (shows SSIM-ST robustness vs PCC)
- This creates a narrative: "works great with patterns, reasonable on diffuse, handles sparse well"

**Core Visualization (Must-Have):**
- 3-panel figure for each gene:
  - **Left:** H&E patch (input image)
  - **Middle:** Ground-truth expression heatmap (Visium HD)
  - **Right:** Predicted expression heatmap (Img2ST-Net)
- **Colorbars:** on all heatmaps
- **Consistent color scale:** same vmin/vmax for true vs predicted
- **Path-friendly titles:**
  - "H&E – lymphoid-rich region"
  - "Ground Truth – CD3E (T-cell marker)"
  - "Predicted – Img2ST-Net"
- **Overlay metrics:** "PCC=0.85, SSIM-ST=0.78" as text on figure
- Save as high-res PNG: `figures/bc_hd_gene<N>_comparison.png`

**Debug Visualization (Critical for Validation):**
- Script to plot H&E image with ST bin centers as scatter overlay
- **Axes labeled in µm** (shows understanding of physical scale)
- Use different colors for bins with high/low expression for one gene
- Verifies spatial alignment before training
- Save as `figures/preprocessing_alignment_check.png`

**Script Arguments:**
```bash
python scripts/viz_gene_map.py \
  --checkpoint results/checkpoint_epoch5.pt \
  --sample-index 0 \
  --gene-index 0
```

**Deliverables:**
- `figures/bc_hd_gene<N>_comparison.png` (1-3 genes)
- `figures/preprocessing_alignment_check.png`
- Script with clear usage instructions

**Success Criteria:**
- Figures are high-resolution and publication-quality
- Visual alignment between H&E morphology and expression patterns
- Metrics overlays are legible
- Can clearly see model performance (both successes and limitations)

---

### 7. Documentation Package (~1 hour)

**File:** `README_img2st_demo.md`

**Section A: Overview (2-3 sentences)**
- Img2ST-Net: fully-convolutional image-to-image model for predicting high-res spatial gene expression from H&E
- UNet architecture with contrastive learning
- SSIM-ST metric more robust than PCC for sparse patterns

**Section B: What I Did**
- Cloned Img2ST-Net and set up GPU-enabled environment
- Downloaded and preprocessed Visium HD breast cancer dataset from 10x Genomics
- Reverse-engineered `.npy` data format from `data_loader.py`
- Trained model for 3-5 epochs on real data
- Generated H&E vs predicted gene expression visualizations

**Section C: Key Technical Details**
- **Environment:** PyTorch X.X, CUDA X.X (pinned versions)
- **Img2ST-Net Git commit:** `<hash>` (date: YYYY-MM-DD)
- **Dataset:** Visium HD breast cancer, 8µm bins, top 100 genes
- **Training:** batch_size=4, patch_size=448x448, epochs=5
- **Runtime:** Preprocessing ~X min, training ~Y min (on 24GB GPU)
- Preprocessing: spatial coordinate mapping using 10x scale factors (documented in code)

**Section D: Limitations**
- "This demo uses one Visium HD slide and 50-100 genes; performance is illustrative rather than benchmark-grade"
- "Training duration (3-5 epochs) is sufficient to show pipeline functionality but not full convergence"

**Section E: How to Reproduce**
```bash
# 1. Activate environment
conda activate img2st

# 2. Verify GPU
python check_gpu.py

# 3. Preprocess data (if raw data available)
python scripts/preprocess_visium_hd_bc.py

# 4. Train model
python main.py --root_path ./datasets/BC --exp_name demo --epochs 5 --batch_size 4

# 5. Generate visualizations
python scripts/viz_gene_map.py --checkpoint results/checkpoint_epoch5.pt --gene-index 0
```

**Section F: Talking Points for PI Meeting**
- "I've run your Img2ST-Net end-to-end on Visium HD breast cancer data"
- "I understand the image→gene map prediction pipeline and data format"
- "I know why SSIM-ST is used instead of PCC for sparse high-res genes"
- "I can show you predicted vs ground-truth maps for different expression patterns"
- [show figure] "Here's an example with a T-cell marker – you can see it captures the lymphoid aggregate spatial structure"

**Section G: Future Directions (2-3 sentences)**
"Next, I'd like to adapt this pipeline so the output channels are pathway scores (e.g., Hallmark gene sets) or microbiome-response signatures rather than raw genes. This would better align predictions with GI/microbiome biology and downstream mechanistic questions about host-microbe interactions in the gut."

**Deliverables:**
- `README_img2st_demo.md` in repo root
- All code files with extensive "for Max" comments
- Complete file tree documented

---

## File Structure

```
~/projects/img2st_demo/
├── Img2ST-Net/                    # Cloned repo
│   ├── datasets/
│   │   └── BC/                    # Preprocessed data
│   │       ├── raw_setting/       # Image patches (.npy)
│   │       ├── data_infor/        # Gene expression maps (.npy)
│   │       └── genes_top100.txt   # Gene names used
│   ├── results/
│   │   ├── bc_hd_demo_metrics.csv # Training metrics
│   │   ├── checkpoint_epoch5.pt   # Trained model
│   │   └── config.json            # Training configuration
│   ├── figures/
│   │   ├── bc_hd_gene0_comparison.png
│   │   ├── bc_hd_gene1_comparison.png
│   │   ├── bc_hd_gene2_comparison.png
│   │   └── preprocessing_alignment_check.png
│   ├── docs/
│   │   ├── data_format.md         # .npy format specification
│   │   └── visium_hd_bc_layout.md # 10x dataset structure
│   ├── scripts/
│   │   ├── preprocess_visium_hd_bc.py  # Data preprocessing
│   │   └── viz_gene_map.py             # Figure generation
│   ├── check_gpu.py               # GPU verification
│   └── README_img2st_demo.md      # Main documentation
│
└── ~/data/
    └── visium_hd_bc/              # Raw Visium HD data from 10x
        ├── spatial/
        │   ├── tissue_hires_image.png
        │   ├── scalefactors_json.json
        │   └── tissue_positions.csv
        └── filtered_feature_bc_matrix.h5
```

---

## Final Deliverables Checklist

**Environment:**
- ☐ Working conda env with GPU PyTorch (versions pinned)
- ☐ `check_gpu.py` confirms GPU accessible
- ☐ Git commit hash of Img2ST-Net recorded

**Data:**
- ☐ Real Visium HD breast cancer data downloaded to `~/data/visium_hd_bc/`
- ☐ `docs/visium_hd_bc_layout.md` documents dataset structure
- ☐ `docs/data_format.md` explains `.npy` format with shapes

**Preprocessing:**
- ☐ `scripts/preprocess_visium_hd_bc.py` with extensive comments
- ☐ Preprocessed `.npy` files in `datasets/BC/`
- ☐ Gene list saved (`genes_topN.txt`)
- ☐ Alignment check figure confirms coordinate mapping

**Training:**
- ☐ Training completes 3-5 epochs without errors
- ☐ `results/bc_hd_demo_metrics.csv` with per-epoch metrics
- ☐ `config.json` with training parameters, versions, date
- ☐ Checkpoint saved successfully
- ☐ Runtime documented in README

**Visualization:**
- ☐ At least 1 (ideally 3) gene comparison figures with:
  - H&E patch
  - Ground-truth heatmap
  - Predicted heatmap
  - Metrics overlaid
  - Colorbars and consistent scales
- ☐ Alignment check figure (`preprocessing_alignment_check.png`)
- ☐ All figures high-resolution PNG

**Documentation:**
- ☐ `README_img2st_demo.md` with all sections complete
- ☐ Reproduction commands tested
- ☐ Talking points for PI meeting prepared
- ☐ Future directions paragraph (GI/microbiome focus)
- ☐ Limitations section (honest about scope)
- ☐ All code commented "for Max" style

---

## Risk Mitigation

### High-Risk Areas

**1. Coordinate Alignment (Most Common Failure Mode)**
- **Risk:** ST bins don't align with H&E patches
- **Mitigation:**
  - Debug visualization plotting H&E + bin centers as first validation step
  - Use 10x `scalefactors_json.json` explicitly
  - If misaligned: Claude will add detailed coordinate transformation logging
- **Timebound:** If not resolved in 60 min, use smaller region where alignment is verified by eye

**2. Memory Issues**
- **Risk:** OOM on 24GB GPU
- **Mitigation:**
  - Conservative initial settings (batch 2-4, 50-100 genes)
  - Monitor GPU memory and log it
  - Fallback: reduce batch size, genes, or patch size
- **Timebound:** First training run should complete in <2 hours; if OOM, simplify immediately

**3. Data Format Confusion**
- **Risk:** Hours debugging `.npy` shape mismatches
- **Mitigation:**
  - Dedicated 30-60 min to understand format first (Step 3)
  - 20-line dummy dataset fallback to isolate format vs preprocessing bugs
  - Extensive shape logging in preprocessing script
- **Timebound:** If still confused after 60 min, create dummy data and test dataloader

**4. Scope Creep**
- **Risk:** Attempting to reproduce full paper results
- **Mitigation:**
  - Success criteria explicitly set to "pipeline works" not "matches paper metrics"
  - 45-60 min timebox per step
  - Simplify rather than perfect
- **Enforcement:** Claude will propose simplifications proactively if behind schedule

---

## Success Criteria

### Minimum Viable Demo (Must-Have)
- ✅ Environment set up with GPU PyTorch
- ✅ Real Visium HD data preprocessed into `.npy` format
- ✅ Model trains for 3+ epochs without crashing
- ✅ Loss trends downward
- ✅ At least 1 gene comparison figure (H&E + true vs predicted)
- ✅ README with reproduction commands

### Target Demo (Realistic Goal)
- All of above, plus:
- ✅ 3 gene comparison figures (pattern/diffuse/sparse)
- ✅ Alignment check figure validates preprocessing
- ✅ Metrics CSV with clean per-epoch data
- ✅ Per-gene metric examples logged
- ✅ Config JSON documents training setup
- ✅ Future directions paragraph in README

### Stretch Goals (If Time Permits)
- Compare 8µm vs 16µm bin resolution
- Visualize multiple regions from same slide
- Brief comparison to CRC dataset (GI focus)
- Interactive figure (HTML/Plotly) for exploration

---

## Timeline Estimate

| Phase | Time Estimate | Cumulative |
|-------|---------------|------------|
| 1. Environment Setup | 0.5 hours | 0.5h |
| 2. Data Acquisition | 1 hour | 1.5h |
| 3. Format Understanding | 0.5-1 hour | 2-2.5h |
| 4. Preprocessing | 2-3 hours | 4-5.5h |
| 5. Training | 2-3 hours | 6-8.5h |
| 6. Visualization | 1-2 hours | 7-10.5h |
| 7. Documentation | 1 hour | 8-11.5h |
| **Buffer for debugging** | 2-4 hours | **10-15.5h** |

**Total: 10-16 hours of work** spread over 1-2 weeks, accounting for:
- Iterations and debugging
- Time to understand outputs
- Waiting for training to complete
- Buffer for unexpected issues

---

## Next Steps

1. ✅ Design approved and documented
2. → Set up git worktree for isolated development
3. → Create detailed implementation plan with step-by-step tasks
4. → Begin execution starting with environment setup
5. → Iterate with timeboxed debugging as needed
6. → Package deliverables for meeting with Dr. Huo

---

## Notes

- This document is a living design - adjustments may be made during implementation
- All simplifications and deviations from this plan should be documented in code comments
- Priority is shipping a working demo, not perfect reproduction of the paper
- Documentation quality is as important as technical execution for rotation success
