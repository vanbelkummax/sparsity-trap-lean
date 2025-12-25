# PolyMaX Synthesizer MCP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal**: Build a dual-mode MCP server that generates publication-ready manuscripts from GitHub repositories with deep literature synthesis.

**Architecture**: Standalone MCP server extending Vanderbilt Professors database, using Claude Opus 4.5 for domain synthesis and parallel subagents for paper extraction.

**Tech Stack**: Python 3.11+, SQLite, MCP SDK, Anthropic SDK, pandas (CSV parsing), pathlib, json

---

## Phase 1: Database Schema (Tasks 1-8)

### Task 1: Create Database Schema File

**Files:**
- Create: `/home/user/mcp_servers/polymax-synthesizer/schema.sql`
- Create: `/home/user/mcp_servers/polymax-synthesizer/__init__.py` (empty)

**Step 1: Write the database schema**

Create `/home/user/mcp_servers/polymax-synthesizer/schema.sql`:

```sql
-- PolyMaX Synthesizer Database Schema
-- Extends Vanderbilt Professors MCP for manuscript generation

-- Professors table (new, replaces JSON storage)
CREATE TABLE IF NOT EXISTS professors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    affiliation TEXT,
    email TEXT,
    google_scholar_url TEXT,
    h_index INTEGER,
    domains TEXT,  -- JSON array
    research_keywords TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, affiliation)
);

-- Papers table (new, full-text in BLOB)
CREATE TABLE IF NOT EXISTS papers (
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
    full_text_markdown TEXT,  -- Full paper content
    pdf_path TEXT,
    professor_id INTEGER,
    domain TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (professor_id) REFERENCES professors(id)
);

CREATE INDEX IF NOT EXISTS idx_papers_pmid ON papers(pmid);
CREATE INDEX IF NOT EXISTS idx_papers_professor ON papers(professor_id);
CREATE INDEX IF NOT EXISTS idx_papers_domain ON papers(domain);

-- Paper extractions (hierarchical JSON)
CREATE TABLE IF NOT EXISTS paper_extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL,
    high_level TEXT,  -- JSON: {main_claim, novelty, contribution}
    mid_level TEXT,   -- JSON: {stats, methods}
    low_level TEXT,   -- JSON: {quotes}
    code_methods TEXT,  -- JSON: {algorithms, equations, hyperparameters}
    extraction_model TEXT DEFAULT 'claude-opus-4-5-20251101',
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paper_id) REFERENCES papers(id)
);

-- Domains taxonomy
CREATE TABLE IF NOT EXISTS domains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    keywords TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Synthesis runs (orchestration metadata)
CREATE TABLE IF NOT EXISTS synthesis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_path TEXT NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('primary_research', 'review')),
    detected_domains TEXT,  -- JSON array
    main_finding TEXT,  -- JSON for primary research
    research_question TEXT,
    status TEXT DEFAULT 'analyzing' CHECK(status IN ('analyzing', 'discovering', 'extracting', 'synthesizing', 'writing', 'complete')),
    current_stage TEXT,
    professors_found INTEGER DEFAULT 0,
    papers_found INTEGER DEFAULT 0,
    papers_extracted INTEGER DEFAULT 0,
    domains_synthesized INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Domain syntheses (reusable 1-page summaries)
CREATE TABLE IF NOT EXISTS domain_syntheses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synthesis_run_id INTEGER NOT NULL,
    domain_id INTEGER NOT NULL,
    summary_markdown TEXT,
    key_findings TEXT,  -- JSON
    cross_field_insights TEXT,  -- JSON
    papers_analyzed INTEGER,
    paper_ids TEXT,  -- JSON array
    synthesized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (synthesis_run_id) REFERENCES synthesis_runs(id),
    FOREIGN KEY (domain_id) REFERENCES domains(id)
);

-- Manuscripts (versioned LaTeX output)
CREATE TABLE IF NOT EXISTS manuscripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synthesis_run_id INTEGER NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('research', 'review', 'extended-review', 'hypothesis')),
    version INTEGER DEFAULT 1,
    latex_content TEXT,
    abstract TEXT,
    introduction TEXT,
    methods TEXT,
    results TEXT,
    discussion TEXT,
    word_count INTEGER,
    citation_count INTEGER,
    figure_count INTEGER,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (synthesis_run_id) REFERENCES synthesis_runs(id)
);
```

**Step 2: Create empty __init__.py**

```bash
touch /home/user/mcp_servers/polymax-synthesizer/__init__.py
```

**Step 3: Commit**

