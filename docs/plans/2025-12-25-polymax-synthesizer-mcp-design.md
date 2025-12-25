# PolyMaX Synthesizer MCP: Academic Manuscript Generation System

**Date**: 2025-12-25
**Author**: Max Van Belkum
**Status**: Design Complete

## Executive Summary

PolyMaX Synthesizer is a dual-mode MCP server that generates publication-ready academic manuscripts from GitHub repositories. It combines deep literature synthesis with precise citation of original findings, supporting both primary research papers and comprehensive reviews.

**Key Innovation**: Conversational multi-stage workflow where the user directs Claude, who orchestrates subagents for parallel literature analysis while maintaining ground truth from experimental results.

**Companion System**: Extends Vanderbilt Professors MCP into a growing academic knowledge graph, scaling from 7 faculty → 1000+ professors across disciplines.

---

## Architecture Overview

### Two Operating Modes

**Mode 1: Primary Research (Results-First)**
- Input: GitHub repo with `tables/*.csv`, `figures/`, experimental results
- Process: Ingest results → targeted literature → manuscript generation
- Output: IMRaD manuscript citing YOUR specific findings
- Example: "The Sparsity Trap" paper (SSIM 0.542 vs 0.200, p<0.001)

**Mode 2: Review/Synthesis (Literature-First)**
- Input: Research question or topic
- Process: Domain discovery → literature harvesting → synthesis → manuscript
- Output: Comprehensive review with 100-200 citations
- Example: "Loss Functions for Sparse Count Data: A Cross-Disciplinary Review"

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                  PolyMaX Synthesizer MCP                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Analyze Repo] ──→ [Ingest Results] ──→ [Generate Draft]  │
│         │                                        ↑           │
│         └──→ [Discover Literature] ──────────────┘          │
│                      ↓                                       │
│              [Extract Papers]                               │
│                      ↓                                       │
│           [Synthesize Domains]                              │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│              Vanderbilt Professors MCP (Extended)           │
│  • Professors DB (7 → 1000+ faculty)                       │
│  • Papers DB (212 → 10,000+ papers, full-text BLOB)        │
│  • Extractions DB (hierarchical: claims, stats, methods)   │
│  • Domain Syntheses (reusable cross-paper insights)        │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Extended Vanderbilt Professors MCP

Extends existing structure with new tables in `/home/user/vanderbilt_professors_mcp/data/professors.db`:

```sql
-- New Tables (Add to Existing Schema)

CREATE TABLE professors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    affiliation TEXT,
    email TEXT,
    google_scholar_url TEXT,
    h_index INTEGER,
    domains TEXT,  -- JSON array: ["neuroscience", "spatial-transcriptomics"]
    research_keywords TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, affiliation)
);

CREATE TABLE papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pmid TEXT UNIQUE,
    doi TEXT,
    arxiv_id TEXT,
    title TEXT NOT NULL,
    abstract TEXT,
    authors TEXT,  -- JSON array
    journal TEXT,
    year INTEGER,
    citations INTEGER,

    -- Full-text storage (BLOB for scale)
    full_text_markdown TEXT,  -- Complete paper in markdown
    pdf_path TEXT,  -- Optional: path to PDF if downloaded

    professor_id INTEGER,
    domain TEXT,  -- Primary domain classification

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (professor_id) REFERENCES professors(id)
);

CREATE INDEX idx_papers_pmid ON papers(pmid);
CREATE INDEX idx_papers_professor ON papers(professor_id);
CREATE INDEX idx_papers_domain ON papers(domain);

CREATE TABLE paper_extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL,

    -- Hierarchical extraction (JSON BLOB)
    high_level JSON,  -- {main_claim, novelty, contribution}
    mid_level JSON,   -- {stats: [{type, value, context, page}], methods: [...]}
    low_level JSON,   -- {quotes: [{text, page, section, context}]}
    code_methods JSON,  -- {algorithms: [...], equations: [...], hyperparameters: [...]}

    extraction_model TEXT,  -- "claude-opus-4-5-20251101"
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (paper_id) REFERENCES papers(id)
);

CREATE TABLE domains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,  -- "neuroscience", "ecology", etc.
    description TEXT,
    keywords TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE domain_syntheses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synthesis_run_id INTEGER NOT NULL,
    domain_id INTEGER NOT NULL,

    -- Synthesis content
    summary_markdown TEXT,  -- 1-page synthesis
    key_findings JSON,  -- Structured key findings
    cross_field_insights JSON,  -- Connections to other domains

    papers_analyzed INTEGER,  -- Count of papers
    paper_ids TEXT,  -- JSON array of paper IDs

    synthesized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (synthesis_run_id) REFERENCES synthesis_runs(id),
    FOREIGN KEY (domain_id) REFERENCES domains(id)
);

CREATE TABLE synthesis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_path TEXT NOT NULL,
    mode TEXT NOT NULL,  -- "primary_research" or "review"

    -- Auto-detected metadata
    detected_domains TEXT,  -- JSON array
    main_finding TEXT,  -- For primary research mode
    research_question TEXT,  -- For review mode

    -- Progress tracking
    status TEXT DEFAULT 'analyzing',  -- analyzing|discovering|extracting|synthesizing|writing|complete
    current_stage TEXT,

    -- Results
    professors_found INTEGER DEFAULT 0,
    papers_found INTEGER DEFAULT 0,
    papers_extracted INTEGER DEFAULT 0,
    domains_synthesized INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE manuscripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synthesis_run_id INTEGER NOT NULL,

    mode TEXT NOT NULL,  -- "research"|"review"|"extended-review"|"hypothesis"

    -- Content (versioned)
    version INTEGER DEFAULT 1,
    latex_content TEXT,  -- Full LaTeX manuscript

    -- Section-level storage (for incremental updates)
    abstract TEXT,
    introduction TEXT,
    methods TEXT,
    results TEXT,
    discussion TEXT,

    -- Metadata
    word_count INTEGER,
    citation_count INTEGER,
    figure_count INTEGER,

    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (synthesis_run_id) REFERENCES synthesis_runs(id)
);
```

