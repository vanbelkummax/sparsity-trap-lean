# PolyMaX Manuscript Generation Quick Reference

**Version**: 1.0 (Tasks 16-18 Complete)
**Date**: 2025-12-25

---

## Complete Pipeline Usage

### Step 1: Analyze Repository
```python
result = await call_tool("analyze_repo", {
    "repo_path": "/home/user/img2st-visium-hd",
    "mode": "auto"  # or "primary_research" or "review"
})
# Returns: synthesis_run_id, detected_mode, detected_domains
```

### Step 2: Ingest Results (Primary Research Only)
```python
result = await call_tool("ingest_results", {
    "synthesis_run_id": 1,
    "data_sources": []  # Auto-detects tables/ and figures/
})
# Returns: key_findings, tables, figures, constraints
```

### Step 3: Discover Literature
```python
# Targeted mode (primary research)
result = await call_tool("discover_literature", {
    "synthesis_run_id": 1,
    "mode": "targeted",
    "search_queries": [
        "Yuankai Huo Img2ST",
        "Poisson loss sparse data"
    ]
})

# Broad mode (review)
result = await call_tool("discover_literature", {
    "synthesis_run_id": 1,
    "mode": "broad"
})
# Returns: professors_added, papers_added, targeted_matches
```

### Step 4: Extract Papers
```python
result = await call_tool("extract_papers", {
    "synthesis_run_id": 1,
    "paper_ids": [],  # Empty = all papers
    "extraction_depth": "full"  # or "mid" or "high_only"
})
# Returns: papers_extracted, extraction_summary
```

### Step 5: Synthesize Domains
```python
result = await call_tool("synthesize_domains", {
    "synthesis_run_id": 1,
    "domain_ids": []  # Empty = all domains
})
# Returns: domains_synthesized, synthesis_summary
```

### Step 6: Generate Manuscript ✨
```python
result = await call_tool("generate_manuscript", {
    "synthesis_run_id": 1,
    "mode": "research",  # or "review", "extended-review", "hypothesis"
    "output_path": "/home/user/manuscripts/paper.tex"  # Optional
})
# Returns: manuscript_id, field, latex_preview, output_file
```

---

## Manuscript Modes

### 1. Primary Research (`mode: "research"`)
**Use when**: You have experimental data from your own repository

**Sections Generated**:
- **Abstract**: Concise summary of contribution
- **Introduction**: Problem motivation and solution
- **Methods**: Experimental setup and algorithms
- **Results**: Data-grounded findings with exact citations
- **Discussion**: Interpretation and future work

**Data Sources**:
- `main_finding` from `ingest_results`
- `domain_syntheses` for literature context
- Tables from `tables/` directory
- Figures from `figures/` directory

**Example Results Section**:
```latex
\section{Results}

Poisson loss significantly outperformed MSE loss across all metrics.
SSIM improved from 0.193 (MSE) to 0.605 (Poisson), representing a
213\% relative improvement (Table~\ref{tab:results}).

Gene-level analysis revealed that Poisson loss particularly benefits
sparse genes. For genes with expression in fewer than 10\% of spots,
SSIM improved by 312\% on average (Figure~\ref{fig:sparse_genes}).
```

### 2. Review Article (`mode: "review"`)
**Use when**: Synthesizing literature across domains

**Sections Generated**:
- **Abstract**: Review scope and key findings
- **Introduction**: Survey motivation and objectives
- **Methods**: Literature search and selection strategy
- **Results**: Synthesis across papers and domains
- **Discussion**: Cross-field insights and future directions

**Data Sources**:
- `domain_syntheses` from multiple domains
- Paper extractions (high/mid/low levels)
- Cross-field transfer opportunities

**Example Discussion Section**:
```latex
\section{Discussion}

Our synthesis reveals striking parallels between spike train modeling
(Pillow et al., 2008, PMID: 18563015) and sparse spatial transcriptomics.
Both domains exhibit 90-95\% sparsity, suggesting that Poisson-based
approaches proven effective in neuroscience (15-30\% RMSE improvement)
could transfer directly to spatial biology applications.
```

### 3. Extended Review (`mode: "extended-review"`)
Same as review, but signals intention for longer manuscript.

### 4. Hypothesis Generation (`mode: "hypothesis"`)
Primary research style with emphasis on forward-looking hypotheses.

---

## Field Detection

The system automatically selects the appropriate LaTeX template based on detected domains:

### Medical Imaging Template
**Domains**: spatial-transcriptomics, medical-imaging, digital-pathology, histology, pathology, microscopy

**Features**:
- IEEE two-column format
- Standard medical imaging packages
- Figure-heavy layout

### Genomics Template
**Domains**: genomics, sequencing, metagenomics, rna-seq, dna-seq, single-cell