```bash
cd /home/user
git add mcp_servers/polymax-synthesizer/schema.sql mcp_servers/polymax-synthesizer/__init__.py
git commit -m "feat: add polymax-synthesizer database schema

- 7 tables: professors, papers, paper_extractions, domains, domain_syntheses, synthesis_runs, manuscripts
- Full-text storage in TEXT columns (not files)
- Hierarchical extraction JSON structure
- Synthesis orchestration metadata"
```

---

### Task 2: Create Database Module

**Files:**
- Create: `/home/user/mcp_servers/polymax-synthesizer/database.py`

**Step 1: Write failing test**

Create `/home/user/mcp_servers/polymax-synthesizer/test_database.py`:

```python
"""Tests for database module."""
import pytest
import sqlite3
from pathlib import Path
from database import Database, init_database

def test_init_database_creates_tables(tmp_path):
    """Test that init_database creates all required tables."""
    db_path = tmp_path / "test.db"
    init_database(str(db_path))

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check that tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    expected_tables = {
        'professors', 'papers', 'paper_extractions',
        'domains', 'domain_syntheses', 'synthesis_runs', 'manuscripts'
    }

    assert expected_tables.issubset(tables)
    conn.close()

def test_database_context_manager(tmp_path):
    """Test Database class context manager."""
    db_path = tmp_path / "test.db"
    init_database(str(db_path))

    with Database(str(db_path)) as db:
        assert db.conn is not None
        # Test a simple query
        cursor = db.conn.execute("SELECT COUNT(*) FROM professors")
        count = cursor.fetchone()[0]
        assert count == 0
```

**Step 2: Run test to verify it fails**

```bash
cd /home/user/mcp_servers/polymax-synthesizer
python -m pytest test_database.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'database'"

**Step 3: Write minimal implementation**

Create `/home/user/mcp_servers/polymax-synthesizer/database.py`:

```python
"""Database management for PolyMaX Synthesizer."""
import sqlite3
from pathlib import Path
from typing import Optional

SCHEMA_FILE = Path(__file__).parent / "schema.sql"

def init_database(db_path: str) -> None:
    """Initialize database with schema."""
    schema = SCHEMA_FILE.read_text()
    conn = sqlite3.connect(db_path)
    conn.executescript(schema)
    conn.commit()
    conn.close()

class Database:
    """Database context manager."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest test_database.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add database.py test_database.py
git commit -m "feat: add database initialization and context manager

- init_database() creates all tables from schema.sql
- Database context manager for connection handling
- Tests verify table creation"
```

---

### Task 3: Migrate Existing Vanderbilt Papers to Database

**Files:**
- Create: `/home/user/mcp_servers/polymax-synthesizer/migrate_existing.py`
- Modify: `/home/user/mcp_servers/polymax-synthesizer/test_database.py` (add migration test)

**Step 1: Write failing test**

Add to `/home/user/mcp_servers/polymax-synthesizer/test_database.py`:

```python
import json

def test_migrate_professor_papers(tmp_path):
    """Test migrating professor papers from JSON to database."""
    from migrate_existing import migrate_professor_papers

    # Create mock JSON data
    papers_data = [
        {
            "pmid": "12345678",
            "title": "Test Paper",
            "year": 2023,
            "authors": ["Smith J", "Doe A"]
        }
    ]
    json_file = tmp_path / "all_papers.json"
    json_file.write_text(json.dumps(papers_data))

    # Migrate to database
    db_path = tmp_path / "test.db"
    init_database(str(db_path))

    professor_id = migrate_professor_papers(
        str(db_path),
        "Test Professor",
        "Test University",
        str(json_file)
    )

    # Verify migration
    with Database(str(db_path)) as db:
        cursor = db.conn.execute("SELECT COUNT(*) FROM papers")
        assert cursor.fetchone()[0] == 1

        cursor = db.conn.execute("SELECT * FROM papers WHERE pmid=?", ("12345678",))
        paper = cursor.fetchone()
        assert paper["title"] == "Test Paper"
        assert paper["professor_id"] == professor_id
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest test_database.py::test_migrate_professor_papers -v
```

Expected: FAIL with "ImportError: cannot import name 'migrate_professor_papers'"

**Step 3: Write minimal implementation**

Create `/home/user/mcp_servers/polymax-synthesizer/migrate_existing.py`:

```python
"""Migrate existing Vanderbilt professor papers to database."""
import json
import sqlite3
from pathlib import Path
from database import Database

def migrate_professor_papers(
    db_path: str,
    professor_name: str,
    affiliation: str,
    json_file: str
) -> int:
    """
    Migrate papers from JSON to database.

    Returns:
        professor_id
    """
    with Database(db_path) as db:
        # Insert or get professor
        cursor = db.conn.execute(
            "INSERT OR IGNORE INTO professors (name, affiliation) VALUES (?, ?)",
            (professor_name, affiliation)
        )
        db.conn.commit()

        cursor = db.conn.execute(
            "SELECT id FROM professors WHERE name=? AND affiliation=?",
            (professor_name, affiliation)
        )
        professor_id = cursor.fetchone()["id"]

        # Load papers from JSON
        with open(json_file) as f:
            papers = json.load(f)
            if isinstance(papers, dict):
                papers = list(papers.values())

        # Insert papers
        for paper in papers:
            db.conn.execute(
                """INSERT OR IGNORE INTO papers
                   (pmid, title, year, authors, professor_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    paper.get("pmid"),
                    paper.get("title"),
                    paper.get("year"),
                    json.dumps(paper.get("authors", [])),
                    professor_id
                )
            )

        db.conn.commit()
        return professor_id

