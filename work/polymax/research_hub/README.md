# Research Hub - Central Knowledge & Hypothesis Tracker

**Purpose**: Single source of truth for all research hypotheses, experiments, papers, and synthesis runs.

---

## Quick Start

### Get Started in 5 Minutes

1. **Import key papers** (for 2um sparsity trap):
   ```bash
   cd /home/user/work/polymax/research_hub
   ./scripts/import_2um_papers.sh
   ```

2. **View existing hypotheses**:
   ```bash
   # List by priority (EV score)
   cd hypotheses/pending
   grep -h "ev_estimate:" *.yaml | sort -t: -k2 -rn

   # Read highest priority hypothesis
   cat H_20241224_007.yaml  # TICON (EV 8.5)
   ```

3. **Test a hypothesis**:
   ```bash
   # Move to active
   mv pending/H_20241224_007.yaml active/

   # Run experiment (follow minimal_test in YAML)
   # Update validation section with results

   # Move to validated or rejected
   mv active/H_20241224_007.yaml validated/
   ```

4. **Generate new hypotheses**:
   ```bash
   # In Claude Code
   /research-synthesis

   # Or use create script
   python scripts/create_hypothesis.py \
     --claim "..." \
     --minimal-test "..." \
     --kill-shot "..." \
     --ev 7.0
   ```

### Quick Commands

```bash
# Paper management
./scripts/manage_papers.py list                    # List all papers
./scripts/manage_papers.py search "TICON"          # Search papers
./scripts/manage_papers.py add-arxiv "2512.21331"  # Add new paper

# Hypothesis queries
grep -r "TICON" hypotheses/ --include="*.yaml"     # Find hypotheses mentioning TICON
grep -l "project: 2um" pending/*.yaml              # List 2um hypotheses

# Create new hypothesis
python scripts/create_hypothesis.py --help         # See options
```

---

## Directory Structure

```
research_hub/
├── hypotheses/           # All hypotheses with metadata
│   ├── active/          # Currently being tested
│   ├── validated/       # Experimentally validated
│   ├── rejected/        # Failed kill-shot criteria
│   └── pending/         # Generated but not yet tested
│
├── experiments/         # Experiment logs and results
│   ├── YYYY-MM-DD_experiment_name/
│   │   ├── setup.yaml   # Experiment configuration
│   │   ├── log.md       # Daily notes and observations
│   │   ├── results/     # Outputs, checkpoints, figures
│   │   └── analysis.md  # Final analysis and conclusions
│
├── papers/              # Full papers and metadata
│   ├── pdfs/           # Downloaded PDFs
│   ├── metadata/       # Extracted metadata (JSON)
│   └── notes/          # Reading notes and annotations
│
├── knowledge_base/      # Synthesized knowledge
│   ├── insights/       # Cross-field insights
│   ├── methods/        # Reusable methods catalog
│   └── collaborations/ # Collaborator tracking
│
└── synthesis_runs/      # PolyMaX synthesis outputs
    └── YYYY-MM-DD_run_name/
        ├── papers.json
        ├── hypotheses.json
        ├── insights.md
        └── memory_snapshot.json
```

---

## Hypothesis Tracking System

### Hypothesis Metadata Schema

```yaml
id: H_YYYYMMDD_NNN
status: pending | active | validated | rejected
created_date: YYYY-MM-DD
updated_date: YYYY-MM-DD
source: paper | synthesis_run | manual
project: img2st | polymax | other

hypothesis:
  claim: "Specific, testable statement"
  minimal_test: "Simplest experiment to validate"
  kill_shot: "Specific failure condition"
  ev_estimate: 0.0-10.0
  rationale: "Why this should work (with citations)"

paper_sources:
  - arxiv_id: "2512.21331v1"
    title: "TICON"
    relevance: "Addresses spatial context gap"

cross_field_insights:
  - domain: "NLP"
    method: "BERT masked autoencoding"
    transfer: "Apply to gene expression prediction"

experiment:
  started: YYYY-MM-DD | null
  completed: YYYY-MM-DD | null
  results_path: experiments/2024-12-24_ticon_integration/

validation:
  tested: true | false
  outcome: success | failure | partial | null
  metrics:
    - name: "Pearson correlation"
      baseline: 0.40
      achieved: 0.52
      improvement: "+30%"
  kill_shot_triggered: false
  notes: "Summary of experimental findings"

next_steps:
  - "Action item 1"
  - "Action item 2"

related_hypotheses:
  - H_20241224_001  # TICON unification
  - H_20241224_002  # Data efficiency
```

---

## Usage Patterns

### 1. Generate Hypotheses (via PolyMaX)
```bash
cd /home/user/work/polymax
source .venv/bin/activate

# Run synthesis
polymax synthesize --mode interactive

# Store results
polymax store-synthesis response.json

# Export to research hub
python scripts/export_to_research_hub.py
```

### 2. Start an Experiment
```bash
# Create experiment directory
python research_hub/scripts/create_experiment.py \
    --hypothesis H_20241224_001 \
    --name "ticon_integration_test"

# This creates:
# research_hub/experiments/2024-12-24_ticon_integration_test/
#   ├── setup.yaml      (auto-populated from hypothesis)
#   ├── log.md          (experiment journal)
#   └── results/        (for outputs)
```

### 3. Update Hypothesis Status
```bash
python research_hub/scripts/update_hypothesis.py \
    --id H_20241224_001 \
    --status active \
    --experiment 2024-12-24_ticon_integration_test
```

