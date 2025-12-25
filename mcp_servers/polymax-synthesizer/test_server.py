"""Tests for MCP server."""
import pytest
import asyncio
from mcp.types import Tool

def test_server_has_required_tools():
    """Test that server exposes all required tools."""
    from server import list_tools

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
    tools = asyncio.run(list_tools())
    tool_names = {tool.name for tool in tools}

    assert expected_tools.issubset(tool_names)

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

def test_ingest_results_from_csv(tmp_path):
    """Test ingesting results from CSV tables."""
    import pandas as pd
    from results_ingester import ingest_results_data

    # Create mock table
    csv_file = tmp_path / "tables" / "results.csv"
    csv_file.parent.mkdir(parents=True)
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

def test_discover_literature_targeted():
    """Test targeted literature discovery."""
    from literature_discovery import discover_targeted_literature
    from pathlib import Path

    DB_PATH = Path(__file__).parent / "papers.db"

    queries = [
        "Yuankai Huo Img2ST",
        "Poisson loss sparse data"
    ]

    # This uses existing database, so just verify structure
    result = discover_targeted_literature(queries, str(DB_PATH))

    assert "professors_added" in result
    assert "papers_added" in result
    assert "targeted_matches" in result

def test_extract_single_paper():
    """Test extracting a single paper with MVP rule-based extractor."""
    from paper_extractor import extract_single_paper
    from pathlib import Path
    import json

    DB_PATH = Path(__file__).parent / "papers.db"

    # Use paper ID 1 (GLAM paper with abstract)
    result = extract_single_paper(1, str(DB_PATH))

    # Verify structure matches expected format
    assert "high_level" in result
    assert "mid_level" in result
    assert "low_level" in result
    assert "code_methods" in result

    # Verify high_level contains expected fields
    assert "main_claim" in result["high_level"]
    assert "novelty" in result["high_level"]
    assert "contribution" in result["high_level"]

    # Verify mid_level contains arrays
    assert "stats" in result["mid_level"]
    assert isinstance(result["mid_level"]["stats"], list)
    assert "methods" in result["mid_level"]
    assert isinstance(result["mid_level"]["methods"], list)

    # Verify low_level contains quotes array
    assert "quotes" in result["low_level"]
    assert isinstance(result["low_level"]["quotes"], list)

    # Verify code_methods contains arrays
    assert "algorithms" in result["code_methods"]
    assert "equations" in result["code_methods"]

    # Verify extraction was stored in database
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.execute(
        "SELECT high_level, mid_level, low_level, code_methods FROM paper_extractions WHERE paper_id=?",
        (1,)
    )
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    stored_high = json.loads(row[0])
    assert stored_high["main_claim"] == result["high_level"]["main_claim"]

def test_extract_papers_tool():
    """Test extract_papers MCP tool with batch extraction."""
    from server import call_tool
    from pathlib import Path
    from database import Database
    import json
    import asyncio

    DB_PATH = Path(__file__).parent / "papers.db"

    # Create a synthesis run for testing
    with Database(str(DB_PATH)) as db:
        cursor = db.conn.execute(
            """INSERT INTO synthesis_runs
               (repo_path, mode, detected_domains, status)
               VALUES (?, ?, ?, 'extracting')""",
            ("/test/repo", "review", json.dumps(["spatial-transcriptomics"]))
        )
        db.conn.commit()
        synthesis_run_id = cursor.lastrowid

    # Get first 3 papers from database to extract
    with Database(str(DB_PATH)) as db:
        cursor = db.conn.execute("SELECT id FROM papers LIMIT 3")
        paper_ids = [row["id"] for row in cursor.fetchall()]

    # Call extract_papers tool
    result = asyncio.run(call_tool(
        "extract_papers",
        {
            "synthesis_run_id": synthesis_run_id,
            "paper_ids": paper_ids,
            "extraction_depth": "full"
        }
    ))

    # Parse result
    assert len(result) == 1
    result_text = result[0].text
    result_data = json.loads(result_text)

    # Verify response structure
    assert "synthesis_run_id" in result_data
    assert result_data["synthesis_run_id"] == synthesis_run_id
    assert "papers_extracted" in result_data
    assert result_data["papers_extracted"] == len(paper_ids)
    assert "extraction_summary" in result_data

    # Verify extraction_summary structure
    summary = result_data["extraction_summary"]
    assert "total" in summary
    assert "successful" in summary
    assert "failed" in summary
    assert summary["total"] == len(paper_ids)
    assert summary["successful"] == len(paper_ids)
    assert summary["failed"] == 0

    # Verify database was updated
    with Database(str(DB_PATH)) as db:
        # Check synthesis_run status changed to 'synthesizing'
        cursor = db.conn.execute(
            "SELECT status, papers_extracted FROM synthesis_runs WHERE id=?",
            (synthesis_run_id,)
        )
        row = cursor.fetchone()
        assert row["status"] == "synthesizing"
        assert row["papers_extracted"] == len(paper_ids)

        # Verify extractions were stored
        cursor = db.conn.execute(
            "SELECT COUNT(*) as count FROM paper_extractions WHERE paper_id IN ({})".format(
                ",".join("?" * len(paper_ids))
            ),
            paper_ids
        )
        count = cursor.fetchone()["count"]
        assert count == len(paper_ids)

    # Verify next_step is provided
    assert "next_step" in result_data
    assert "synthesize_domains" in result_data["next_step"]

