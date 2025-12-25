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