def migrate_all_professors(db_path: str):
    """Migrate all Vanderbilt professors to database."""
    professors = [
        ("Yuankai Huo", "Vanderbilt University", "/home/user/yuankai_huo_papers/metadata/all_papers.json"),
        ("Ken Lau", "Vanderbilt University", "/home/user/ken_lau_papers/metadata/all_papers.json"),
        ("Tae Hyun Hwang", "Vanderbilt University", "/home/user/vanderbilt_professors_mcp/data/hwang/metadata/all_papers.json"),
        ("Fedaa Najdawi", "Vanderbilt University", "/home/user/vanderbilt_professors_mcp/data/najdawi/metadata/all_papers.json"),
        ("Hirak Sarkar", "Vanderbilt University", "/home/user/vanderbilt_professors_mcp/data/sarkar/metadata/all_papers.json"),
        ("Mary Kay Washington", "Vanderbilt University", "/home/user/vanderbilt_professors_mcp/data/washington/metadata/all_papers.json"),
    ]

    for name, affiliation, json_file in professors:
        if Path(json_file).exists():
            print(f"Migrating {name}...")
            migrate_professor_papers(db_path, name, affiliation, json_file)
            print(f"  ✓ {name} migrated")

if __name__ == "__main__":
    import sys
    from database import init_database

    db_path = sys.argv[1] if len(sys.argv) > 1 else "/home/user/mcp_servers/polymax-synthesizer/papers.db"

    print("Initializing database...")
    init_database(db_path)

    print("Migrating professors...")
    migrate_all_professors(db_path)

    # Print summary
    with Database(db_path) as db:
        cursor = db.conn.execute("SELECT COUNT(*) FROM professors")
        prof_count = cursor.fetchone()[0]
        cursor = db.conn.execute("SELECT COUNT(*) FROM papers")
        paper_count = cursor.fetchone()[0]
        print(f"\n✓ Migration complete: {prof_count} professors, {paper_count} papers")
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest test_database.py::test_migrate_professor_papers -v
```

Expected: PASS

**Step 5: Run migration script**

```bash
cd /home/user/mcp_servers/polymax-synthesizer
python migrate_existing.py
```

Expected output:
```
Initializing database...
Migrating professors...
Migrating Yuankai Huo...
  ✓ Yuankai Huo migrated
Migrating Ken Lau...
  ✓ Ken Lau migrated
...
✓ Migration complete: 6 professors, 800+ papers
```

**Step 6: Commit**

```bash
git add migrate_existing.py test_database.py papers.db
git commit -m "feat: migrate existing Vanderbilt papers to database

- Migrate 6 professors from JSON to SQLite
- ~800 papers now in database
- Migration script with progress reporting
- Test coverage for migration logic"
```

---

## Phase 2: Core MCP Server (Tasks 4-11)

### Task 4: Create MCP Server Skeleton

**Files:**
- Create: `/home/user/mcp_servers/polymax-synthesizer/server.py`
- Create: `/home/user/mcp_servers/polymax-synthesizer/test_server.py`

**Step 1: Write failing test**

Create `/home/user/mcp_servers/polymax-synthesizer/test_server.py`:

```python
"""Tests for MCP server."""
import pytest
from mcp.types import Tool

def test_server_has_required_tools():
    """Test that server exposes all required tools."""
    from server import server

    expected_tools = {
        'analyze_repo',
        'ingest_results',
        'discover_literature',
        'extract_papers',
        'synthesize_domains',
        'generate_section',
        'generate_manuscript'
    }

    # This will fail until we implement the tools
    tools = server.list_tools()
    tool_names = {tool.name for tool in tools}

    assert expected_tools.issubset(tool_names)
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest test_server.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'server'"

**Step 3: Write minimal implementation**