def test_extract_papers_all_papers():
    """Test extract_papers without paper_ids extracts all papers for domains."""
    from server import call_tool
    from pathlib import Path
    from database import Database
    import json
    import asyncio

    DB_PATH = Path(__file__).parent / "papers.db"

    # Create a synthesis run
    with Database(str(DB_PATH)) as db:
        cursor = db.conn.execute(
            """INSERT INTO synthesis_runs
               (repo_path, mode, detected_domains, status)
               VALUES (?, ?, ?, 'extracting')""",
            ("/test/repo2", "review", json.dumps(["spatial-transcriptomics"]))
        )
        db.conn.commit()
        synthesis_run_id = cursor.lastrowid

    # Call extract_papers without paper_ids (should extract all)
    result = asyncio.run(call_tool(
        "extract_papers",
        {
            "synthesis_run_id": synthesis_run_id,
            "extraction_depth": "full"
        }
    ))

    # Parse result
    result_data = json.loads(result[0].text)

    # Should have extracted multiple papers
    assert result_data["papers_extracted"] > 0
    assert "extraction_summary" in result_data

def test_extraction_depth_high_only():
    """Test extraction_depth='high_only' filters to high_level only."""
    from paper_extractor import extract_multiple_papers
    from pathlib import Path
    from database import Database
    import json

    DB_PATH = Path(__file__).parent / "papers.db"

    # Get first paper
    with Database(str(DB_PATH)) as db:
        cursor = db.conn.execute("SELECT id FROM papers LIMIT 1")
        paper_id = cursor.fetchone()["id"]

    # Extract with high_only depth
    result = extract_multiple_papers([paper_id], str(DB_PATH), extraction_depth="high_only")

    # Verify success
    assert result["successful"] == 1
    assert result["failed"] == 0

    # Verify database only contains high_level data
    with Database(str(DB_PATH)) as db:
        cursor = db.conn.execute(
            "SELECT high_level, mid_level, low_level, code_methods FROM paper_extractions WHERE paper_id=?",
            (paper_id,)
        )
        row = cursor.fetchone()

    high_level = json.loads(row[0])
    mid_level = json.loads(row[1])
    low_level = json.loads(row[2])
    code_methods = json.loads(row[3])

    # high_level should have content
    assert "main_claim" in high_level
    assert len(high_level["main_claim"]) > 0

    # mid_level, low_level, code_methods should be empty
    assert mid_level == {}
    assert low_level == {}
    assert code_methods == {}

