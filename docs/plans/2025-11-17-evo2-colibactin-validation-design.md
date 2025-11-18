# Evo2-Based Validation of Colibactin Detection Findings

**Date:** November 17, 2025
**Author:** AI-assisted design
**Status:** Approved for implementation
**Related Work:** CLB island detection toolkit (github.com/vanbelkummax/clb-detection-toolkit)

## Overview

This document describes the design for integrating Evo2 (DNA foundation model) into the colibactin (CLB) detection pipeline to validate key findings from the DIAMOND-based metagenomics analysis of 113 infant gut microbiome samples.

## Background

### Key Findings to Validate

From the completed CLB island analysis (95% identity threshold):
- **Primary finding**: 4.6x higher CLB burden in Neo-ABX vs No-ABX infants (p=0.00444)
- **Complete islands**: 33.3% Neo-ABX vs 12.5% No-ABX (OR=3.43, p=0.016)
- **High burden outliers**: 18.2% Neo-ABX vs 2.5% No-ABX with ≥50,000 reads/10M (OR=7.42, p=0.008)

### Validation Goal

Use Evo2's biological plausibility scoring to independently verify that detected CLB sequences are:
1. Genuinely functional at the chosen 95% identity threshold
2. Not artifacts in complete island samples
3. Correlated with abundance (high burden = high quality)

## Architecture

### Pipeline 4: Evo2 Validation Framework

Three-phase validation strategy running post-hoc on existing DIAMOND results:

```
Pipeline 4 (Evo2 Validation)
│
├── Phase A: Identity Threshold Validation (~2 hours)
│   ├── Input: 21 complete island samples
│   ├── Extract: ~150-200 sequences at 90-94.9% and 95-100% identity
│   ├── Test: Does 95%+ have higher Evo2 scores than 90-94.9%?
│   └── Validates: 95% threshold choice
│
├── Phase B: Complete Island Validation (~4 hours)
│   ├── Input: All 21 complete island samples (11 Neo-ABX, 10 No-ABX)
│   ├── Extract: 378 sequences (18 genes × 21 samples)
│   ├── Test 1: Are all islands functionally valid? (vs threshold)
│   ├── Test 2: Are Neo-ABX and No-ABX islands similar quality?
│   └── Validates: Complete island detections are real biology
│
└── Phase C: Abundance-Quality Correlation (~3 hours)
    ├── Input: 40 samples stratified by CLB burden (RPM)
    ├── Extract: 200-400 sequences across burden spectrum
    ├── Test: Does Evo2 score correlate with log(RPM)?
    └── Validates: High abundance reflects functional CLB content
```

## Data Sources

### Input Data Locations

**Reference sequences:**
- `/mnt/x/validation_clbB/proteins/clb_island_nucleotide.fasta` - 50kb IHE3034 CLB island
- `/mnt/x/validation_clbB/proteins/clb_island_complete.fasta` - 19 CLB protein sequences

**Sample data:**
- `/tmp/clean_results.tsv` - 86 samples with gene counts and screening results
- `/mnt/y/aim1b_analysis_v1.0/.worktrees/read-centric/assemblies/` - Assembly FASTAs
- `/mnt/x/validation_clbB/week6_fastqs/{Neo_ABX,No_ABX}/` - Raw paired-end reads
- `/mnt/y/aim1b_analysis_v1.0/.worktrees/read-centric/clb_recovery_analysis/screening/` - DIAMOND hits

**Analysis results:**
- `/mnt/x/final_whole_island_102025_analysis/raw_data/clb_95_identity_summary.csv` - Sample-level statistics

### Output Structure