Create `/home/user/mcp_servers/polymax-synthesizer/server.py`:

```python
#!/usr/bin/env python3
"""PolyMaX Synthesizer MCP Server."""
import json
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from database import Database

# Database path
DB_PATH = Path(__file__).parent / "papers.db"

# Initialize server
server = Server("polymax-synthesizer")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="analyze_repo",
            description="Analyze repository structure and detect operating mode",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "mode": {"type": "string", "enum": ["auto", "primary_research", "review"]}
                },
                "required": ["repo_path"]
            }
        ),
        Tool(
            name="ingest_results",
            description="Load experimental results from repository (primary research mode)",
            inputSchema={
                "type": "object",
                "properties": {
                    "synthesis_run_id": {"type": "integer"},
                    "data_sources": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["synthesis_run_id"]
            }
        ),
        Tool(
            name="discover_literature",
            description="Find professors and papers (mode-adaptive: targeted or broad)",
            inputSchema={
                "type": "object",
                "properties": {
                    "synthesis_run_id": {"type": "integer"},
                    "mode": {"type": "string", "enum": ["targeted", "broad"]},
                    "search_queries": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["synthesis_run_id", "mode"]
            }
        ),
        Tool(
            name="extract_papers",
            description="Hierarchical extraction via parallel subagents",
            inputSchema={
                "type": "object",
                "properties": {
                    "synthesis_run_id": {"type": "integer"},
                    "paper_ids": {"type": "array", "items": {"type": "integer"}},
                    "extraction_depth": {"type": "string", "enum": ["full", "mid", "high_only"]}
                },
                "required": ["synthesis_run_id"]
            }
        ),
        Tool(
            name="synthesize_domains",
            description="Generate 1-page synthesis per domain with cross-field insights",
            inputSchema={
                "type": "object",
                "properties": {
                    "synthesis_run_id": {"type": "integer"},
                    "domain_ids": {"type": "array", "items": {"type": "integer"}}
                },
                "required": ["synthesis_run_id"]
            }
        ),
        Tool(
            name="generate_section",
            description="Write individual manuscript section with data grounding",
            inputSchema={
                "type": "object",
                "properties": {
                    "synthesis_run_id": {"type": "integer"},
                    "section": {"type": "string", "enum": ["introduction", "methods", "results", "discussion", "abstract"]},
                    "mode": {"type": "string", "enum": ["primary_research", "review"]}
                },
                "required": ["synthesis_run_id", "section", "mode"]
            }
        ),
        Tool(
            name="generate_manuscript",
            description="Orchestrate full manuscript generation with checkpoints",
            inputSchema={
                "type": "object",
                "properties": {
                    "synthesis_run_id": {"type": "integer"},
                    "mode": {"type": "string", "enum": ["research", "review", "extended-review", "hypothesis"]},
                    "sections": {"type": "array", "items": {"type": "string"}},
                    "output_path": {"type": "string"}
                },
                "required": ["synthesis_run_id", "mode"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls (stubs for now)."""
    return [TextContent(type="text", text=f"Tool '{name}' not yet implemented")]

async def main():
    """Run server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest test_server.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add server.py test_server.py
git commit -m "feat: add MCP server skeleton with 7 tools

- analyze_repo, ingest_results, discover_literature
- extract_papers, synthesize_domains
- generate_section, generate_manuscript
- All tools return stub responses for now"
```

---

### Task 5: Implement analyze_repo Tool

**Files:**
- Modify: `/home/user/mcp_servers/polymax-synthesizer/server.py`
- Create: `/home/user/mcp_servers/polymax-synthesizer/repo_analyzer.py`
- Modify: `/home/user/mcp_servers/polymax-synthesizer/test_server.py`

**Step 1: Write failing test**

Add to `/home/user/mcp_servers/polymax-synthesizer/test_server.py`:

```python
def test_analyze_repo_primary_research(tmp_path):
    """Test analyze_repo detects primary research mode."""
    from repo_analyzer import analyze_repository

    # Create mock repo structure
    repo = tmp_path / "test-repo"
    repo.mkdir()
    (repo / "tables").mkdir()
    (repo / "figures").mkdir()
    (repo / "tables" / "results.csv").write_text("gene,ssim\nGENE1,0.5")
    (repo / "figures" / "fig1.png").write_bytes(b"fake image")
    (repo / "README.md").write_text("# Test\nThis paper studies spatial transcriptomics.")

    result = analyze_repository(str(repo))

    assert result["detected_mode"] == "primary_research"
    assert result["repo_structure"]["has_results"] == True
    assert "spatial-transcriptomics" in result["detected_domains"]
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest test_server.py::test_analyze_repo_primary_research -v
```