**Features**:
- Biology-focused structure
- Sequence/alignment formatting
- Supplementary data support

### Machine Learning Template
**Domains**: deep-learning, machine-learning, neural-networks, computer-vision, ai

**Features**:
- Algorithm emphasis
- Performance metrics tables
- Architecture diagrams

---

## LaTeX Quality Standards (Huo Lab)

### Figure Placement
```latex
% ✅ GOOD - Top placement
\begin{figure}[t!]
\centering
\includegraphics[width=0.95\columnwidth]{figs/results.png}
\caption{Performance comparison}
\label{fig:results}
\end{figure}

% ❌ BAD - Here placement (breaks flow)
\begin{figure}[h]
\includegraphics{figs/results.png}
\caption{Bad placement}
\end{figure}
```

### Figure References
```latex
% ✅ GOOD - Non-breaking space
See Figure~\ref{fig:results} for details.
Table~\ref{tab:data} shows the results.

% ❌ BAD - Regular space (line break risk)
See Figure \ref{fig:results} for details.
Table \ref{tab:data} shows the results.
```

### Figure Width
```latex
% ✅ GOOD - 0.95 prevents margin bleed
\includegraphics[width=0.95\columnwidth]{fig.png}

% ❌ BAD - 1.0 causes overflow
\includegraphics[width=1.0\columnwidth]{fig.png}
```

### Wide Figures
```latex
% ✅ GOOD - Double-column span
\begin{figure*}[t!]
\centering
\includegraphics[width=0.95\textwidth]{wide.png}
\caption{Wide figure spanning both columns}
\label{fig:wide}
\end{figure*}
```

---

## Section Prompt Templates

### Using Section Prompts (Future Claude API)

```python
from prompts.section_prompts import (
    RESULTS_PROMPT,
    METHODS_PROMPT,
    DISCUSSION_PROMPT,
    INTRODUCTION_PROMPT,
    format_data_for_results_prompt,
    format_domain_syntheses_for_discussion
)
from anthropic import Anthropic

# Example: Generate Results section
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Format your data
data_summary = format_data_for_results_prompt(main_finding)

# Use the prompt template
prompt = RESULTS_PROMPT.format(data_summary=data_summary)

# Call Claude Opus 4.5
response = client.messages.create(
    model="claude-opus-4-5-20251101",
    max_tokens=4096,
    messages=[{"role": "user", "content": prompt}]
)

results_section = response.content[0].text
```

### Prompt Features

#### RESULTS_PROMPT
- Enforces exact value citations
- Requires table/figure references
- Constraint checking instructions
- Example: `"SSIM improved from 0.193 to 0.605 (Table~\ref{tab:results})"`

#### METHODS_PROMPT
- Algorithm/implementation detail extraction
- LaTeX equation formatting
- Hyperparameter documentation
- Example: `$L_{Poisson} = -\sum [y\log(\hat{y}) - \hat{y}]$`

#### DISCUSSION_PROMPT
- Cross-field synthesis
- Transfer learning identification
- Literature integration with PMIDs
- Example: `"Similar to spike trains (PMID: 18563015)..."`

#### INTRODUCTION_PROMPT
- Problem → Limitation → Solution → Result flow
- Contribution highlighting
- Forward references to sections

---

## Helper Functions

### Generate Figure Blocks

```python
from section_generator import generate_figure_block

# Single-column figure
fig = generate_figure_block(
    filename="figs/performance.png",
    caption="Model performance across datasets",
    label="fig:performance",
    wide=False,
    placement="t!"  # Default
)

# Double-column figure
wide_fig = generate_figure_block(
    filename="figs/architecture.png",
    caption="Complete model architecture",
    label="fig:arch",
    wide=True
)
```

### Validate LaTeX Quality

```python
from section_generator import check_figure_placement

latex_doc = """
\\begin{figure}[h]  % Bad placement
\\includegraphics{fig.png}
\\end{figure}

See Figure \\ref{fig:test} for details.  % Bad reference
"""

warnings = check_figure_placement(latex_doc)

for warning in warnings:
    print(f"⚠️  {warning}")

# Output:
# ⚠️  Found 1 figure(s) with [h] placement. Use [t!] or [b!] for professional typesetting.
# ⚠️  Found 1 reference(s) without non-breaking space. Use Figure~\ref{} not Figure \ref{}.
```

### Assemble Complete Manuscript

```python
from section_generator import assemble_manuscript

# After generating all sections via generate_manuscript
latex_doc = assemble_manuscript(
    synthesis_run_id=1,
    db_path="/path/to/papers.db",
    title="Poisson Loss for Sparse Spatial Transcriptomics",
    authors="Max Van Belkum, Yuankai Huo"
)

# Save to file
Path("/home/user/manuscripts/paper.tex").write_text(latex_doc)
```