```
/mnt/y/aim1b_analysis_v1.0/.worktrees/read-centric/evo2_validation/
├── input_sequences/
│   ├── phase_a_identity/
│   │   ├── identity_90-94/        # Lower identity sequences
│   │   └── identity_95-100/       # Higher identity sequences
│   ├── phase_b_complete_islands/
│   │   ├── neo_abx/               # 11 samples × 18 genes = 198 sequences
│   │   └── no_abx/                # 10 samples × 18 genes = 180 sequences
│   └── phase_c_abundance/
│       ├── zero_burden/           # 10 samples, negative controls
│       ├── low_burden/            # 10 samples, RPM 1-1000
│       ├── moderate_burden/       # 10 samples, RPM 1000-50000
│       └── high_burden/           # 10 samples, RPM >50000
├── evo2_scores/
│   ├── phase_a_scores.tsv         # Columns: sequence_id, identity_range, evo2_score
│   ├── phase_b_scores.tsv         # Columns: sample_id, group, gene, evo2_score
│   └── phase_c_scores.tsv         # Columns: sample_id, burden_stratum, mean_evo2_score, clb_rpm
├── statistical_tests/
│   ├── phase_a_identity_validation.txt
│   ├── phase_b_functional_validation.txt
│   └── phase_c_abundance_correlation.txt
├── figures/
│   ├── phase_a_identity_boxplot.pdf
│   ├── phase_b_group_comparison.pdf
│   ├── phase_c_abundance_scatter.pdf
│   └── combined_validation_summary.pdf
├── logs/
│   ├── sequence_extraction.log
│   ├── evo2_execution.log
│   └── statistical_analysis.log
└── EVO2_VALIDATION_REPORT.md
```

## Phase A: Identity Threshold Validation

### Objective
Verify that 95% identity threshold captures functionally superior sequences compared to 90-94.9% range.

### Sample Selection
- **Source**: All 21 samples with complete CLB islands (gold standard)
  - 11 Neo-ABX: SRR24058584, SRR24058602, SRR24058609, SRR24058646, SRR24058653, SRR24058658, SRR24058668, SRR24058681, SRR24058694, SRR24058697, SRR24058699
  - 10 No-ABX: (from clean_results.tsv with 18 genes)
- **Rationale**: Complete islands = known functional CLB, avoids false positives

### Sequence Extraction

**Method**: Read-based extraction from DIAMOND hits
1. Parse DIAMOND alignment files from `/screening/` directory
2. Filter hits by identity: 90-94.9% vs 95-100%
3. Extract read IDs from each identity range
4. Pull sequences from FASTQ using `seqtk subseq`
5. Sample ~5-10 sequences per identity range per sample (target 150-200 total)

**Implementation**:
```bash
# For each sample:
# 1. Get read IDs from DIAMOND hits in identity ranges
grep "^SRR" sample_diamond.tsv | awk '$3 >= 90 && $3 < 95' | cut -f1 > reads_90-94.txt
grep "^SRR" sample_diamond.tsv | awk '$3 >= 95' | cut -f1 > reads_95-100.txt

# 2. Extract sequences from FASTQ
seqtk subseq sample_1.fastq.gz reads_90-94.txt > identity_90-94/sample.fasta
seqtk subseq sample_1.fastq.gz reads_95-100.txt > identity_95-100/sample.fasta
```

### Evo2 Scoring

**Process**:
1. Load Evo2 model in `evo2` conda environment
2. Process sequences in 50-sequence batches (memory management for 24GB VRAM)
3. Score each sequence: `evo2_score = model.score_sequence(dna_seq)`
4. Record: `sequence_id, sample_id, identity_range, evo2_score`

**Expected runtime**: ~2 hours for 150-200 sequences

### Statistical Analysis

**Test**: Two-sample t-test (one-tailed)
- **H₀**: mean(Evo2_95-100%) ≤ mean(Evo2_90-94.9%)
- **H₁**: mean(Evo2_95-100%) > mean(Evo2_90-94.9%)
- **Expected**: p < 0.05, mean difference >0

**Implementation**:
```python
from scipy import stats
scores_95_100 = df[df['identity_range'] == '95-100']['evo2_score']
scores_90_94 = df[df['identity_range'] == '90-94']['evo2_score']
t_stat, p_value = stats.ttest_ind(scores_95_100, scores_90_94, alternative='greater')
```

**Validation criteria**:
- ✓ Pass if p < 0.05 and mean_95-100 > mean_90-94
- ✗ Fail if p ≥ 0.05 or mean_95-100 ≤ mean_90-94

## Phase B: Complete Island Functional Validation

### Objective
1. Verify complete islands are functionally valid (not assembly artifacts)
2. Confirm no systematic bias between Neo-ABX and No-ABX groups

### Sample Selection
- **All 21 complete island samples** (11 Neo-ABX, 10 No-ABX)
- **378 total sequences**: 18 genes × 21 samples

### Sequence Extraction

**Method**: Assembly-based extraction using Prodigal gene predictions