Expected: FAIL with "ImportError: cannot import name 'analyze_repository'"

**Step 3: Write minimal implementation**

Create `/home/user/mcp_servers/polymax-synthesizer/repo_analyzer.py`:

```python
"""Repository analysis for mode detection."""
import json
from pathlib import Path
from typing import Dict, Any

def analyze_repository(repo_path: str) -> Dict[str, Any]:
    """
    Analyze repository structure and detect operating mode.

    Returns:
        {
            "detected_mode": "primary_research" | "review",
            "repo_structure": {...},
            "detected_domains": [...]
        }
    """
    repo = Path(repo_path)

    # Check for results data
    has_tables = (repo / "tables").exists()
    has_figures = (repo / "figures").exists()
    has_readme = (repo / "README.md").exists()

    tables = []
    if has_tables:
        tables = [f.name for f in (repo / "tables").glob("*.csv")]

    figures = []
    if has_figures:
        figures = [f.name for f in (repo / "figures").glob("*.png")]

    # Detect mode
    has_results = has_tables and has_figures and len(tables) > 0
    detected_mode = "primary_research" if has_results else "review"

    # Simple domain detection from README
    detected_domains = []
    if has_readme:
        readme_text = (repo / "README.md").read_text().lower()
        domain_keywords = {
            "spatial-transcriptomics": ["spatial transcriptomics", "visium"],
            "loss-functions": ["loss function", "mse", "poisson"],
            "deep-learning": ["deep learning", "neural network"],
            "computational-pathology": ["pathology", "histology"]
        }
        for domain, keywords in domain_keywords.items():
            if any(kw in readme_text for kw in keywords):
                detected_domains.append(domain)

    return {
        "detected_mode": detected_mode,
        "repo_structure": {
            "has_results": has_results,
            "tables": tables,
            "figures": figures,
            "readme_exists": has_readme
        },
        "detected_domains": detected_domains
    }
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest test_server.py::test_analyze_repo_primary_research -v
```

Expected: PASS

**Step 5: Integrate into server.py**

Modify `/home/user/mcp_servers/polymax-synthesizer/server.py`:

```python
# Add import at top
from repo_analyzer import analyze_repository

# Replace stub in call_tool()
@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""

    if name == "analyze_repo":
        repo_path = arguments.get("repo_path")
        mode = arguments.get("mode", "auto")

        # Analyze repository
        analysis = analyze_repository(repo_path)

        # Create synthesis run
        with Database(DB_PATH) as db:
            cursor = db.conn.execute(
                """INSERT INTO synthesis_runs
                   (repo_path, mode, detected_domains, status)
                   VALUES (?, ?, ?, 'analyzing')""",
                (
                    repo_path,
                    analysis["detected_mode"],
                    json.dumps(analysis["detected_domains"])
                )
            )
            db.conn.commit()
            synthesis_run_id = cursor.lastrowid

        result = {
            "synthesis_run_id": synthesis_run_id,
            **analysis,
            "next_step": "Call ingest_results to load experimental data" if analysis["detected_mode"] == "primary_research" else "Call discover_literature"
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # Other tools return stub
    return [TextContent(type="text", text=f"Tool '{name}' not yet implemented")]
```

**Step 6: Test end-to-end with sparsity-trap repo**

```bash
# Start server in background
cd /home/user/mcp_servers/polymax-synthesizer
python server.py &
SERVER_PID=$!

# Call tool via MCP (simulate)
# In real usage, Claude Code will call this
# For now, just verify it doesn't crash

kill $SERVER_PID
```

**Step 7: Commit**

```bash
git add repo_analyzer.py server.py test_server.py
git commit -m "feat: implement analyze_repo tool

- Detects primary_research vs review mode
- Parses repository structure (tables, figures, README)
- Simple keyword-based domain detection
- Creates synthesis_run record in database
- Returns synthesis_run_id for next steps"
```

---

### Task 6: Implement ingest_results Tool

**Files:**
- Create: `/home/user/mcp_servers/polymax-synthesizer/results_ingester.py`
- Modify: `/home/user/mcp_servers/polymax-synthesizer/server.py`
- Modify: `/home/user/mcp_servers/polymax-synthesizer/test_server.py`

**Step 1: Write failing test**

Add to test_server.py:

```python
import pandas as pd

def test_ingest_results_from_csv(tmp_path):
    """Test ingesting results from CSV tables."""
    from results_ingester import ingest_results_data

    # Create mock table
    csv_file = tmp_path / "results.csv"
    df = pd.DataFrame({
        "Gene": ["GENE1", "GENE2"],
        "SSIM_Poisson": [0.542, 0.601],
        "SSIM_MSE": [0.200, 0.189],
        "Delta_SSIM": [0.342, 0.412]
    })
    df.to_csv(csv_file, index=False)

    result = ingest_results_data(str(tmp_path))

    assert len(result["key_findings"]) > 0
    assert any("SSIM" in f["claim"] for f in result["key_findings"])
    assert len(result["constraints"]) > 0
```

**Step 2: Run test**

```bash
python -m pytest test_server.py::test_ingest_results_from_csv -v
```

Expected: FAIL

**Step 3: Implement**

Create `/home/user/mcp_servers/polymax-synthesizer/results_ingester.py`:

```python
"""Ingest experimental results from repository."""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any

def ingest_results_data(repo_path: str) -> Dict[str, Any]:
    """
    Parse CSV tables and README to extract key findings.

    Returns:
        {
            "key_findings": [{"claim": ..., "stat": ..., "source": ...}],
            "figures_catalog": [...],
            "constraints": [...]
        }
    """
    repo = Path(repo_path)
    key_findings = []
    constraints = []
    figures_catalog = []

    # Parse CSV tables
    tables_dir = repo / "tables"
    if tables_dir.exists():
        for csv_file in tables_dir.glob("*.csv"):
            df = pd.read_csv(csv_file)

            # Extract statistics from table
            if "SSIM" in df.columns or any("SSIM" in col for col in df.columns):
                # Find SSIM columns
                ssim_cols = [col for col in df.columns if "SSIM" in col]

                for col in ssim_cols:
                    mean_val = df[col].mean()
                    key_findings.append({
                        "claim": f"Mean {col}: {mean_val:.3f}",
                        "stat": f"{col} = {mean_val:.3f}",
                        "source": f"tables/{csv_file.name}",
                        "constraint": f"Must cite exact values from {csv_file.name}"
                    })

                # Constraint: values must match table
                constraints.append(f"All values must match {csv_file.name} exactly")
                constraints.append(f"Gene names limited to those in {csv_file.name}")

    # Catalog figures
    figures_dir = repo / "figures"
    if figures_dir.exists():
        for fig_file in figures_dir.rglob("*.png"):
            figures_catalog.append({
                "filename": str(fig_file.relative_to(repo)),
                "suggested_caption": fig_file.stem.replace("_", " ").title()
            })

    return {
        "key_findings": key_findings,
        "figures_catalog": figures_catalog,
        "constraints": constraints
    }
```

**Step 4: Run test**

```bash
python -m pytest test_server.py::test_ingest_results_from_csv -v
```

Expected: PASS

**Step 5: Integrate into server**

Modify server.py:

```python
from results_ingester import ingest_results_data

# In call_tool()
elif name == "ingest_results":
    synthesis_run_id = arguments.get("synthesis_run_id")

    # Get repo path from synthesis_run
    with Database(DB_PATH) as db:
        cursor = db.conn.execute(
            "SELECT repo_path FROM synthesis_runs WHERE id=?",
            (synthesis_run_id,)
        )
        row = cursor.fetchone()
        if not row:
            return [TextContent(type="text", text=f"Synthesis run {synthesis_run_id} not found")]
        repo_path = row["repo_path"]

    # Ingest results
    ingested = ingest_results_data(repo_path)

    # Store in database
    with Database(DB_PATH) as db:
        db.conn.execute(
            "UPDATE synthesis_runs SET main_finding=?, status='discovering' WHERE id=?",
            (json.dumps(ingested), synthesis_run_id)
        )
        db.conn.commit()

    result = {
        "synthesis_run_id": synthesis_run_id,
        **ingested,
        "next_step": "Call discover_literature with targeted mode"
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
```

**Step 6: Commit**

```bash
git add results_ingester.py server.py test_server.py
git commit -m "feat: implement ingest_results tool

- Parses CSV tables to extract key statistics
- Catalogs figure files
- Creates constraints for manuscript generation
- Stores ingested data in synthesis_runs.main_finding"
```

---

### Task 7: Implement discover_literature Tool (Targeted Mode)

**Files:**
- Create: `/home/user/mcp_servers/polymax-synthesizer/literature_discovery.py`
- Modify: `/home/user/mcp_servers/polymax-synthesizer/server.py`
- Modify: `/home/user/mcp_servers/polymax-synthesizer/test_server.py`

**Step 1: Write failing test**

```python
def test_discover_literature_targeted():
    """Test targeted literature discovery."""
    from literature_discovery import discover_targeted_literature

    queries = [
        "Yuankai Huo Img2ST",
        "Poisson loss sparse data"
    ]

    # This uses existing database, so just verify structure
    result = discover_targeted_literature(queries, str(DB_PATH))

    assert "professors_added" in result
    assert "papers_added" in result
    assert "targeted_matches" in result
```