---

## MCP Server Tools

### Tool 1: `analyze_repo`

**Purpose**: Detect repository structure and determine operating mode.

```python
{
  "repo_path": "/home/user/sparsity-trap-manuscript",
  "mode": "auto"  # auto|primary_research|review
}
```

**Returns**:
```json
{
  "synthesis_run_id": 47,
  "detected_mode": "primary_research",
  "repo_structure": {
    "has_results": true,
    "tables": ["table_s1_pergene_metrics.csv", "table_s2_category_summary.csv"],
    "figures": ["figure_1_combined.png", ...],
    "readme_exists": true,
    "latex_dir": "paper/"
  },
  "detected_domains": [
    "spatial-transcriptomics",
    "loss-functions",
    "deep-learning",
    "computational-pathology"
  ],
  "next_step": "Call ingest_results to load experimental data"
}
```

**Implementation**:
- Reads file structure
- Parses README.md to extract research topic
- Uses Claude Opus 4.5 to identify domains from README + file names
- Creates `synthesis_runs` record

---

### Tool 2: `ingest_results`

**Purpose**: Load experimental results from repository (primary research mode only).

```python
{
  "synthesis_run_id": 47,
  "data_sources": ["tables/*.csv", "figures/", "README.md"]
}
```

**Returns**:
```json
{
  "key_findings": [
    {
      "claim": "Poisson loss achieves 2.7× SSIM improvement over MSE",
      "stat": "SSIM 0.542 vs 0.200, p<0.001",
      "source": "tables/table_s1_pergene_metrics.csv",
      "constraint": "Must cite exact values from Table S1"
    },
    {
      "claim": "All 50 genes benefit from Poisson loss",
      "stat": "100% success rate, mean Δ-SSIM +0.412",
      "source": "tables/table_s1_pergene_metrics.csv"
    }
  ],
  "figures_catalog": [
    {
      "filename": "figure_1_combined.png",
      "suggested_caption": "Poisson loss avoids sparsity trap",
      "referenced_data": "table_s1"
    }
  ],
  "constraints": [
    "SSIM values must match table_s1_pergene_metrics.csv exactly",
    "Do not hallucinate gene names beyond the 50 in Table S1"
  ]
}
```

**Implementation**:
- Parses CSV files, extracts statistics
- Reads README for main findings
- Creates constraints for manuscript generation
- Stores in `synthesis_runs.main_finding` (JSON)

---

### Tool 3: `discover_literature`

**Purpose**: Find professors and papers. Mode-adaptive: targeted for primary research, broad for reviews.

```python
{
  "synthesis_run_id": 47,
  "mode": "targeted",  # targeted|broad
  "search_queries": [
    "Yuankai Huo Img2ST spatial transcriptomics",
    "Ken Lau colorectal cancer spatial atlas",
    "Poisson loss sparse count data"
  ],  # For targeted mode
  "domains": null  # For broad mode (from synthesis_run)
}
```

**Returns**:
```json
{
  "professors_added": 12,
  "papers_added": 87,
  "breakdown_by_domain": {
    "spatial-transcriptomics": {
      "professors": 3,
      "papers": 25,
      "top_professor": "Yuankai Huo (Vanderbilt)"
    },
    "loss-functions": {
      "professors": 4,
      "papers": 31
    }
  },
  "targeted_matches": [
    {
      "query": "Yuankai Huo Img2ST",
      "professor": "Yuankai Huo",
      "papers_found": 8,
      "key_paper": "Img2ST-Net predicts spatial transcriptomics (PMID: 12345678)"
    }
  ]
}
```

