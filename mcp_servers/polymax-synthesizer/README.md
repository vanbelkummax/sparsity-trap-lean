# PolyMaX Synthesizer

**Automated research synthesis and manuscript generation from computational biology repositories.**

Transform your computational research into publication-ready manuscripts with AI-powered domain synthesis, literature integration, and constraint-aware manuscript generation.

---

## Overview

PolyMaX Synthesizer is an MCP (Model Context Protocol) server that automates the workflow from computational results to manuscript draft. It analyzes your research repository, integrates relevant literature, and generates LaTeX manuscripts with proper citations and constraint satisfaction.

**Key Features**:
- **Automated Repository Analysis**: Detects research domains, tables, figures, and README content
- **Literature Discovery**: Finds relevant papers from PubMed, bioRxiv, and Vanderbilt faculty
- **Domain Synthesis**: Combines your results with literature into coherent knowledge
- **Manuscript Generation**: Creates publication-ready LaTeX with proper citations
- **Constraint Satisfaction**: Ensures manuscript values match your actual results
- **Database-Driven**: Persistent storage for reproducible workflows

---

## Quick Start

### Installation

```bash
# Clone or navigate to the repository
cd /home/user/mcp_servers/polymax-synthesizer

# Install dependencies
pip install -r requirements.txt

# Initialize database
python3 -c "from database import init_database; init_database('papers.db')"

# Verify installation
pytest test_database.py
```

### Add to Claude Code

Add to your `~/.claude.json` under the `/home/user` project:

```json
{
  "projects": {
    "/home/user": {
      "mcpServers": {
        "polymax-synthesizer": {
          "type": "stdio",
          "command": "python3",
          "args": ["/home/user/mcp_servers/polymax-synthesizer/server.py"],
          "env": {}
        }
      }
    }
  }
}
```

Restart Claude Code to load the server.

---

## Complete Usage Example

### Step 1: Analyze Repository

```python
# In Claude Code, use the MCP tool:
mcp__polymax-synthesizer__analyze_repo(
    repo_path="/home/user/sparsity-trap-manuscript"
)
```

**Returns**:
```json
{
  "detected_mode": "primary_research",
  "repo_structure": {
    "has_results": true,
    "has_figures": true,
    "table_count": 3,
    "figure_count": 9
  },
  "detected_domains": ["spatial-transcriptomics", "loss-functions"],
  "suggested_queries": [
    "spatial transcriptomics prediction from histology",
    "loss functions for sparse gene expression"
  ]
}
```

### Step 2: Ingest Results

```python
mcp__polymax-synthesizer__ingest_results(
    repo_path="/home/user/sparsity-trap-manuscript",
    tables_subdir="tables"
)
```

**Returns**:
```json
{
  "total_experiments": 1,
  "total_results": 50,
  "metrics_summary": {
    "SSIM_Poisson": {"mean": 0.542, "std": 0.019},
    "SSIM_MSE": {"mean": 0.200, "std": 0.012}
  }
}
```

### Step 3: Discover Literature

```python
# Targeted mode (fast, 3 papers per query)
mcp__polymax-synthesizer__discover_literature(
    queries=[
        "spatial transcriptomics prediction histology",
        "Poisson loss sparse gene expression"
    ],
    mode="targeted",
    papers_per_query=3
)

# OR comprehensive mode (thorough, 10 papers per query)
mcp__polymax-synthesizer__discover_literature(
    queries=[
        "spatial transcriptomics Img2ST Hist2ST",
        "MSE vs Poisson loss gene expression",
        "2um Visium HD spatial resolution"
    ],
    mode="comprehensive",
    papers_per_query=10
)
```

**Returns**:
```json
{
  "total_papers_found": 18,
  "queries_processed": 3,
  "papers_by_source": {
    "pubmed": 12,
    "vanderbilt": 6
  }
}
```

### Step 4: Extract Papers

```python
mcp__polymax-synthesizer__extract_papers()
```

**Returns**:
```json
{
  "total_papers": 18,
  "successfully_extracted": 16,
  "failed": 2
}
```

### Step 5: Synthesize Domains

```python
mcp__polymax-synthesizer__synthesize_domains()
```

**Returns**:
```json
{
  "domains_synthesized": 2,
  "total_papers_analyzed": 16,
  "synthesis_summary": {
    "spatial-transcriptomics": "8 papers",
    "loss-functions": "8 papers"
  }
}
```

### Step 6: Generate Manuscript

