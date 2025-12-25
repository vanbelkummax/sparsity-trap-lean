# PolyMaX Synthesizer Architecture

**System design for automated research synthesis and manuscript generation.**

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     PolyMaX Synthesizer                         │
│                   (MCP Server Process)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ stdio transport
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
        ▼                                           ▼
┌──────────────┐                            ┌──────────────┐
│ Claude Code  │                            │  Database    │
│   (Client)   │                            │  (SQLite)    │
└──────────────┘                            └──────────────┘
        │                                           │
        │ MCP tool calls                            │ SQL queries
        │                                           │
        ▼                                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Tool Handlers                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Repo       │  │  Results     │  │ Literature   │         │
│  │  Analyzer    │  │  Ingester    │  │  Discovery   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Paper      │  │   Domain     │  │ Manuscript   │         │
│  │  Extractor   │  │ Synthesizer  │  │  Generator   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. Database Layer

**File**: `database.py`, `schema.sql`

**Purpose**: Persistent storage for experiments, results, papers, and syntheses.

**Schema**:

```sql
experiments
├── id (PRIMARY KEY)
├── repo_path (TEXT, UNIQUE)
├── experiment_name (TEXT)
├── description (TEXT)
├── domains (JSON)
└── created_at (TIMESTAMP)

results
├── id (PRIMARY KEY)
├── experiment_id (FOREIGN KEY)
├── gene_name (TEXT)
├── metric_name (TEXT)
├── metric_value (REAL)
├── category (TEXT)
└── metadata (JSON)

papers
├── id (PRIMARY KEY)
├── pmid (TEXT, UNIQUE)
├── title (TEXT)
├── authors (TEXT)
├── year (INTEGER)
├── abstract (TEXT)
├── full_text (TEXT)
├── source (TEXT)
├── domains (JSON)
└── created_at (TIMESTAMP)

domain_syntheses
├── id (PRIMARY KEY)
├── domain_name (TEXT, UNIQUE)
├── synthesis (TEXT)
├── paper_ids (JSON)
├── experiment_ids (JSON)
└── created_at (TIMESTAMP)
```

**Design Decisions**:
- SQLite for simplicity and portability
- JSON fields for flexible metadata
- Unique constraints on repo_path and pmid
- Timestamps for reproducibility

---

### 2. MCP Server

**File**: `server.py`

**Purpose**: Exposes 7 tools via Model Context Protocol.

**Tools**:
1. `analyze_repo`: Repository analysis
2. `ingest_results`: Results ingestion
3. `discover_literature`: Paper discovery
4. `extract_papers`: Paper extraction
5. `synthesize_domains`: Knowledge synthesis
6. `generate_section`: Section generation (internal)
7. `generate_manuscript`: Full manuscript generation

**Architecture**:

```python
# server.py structure
async def main():
    server = Server("polymax-synthesizer")

    # Register tool handlers
    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        # Return tool definitions

    @server.call_tool()
    async def handle_call_tool(name, arguments):
        # Route to appropriate handler

    # Start stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(...)
```

**Transport**: stdio (compatible with Claude Code)

**Error Handling**:
- Try/except blocks in all tool handlers
- Detailed error messages returned as tool results
- Logging to stderr for debugging

---

### 3. Repository Analyzer

**File**: `repo_analyzer.py`

**Purpose**: Analyzes research repository structure and content.

**Process**:

```
Input: repo_path
    │
    ├─→ Scan directory structure
    │   ├── Count tables (CSV files)
    │   ├── Count figures (PNG, JPG, PDF)
    │   └── Detect code files
    │
    ├─→ Read README.md
    │   ├── Extract title
    │   ├── Extract description
    │   └── Detect domains via keyword matching
    │
    ├─→ Determine mode
    │   ├── primary_research: has tables/figures
    │   └── literature_review: README-only
    │
    └─→ Generate suggested queries
        └── Based on detected domains

Output: Analysis JSON
```

**Domain Detection**:

```python
DOMAIN_KEYWORDS = {
    "spatial-transcriptomics": [
        "spatial transcriptomics",
        "Visium",
        "Img2ST",
        "Hist2ST",
        "gene expression"
    ],
    "loss-functions": [
        "MSE",
        "Poisson",
        "loss function"
    ],
    # ... more domains
}
```

**Design**: Keyword-based classification with extensible domain definitions.

---

### 4. Results Ingester

**File**: `results_ingester.py`

**Purpose**: Parses CSV tables and loads into database.

**Process**:

```
Input: tables_dir
    │
    ├─→ Create experiment record
    │   ├── repo_path
    │   ├── experiment_name (from README)
    │   └── domains
    │
    ├─→ For each CSV file:
    │   ├── Detect schema (columns)
    │   ├── Parse rows
    │   ├── Extract gene, metric, value
    │   └── Insert into results table
    │
    └─→ Compute statistics
        └── mean, std for each metric

Output: Ingestion summary
```

**Schema Detection**:

```python
# Flexible column mapping
COLUMN_PATTERNS = {
    "gene": ["gene", "gene_name", "symbol"],
    "metric": ["metric", "metric_name", "measure"],
    "value": ["value", "metric_value", "score"],
    "category": ["category", "type", "class"]
}
```

**Design**: Handles multiple CSV formats automatically.

---

### 5. Literature Discovery

**File**: `literature_discovery.py`

**Purpose**: Discovers relevant papers from multiple sources.

**Architecture**:

```
Input: queries[], mode
    │
    ├─→ For each query:
    │   │
    │   ├─→ PubMed Search
    │   │   ├── Entrez esearch
    │   │   ├── Fetch PMIDs
    │   │   └── Parse metadata
    │   │
    │   ├─→ bioRxiv Search
    │   │   ├── API query
    │   │   ├── Fetch preprints
    │   │   └── Parse metadata
    │   │
    │   └─→ Vanderbilt Professors MCP
    │       ├── search_all_professors()
    │       ├── Get matching papers
    │       └── Parse metadata
    │
    ├─→ Deduplicate by PMID
    │
    └─→ Insert into papers table

Output: Discovery summary
```

**Modes**:
- **targeted**: 3 papers per query (fast)
- **comprehensive**: 10 papers per query (thorough)

**Sources**:
1. **PubMed**: NCBI Entrez API
2. **bioRxiv**: bioRxiv API
3. **Vanderbilt MCP**: Faculty paper database

**Design**: Multi-source with deduplication for broad coverage.

---

### 6. Paper Extractor

**File**: `paper_extractor.py`

**Purpose**: Fetches full abstracts and metadata for papers.

**Process**:

```
Input: db_path
    │
    ├─→ Query papers without abstracts
    │
    ├─→ For each paper:
    │   │
    │   ├─→ If PMID exists:
    │   │   ├── Entrez efetch
    │   │   ├── Parse XML
    │   │   └── Extract abstract
    │   │
    │   └─→ If Vanderbilt paper:
    │       ├── get_paper_abstract(pmid)
    │       └── Extract abstract
    │
    └─→ Update papers table

Output: Extraction summary
```

**API Usage**:

```python
# Entrez
from Bio import Entrez
Entrez.email = "max.vanbelkum@vanderbilt.edu"

handle = Entrez.efetch(
    db="pubmed",
    id=pmid,
    retmode="xml"
)
```

**Design**: Batched fetching with error recovery.

---

### 7. Domain Synthesizer

**File**: `domain_synthesizer.py`

**Purpose**: Combines papers and results into coherent synthesis.

**Process**:

```
Input: db_path
    │
    ├─→ Get all domains
    │
    ├─→ For each domain:
    │   │
    │   ├─→ Get relevant papers
    │   │   └── WHERE domains LIKE '%domain%'
    │   │
    │   ├─→ Get relevant results
    │   │   └── JOIN experiments ON domains
    │   │
    │   ├─→ Call Claude Sonnet 4.5
    │   │   ├── System prompt from prompts/
    │   │   ├── Papers as context
    │   │   ├── Results as context
    │   │   └── Generate synthesis
    │   │
    │   └─→ Store in domain_syntheses
    │
    └─→ Return summary

Output: Synthesis summary
```

**Prompt Structure**:

```
System: You are a computational biology expert synthesizing knowledge.

Papers:
[1] Paper Title (Year)
Abstract: ...

[2] Paper Title (Year)
Abstract: ...

Results:
Gene: TSPAN8
SSIM_Poisson: 0.890 ± 0.045
Category: Epithelial

Task: Synthesize the state-of-the-art for [domain].
```

**Design**: Claude-powered synthesis with structured prompts.

---

### 8. Manuscript Generator

**File**: `section_generator.py`

**Purpose**: Generates publication-ready LaTeX manuscript.

**Architecture**:

```
Input: output_dir, sections[]
    │
    ├─→ Load domain syntheses
    │
    ├─→ Load experimental results
    │
    ├─→ Load papers for citations
    │
    ├─→ For each section:
    │   │
    │   ├─→ Load prompt template
    │   │   └── prompts/{section}.txt
    │   │
    │   ├─→ Build context
    │   │   ├── Domain synthesis
    │   │   ├── Results with constraints
    │   │   └── Citation list
    │   │
    │   ├─→ Call Claude Sonnet 4.5
    │   │   ├── Generate LaTeX
    │   │   ├── Include \cite{}
    │   │   └── Include result values
    │   │
    │   └─→ Store section
    │
    ├─→ Combine sections
    │   ├── Add LaTeX preamble
    │   ├── Add bibliography
    │   └── Add figure/table refs
    │
    └─→ Write manuscript.tex

Output: Manuscript file
```

**LaTeX Structure**:

```latex
\documentclass{article}
\usepackage{graphicx}
\usepackage{natbib}

\begin{document}

\title{Manuscript Title}
\author{Authors}
\maketitle

\section{Introduction}
... \cite{paper1} ...

\section{Methods}
... \cite{paper2} ...

\section{Results}
TSPAN8 achieved SSIM of 0.890 ± 0.045 ...

\section{Discussion}
... \cite{paper3} ...

\bibliographystyle{plain}
\bibliography{references}

\end{document}
```

**Constraint Satisfaction**:

```python
# Extract values from results table
SELECT metric_name, metric_value FROM results
WHERE gene_name = 'TSPAN8'

# Inject into prompt
"Use exact value: SSIM_Poisson = 0.890 ± 0.045"

# Validate in output
assert "0.890" in manuscript_text
```

**Design**: Template-based generation with strict value matching.

---

## Data Flow

### End-to-End Pipeline

```
1. analyze_repo
   ├─→ Scan repository
   └─→ Return domains[]

2. ingest_results
   ├─→ Read CSVs
   ├─→ INSERT INTO experiments
   └─→ INSERT INTO results

3. discover_literature
   ├─→ Query PubMed/bioRxiv/Vanderbilt
   ├─→ Deduplicate
   └─→ INSERT INTO papers

4. extract_papers
   ├─→ Fetch abstracts
   └─→ UPDATE papers SET abstract

5. synthesize_domains
   ├─→ Group papers by domain
   ├─→ Call Claude for synthesis
   └─→ INSERT INTO domain_syntheses

6. generate_manuscript
   ├─→ Load syntheses + results + papers
   ├─→ Generate sections with Claude
   ├─→ Combine into LaTeX
   └─→ Write manuscript.tex
```

---

## External Dependencies

### MCP Servers

**Vanderbilt Professors MCP**:
- Location: `/home/user/vanderbilt_professors_mcp/server.py`
- Purpose: Search faculty papers
- Tools:
  - `search_all_professors(query)`
  - `get_paper_abstract(pmid)`

**LaTeX Architect MCP**:
- Location: `/home/user/mcp_servers/latex-architect/latex_architect.py`
- Purpose: IEEE/MICCAI formatting
- Tools:
  - `generate_figure_block()`
  - `check_spatial_inclusion()`

### APIs

**PubMed (Entrez)**:
- Protocol: HTTP REST
- Rate limit: 3 requests/second
- Email required: `Entrez.email`

**bioRxiv**:
- Protocol: HTTP REST
- Rate limit: None specified
- Endpoint: `https://api.biorxiv.org/`

### Python Packages

```
mcp>=1.0.0
anthropic>=0.40.0
biopython>=1.80
pandas>=2.0.0
sqlite3 (built-in)
```

---

## Error Handling Strategy

### Database Errors

```python
try:
    conn = sqlite3.connect(db_path)
    # ... operations
except sqlite3.Error as e:
    return {
        "error": f"Database error: {str(e)}",
        "suggestion": "Check database path and permissions"
    }
```

### API Errors

```python
try:
    handle = Entrez.efetch(...)
except Exception as e:
    # Retry with exponential backoff
    time.sleep(2 ** retry_count)
    # Fall back to alternative source
```

### Claude API Errors

```python
try:
    response = client.messages.create(...)
except anthropic.APIError as e:
    # Log to stderr
    print(f"Claude API error: {e}", file=sys.stderr)
    # Return graceful error
    return {"error": "Synthesis failed"}
```

---

## Performance Considerations

### Database Optimization

**Indexes**:
```sql
CREATE INDEX idx_results_gene ON results(gene_name);
CREATE INDEX idx_papers_pmid ON papers(pmid);
CREATE INDEX idx_papers_domains ON papers(domains);
```

**Batching**:
- Insert results in batches of 100
- Fetch papers in batches of 20

### API Rate Limiting

**PubMed**:
- Max 3 requests/second
- Implemented with `time.sleep(0.34)`

**Claude**:
- No explicit limit (usage-based billing)
- Batch synthesis calls when possible

### Memory Management