**Implementation**:

**Targeted Mode** (Primary Research):
1. Use web search for specific queries
2. Extract professor names, affiliations from results
3. Query PubMed for their papers
4. Insert into `professors` and `papers` tables

**Broad Mode** (Review):
1. For each domain from `synthesis_runs.detected_domains`:
   - Web search: "top researchers in [domain]"
   - Extract names, affiliations
   - PubMed search: author + domain keywords
   - Top 5-10 professors per domain
   - Top 5-10 papers per professor

---

### Tool 4: `extract_papers`

**Purpose**: Hierarchical extraction via parallel subagents.

```python
{
  "synthesis_run_id": 47,
  "paper_ids": [1, 2, 3, ...],  # Optional: specific papers, or null for all
  "extraction_depth": "full"  # full|mid|high_only
}
```

**Returns**:
```json
{
  "papers_extracted": 87,
  "avg_extraction_time": "4.2 minutes/paper",
  "total_time": "6 hours",
  "extraction_summary": {
    "high_level_claims": 87,
    "mid_level_stats": 432,
    "low_level_quotes": 1053,
    "algorithms_extracted": 78,
    "equations_extracted": 156
  }
}
```

**Implementation** (Sequential domains, parallel papers within each):
```
For each domain:
  papers = get_papers_for_domain(domain)

  # Launch parallel subagents (5-10 papers each)
  chunks = chunk(papers, size=10)
  for chunk in chunks:
    subagents = []
    for paper in chunk:
      agent = spawn_subagent(extract_single_paper, paper_id)
      subagents.append(agent)

    # Wait for all subagents in chunk to complete
    results = await_all(subagents)

    # Store extractions in database
    for result in results:
      insert_extraction(result)
```

**Extraction Format** (JSON BLOB per paper):
```json
{
  "high_level": {
    "main_claim": "ZINB loss outperforms Poisson for zero-inflated data",
    "novelty": "First application to 2μm spatial transcriptomics",
    "contribution": "Separates structural vs sampling zeros"
  },
  "mid_level": {
    "stats": [
      {
        "type": "performance_metric",
        "metric": "SSIM",
        "value": 0.70,
        "context": "ZINB on Visium HD",
        "page": 5,
        "comparison": "vs 0.54 for Poisson"
      }
    ],
    "methods": [
      {
        "name": "ZINB loss",
        "parameters": {"pi": "zero-inflation", "theta": "dispersion"},
        "page": 3
      }
    ]
  },
  "low_level": {
    "quotes": [
      {
        "text": "ZINB achieves SSIM of 0.70 compared to 0.54 for Poisson (p<0.001)",
        "page": 5,
        "section": "Results",
        "context": "2μm Visium HD validation set"
      }
    ]
  },
  "code_methods": {
    "algorithms": [
      {
        "name": "ZINB NLL",
        "pseudocode": "def zinb_nll(y, mu, theta, pi): ...",
        "page": 12
      }
    ],
    "equations": [
      {
        "latex": "\\mathcal{L} = -\\log(\\pi \\cdot \\delta_{y,0} + (1-\\pi) \\cdot NB(y; \\mu, \\theta))",
        "description": "ZINB likelihood",
        "page": 3
      }
    ]
  }
}
```

---

### Tool 5: `synthesize_domains`

**Purpose**: Generate 1-page synthesis per domain with cross-field insights.

```python
{
  "synthesis_run_id": 47,
  "domain_ids": [1, 2, 3, ...]  # null = all domains
}
```

**Returns**:
```json
{
  "domains_synthesized": 10,
  "syntheses": [
    {
      "domain": "neuroscience",
      "summary_preview": "Spike trains exhibit similar sparsity (90-95% zeros)...",
      "key_papers": 15,
      "cross_field_insight": "Neural spike modeling with Poisson/NB2 directly applicable to gene expression"
    }
  ]
}
```

**Implementation**:
```
For each domain (sequential):
  papers = get_papers_with_extractions(domain)

  # Main agent synthesizes
  synthesis = opus_agent.synthesize(
    papers=papers,
    extractions=get_extractions(papers),
    task="Write 1-page synthesis highlighting key stats, algorithms, and cross-field insights"
  )

  store_domain_synthesis(synthesis, domain)
```