def test_extraction_depth_mid():
    """Test extraction_depth='mid' includes high_level and mid_level."""
    from paper_extractor import extract_multiple_papers
    from pathlib import Path
    from database import Database
    import json

    DB_PATH = Path(__file__).parent / "papers.db"

    # Get second paper
    with Database(str(DB_PATH)) as db:
        cursor = db.conn.execute("SELECT id FROM papers LIMIT 1 OFFSET 1")
        paper_id = cursor.fetchone()["id"]

    # Extract with mid depth
    result = extract_multiple_papers([paper_id], str(DB_PATH), extraction_depth="mid")

    # Verify success
    assert result["successful"] == 1
    assert result["failed"] == 0

    # Verify database contains high_level and mid_level
    with Database(str(DB_PATH)) as db:
        cursor = db.conn.execute(
            "SELECT high_level, mid_level, low_level, code_methods FROM paper_extractions WHERE paper_id=?",
            (paper_id,)
        )
        row = cursor.fetchone()

    high_level = json.loads(row[0])
    mid_level = json.loads(row[1])
    low_level = json.loads(row[2])
    code_methods = json.loads(row[3])

    # high_level and mid_level should have content
    assert "main_claim" in high_level
    assert len(high_level["main_claim"]) > 0
    assert "stats" in mid_level
    assert "methods" in mid_level

    # low_level and code_methods should be empty
    assert low_level == {}
    assert code_methods == {}

def test_extraction_depth_full():
    """Test extraction_depth='full' includes all levels."""
    from paper_extractor import extract_multiple_papers
    from pathlib import Path
    from database import Database
    import json

    DB_PATH = Path(__file__).parent / "papers.db"

    # Get third paper
    with Database(str(DB_PATH)) as db:
        cursor = db.conn.execute("SELECT id FROM papers LIMIT 1 OFFSET 2")
        paper_id = cursor.fetchone()["id"]

    # Extract with full depth (default)
    result = extract_multiple_papers([paper_id], str(DB_PATH), extraction_depth="full")

    # Verify success
    assert result["successful"] == 1
    assert result["failed"] == 0

    # Verify database contains all levels
    with Database(str(DB_PATH)) as db:
        cursor = db.conn.execute(
            "SELECT high_level, mid_level, low_level, code_methods FROM paper_extractions WHERE paper_id=?",
            (paper_id,)
        )
        row = cursor.fetchone()

    high_level = json.loads(row[0])
    mid_level = json.loads(row[1])
    low_level = json.loads(row[2])
    code_methods = json.loads(row[3])

    # All levels should have expected structure
    assert "main_claim" in high_level
    assert len(high_level["main_claim"]) > 0
    assert "stats" in mid_level
    assert "methods" in mid_level
    assert "quotes" in low_level
    assert "algorithms" in code_methods
    assert "equations" in code_methods

def test_synthesize_single_domain():
    """Test synthesizing a single domain with mock paper extractions."""
    from domain_synthesizer import synthesize_single_domain
    from pathlib import Path
    from database import Database
    import json

    DB_PATH = Path(__file__).parent / "papers.db"

    # Create mock paper extractions
    mock_extractions = [
        {
            "paper_id": 1,
            "title": "Poisson regression for spike trains",
            "year": 2008,
            "pmid": "18563015",
            "high_level": {
                "main_claim": "GLM with Poisson loss improves spike train modeling",
                "novelty": "First application to neural data",
                "contribution": "Demonstrates 15% improvement over baseline"
            },
            "mid_level": {
                "stats": [
                    {
                        "type": "performance",
                        "metric": "RMSE improvement",
                        "value": "15%",
                        "context": "15% RMSE improvement over baseline",
                        "page": "7"
                    }
                ],
                "methods": [
                    {
                        "name": "Poisson GLM",
                        "parameters": {"learning_rate": 0.01},
                        "page": "Methods"
                    }
                ]
            },
            "low_level": {
                "quotes": [
                    {
                        "text": "Poisson assumption works well for sparse data",
                        "page": "7",
                        "section": "Results"
                    }
                ]
            }
        },
        {
            "paper_id": 2,
            "title": "Negative binomial for overdispersed spike data",
            "year": 2015,
            "pmid": "25678901",
            "high_level": {
                "main_claim": "NB2 addresses overdispersion in spike trains",
                "novelty": "Variance modeling for neural data",
                "contribution": "30% improvement over Poisson"
            },
            "mid_level": {
                "stats": [
                    {
                        "type": "performance",
                        "metric": "RMSE improvement",
                        "value": "30%",
                        "context": "30% RMSE improvement over Poisson GLM",
                        "page": "12"
                    }
                ],
                "methods": [
                    {
                        "name": "Negative Binomial",
                        "parameters": {"theta": 0.5},
                        "page": "Methods"
                    }
                ]
            },
            "low_level": {
                "quotes": [
                    {
                        "text": "Overdispersion is common in neural spike data",
                        "page": "12",
                        "section": "Discussion"
                    }
                ]
            }
        }
    ]

    # Call synthesize_single_domain
    result = synthesize_single_domain("neuroscience", mock_extractions, str(DB_PATH))

    # Verify markdown structure
    assert "# neuroscience" in result.lower()
    assert "## Key Findings" in result or "## Key Finding" in result
    assert "## Statistical Approaches" in result
    assert "## Cross-Field Transfer" in result
    assert "## Top Papers" in result

    # Verify contains specific stats from mock data
    assert "15%" in result or "30%" in result
    assert "PMID" in result or "pmid" in result.lower()