**Step 2: Run test**

```bash
python -m pytest test_server.py::test_discover_literature_targeted -v
```

Expected: FAIL

**Step 3: Implement**

Create `/home/user/mcp_servers/polymax-synthesizer/literature_discovery.py`:

```python
"""Literature discovery (targeted and broad modes)."""
import json
from database import Database
from typing import List, Dict, Any

def discover_targeted_literature(queries: List[str], db_path: str) -> Dict[str, Any]:
    """
    Targeted literature discovery (for primary research mode).

    Searches existing database for papers matching queries.
    In production, would also use WebSearch + PubMed APIs.

    Args:
        queries: List of search queries (e.g., "Yuankai Huo Img2ST")
        db_path: Path to database

    Returns:
        {
            "professors_added": int,
            "papers_added": int,
            "targeted_matches": [...]
        }
    """
    targeted_matches = []
    professors_found = set()
    papers_found = set()

    with Database(db_path) as db:
        for query in queries:
            query_lower = query.lower()
            terms = query_lower.split()

            # Search papers by title
            cursor = db.conn.execute(
                "SELECT p.*, prof.name as professor_name FROM papers p LEFT JOIN professors prof ON p.professor_id = prof.id"
            )

            for row in cursor.fetchall():
                title = (row["title"] or "").lower()
                professor = row["professor_name"] or ""

                # Score by number of matching terms
                score = sum(1 for term in terms if term in title or term in professor.lower())

                if score > 0:
                    professors_found.add(row["professor_id"])
                    papers_found.add(row["id"])

                    # Record match
                    if not any(m["query"] == query and m["paper_id"] == row["id"] for m in targeted_matches):
                        targeted_matches.append({
                            "query": query,
                            "professor": professor,
                            "paper_id": row["id"],
                            "paper_title": row["title"],
                            "pmid": row["pmid"],
                            "score": score
                        })

    # Sort matches by score
    for match_group in targeted_matches:
        if "score" in match_group:
            pass  # Already has score

    return {
        "professors_added": len(professors_found),
        "papers_added": len(papers_found),
        "breakdown_by_domain": {},  # TODO: implement domain breakdown
        "targeted_matches": sorted(targeted_matches, key=lambda x: x.get("score", 0), reverse=True)[:20]
    }

def discover_broad_literature(domains: List[str], db_path: str) -> Dict[str, Any]:
    """
    Broad literature discovery (for review mode).

    TODO: Implement web search + PubMed for each domain.
    For now, just searches existing database.
    """
    # Stub for now
    return {
        "professors_added": 0,
        "papers_added": 0,
        "breakdown_by_domain": {}
    }
```

**Step 4: Run test**

```bash
python -m pytest test_server.py::test_discover_literature_targeted -v
```

Expected: PASS

**Step 5: Integrate into server**

```python
from literature_discovery import discover_targeted_literature, discover_broad_literature

# In call_tool()
elif name == "discover_literature":
    synthesis_run_id = arguments.get("synthesis_run_id")
    mode = arguments.get("mode")
    search_queries = arguments.get("search_queries", [])

    if mode == "targeted":
        result = discover_targeted_literature(search_queries, str(DB_PATH))
    else:
        # Get domains from synthesis_run
        with Database(DB_PATH) as db:
            cursor = db.conn.execute(
                "SELECT detected_domains FROM synthesis_runs WHERE id=?",
                (synthesis_run_id,)
            )
            row = cursor.fetchone()
            domains = json.loads(row["detected_domains"]) if row else []

        result = discover_broad_literature(domains, str(DB_PATH))

    # Update synthesis_run
    with Database(DB_PATH) as db:
        db.conn.execute(
            "UPDATE synthesis_runs SET papers_found=?, status='extracting' WHERE id=?",
            (result["papers_added"], synthesis_run_id)
        )
        db.conn.commit()

    result["synthesis_run_id"] = synthesis_run_id
    result["next_step"] = "Call extract_papers to perform hierarchical extraction"

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
```

**Step 6: Commit**

```bash
git add literature_discovery.py server.py test_server.py
git commit -m "feat: implement discover_literature tool (targeted mode)

- Searches existing database for papers matching queries
- Returns targeted_matches with professor/paper info
- Updates synthesis_run with papers_found count
- Broad mode stubbed for future implementation"
```

---

**Due to length constraints, I'll now summarize the remaining tasks. The full plan would continue in the same detailed format for all remaining phases.**

---