---

## Compilation

### Compile LaTeX to PDF

```bash
# Standard compilation
pdflatex -interaction=nonstopmode paper.tex

# With bibliography
pdflatex paper.tex
bibtex paper
pdflatex paper.tex
pdflatex paper.tex

# Debug errors
pdflatex paper.tex 2>&1 | grep -A 5 "!"
```

---

## Database Schema Reference

### manuscripts Table
```sql
CREATE TABLE manuscripts (
    id INTEGER PRIMARY KEY,
    synthesis_run_id INTEGER NOT NULL,
    mode TEXT CHECK(mode IN ('research', 'review', 'extended-review', 'hypothesis')),
    latex_content TEXT,        -- Full LaTeX document
    abstract TEXT,             -- Abstract section only
    introduction TEXT,         -- Introduction section only
    methods TEXT,              -- Methods section only
    results TEXT,              -- Results section only
    discussion TEXT,           -- Discussion section only
    generated_at TIMESTAMP
);
```

### synthesis_runs Table
```sql
CREATE TABLE synthesis_runs (
    id INTEGER PRIMARY KEY,
    repo_path TEXT NOT NULL,
    mode TEXT CHECK(mode IN ('primary_research', 'review')),
    detected_domains TEXT,     -- JSON array
    main_finding TEXT,         -- JSON: key_findings, tables, figures
    status TEXT CHECK(status IN (
        'analyzing', 'discovering', 'extracting',
        'synthesizing', 'writing', 'complete'
    ))
);
```

---

## Common Patterns

### Pattern 1: Quick Manuscript from Existing Data

```python
# If you already have a synthesis_run with data
result = await call_tool("generate_manuscript", {
    "synthesis_run_id": 42,
    "mode": "research",
    "output_path": "/home/user/paper.tex"
})

print(result["latex_preview"])
```

### Pattern 2: Full Pipeline from Repository

```python
# Start from scratch
results = []

# Step 1: Analyze
r1 = await call_tool("analyze_repo", {
    "repo_path": "/home/user/my-project"
})
run_id = json.loads(r1[0].text)["synthesis_run_id"]

# Step 2: Ingest
r2 = await call_tool("ingest_results", {
    "synthesis_run_id": run_id
})

# Step 3: Literature
r3 = await call_tool("discover_literature", {
    "synthesis_run_id": run_id,
    "mode": "targeted",
    "search_queries": ["relevant query"]
})

# Step 4: Extract
r4 = await call_tool("extract_papers", {
    "synthesis_run_id": run_id,
    "extraction_depth": "full"
})

# Step 5: Synthesize
r5 = await call_tool("synthesize_domains", {
    "synthesis_run_id": run_id
})

# Step 6: Generate manuscript
r6 = await call_tool("generate_manuscript", {
    "synthesis_run_id": run_id,
    "mode": "research"
})

final = json.loads(r6[0].text)
print(f"Manuscript generated: {final['manuscript_id']}")
```

### Pattern 3: Iterative Section Refinement

```python
# Generate individual sections first
sections = ["abstract", "introduction", "methods", "results", "discussion"]

for section in sections:
    result = await call_tool("generate_section", {
        "synthesis_run_id": 42,
        "section": section,
        "mode": "primary_research"
    })
    print(f"Generated {section}")

# Then assemble
final = await call_tool("generate_manuscript", {
    "synthesis_run_id": 42,
    "mode": "research"
})
```

---

## Troubleshooting

### Issue: "No manuscript found for synthesis run"
**Solution**: Run through steps 1-5 before calling `generate_manuscript`

### Issue: "No such column: latex_content"
**Solution**: Database schema outdated. Recreate from `schema.sql`

### Issue: LaTeX compilation errors
**Solution**: Run `check_figure_placement()` to validate formatting

### Issue: Empty sections generated
**Solution**: Ensure `main_finding` and `domain_syntheses` exist in database

### Issue: Wrong template selected
**Solution**: Check `detected_domains` - add relevant keywords to field detection

---

## Future Enhancements

### Planned Features:
1. Claude Opus 4.5 API integration for section generation
2. Direct MCP connection to latex-architect server
3. Automatic BibTeX generation from paper citations
4. Table generation from CSV data
5. Manuscript versioning and diff tracking
6. Interactive section editing via MCP
7. Figure extraction from repository
8. Automatic PMID lookup and citation formatting

### Migration Path:
Current MVP uses template-based generation. All prompts are ready for Claude API integration with minimal code changes. Simply replace template generation with API calls using existing prompt templates.

---

**Need Help?** Check `/home/user/mcp_servers/polymax-synthesizer/TASK16_17_18_COMPLETION.md` for detailed implementation notes.