def test_synthesize_domains_tool():
    """Test synthesize_domains MCP tool."""
    from server import call_tool
    from pathlib import Path
    from database import Database
    import json
    import asyncio

    DB_PATH = Path(__file__).parent / "papers.db"

    # Create synthesis run with extracted papers
    with Database(str(DB_PATH)) as db:
        # Create domain
        cursor = db.conn.execute(
            "INSERT OR IGNORE INTO domains (name, description) VALUES (?, ?)",
            ("spatial-transcriptomics", "Spatial gene expression analysis")
        )
        db.conn.commit()

        cursor = db.conn.execute("SELECT id FROM domains WHERE name=?", ("spatial-transcriptomics",))
        domain_id = cursor.fetchone()["id"]

        # Create synthesis run
        cursor = db.conn.execute(
            """INSERT INTO synthesis_runs
               (repo_path, mode, detected_domains, status, papers_extracted)
               VALUES (?, ?, ?, 'synthesizing', 3)""",
            ("/test/repo", "review", json.dumps(["spatial-transcriptomics"]))
        )
        db.conn.commit()
        synthesis_run_id = cursor.lastrowid

    # Call synthesize_domains tool
    result = asyncio.run(call_tool(
        "synthesize_domains",
        {
            "synthesis_run_id": synthesis_run_id,
            "domain_ids": [domain_id]
        }
    ))

    # Parse result
    assert len(result) == 1
    result_text = result[0].text
    result_data = json.loads(result_text)

    # Verify response structure
    assert "synthesis_run_id" in result_data
    assert result_data["synthesis_run_id"] == synthesis_run_id
    assert "domains_synthesized" in result_data
    assert result_data["domains_synthesized"] == 1
    assert "synthesis_summary" in result_data

    # Verify database was updated
    with Database(str(DB_PATH)) as db:
        # Check synthesis_run status changed to 'writing'
        cursor = db.conn.execute(
            "SELECT status, domains_synthesized FROM synthesis_runs WHERE id=?",
            (synthesis_run_id,)
        )
        row = cursor.fetchone()
        assert row["status"] == "writing"
        assert row["domains_synthesized"] == 1

        # Verify domain_syntheses was created
        cursor = db.conn.execute(
            "SELECT summary_markdown FROM domain_syntheses WHERE synthesis_run_id=? AND domain_id=?",
            (synthesis_run_id, domain_id)
        )
        row = cursor.fetchone()
        assert row is not None
        summary = row["summary_markdown"]
        assert len(summary) > 0
        assert "##" in summary  # Should have markdown headers

    # Verify next_step is provided
    assert "next_step" in result_data
    assert "generate_section" in result_data["next_step"] or "generate_manuscript" in result_data["next_step"]

def test_detect_field_from_domains():
    """Test field detection from domains."""
    from section_generator import detect_field_from_domains

    # Medical imaging domains
    assert detect_field_from_domains(["spatial-transcriptomics", "medical-imaging"]) == "medical_imaging"
    assert detect_field_from_domains(["digital-pathology"]) == "medical_imaging"

    # Genomics domains
    assert detect_field_from_domains(["genomics", "sequencing"]) == "genomics"
    assert detect_field_from_domains(["metagenomics"]) == "genomics"

    # Machine learning domains
    assert detect_field_from_domains(["deep-learning", "machine-learning"]) == "machine_learning"
    assert detect_field_from_domains(["neural-networks"]) == "machine_learning"

    # Default case
    assert detect_field_from_domains(["unknown-domain"]) == "machine_learning"
    assert detect_field_from_domains([]) == "machine_learning"

