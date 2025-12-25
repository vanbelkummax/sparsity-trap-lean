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