**Synthesis Format** (Markdown stored in `domain_syntheses.summary_markdown`):
```markdown
# Neuroscience: Sparse Spike Train Modeling

## Key Finding
Neural spike trains exhibit 90-95% sparsity (Pillow et al., 2008), similar to 2μm spatial transcriptomics.

## Statistical Approaches
1. **Poisson GLM**: Standard for spike modeling (Truccolo et al., 2005)
   - Assumption: Variance = mean
   - Fails for overdispersed data (variance >> mean)

2. **Negative Binomial**: Addresses overdispersion (Gao et al., 2015)
   - Parameters: μ (mean), θ (dispersion)
   - Variance = μ + μ²/θ
   - **Key stat**: 15-30% RMSE improvement over Poisson (PMID: 25678901, p.7)

3. **ZINB**: For zero-inflated data (Park et al., 2014)
   - **Equation**: L = -log(π·δ(y,0) + (1-π)·NB(y;μ,θ))
   - Used in calcium imaging (Chen et al., 2013)

## Cross-Field Transfer
- **Similarity**: Sparse binary events (spike/no-spike ≈ gene expressed/not expressed)
- **Transferable**: Loss function design, dispersion parameter estimation
- **Insight**: If NB2 improves spike modeling by 15-30%, similar gains expected for gene expression

## Top Papers
1. Pillow et al. (2008) - GLM for spike trains (PMID: 18563015)
2. Gao et al. (2015) - NB2 for overdispersion (PMID: 25678901)
3. Chen et al. (2013) - ZINB for calcium imaging (PMID: 23456789)
```

---

### Tool 6: `generate_section`

**Purpose**: Write individual manuscript sections with data grounding.

```python
{
  "synthesis_run_id": 47,
  "section": "results",  # introduction|methods|results|discussion|abstract
  "mode": "primary_research",
  "data_source": "tables/",  # For primary research
  "synthesis_source": "domain_syntheses"  # For review
}
```

**Returns**:
```json
{
  "section": "results",
  "latex_content": "\\section{Results}\n...",
  "word_count": 1247,
  "citations_added": 8,
  "figures_referenced": ["fig:main_effects", "fig:gene_scatter"],
  "constraints_satisfied": [
    "All SSIM values match table_s1_pergene_metrics.csv",
    "Cited exact p-values from statistical tests"
  ]
}
```

**Implementation**:

**Primary Research Mode**:
```python
# Read ingested results
key_findings = get_synthesis_run_findings(synthesis_run_id)
constraints = get_synthesis_run_constraints(synthesis_run_id)

# Read domain syntheses for literature context
domain_syntheses = get_domain_syntheses(synthesis_run_id)

# Generate section
latex = opus_agent.generate(
  section=section,
  your_findings=key_findings,  # GROUND IN YOUR DATA
  literature_context=domain_syntheses,
  constraints=constraints,
  template=get_latex_template(mode="primary_research")
)

# Verify constraints
verify_citations_match_tables(latex, constraints)
```

**Review Mode**:
```python
domain_syntheses = get_domain_syntheses(synthesis_run_id)
cross_domain_insights = extract_cross_domain_connections(domain_syntheses)

latex = opus_agent.generate(
  section=section,
  domain_syntheses=domain_syntheses,
  cross_domain_insights=cross_domain_insights,
  template=get_latex_template(mode="review")
)
```

---

### Tool 7: `generate_manuscript`

**Purpose**: Orchestrate full manuscript generation with section-by-section checkpoints.

```python
{
  "synthesis_run_id": 47,
  "mode": "research",  # research|review|extended-review|hypothesis
  "sections": ["introduction", "methods", "results", "discussion"],
  "output_path": "paper/manuscript.tex"
}
```

**Returns**:
```json
{
  "manuscript_id": 12,
  "sections_generated": 5,
  "total_word_count": 4523,
  "total_citations": 47,
  "latex_path": "paper/manuscript.tex",
  "checkpoint_summary": "All sections complete. Ready for review."
}
```

**Implementation** (Conversational checkpoints):
```
For each section in [abstract, introduction, methods, results, discussion]:

  # Generate section
  latex = call_generate_section(section)

  # Show to user via Claude
  claude_says: "Generated {section} section (${word_count} words, ${citations} citations)."
  claude_says: "Preview: ${first_200_chars}..."
  claude_says: "Continue to next section?"

  # Wait for user confirmation
  user_input = wait_for_user()

  if user_input == "adjust X":
    # Regenerate with adjustment
    latex = regenerate_section(section, adjustment=X)

  # Store section
  store_manuscript_section(manuscript_id, section, latex)

# Assemble full manuscript
full_latex = assemble_sections() + generate_bibliography()
write_file(output_path, full_latex)
```

---

## LaTeX Template System

### Field Detection