def test_generate_section_primary_research():
    """Test section generation in primary research mode."""
    from section_generator import generate_section
    from pathlib import Path
    from database import Database
    import json

    DB_PATH = Path(__file__).parent / "papers.db"

    # Create synthesis run with main_finding
    with Database(str(DB_PATH)) as db:
        cursor = db.conn.execute(
            """INSERT INTO synthesis_runs
               (repo_path, mode, detected_domains, main_finding, status)
               VALUES (?, ?, ?, ?, 'writing')""",
            (
                "/test/repo",
                "primary_research",
                json.dumps(["spatial-transcriptomics"]),
                json.dumps({
                    "key_findings": [
                        {
                            "claim": "Poisson loss improved SSIM from 0.193 to 0.605",
                            "evidence": "Table 1",
                            "value": 0.605
                        }
                    ],
                    "tables": [{"name": "Table 1", "path": "/test/tables/results.csv"}],
                    "figures": [{"name": "Figure 1", "path": "/test/figures/results.png"}]
                })
            )
        )
        db.conn.commit()
        synthesis_run_id = cursor.lastrowid

    # Generate results section
    section_text = generate_section(
        synthesis_run_id=synthesis_run_id,
        section="results",
        manuscript_mode="primary_research",
        db_path=str(DB_PATH)
    )

    # Verify LaTeX structure
    assert "section{Results}" in section_text or "section*{Results}" in section_text
    assert "0.605" in section_text  # Contains actual value from findings
    assert "Table~\\ref" in section_text or "Table 1" in section_text  # Proper table reference
    assert len(section_text) > 100  # Non-trivial content

def test_generate_section_review_mode():
    """Test section generation in review mode."""
    from section_generator import generate_section
    from pathlib import Path
    from database import Database
    import json

    DB_PATH = Path(__file__).parent / "papers.db"

    # Create synthesis run with domain syntheses
    with Database(str(DB_PATH)) as db:
        # Create domain
        cursor = db.conn.execute(
            "INSERT OR IGNORE INTO domains (name, description) VALUES (?, ?)",
            ("spatial-transcriptomics", "Spatial gene expression analysis")
        )
        db.conn.commit()

        cursor = db.conn.execute("SELECT id FROM domains WHERE name=?", ("spatial-transcriptomics",))
        domain_id = cursor.fetchone()["id"]

        # Create synthesis run
        cursor = db.conn.execute(
            """INSERT INTO synthesis_runs
               (repo_path, mode, detected_domains, status)
               VALUES (?, ?, ?, 'writing')""",
            ("/test/repo", "review", json.dumps(["spatial-transcriptomics"]))
        )
        db.conn.commit()
        synthesis_run_id = cursor.lastrowid

        # Create domain synthesis
        db.conn.execute(
            """INSERT INTO domain_syntheses
               (synthesis_run_id, domain_id, summary_markdown, papers_analyzed)
               VALUES (?, ?, ?, 3)""",
            (
                synthesis_run_id,
                domain_id,
                "# Spatial Transcriptomics\n\n## Key Findings\n\nPoisson loss improves sparse data modeling.\n\n## Statistical Approaches\n\nGLM with Poisson regression."
            )
        )
        db.conn.commit()

    # Generate discussion section
    section_text = generate_section(
        synthesis_run_id=synthesis_run_id,
        section="discussion",
        manuscript_mode="review",
        db_path=str(DB_PATH)
    )

    # Verify LaTeX structure
    assert "section{Discussion}" in section_text or "section*{Discussion}" in section_text
    assert "Poisson" in section_text  # Contains content from domain synthesis
    assert len(section_text) > 100  # Non-trivial content

