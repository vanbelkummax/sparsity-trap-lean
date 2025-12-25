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