### 4. Record Results
```bash
python research_hub/scripts/record_results.py \
    --experiment 2024-12-24_ticon_integration_test \
    --metric "pearson_correlation" \
    --baseline 0.40 \
    --achieved 0.52

# Automatically checks kill-shot criteria
# Updates hypothesis status if validated/rejected
```

### 5. Query Knowledge Base
```bash
# Find all active hypotheses
python research_hub/scripts/query.py --status active

# Find hypotheses related to "spatial context"
python research_hub/scripts/query.py --keyword "spatial context"

# Find validated hypotheses with high EV
python research_hub/scripts/query.py --validated --ev-min 7.0

# Get full history for a hypothesis
python research_hub/scripts/get_hypothesis.py --id H_20241224_001
```

---

## Integration with PolyMaX

PolyMaX automatically:
1. Stores new papers in `papers/metadata/`
2. Creates hypothesis YAML files in `hypotheses/pending/`
3. Updates memory MCP with knowledge graph
4. Exports synthesis runs to `synthesis_runs/`

Manual steps:
1. Download paper PDFs to `papers/pdfs/` (when available)
2. Move hypotheses from `pending/` to `active/` when starting experiments
3. Update hypothesis metadata as experiments progress
4. Archive completed experiments

---

## Best Practices

### Hypothesis Lifecycle

```
pending → active → [validated | rejected]
                ↘ partial → active (iterate)
```

### Experiment Logging

**Daily log.md entries**:
```markdown
## 2024-12-24

### Setup
- Downloaded HEST-Bench dataset (10 slides)
- Installed TICON dependencies
- Verified baseline Img2ST-Net performance: PCC=0.40

### Work Done
- Integrated TICON contextualizer into Img2ST encoder
- Initial training: 10 epochs
- VRAM usage: 38GB (within 40GB limit ✓)

### Observations
- Training slower than expected (15 min/epoch vs 10 min baseline)
- Loss converging smoothly
- Visual inspection shows better spatial coherence

### Issues
- TICON weights not publicly available - had to pretrain from scratch
- Memory bottleneck during validation (need to reduce batch size)

### Next Steps
- Complete 50-epoch training
- Run full evaluation on held-out test set
- If PCC > 0.48 (+20%), proceed to full benchmark
```

### Cross-Referencing

Always link:
- Hypotheses → Experiments → Results
- Papers → Hypotheses they inspired
- Insights → Multiple hypotheses they inform

Use consistent IDs:
- Hypotheses: `H_YYYYMMDD_NNN`
- Experiments: `E_YYYYMMDD_name`
- Papers: ArXiv ID or PMID
- Insights: `I_YYYYMMDD_NNN`

---

## Recursive Self-Improvement

### Feedback Loop

1. **Synthesis** → Generate hypotheses from papers
2. **Experiment** → Test hypotheses, collect results
3. **Analysis** → Extract insights from results
4. **Update** → Feed insights back to PolyMaX knowledge base
5. **Repeat** → Next synthesis cycle uses updated knowledge

### Example

```
PolyMaX finds TICON paper
  → Generates H_001: "TICON improves Img2ST by 12-18%"
  → Test in experiment E_001
  → Result: +15% improvement (validated!)
  → Extract insight: "Transformer contextualization works for ST"
  → Update memory MCP with validation
  → Next synthesis: Prioritize other transformer methods
                   (attention mechanisms, positional encoding, etc.)
```

### Agentic Work

**Autonomous actions** (when configured):
1. Check arXiv daily for new papers matching keywords
2. Run Intern filtering automatically
3. Generate synthesis prompts for high-scoring papers
4. Email user with weekly digest of new hypotheses
5. Monitor experiment logs for kill-shot triggers
6. Auto-update hypothesis status based on results
7. Generate monthly research summaries

---

## Current Projects

### 1. 2um Sparsity Trap
**Problem**: MSE collapses on 2um Visium HD data (95% zeros)
**Solution**: Poisson loss (2.7x SSIM improvement proven)
**Next**: Explore other distributions, TICON integration, physics priors

**Active Hypotheses**:
- H_20241224_005: Negative Binomial NB2 for overdispersion
- H_20241224_006: Zero-Inflated Poisson for structural zeros
- H_20241224_007: TICON spatial context for 2um
- H_20241224_008: Physics conservation laws

**Experiments**:
- E_20241224_mse_vs_poisson (COMPLETED - validated Poisson superiority)
- E_TBD_negative_binomial (PENDING)

### 2. Cross-Field Transfers
**Domains**: NLP (BERT), Physics (PINNs), Recommender Systems (Poisson factorization)
**Status**: Literature review complete, prototypes pending

---

## Maintenance

### Weekly
- Review active experiments, update logs
- Move completed hypotheses to validated/rejected
- Sync memory MCP with new insights
- Run PolyMaX synthesis on new papers

### Monthly
- Generate research summary report
- Archive old experiments
- Clean up pending hypotheses (>90 days → archive or activate)
- Update cross-field insights catalog

### Quarterly
- Full knowledge base audit
- Identify recurring patterns across experiments
- Update PolyMaX prompts based on validated insights
- Plan next research directions based on EV rankings

---

**Created**: 2024-12-24
**Version**: 1.0
**Owner**: Max Van Belkum
**Lab**: Huo Lab, Vanderbilt University
