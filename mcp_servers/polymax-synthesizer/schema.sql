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