## Phase 3: Paper Extraction System (Tasks 8-10)

### Task 8: Implement Subagent Orchestration for extract_papers

- Create `paper_extractor.py` with `extract_single_paper()` function
- Use Claude API to extract hierarchical data from paper text
- Store extractions in `paper_extractions` table

### Task 9: Create Extraction Prompts

- Create `prompts/extraction_prompts.py` with structured prompts
- High-level, mid-level, low-level, code_methods templates

### Task 10: Integrate extract_papers into Server

- Implement sequential domain processing
- Spawn parallel subagents (via Claude API Task tool)
- Progress tracking and database updates

---

## Phase 4: Domain Synthesis (Tasks 11-12)

### Task 11: Implement Domain Synthesis Logic

- Create `domain_synthesizer.py`
- Use Claude Opus 4.5 to synthesize 1-page markdown per domain
- Store in `domain_syntheses` table

### Task 12: Create Synthesis Prompts

- Cross-field insight prompts
- Transfer learning prompts
- Structured output format

---

## Phase 5: Manuscript Generation (Tasks 13-18)

### Task 13: Create LaTeX Templates

- Create `templates/medical_imaging.tex`
- Create `templates/genomics.tex`
- Create `templates/machine_learning.tex`

### Task 14: Implement Field Detection

- Detect field from domains
- Select appropriate template

### Task 15: Implement generate_section

- Primary research mode: ground in YOUR data
- Review mode: ground in domain syntheses
- Constraint verification

### Task 16: Create Section Generation Prompts

- Results section prompt (with table citations)
- Methods section prompt
- Discussion section prompt (with cross-field insights)

### Task 17: Implement generate_manuscript

- Orchestrate section-by-section generation
- Conversational checkpoints (via returning status to Claude)
- Assemble full LaTeX document

### Task 18: Integrate latex-architect MCP

- Use `mcp__latex-architect__generate_figure_block` for figures
- Use `mcp__latex-architect__check_spatial_inclusion` for validation

---

## Phase 6: Validation & Polish (Tasks 19-21)

### Task 19: End-to-End Test with Sparsity Trap

- Run full pipeline on `/home/user/sparsity-trap-manuscript`
- Verify manuscript matches expected structure
- Check constraint satisfaction

### Task 20: Add MCP to Claude Code Config

Update `~/.claude.json`:

```json
{
  "mcpServers": {
    "polymax-synthesizer": {
      "command": "python3",
      "args": ["/home/user/mcp_servers/polymax-synthesizer/server.py"]
    }
  }
}
```

### Task 21: Create Documentation

- Create `README.md` with usage examples
- Create `ARCHITECTURE.md` with system overview
- Final commit

---

## Testing Strategy

### Unit Tests
- `test_database.py`: Database operations
- `test_repo_analyzer.py`: Repository analysis
- `test_results_ingester.py`: CSV parsing
- `test_literature_discovery.py`: Search logic
- `test_paper_extractor.py`: Extraction logic
- `test_domain_synthesizer.py`: Synthesis logic

### Integration Tests
- `test_server.py`: MCP tool integration
- `test_end_to_end.py`: Full pipeline on sparsity-trap

### Manual Testing
- Conversational flow with Claude Code
- LaTeX compilation
- Constraint verification

---

## Success Criteria

- ✅ All 7 tools implemented and tested
- ✅ Database migrated with 800+ papers
- ✅ analyze_repo + ingest_results work on sparsity-trap-manuscript
- ✅ discover_literature finds relevant papers
- ✅ extract_papers creates hierarchical JSON
- ✅ synthesize_domains creates markdown summaries
- ✅ generate_section cites exact table values
- ✅ generate_manuscript compiles to PDF
- ✅ MCP server registered in Claude Code config
- ✅ Documentation complete

---

## Estimated Timeline

- **Phase 1 (Tasks 1-3)**: 4 hours
- **Phase 2 (Tasks 4-7)**: 8 hours
- **Phase 3 (Tasks 8-10)**: 8 hours
- **Phase 4 (Tasks 11-12)**: 4 hours
- **Phase 5 (Tasks 13-18)**: 12 hours
- **Phase 6 (Tasks 19-21)**: 4 hours

**Total**: ~40 hours (5 days at 8 hours/day)

---

## Next Steps After Implementation

1. Test with sparsity-trap-manuscript end-to-end
2. Refine extraction prompts based on quality
3. Add web search integration for discover_literature (broad mode)
4. Implement review mode manuscript generation
5. Add more LaTeX templates (Nature, Cell, etc.)
6. Performance optimization (caching, parallel processing)

---

**Plan complete. Ready for execution with superpowers:executing-plans skill.**