def test_latex_templates_exist():
    """Test that LaTeX templates exist and are valid."""
    from pathlib import Path

    templates_dir = Path(__file__).parent / "templates"
    assert templates_dir.exists(), "templates/ directory should exist"

    # Check all three templates exist
    medical_imaging = templates_dir / "medical_imaging.tex"
    genomics = templates_dir / "genomics.tex"
    machine_learning = templates_dir / "machine_learning.tex"

    assert medical_imaging.exists(), "medical_imaging.tex template should exist"
    assert genomics.exists(), "genomics.tex template should exist"
    assert machine_learning.exists(), "machine_learning.tex template should exist"

    # Verify templates have required placeholders
    for template_file in [medical_imaging, genomics, machine_learning]:
        content = template_file.read_text()
        assert "{{TITLE}}" in content
        assert "{{AUTHORS}}" in content
        assert "{{ABSTRACT}}" in content
        assert "{{INTRODUCTION}}" in content
        assert "{{METHODS}}" in content
        assert "{{RESULTS}}" in content
        assert "{{DISCUSSION}}" in content
        assert "{{BIBLIOGRAPHY}}" in content

def test_latex_non_breaking_spaces():
    """Test that generated LaTeX uses non-breaking spaces for references."""
    from section_generator import generate_section
    from pathlib import Path
    from database import Database
    import json

    DB_PATH = Path(__file__).parent / "papers.db"

    # Create synthesis run
    with Database(str(DB_PATH)) as db:
        cursor = db.conn.execute(
            """INSERT INTO synthesis_runs
               (repo_path, mode, detected_domains, main_finding, status)
               VALUES (?, ?, ?, ?, 'writing')""",
            (
                "/test/repo",
                "primary_research",
                json.dumps(["spatial-transcriptomics"]),
                json.dumps({
                    "key_findings": [{"claim": "Test finding", "evidence": "Table 1"}],
                    "tables": [{"name": "Table 1", "path": "/test/table.csv"}],
                    "figures": [{"name": "Figure 1", "path": "/test/fig.png"}]
                })
            )
        )
        db.conn.commit()
        synthesis_run_id = cursor.lastrowid

    section_text = generate_section(
        synthesis_run_id=synthesis_run_id,
        section="results",
        manuscript_mode="primary_research",
        db_path=str(DB_PATH)
    )

    # Should use ~ for non-breaking space, not regular space
    # Good: Figure~\ref{fig:label} or Table~\ref{tab:label}
    # Bad: Figure \ref or Table \ref
    import re
    if "\\ref" in section_text:
        # Check for proper non-breaking spaces before \ref
        bad_refs = re.findall(r'(Figure|Table)\s+\\ref', section_text)
        assert len(bad_refs) == 0, f"Found references without non-breaking space: {bad_refs}"