**Process**:
1. Use assembly FASTAs from `/assemblies/` or `/optimized_assemblies_*/`
2. Run Prodigal gene prediction (or use existing predictions from screening)
3. Match predicted CDS to CLB genes using DIAMOND coordinates
4. Extract nucleotide sequences for all 18 CLB genes per sample
5. Organize by group: `neo_abx/` vs `no_abx/`

**Implementation**:
```bash
# For each sample:
# 1. Run Prodigal if needed
prodigal -i assembly.fasta -d genes.fna -a proteins.faa -p meta

# 2. Extract CLB genes using DIAMOND hit coordinates
# Parse DIAMOND screening results for gene positions
# Extract corresponding sequences from genes.fna

# 3. Separate by exposure group
if [[ "$GROUP" == "Neo-ABX" ]]; then
    cp genes.fna phase_b_complete_islands/neo_abx/${SAMPLE}_clb_genes.fasta
else
    cp genes.fna phase_b_complete_islands/no_abx/${SAMPLE}_clb_genes.fasta
fi
```

### Evo2 Scoring

**Process**:
1. Score all 378 sequences (batch processing)
2. Record: `sample_id, exposure_group, gene_name, evo2_score`
3. Calculate summary statistics per sample and per group

**Expected runtime**: ~4 hours for 378 sequences

### Statistical Analysis

**Test 1: Absolute Functional Validation**
- **Establish functional threshold first**: Score reference CLB genes from `/proteins/clb_island_nucleotide.fasta`
- **Test**: One-sample t-test
  - H₀: mean(Evo2_all_378) ≤ functional_threshold
  - H₁: mean(Evo2_all_378) > functional_threshold
  - Expected: p < 0.05, confirms islands are functional

**Test 2: Group Comparison (No Bias)**
- **Test**: Two-sample t-test (two-tailed)
  - H₀: mean(Evo2_NeoABX) = mean(Evo2_NoABX)
  - H₁: mean(Evo2_NeoABX) ≠ mean(Evo2_NoABX)
  - Expected: p > 0.05, confirms no systematic bias

**Implementation**:
```python
from scipy import stats

# Test 1: Absolute validation
all_scores = df['evo2_score']
t_stat, p_value = stats.ttest_1samp(all_scores, functional_threshold, alternative='greater')

# Test 2: Group comparison
neo_abx_scores = df[df['group'] == 'Neo-ABX']['evo2_score']
no_abx_scores = df[df['group'] == 'No-ABX']['evo2_score']
t_stat, p_value = stats.ttest_ind(neo_abx_scores, no_abx_scores)
```

**Validation criteria**:
- ✓ Pass if Test 1 p < 0.05 AND Test 2 p > 0.05
- ⚠ Warning if only one test passes
- ✗ Fail if both tests fail

## Phase C: Abundance-Quality Correlation Validation

### Objective
Verify that high CLB burden correlates with high Evo2 functional scores (high abundance = high quality, not just noise).

### Sample Selection

**Stratified sampling**: 40 samples across burden spectrum
- **Zero burden** (CLB RPM = 0): 10 samples → Negative controls
- **Low burden** (CLB RPM 1-1,000): 10 samples
- **Moderate burden** (CLB RPM 1,000-50,000): 10 samples
- **High burden** (CLB RPM >50,000): 10 samples (includes 6 extreme outliers)

**Source**: `/mnt/x/final_whole_island_102025_analysis/raw_data/clb_95_identity_summary.csv`

### Sequence Extraction

**Method**: Read-based extraction from DIAMOND hits (like Phase A)

**Process**:
1. For each sample, extract 5-10 representative CLB sequences from DIAMOND hits
2. Use `seqtk` to pull from FASTQ files
3. Total: 200-400 sequences across all strata

**Stratification logic**:
```python
import pandas as pd
import numpy as np

df = pd.read_csv('clb_95_identity_summary.csv')

# Define strata
df['burden_stratum'] = pd.cut(
    df['Normalized_Burden_per_10M'],
    bins=[0, 1, 1000, 50000, np.inf],
    labels=['zero', 'low', 'moderate', 'high']
)

# Sample 10 from each stratum
stratified_samples = df.groupby('burden_stratum').sample(n=10, random_state=42)
```

### Evo2 Scoring