**Large Files**:
- Stream CSV parsing with pandas chunks
- Limit abstract length to 5000 chars
- Limit full_text to 50000 chars

---

## Security Considerations

### Input Validation

```python
# Path traversal prevention
assert os.path.abspath(repo_path).startswith(ALLOWED_DIR)

# SQL injection prevention
cursor.execute(
    "SELECT * FROM papers WHERE pmid = ?",
    (pmid,)  # Parameterized query
)
```

### API Keys

- Stored in environment variables
- Never logged or exposed in errors
- Loaded from secure locations only

### File System Access

- Restrict to `/home/user/` directory
- Validate all paths before operations
- Use read-only mode where possible

---

## Testing Strategy

### Unit Tests

**test_database.py**:
- Schema creation
- CRUD operations
- Constraint validation

**test_server.py**:
- Tool registration
- Parameter validation
- Error handling

### Integration Tests

**test_end_to_end.py**:
- Full pipeline with real repository
- Database state validation
- Constraint satisfaction checks

### Test Data

**Mock Repository**:
```
/tmp/test-repo/
├── README.md
├── tables/
│   └── results.csv
└── figures/
    └── fig1.png
```

---

## Future Enhancements

### Phase 1: Core Improvements

1. **Figure Integration**
   - Analyze figure images with Claude vision
   - Extract captions automatically
   - Generate LaTeX figure blocks

2. **Citation Management**
   - BibTeX generation from papers table
   - Citation style customization (IEEE, Nature, etc.)
   - Cross-reference validation

3. **Multi-repository Support**
   - Compare multiple experiments
   - Meta-analysis synthesis
   - Shared literature database

### Phase 2: Advanced Features

4. **Interactive Refinement**
   - User feedback on syntheses
   - Iterative manuscript improvement
   - Section-level regeneration

5. **Collaborative Writing**
   - Multi-user database
   - Version control integration
   - Comment/annotation system

6. **Publication Pipeline**
   - Automated submission formatting
   - Supplementary material generation
   - Cover letter drafting

### Phase 3: Domain Expansion

7. **Domain-Specific Templates**
   - Genomics manuscript structure
   - Imaging study templates
   - Clinical trial reports

8. **Custom Synthesis Models**
   - Fine-tuned for specific domains
   - Specialized prompts per field
   - Domain expert validation

9. **Multi-modal Analysis**
   - Code analysis (methods section)
   - Data visualization (results)
   - Video/animation integration

---

## Deployment

### Production Setup

```bash
# Clone repository
git clone https://github.com/vanbelkummax/polymax-synthesizer
cd polymax-synthesizer

# Install dependencies
pip install -r requirements.txt

# Initialize production database
python3 -c "from database import init_database; init_database('/data/polymax.db')"

# Configure MCP server
# Add to ~/.claude.json with production db_path
```

### Monitoring

**Logging**:
- stderr: Errors and warnings
- Database: All operations logged with timestamps
- Tool calls: Tracked in MCP layer

**Metrics**:
- Papers discovered per hour
- Synthesis success rate
- Manuscript generation time
- Database size growth

### Backup Strategy

```bash
# Daily database backup
cp /data/polymax.db /backups/polymax_$(date +%Y%m%d).db

# Weekly cleanup of old backups
find /backups -name "polymax_*.db" -mtime +30 -delete
```

---

## Contributing

### Code Standards

- **PEP 8**: Python style guide
- **Type hints**: Required for all functions
- **Docstrings**: Google style
- **Tests**: 80%+ coverage required

### Pull Request Process

1. Create feature branch
2. Add tests
3. Update documentation
4. Submit PR with description
5. Pass CI checks
6. Code review
7. Merge to main

---

## License

MIT License - see LICENSE file for details.

---

## Maintainers

**Max Van Belkum**
- Email: max.vanbelkum@vanderbilt.edu
- GitHub: [@vanbelkummax](https://github.com/vanbelkummax)
- Role: Primary developer and maintainer

**Yuankai Huo Lab**
- Institution: Vanderbilt University
- Department: Computer Science
- Focus: Computational pathology and spatial transcriptomics

---

## References

### Related Projects

- **Img2ST**: Spatial transcriptomics prediction from H&E
- **Hist2ST**: Deep learning for spatial gene expression
- **Visium HD**: High-resolution spatial transcriptomics platform

### Key Publications

1. Huo et al. "Img2ST: Predicting spatial transcriptomics from histology images"
2. Landman et al. "Medical image harmonization methods"
3. Lau et al. "CRC spatial atlas and tumor microenvironment"

---

*Last updated: 2025-12-25*
*Version: 1.0.0-mvp*