def test_generate_section_tool():
    """Test generate_section MCP tool."""
    from server import call_tool
    from pathlib import Path
    from database import Database
    import json
    import asyncio

    DB_PATH = Path(__file__).parent / "papers.db"

    # Create synthesis run
    with Database(str(DB_PATH)) as db:
        cursor = db.conn.execute(
            """INSERT INTO synthesis_runs
               (repo_path, mode, detected_domains, main_finding, status)
               VALUES (?, ?, ?, ?, 'writing')""",
            (
                "/test/repo",
                "primary_research",
                json.dumps(["spatial-transcriptomics"]),
                json.dumps({
                    "key_findings": [{"claim": "Test", "evidence": "Table 1"}],
                    "tables": [],
                    "figures": []
                })
            )
        )
        db.conn.commit()
        synthesis_run_id = cursor.lastrowid

    # Call generate_section tool
    result = asyncio.run(call_tool(
        "generate_section",
        {
            "synthesis_run_id": synthesis_run_id,
            "section": "results",
            "mode": "primary_research"
        }
    ))

    # Parse result
    assert len(result) == 1
    result_text = result[0].text
    result_data = json.loads(result_text)

    # Verify response structure
    assert "synthesis_run_id" in result_data
    assert "section" in result_data
    assert "mode" in result_data
    assert "field" in result_data
    assert "preview" in result_data
    assert len(result_data["preview"]) <= 200  # First 200 chars

    # Verify database was updated
    with Database(str(DB_PATH)) as db:
        cursor = db.conn.execute(
            "SELECT results FROM manuscripts WHERE synthesis_run_id=?",
            (synthesis_run_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert len(row["results"]) > 0

def test_section_prompts_exist():
    """Test that section prompt templates are defined."""
    from prompts.section_prompts import (
        RESULTS_PROMPT,
        METHODS_PROMPT,
        DISCUSSION_PROMPT,
        INTRODUCTION_PROMPT
    )

    # All prompts should exist and be non-empty
    assert len(RESULTS_PROMPT) > 100
    assert len(METHODS_PROMPT) > 100
    assert len(DISCUSSION_PROMPT) > 100
    assert len(INTRODUCTION_PROMPT) > 100

    # Results prompt should mention table citations
    assert "Table" in RESULTS_PROMPT or "table" in RESULTS_PROMPT
    assert "cite" in RESULTS_PROMPT.lower()

    # Methods prompt should mention algorithms
    assert "algorithm" in METHODS_PROMPT.lower() or "method" in METHODS_PROMPT.lower()

    # Discussion prompt should mention cross-field
    assert "cross-field" in DISCUSSION_PROMPT.lower() or "transfer" in DISCUSSION_PROMPT.lower()

    # All prompts should mention LaTeX formatting
    for prompt in [RESULTS_PROMPT, METHODS_PROMPT, DISCUSSION_PROMPT, INTRODUCTION_PROMPT]:
        assert "~" in prompt or "non-breaking" in prompt.lower()

def test_generate_manuscript_tool():
    """Test generate_manuscript orchestration tool."""
    from server import call_tool
    from pathlib import Path
    from database import Database
    import json
    import asyncio

    DB_PATH = Path(__file__).parent / "papers.db"

    # Create synthesis run with domain syntheses
    with Database(str(DB_PATH)) as db:
        # Create domain
        cursor = db.conn.execute(
            "INSERT OR IGNORE INTO domains (name, description) VALUES (?, ?)",
            ("spatial-transcriptomics", "Spatial gene expression analysis")
        )
        db.conn.commit()

        cursor = db.conn.execute("SELECT id FROM domains WHERE name=?", ("spatial-transcriptomics",))
        domain_id = cursor.fetchone()["id"]

        # Create synthesis run
        cursor = db.conn.execute(
            """INSERT INTO synthesis_runs
               (repo_path, mode, detected_domains, status, main_finding)
               VALUES (?, ?, ?, 'writing', ?)""",
            (
                "/test/repo",
                "primary_research",
                json.dumps(["spatial-transcriptomics"]),
                json.dumps({
                    "key_findings": [{"claim": "Test finding", "evidence": "Table 1", "value": 0.5}],
                    "tables": [{"name": "Table 1", "path": "/test/table.csv"}],
                    "figures": [{"name": "Figure 1", "path": "/test/fig.png"}]
                })
            )
        )
        db.conn.commit()
        synthesis_run_id = cursor.lastrowid

        # Create domain synthesis
        db.conn.execute(
            """INSERT INTO domain_syntheses
               (synthesis_run_id, domain_id, summary_markdown, papers_analyzed)
               VALUES (?, ?, ?, 3)""",
            (
                synthesis_run_id,
                domain_id,
                "# Spatial Transcriptomics\n\n## Key Findings\n\nTest findings.\n"
            )
        )
        db.conn.commit()

    # Call generate_manuscript tool
    result = asyncio.run(call_tool(
        "generate_manuscript",
        {
            "synthesis_run_id": synthesis_run_id,
            "mode": "research"
        }
    ))

    # Parse result
    assert len(result) == 1
    result_text = result[0].text
    result_data = json.loads(result_text)

    # Verify response structure
    assert "status" in result_data
    assert result_data["status"] == "complete"
    assert "manuscript_id" in result_data
    assert "field" in result_data
    assert "latex_preview" in result_data
    assert len(result_data["latex_preview"]) > 0
    assert "next_step" in result_data

    # Verify database was updated
    with Database(str(DB_PATH)) as db:
        # Check synthesis_run status changed to 'complete'
        cursor = db.conn.execute(
            "SELECT status FROM synthesis_runs WHERE id=?",
            (synthesis_run_id,)
        )
        row = cursor.fetchone()
        assert row["status"] == "complete"

        # Verify manuscript was created with all sections
        cursor = db.conn.execute(
            """SELECT abstract, introduction, methods, results, discussion, latex_content
               FROM manuscripts WHERE synthesis_run_id=?""",
            (synthesis_run_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["abstract"] is not None and len(row["abstract"]) > 0
        assert row["introduction"] is not None and len(row["introduction"]) > 0
        assert row["methods"] is not None and len(row["methods"]) > 0
        assert row["results"] is not None and len(row["results"]) > 0
        assert row["discussion"] is not None and len(row["discussion"]) > 0
        assert row["latex_content"] is not None and len(row["latex_content"]) > 0

        # Verify LaTeX document structure
        latex = row["latex_content"]
        assert "\\documentclass" in latex
        assert "\\begin{document}" in latex
        assert "\\end{document}" in latex
        assert "\\section{Results}" in latex or "\\section{Introduction}" in latex

def test_generate_figure_block():
    """Test figure block generation with latex-architect MCP."""
    from section_generator import generate_figure_block

    # Test figure block generation
    fig_block = generate_figure_block(
        filename="figs/results.png",
        caption="Performance comparison across models",
        label="fig:results",
        wide=False
    )

    # Verify structure
    assert "\\begin{figure}" in fig_block
    assert "\\includegraphics" in fig_block
    assert "figs/results.png" in fig_block
    assert "\\caption{Performance comparison across models}" in fig_block
    assert "\\label{fig:results}" in fig_block
    assert "\\end{figure}" in fig_block
    assert "[t!]" in fig_block  # Top placement

    # Test wide figure
    wide_block = generate_figure_block(
        filename="figs/wide.png",
        caption="Wide figure",
        label="fig:wide",
        wide=True
    )
    assert "\\begin{figure*}" in wide_block
    assert "\\end{figure*}" in wide_block

def test_check_figure_placement():
    """Test figure placement validation."""
    from section_generator import check_figure_placement

    # Good LaTeX with [t!] placement
    good_latex = r"""
    \begin{figure}[t!]
    \includegraphics{fig.png}
    \caption{Test}
    \end{figure}
    """

    warnings = check_figure_placement(good_latex)
    assert len(warnings) == 0

    # Bad LaTeX with [h] placement
    bad_latex = r"""
    \begin{figure}[h]
    \includegraphics{fig.png}
    \caption{Test}
    \end{figure}
    """

    warnings = check_figure_placement(bad_latex)
    assert len(warnings) > 0
    assert any("[h]" in w for w in warnings)

def test_assemble_manuscript_integration():
    """Test full manuscript assembly."""
    from section_generator import assemble_manuscript
    from pathlib import Path
    from database import Database
    import json

    DB_PATH = Path(__file__).parent / "papers.db"

    # Create synthesis run and manuscript
    with Database(str(DB_PATH)) as db:
        cursor = db.conn.execute(
            """INSERT INTO synthesis_runs
               (repo_path, mode, detected_domains, status)
               VALUES (?, ?, ?, 'complete')""",
            ("/test/repo", "primary_research", json.dumps(["spatial-transcriptomics"]))
        )
        db.conn.commit()
        synthesis_run_id = cursor.lastrowid

        # Create manuscript with sections
        db.conn.execute(
            """INSERT INTO manuscripts
               (synthesis_run_id, mode, abstract, introduction, methods, results, discussion)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                synthesis_run_id,
                "research",
                "This is the abstract.",
                "\\section{Introduction}\nThis is the introduction.",
                "\\section{Methods}\nThese are the methods.",
                "\\section{Results}\nThese are the results.",
                "\\section{Discussion}\nThis is the discussion."
            )
        )
        db.conn.commit()

    # Assemble manuscript
    latex_doc = assemble_manuscript(
        synthesis_run_id=synthesis_run_id,
        db_path=str(DB_PATH),
        title="Test Manuscript",
        authors="Test Author"
    )

    # Verify structure
    assert "\\documentclass" in latex_doc
    assert "Test Manuscript" in latex_doc
    assert "Test Author" in latex_doc
    assert "This is the abstract" in latex_doc
    assert "This is the introduction" in latex_doc
    assert "These are the methods" in latex_doc
    assert "These are the results" in latex_doc
    assert "This is the discussion" in latex_doc
    assert "\\begin{document}" in latex_doc
    assert "\\end{document}" in latex_doc