```python
def detect_field(repo_structure, domains):
    """
    Returns: "medical-imaging"|"genomics"|"machine-learning"|"interdisciplinary"
    """
    if "spatial-transcriptomics" in domains or "pathology" in domains:
        return "medical-imaging"
    elif "single-cell" in domains or "genomics" in domains:
        return "genomics"
    elif "deep-learning" in domains and not medical_related:
        return "machine-learning"
    else:
        return "interdisciplinary"
```

### Templates

**Medical Imaging** (IEEE/MICCAI):
```latex
\documentclass[conference]{IEEEtran}

% Figure placement: ALWAYS [t!] or [b!]
\begin{figure}[t!]
  \centering
  \includegraphics[width=0.95\columnwidth]{figs/results.png}
  \caption{...}
  \label{fig:results}
\end{figure}

% Units: \SI{2}{\micro\meter}
% References: Figure~\ref{fig:results}
```

**Genomics** (Nature/Cell):
```latex
\documentclass{article}

% Methods at end
% Extended data figures in supplement
% Main figures: multi-panel with a,b,c labels
```

**Machine Learning** (NeurIPS/ICML):
```latex
\documentclass{article}

% Algorithm blocks
\begin{algorithm}
\caption{ZINB Loss}
\begin{algorithmic}
...
\end{algorithmic}
\end{algorithm}

% Theorem environments
\begin{theorem}
...
\end{theorem}
```

### AI Refinement

After selecting template, agent analyzes top 3 papers from each domain:
```python
for domain in domains:
    top_papers = get_top_papers(domain, limit=3)

    # Extract LaTeX patterns
    patterns = opus_agent.extract_patterns(
        papers=top_papers,
        extract=["section_ordering", "figure_conventions", "equation_style", "citation_format"]
    )

    # Refine template
    template = refine_template(template, patterns)
```

---

## Manuscript Mode Specifications

### Mode 1: Primary Research

**Structure**: IMRaD
- Abstract: 150-250 words, structured (Background, Methods, Results, Conclusions)
- Introduction: 800-1200 words, 15-25 citations
- Methods: 1000-1500 words, algorithmic detail, reproducibility focus
- Results: 1200-1800 words, 4-6 figures, cite YOUR data tables
- Discussion: 1000-1500 words, 20-30 citations, cross-field context

**Total**: 4000-6000 words, 40-60 citations

**Depth**: Focus on YOUR findings, literature provides context

**Example**: "The Sparsity Trap" paper

---

### Mode 2: Standard Review

**Structure**: Topic-organized
- Abstract: 200-300 words, unstructured narrative
- Introduction: 1000-1500 words, define scope
- Section 2-5: Topical sections (e.g., "Statistical Approaches", "Deep Learning Methods")
- Future Directions: 500-800 words
- Conclusions: 300-500 words

**Total**: 5000-7000 words, 60-100 citations

**Depth**: Balanced coverage, synthesize existing work

**Example**: "Loss Functions for Sparse Spatial Data: A Review"

---

### Mode 3: Extended Review

**Structure**: Comprehensive synthesis
- Abstract: 300-400 words
- Introduction: 1500-2000 words
- 6-10 major sections with subsections
- Cross-field synthesis sections
- Critical analysis sections
- Conclusions: 500-800 words

**Total**: 8000-12000 words, 100-200 citations

**Depth**: Exhaustive, authoritative reference

**Example**: "Spatial Transcriptomics: From Technology to Discovery"

---

### Mode 4: Hypothesis/Opinion

**Structure**: Thesis-driven narrative
- Abstract: 150-200 words, provocative framing
- Thesis Statement: Clear claim
- 3-5 supporting sections with evidence
- Counterarguments section
- Implications: 800-1200 words

**Total**: 2000-3000 words, 20-40 citations

**Depth**: Selective citations, emphasize novel connections

**Example**: "The MSE Trap: Why Computer Vision Should Abandon L2 Loss for Sparse Data"

---

## Conversation Flow Examples

### Primary Research (Sparsity Trap)

**User**: "Analyze the sparsity trap repo"

**Claude**: [calls `analyze_repo`]
> Created synthesis run #47. Detected **primary research mode**.
>
> **Repository Structure**:
> - Tables: table_s1_pergene_metrics.csv (50 genes), table_s2_category_summary.csv
> - Figures: 23 PNG files (manuscript/, wsi/, tiles/)
> - README: Main finding identified
>
> **Detected Domains**: spatial-transcriptomics, loss-functions, deep-learning, computational-pathology
>
> Ready to ingest results from tables/?

**User**: "Yes, ingest the results"

**Claude**: [calls `ingest_results`]
> **Key Findings Extracted**:
> 1. Poisson loss SSIM: 0.542 ± 0.019 (Table S1)
> 2. MSE loss SSIM: 0.200 ± 0.012 (Table S1)
> 3. Improvement: 2.7× (p<0.001)
> 4. Success rate: 50/50 genes (100%)
> 5. Top gene: TSPAN8 (+0.73 SSIM improvement)
>
> **Constraints Created**:
> - All SSIM values must match table_s1_pergene_metrics.csv exactly
> - Gene names limited to 50 from Table S1
> - Statistical tests must reference actual p-values
>
> Ready to find literature for context?