```python
mcp__polymax-synthesizer__generate_manuscript(
    output_dir="/home/user/manuscript_draft",
    sections=["introduction", "methods", "results", "discussion"]
)
```

**Returns**:
```json
{
  "sections_generated": 4,
  "output_path": "/home/user/manuscript_draft/manuscript.tex",
  "total_citations": 16,
  "constraint_satisfaction": {
    "values_matched": 12,
    "values_total": 12
  }
}
```

---

## Database Schema

### Core Tables

**experiments**
- `id`: Auto-incrementing primary key
- `repo_path`: Path to research repository
- `experiment_name`: Name extracted from README
- `description`: Research description
- `domains`: JSON array of detected domains
- `created_at`: Timestamp

**results**
- `id`: Auto-incrementing primary key
- `experiment_id`: Foreign key to experiments
- `gene_name`: Gene symbol (e.g., TSPAN8)
- `metric_name`: Metric type (e.g., SSIM_Poisson)
- `metric_value`: Numerical value
- `category`: Gene category (Epithelial, Immune, etc.)
- `metadata`: JSON for additional fields

**papers**
- `id`: Auto-incrementing primary key
- `pmid`: PubMed ID (unique)
- `title`: Paper title
- `authors`: Author list
- `year`: Publication year
- `abstract`: Abstract text
- `full_text`: Extracted full text
- `source`: Discovery source (pubmed, vanderbilt, etc.)
- `domains`: JSON array of relevant domains

**domain_syntheses**
- `id`: Auto-incrementing primary key
- `domain_name`: Domain identifier
- `synthesis`: Combined knowledge synthesis
- `paper_ids`: JSON array of paper IDs used
- `experiment_ids`: JSON array of experiment IDs
- `created_at`: Timestamp

---

## Tool Reference

### analyze_repo

Analyzes a research repository to detect mode, domains, and structure.

**Parameters**:
- `repo_path` (str): Absolute path to repository

**Returns**:
- `detected_mode`: "primary_research" or "literature_review"
- `repo_structure`: Tables, figures, code counts
- `detected_domains`: List of domain keywords
- `suggested_queries`: Recommended literature searches

---

### ingest_results

Ingests experimental results from CSV tables.

**Parameters**:
- `repo_path` (str): Repository path
- `tables_subdir` (str, optional): Subdirectory with tables (default: "tables")
- `db_path` (str, optional): Database path (default: "papers.db")

**Returns**:
- `total_experiments`: Number of experiments created
- `total_results`: Number of results ingested
- `metrics_summary`: Statistics for each metric

---

### discover_literature

Discovers relevant papers using multiple sources.

**Parameters**:
- `queries` (list[str]): Search queries
- `mode` (str): "targeted" (fast) or "comprehensive" (thorough)
- `papers_per_query` (int): Papers to retrieve per query
- `db_path` (str, optional): Database path

**Returns**:
- `total_papers_found`: Total unique papers
- `queries_processed`: Number of queries executed
- `papers_by_source`: Breakdown by source

**Sources**:
- PubMed (via Entrez)
- bioRxiv (via API)
- Vanderbilt Professors MCP (Huo, Landman, Lau, Hwang, Sarkar, Najdawi, Washington)

---

### extract_papers

Extracts full abstracts and metadata for discovered papers.

**Parameters**:
- `db_path` (str, optional): Database path

**Returns**:
- `total_papers`: Papers in database
- `successfully_extracted`: Papers with content
- `failed`: Papers that failed extraction

---

### synthesize_domains

Synthesizes domain knowledge from papers and results.

**Parameters**:
- `db_path` (str, optional): Database path

**Returns**:
- `domains_synthesized`: Number of domains
- `total_papers_analyzed`: Papers used
- `synthesis_summary`: Per-domain statistics

**Process**:
1. Groups papers by domain
2. Combines with experimental results
3. Generates coherent synthesis using Claude
4. Stores in domain_syntheses table

---

### generate_manuscript

Generates a complete LaTeX manuscript.

**Parameters**:
- `output_dir` (str): Output directory path
- `sections` (list[str]): Sections to generate
- `db_path` (str, optional): Database path

**Returns**:
- `sections_generated`: Number of sections created
- `output_path`: Path to manuscript.tex
- `total_citations`: Citation count
- `constraint_satisfaction`: Value matching statistics

**Sections Supported**:
- `introduction`: Background and motivation
- `methods`: Experimental methods
- `results`: Findings and metrics
- `discussion`: Interpretation and implications