**Process**:
1. Score all extracted sequences
2. Calculate mean Evo2 score per sample
3. Merge with CLB RPM data

**Expected runtime**: ~3 hours for 200-400 sequences

### Statistical Analysis

**Test**: Correlation analysis

**Pearson correlation** (linear relationship):
```python
from scipy.stats import pearsonr
r, p = pearsonr(df['mean_evo2_score'], np.log10(df['clb_rpm'] + 1))
```

**Spearman correlation** (monotonic relationship, robust to outliers):
```python
from scipy.stats import spearmanr
rho, p = spearmanr(df['mean_evo2_score'], df['clb_rpm'])
```

**Expected results**:
- Pearson r > 0.5, p < 0.01
- Spearman ρ > 0.5, p < 0.01

**Validation criteria**:
- ✓ Pass if Spearman p < 0.01 and ρ > 0.4 (moderate-strong positive correlation)
- ⚠ Warning if 0.2 < ρ < 0.4 (weak correlation)
- ✗ Fail if ρ < 0.2 or p ≥ 0.01

## Technical Implementation Details

### Dependencies

**Required software**:
- Evo2 model (installed at `/mnt/y/AI_models/evo2_install/`)
- Python 3.12+ (`evo2` conda environment)
- BioPython for sequence parsing: `pip install biopython`
- seqtk for FASTQ extraction: `conda install -c bioconda seqtk`
- Prodigal for gene prediction: `/home/user/mamba/envs/mag/bin/prodigal`

**Python packages**:
- numpy, scipy, pandas (statistical analysis)
- matplotlib, seaborn (visualization)
- evo2 (DNA foundation model)

### Evo2 API Usage

**Initialization**:
```python
from evo2 import Evo2
import torch

# Load model
model = Evo2('evo2_7b')

# Verify GPU availability
assert torch.cuda.is_available(), "CUDA required for Evo2"
```

**Sequence scoring**:
```python
def score_sequences_batch(sequences, batch_size=50):
    """Score sequences in batches to manage 24GB VRAM."""
    scores = []
    for i in range(0, len(sequences), batch_size):
        batch = sequences[i:i+batch_size]
        for seq in batch:
            # Evo2 expects uppercase DNA
            seq_upper = seq.upper()
            # Score sequence (returns biological plausibility)
            score = model.score_sequence(seq_upper)
            scores.append(score)
    return scores
```

**Memory management**:
- Batch size: 50 sequences (conservative for 24GB VRAM)
- Expected VRAM usage: ~14GB per batch
- Headroom: ~10GB available for OS/overhead

### Execution Environment

**Working directory**:
```bash
cd /mnt/y/aim1b_analysis_v1.0/.worktrees/read-centric
export EVO2_DIR="evo2_validation"
```

**Conda environment**:
```bash
source /home/user/miniforge3/etc/profile.d/conda.sh
conda activate evo2
```

**GPU verification**:
```bash
nvidia-smi  # Confirm RTX 5090 24GB available
```

## Output and Reporting

### Generated Outputs

**Phase A outputs**:
- `phase_a_scores.tsv`: Sequence-level Evo2 scores by identity range
- `phase_a_identity_boxplot.pdf`: Boxplot comparing 90-94.9% vs 95-100%
- `phase_a_identity_validation.txt`: Statistical test results

**Phase B outputs**:
- `phase_b_scores.tsv`: Gene-level Evo2 scores by sample and group
- `phase_b_group_comparison.pdf`: Violin plot of Neo-ABX vs No-ABX scores
- `phase_b_functional_validation.txt`: Both statistical tests (absolute + comparative)

**Phase C outputs**:
- `phase_c_scores.tsv`: Sample-level mean Evo2 scores with CLB RPM
- `phase_c_abundance_scatter.pdf`: Scatter plot of Evo2 score vs log(RPM)
- `phase_c_abundance_correlation.txt`: Correlation analysis results

### Final Validation Report

**Markdown report**: `EVO2_VALIDATION_REPORT.md`

**Sections**:
1. Executive Summary
2. Phase A Results: Identity Threshold Validation
3. Phase B Results: Complete Island Validation
4. Phase C Results: Abundance-Quality Correlation
5. Overall Conclusions
6. Supplementary Data

