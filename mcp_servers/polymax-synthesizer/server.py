#!/usr/bin/env python3
"""PolyMaX Synthesizer MCP Server."""
import json
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from database import Database
from repo_analyzer import analyze_repository

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
    """Handle tool calls with error handling and validation."""
    try:
        # Validate arguments
        if not isinstance(arguments, dict):
            return [TextContent(
                type="text",
                text=f"Invalid arguments: expected dict, got {type(arguments).__name__}"
            )]

        if name == "analyze_repo":
            repo_path = arguments.get("repo_path")
            mode = arguments.get("mode", "auto")

            # Analyze repository
            analysis = analyze_repository(repo_path)

            # Create synthesis run
            with Database(str(DB_PATH)) as db:
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
        return [TextContent(
            type="text",
            text=f"Tool '{name}' not yet implemented"
        )]

    except Exception as e:
        import traceback
        error_msg = f"Error in tool '{name}': {str(e)}\n{traceback.format_exc()}"
        return [TextContent(type="text", text=error_msg)]

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