**User**: "Find papers on Huo Img2ST, Lau CRC atlas, and Poisson loss theory"

**Claude**: [calls `discover_literature` with targeted mode]
> **Literature Discovery Complete** (12 professors, 87 papers added to database)
>
> **Targeted Matches**:
> 1. Yuankai Huo (Vanderbilt): 8 papers found
>    - Key: "Hist2ST predicts spatial gene expression" (PMID: 34699352)
> 2. Ken Lau (Vanderbilt): 6 papers found
>    - Key: "CRC spatial atlas" (PMID: TBD, need to verify exact paper)
> 3. Poisson regression theory: 15 papers
>    - McCullagh & Nelder "Generalized Linear Models" (foundational)
>    - Modern: ZINB for scRNA-seq (multiple papers)
>
> Extracting papers now (87 papers × 4 min = ~6 hours). Continue?

**User**: "Yes, extract them"

**Claude**: [calls `extract_papers`]
> **Extraction Progress** (using parallel subagents):
> - Domain 1/4 (spatial-transcriptomics): 25 papers → 25 extractions (2.1 hours)
> - Domain 2/4 (loss-functions): 31 papers → 31 extractions (2.6 hours)
> - Domain 3/4 (deep-learning): 18 papers → 18 extractions (1.5 hours)
> - Domain 4/4 (computational-pathology): 13 papers → 13 extractions (1.1 hours)
>
> **Extraction Complete** (7.3 hours total)
> - High-level claims: 87
> - Stats extracted: 412
> - Citation-ready quotes: 1048
> - Algorithms: 72
>
> Ready to synthesize domains?

**User**: "Synthesize the domains"

**Claude**: [calls `synthesize_domains`]
> **Domain Syntheses Complete**:
>
> 1. **Spatial Transcriptomics** (25 papers)
>    - Key insight: Hist2ST uses Poisson loss (Huo et al.)
>    - Transfer: Your 2μm work extends to higher resolution
>
> 2. **Loss Functions** (31 papers)
>    - Key insight: NB2 outperforms Poisson for overdispersion (θ parameter)
>    - ZINB for zero-inflation (π parameter)
>    - Cross-field: Ecology has 30 years of ZINB for sparse spatial data
>
> 3. **Deep Learning** (18 papers)
>    - Key insight: MSE assumes Gaussian noise (inappropriate for counts)
>    - Focal loss for class imbalance (99% zeros in object detection)
>
> 4. **Computational Pathology** (13 papers)
>    - Key insight: Foundation models (Virchow2, UNI) + task-specific decoders
>
> Ready to write the manuscript?

**User**: "Write the Results section first"

**Claude**: [calls `generate_section` with section="results"]
> **Generating Results Section**...
>
> Grounding in your data:
> - Table S1: 50 genes, SSIM values
> - Figure 1: Factorial design
> - Figure 2: Category analysis
>
> **Results Section Draft** (1,247 words, 8 citations):
>
> ```latex
> \section{Results}
>
> \subsection{Poisson Loss Avoids the Sparsity Trap}
>
> We trained four models in a $2 \times 2$ factorial design crossing loss function (MSE vs Poisson NLL) with decoder architecture (Hist2ST vs Img2ST). Across all 50 genes, Poisson loss achieved a mean SSIM of $0.542 \pm 0.019$ compared to $0.200 \pm 0.012$ for MSE ($p < 0.001$, paired t-test; Table~\ref{tab:main_results}, Figure~\ref{fig:factorial_ssim}).
>
> This $2.7\times$ improvement was universal: all 50 genes showed higher SSIM with Poisson loss (100\% success rate, Figure~\ref{fig:gene_scatter}). The improvement was strongly correlated with gene sparsity ($r = 0.577$, $p < 0.0001$), with the most sparse genes showing the largest gains (Figure~\ref{fig:sparsity_correlation}).
> ...
> ```
>
> **Constraints Verified**:
> ✓ SSIM 0.542 matches table_s1_pergene_metrics.csv
> ✓ p-values cited exactly as computed
> ✓ Gene count (50) matches table
>
> Continue to Methods section?

**User**: "Yes"

**Claude**: [continues section by section...]

---

### Review Mode (Hypothetical)

**User**: "Write a review on loss functions for sparse spatial data"