**Features**:
- IEEE/MICCAI formatting (via LaTeX Architect MCP)
- Proper `\cite{}` citations
- Constraint satisfaction (values from results table)
- Figure and table references

---

## Troubleshooting

### Database Issues

**Error**: `no such table: experiments`

**Solution**: Initialize database:
```bash
python3 -c "from database import init_database; init_database('papers.db')"
```

---

### MCP Server Not Loading

**Check**:
1. Server path in `~/.claude.json` is correct
2. Python dependencies installed
3. Run `pytest test_server.py` to verify

**Debug**:
```bash
# Test server directly
python3 server.py
# Should start without errors
```

---

### Literature Discovery Returns No Papers

**Common Causes**:
- Network issues with PubMed API
- Query too specific
- Vanderbilt MCP server not running

**Solution**:
```python
# Use broader queries
mcp__polymax-synthesizer__discover_literature(
    queries=["spatial transcriptomics"],  # Simpler
    mode="targeted",
    papers_per_query=5
)
```

---

### Manuscript Generation Fails

**Check**:
1. Domains synthesized: `SELECT * FROM domain_syntheses`
2. Results ingested: `SELECT COUNT(*) FROM results`
3. Papers extracted: `SELECT COUNT(*) FROM papers WHERE abstract IS NOT NULL`

**Missing Prerequisites**:
- Run steps 1-5 before generating manuscript
- At least 1 domain synthesis required
- At least 1 paper with content required

---

## Advanced Usage

### Custom Database Path

```python
# Use custom database location
mcp__polymax-synthesizer__ingest_results(
    repo_path="/path/to/repo",
    db_path="/path/to/custom.db"
)

# All subsequent tools must use same db_path
mcp__polymax-synthesizer__discover_literature(
    queries=["query"],
    db_path="/path/to/custom.db"
)
```

---

### Programmatic Access

```python
# Direct Python usage (without MCP)
from repo_analyzer import analyze_repository
from results_ingester import ingest_results_data
from domain_synthesizer import synthesize_all_domains

# Analyze
result = analyze_repository("/path/to/repo")

# Ingest
ingest_results_data("/path/to/repo/tables", "papers.db")

# Synthesize
synthesize_all_domains("papers.db")
```

---

## Development

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest test_database.py
pytest test_server.py

# End-to-end test (requires sparsity-trap-manuscript)
pytest test_end_to_end.py -v

# With coverage
pytest --cov=. --cov-report=html
```

### Adding New Domains

Edit `repo_analyzer.py`:

```python
DOMAIN_KEYWORDS = {
    "your-domain": [
        "keyword1",
        "keyword2",
        "keyword3"
    ]
}
```

### Customizing Prompts

Edit prompts in `prompts/` directory:
- `prompts/domain_synthesis.txt`: Domain synthesis instructions
- `prompts/introduction.txt`: Introduction section template
- `prompts/methods.txt`: Methods section template
- `prompts/results.txt`: Results section template
- `prompts/discussion.txt`: Discussion section template

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design.

**Components**:
- **Database Layer**: SQLite with schema.sql
- **Repository Analysis**: Domain detection, structure parsing
- **Literature Discovery**: Multi-source paper retrieval
- **Paper Extraction**: Abstract and metadata fetching
- **Domain Synthesis**: Knowledge integration
- **Manuscript Generation**: LaTeX output with constraints

---

## Citation

```bibtex
@software{vanbelkum2025polymax,
  author = {Van Belkum, Max},
  title = {PolyMaX Synthesizer: Automated Research Synthesis for Computational Biology},
  year = {2025},
  url = {https://github.com/vanbelkummax/polymax-synthesizer}
}
```

---

## License

MIT License

---

## Contact

Max Van Belkum
MD-PhD Student, Vanderbilt University
max.vanbelkum@vanderbilt.edu
[@vanbelkummax](https://github.com/vanbelkummax)

---

## Acknowledgments

Built with:
- **MCP (Model Context Protocol)**: Tool integration framework
- **Claude Sonnet 4.5**: AI-powered synthesis
- **Vanderbilt Professors MCP**: Faculty paper search
- **LaTeX Architect MCP**: IEEE/MICCAI formatting
- **PubMed/Entrez**: Literature discovery
- **bioRxiv API**: Preprint search

Special thanks to the Huo Lab (Vanderbilt) for spatial transcriptomics research foundations.
