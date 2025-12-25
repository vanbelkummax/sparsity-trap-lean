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