**Claude**: [calls `analyze_repo`]
> No repository provided. Assuming **review mode**.
>
> **Research Question**: "Loss functions for sparse spatial data: cross-disciplinary survey"
>
> **Proposed Domains** (10):
> 1. Spatial transcriptomics
> 2. Neuroscience (spike trains)
> 3. Ecology (species abundance)
> 4. Computer vision (object detection)
> 5. Single-cell genomics
> 6. Medical imaging (lesion detection)
> 7. Statistics (GLM theory)
> 8. Remote sensing
> 9. Econometrics (zero-inflated models)
> 10. Machine learning (loss function design)
>
> Discover literature across all domains?

**User**: "Yes, discover broadly"

**Claude**: [calls `discover_literature` with broad mode]
> **Broad Discovery** (10 domains × 5 professors × 8 papers = ~400 papers)
>
> **Progress**:
> - Domain 1/10: Spatial transcriptomics → 5 professors, 42 papers
> - Domain 2/10: Neuroscience → 6 professors, 51 papers
> - ...
> - Domain 10/10: Machine learning → 5 professors, 38 papers
>
> **Total**: 54 professors, 412 papers added to database
>
> This will take ~28 hours to extract with parallel subagents. Continue overnight?

[User continues conversation...]

---

## Performance Characteristics

### Time Estimates

**Primary Research Mode** (e.g., Sparsity Trap):
- Analyze repo: 2 minutes
- Ingest results: 5 minutes
- Discover literature (targeted): 30 minutes
- Extract papers (87 papers): 6-8 hours (parallel subagents)
- Synthesize domains: 1 hour
- Generate manuscript: 2-3 hours (with checkpoints)
- **Total**: ~10-12 hours

**Review Mode** (broad discovery):
- Analyze topic: 5 minutes
- Discover literature (broad): 2-3 hours
- Extract papers (400 papers): 24-30 hours (parallel subagents)
- Synthesize domains: 3-4 hours
- Generate manuscript: 4-6 hours (with checkpoints)
- **Total**: ~35-45 hours

### Cost Estimates (Claude Opus 4.5)

**Primary Research**:
- Repository analysis: $0.50
- Literature discovery: $2.00
- Paper extraction (87 papers × $0.80): $70
- Domain synthesis: $15
- Manuscript generation: $25
- **Total**: ~$112

**Review Mode**:
- Literature discovery: $10
- Paper extraction (400 papers × $0.80): $320
- Domain synthesis: $45
- Manuscript generation: $60
- **Total**: ~$435

### Database Growth

Starting: 212 papers (Vanderbilt only)

After 10 manuscripts:
- Professors: ~500
- Papers: ~5,000
- Extractions: ~5,000
- Domain syntheses: ~100
- Database size: ~2-3 GB

After 100 manuscripts:
- Professors: ~2,000
- Papers: ~30,000
- Database size: ~15-20 GB

**Reuse**: Once papers are extracted, subsequent manuscripts using the same literature have near-zero extraction cost.

---

## Implementation Plan

### Phase 1: Database Schema (1 day)
1. Extend Vanderbilt Professors MCP database
2. Add new tables: `professors`, `papers`, `paper_extractions`, `domains`, `domain_syntheses`, `synthesis_runs`, `manuscripts`
3. Migration script to preserve existing 212 papers
4. Test: Insert dummy data, verify queries

### Phase 2: Core MCP Server (2 days)
1. Create `/home/user/mcp_servers/polymax-synthesizer/server.py`
2. Implement tools 1-3: `analyze_repo`, `ingest_results`, `discover_literature`
3. Test: Analyze sparsity-trap-manuscript, verify database insertion
4. Add to Claude Code MCP config

### Phase 3: Paper Extraction System (2 days)
1. Implement `extract_papers` tool
2. Build subagent orchestration (sequential domains, parallel papers)
3. Create hierarchical extraction prompts
4. Test: Extract 10 papers, verify JSON structure

### Phase 4: Domain Synthesis (1 day)
1. Implement `synthesize_domains` tool
2. Create synthesis prompts with cross-field focus
3. Test: Synthesize 2 domains, verify markdown quality

### Phase 5: Manuscript Generation (3 days)
1. Create LaTeX templates (medical-imaging, genomics, ML, interdisciplinary)
2. Implement `generate_section` tool with constraint verification
3. Implement `generate_manuscript` orchestration
4. Integrate `latex-architect` MCP for figure blocks
5. Test: Generate sparsity-trap manuscript

### Phase 6: Validation & Polish (1 day)
1. End-to-end test: Primary research mode on sparsity-trap
2. End-to-end test: Review mode on synthetic topic
3. Documentation: User guide, API reference
4. Git commit and deploy

**Total**: 10 days

---

## Success Criteria