**Pass/Fail criteria**:
- ✅ **PASS**: All three phases meet validation criteria
- ⚠️ **PARTIAL**: 2/3 phases pass
- ❌ **FAIL**: ≤1 phase passes

## Timeline and Milestones

**Total estimated runtime**: 9 hours

**Breakdown**:
1. **Setup** (30 min): Directory creation, dependency verification
2. **Phase A** (2 hours): Identity threshold validation
3. **Phase B** (4 hours): Complete island validation
4. **Phase C** (3 hours): Abundance correlation validation
5. **Reporting** (30 min): Generate final report and figures

**Milestones**:
- [ ] M1: Directory structure created, dependencies verified
- [ ] M2: Phase A complete, identity threshold validated
- [ ] M3: Phase B complete, complete islands validated
- [ ] M4: Phase C complete, abundance correlation validated
- [ ] M5: Final validation report generated

## Success Criteria

### Scientific Validation

**Primary success** (all must be true):
1. ✅ Phase A: 95% identity sequences have significantly higher Evo2 scores (p < 0.05)
2. ✅ Phase B: Complete islands are functionally valid AND no group bias
3. ✅ Phase C: Positive correlation between Evo2 score and CLB burden (ρ > 0.4, p < 0.01)

**Interpretation**:
- If all pass → DIAMOND findings are validated by independent DNA foundation model
- If 2/3 pass → Findings are mostly robust, investigate failing phase
- If ≤1 pass → Serious concerns about DIAMOND detection accuracy

### Technical Success

**Implementation milestones**:
- [ ] Sequence extraction scripts work correctly
- [ ] Evo2 scoring runs without OOM errors
- [ ] Statistical tests execute properly
- [ ] Figures are publication-quality
- [ ] Report is comprehensive and clear

## Risk Mitigation

### Known Limitations

**Evo2 constraints**:
- Trained on prokaryotic genomes (300B tokens, 2.7M genomes) - CLB should be well-represented
- Practical sequence length: 50-5000bp - matches typical read/gene lengths
- 24GB VRAM limit - mitigated by batch processing

**Data constraints**:
- Read extraction depends on DIAMOND alignment quality
- Assembly extraction depends on Prodigal accuracy
- Some samples may have insufficient sequences for stratification

### Contingency Plans

**If Phase A fails**:
- Check if 95% threshold is too stringent (test 90% vs 85%)
- Verify sequence extraction is pulling correct reads
- Try assembly-based extraction instead of read-based

**If Phase B fails (low scores)**:
- Re-run with reference CLB sequences to calibrate threshold
- Check if Evo2 is properly scoring bacterial DNA vs artifacts

**If Phase B fails (group difference)**:
- Investigate if Neo-ABX samples have different sequence quality issues
- Check for batch effects in sequencing/assembly

**If Phase C fails**:
- Verify RPM calculations are correct
- Check if zero-burden samples are contaminating correlation
- Try log-transformation or rank-based methods

## Related Documentation

- [CLB Detection Toolkit README](https://github.com/vanbelkummax/clb-detection-toolkit/README.md)
- [Final Analysis Results](/mnt/x/final_whole_island_102025_analysis/README.md)
- [Evo2 Model Documentation](/home/user/work/MODEL_USE_CASES_AND_DEMOS.md)
- [DIAMOND Pipeline Documentation](pipeline2_diamond/README.md)

## Appendix: Command Reference

### Quick Commands

**Activate Evo2 environment**:
```bash
conda activate evo2
```

**Run sequence extraction** (example for Phase A):
```bash
python scripts/extract_sequences_phase_a.py \
    --input /tmp/clean_results.tsv \
    --output evo2_validation/input_sequences/phase_a_identity/
```

**Run Evo2 scoring**:
```bash
python scripts/run_evo2_scoring.py \
    --phase A \
    --input evo2_validation/input_sequences/phase_a_identity/ \
    --output evo2_validation/evo2_scores/phase_a_scores.tsv
```

**Run statistical analysis**:
```bash
python scripts/statistical_analysis.py \
    --phase A \
    --scores evo2_validation/evo2_scores/phase_a_scores.tsv \
    --output evo2_validation/statistical_tests/
```

**Generate report**:
```bash
python scripts/generate_validation_report.py \
    --output evo2_validation/EVO2_VALIDATION_REPORT.md
```

---

**End of Design Document**