### For Primary Research Mode
1. ✅ Manuscript cites exact values from `tables/*.csv` (no hallucination)
2. ✅ All figures referenced with proper LaTeX labels
3. ✅ Literature provides context, not conflicting results
4. ✅ LaTeX compiles without errors
5. ✅ Word count within target range (4000-6000 for research)
6. ✅ Citations properly formatted for detected field

### For Review Mode
1. ✅ Comprehensive coverage (50+ professors, 300+ papers)
2. ✅ Cross-field insights identified and synthesized
3. ✅ No duplicate content across sections
4. ✅ Citations balanced across domains
5. ✅ LaTeX compiles without errors
6. ✅ Word count within target range (5000-12000 depending on mode)

### For Knowledge Base Growth
1. ✅ Database scales to 10,000+ papers
2. ✅ Query performance <1s for typical lookups
3. ✅ Full-text stored as TEXT (not files)
4. ✅ Extractions reusable across manuscripts
5. ✅ Professors deduplicated by (name, affiliation)

---

## Future Enhancements

### Version 2.0 Features
1. **Multi-author collaboration**: Track contributions per section
2. **Journal-specific formatting**: Nature, Cell, Science templates
3. **Figure generation**: Auto-generate plots from tables
4. **Citation management**: Export to Zotero, integrate with existing libraries
5. **Iterative refinement**: User edits → AI incorporates feedback → regenerate
6. **Preprint generation**: ArXiv/bioRxiv formatting with auto-upload

### Version 3.0 Features
1. **Grant proposal mode**: Specific aims, research strategy, budget justification
2. **Rebuttal generator**: Response to reviewer comments with literature support
3. **Presentation mode**: Generate conference slides from manuscript
4. **Meta-analysis mode**: Quantitative synthesis across papers
5. **Reproducibility package**: Code + data + manuscript in one command

---

## Appendix: Example Extraction

**Paper**: "Focal Loss for Dense Object Detection" (Lin et al., ICCV 2017)

```json
{
  "high_level": {
    "main_claim": "Focal loss solves extreme class imbalance (99% background) by down-weighting easy examples",
    "novelty": "Multiplicative focal term (1-p)^γ focuses learning on hard examples",
    "contribution": "Enables one-stage detectors to match two-stage detector accuracy"
  },
  "mid_level": {
    "stats": [
      {
        "type": "performance_metric",
        "metric": "AP",
        "value": 39.1,
        "context": "RetinaNet on COCO test-dev",
        "page": 7,
        "comparison": "vs 34.0 for previous best one-stage detector"
      }
    ],
    "methods": [
      {
        "name": "Focal loss",
        "parameters": {"gamma": 2.0, "alpha": 0.25},
        "page": 3,
        "description": "Addresses class imbalance by down-weighting well-classified examples"
      }
    ]
  },
  "low_level": {
    "quotes": [
      {
        "text": "With γ=2, an example classified with pt=0.9 would have 100× lower loss compared with CE",
        "page": 4,
        "section": "Focal Loss",
        "context": "Demonstrating the effect of focal term"
      },
      {
        "text": "The focal loss enables the one-stage detector to match the AP of state-of-the-art two-stage detectors",
        "page": 1,
        "section": "Abstract",
        "context": "Main result summary"
      }
    ]
  },
  "code_methods": {
    "algorithms": [],
    "equations": [
      {
        "latex": "FL(p_t) = -(1-p_t)^\\gamma \\log(p_t)",
        "description": "Focal loss formula",
        "page": 3,
        "variables": {
          "p_t": "model's estimated probability for correct class",
          "gamma": "focusing parameter (typically 2)"
        }
      }
    ],
    "hyperparameters": [
      {
        "name": "gamma",
        "optimal_value": 2.0,
        "range_tested": [0, 0.5, 1, 2, 5],
        "page": 5
      },
      {
        "name": "alpha",
        "optimal_value": 0.25,
        "description": "Class weighting factor",
        "page": 4
      }
    ]
  }
}
```

**Transfer to Sparsity Trap**:
- 99% background in object detection ≈ 95% zeros in gene expression
- Focal loss down-weights easy zeros → focuses learning on non-zero genes
- Hypothesis: Focal + Poisson might improve beyond plain Poisson

---

## Conclusion

PolyMaX Synthesizer represents a new paradigm: **conversational academic writing** where the researcher directs a multi-agent system that handles literature discovery, extraction, synthesis, and LaTeX generation while maintaining ground truth from experimental results.

The dual-mode architecture ensures precision for primary research (your data is sacred) while enabling comprehensive synthesis for reviews (literature is the data).

By extending the Vanderbilt Professors MCP into a growing knowledge graph, each manuscript makes future manuscripts faster and more comprehensive—a compounding knowledge base that grows with every paper written.

**Next Steps**: Implement Phase 1 (database schema) and test with sparsity-trap-manuscript.
