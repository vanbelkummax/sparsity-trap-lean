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
from results_ingester import ingest_results_data
from literature_discovery import discover_targeted_literature, discover_broad_literature
from paper_extractor import extract_multiple_papers

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

        elif name == "ingest_results":
            synthesis_run_id = arguments.get("synthesis_run_id")

            # Get repo path from synthesis_run
            with Database(str(DB_PATH)) as db:
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
            with Database(str(DB_PATH)) as db:
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

        elif name == "discover_literature":
            synthesis_run_id = arguments.get("synthesis_run_id")
            mode = arguments.get("mode")
            search_queries = arguments.get("search_queries", [])

            if mode == "targeted":
                result = discover_targeted_literature(search_queries, str(DB_PATH))
            else:
                # Get domains from synthesis_run
                with Database(str(DB_PATH)) as db:
                    cursor = db.conn.execute(
                        "SELECT detected_domains FROM synthesis_runs WHERE id=?",
                        (synthesis_run_id,)
                    )
                    row = cursor.fetchone()
                    domains = json.loads(row["detected_domains"]) if row else []

                result = discover_broad_literature(domains, str(DB_PATH))

            # Update synthesis_run
            with Database(str(DB_PATH)) as db:
                db.conn.execute(
                    "UPDATE synthesis_runs SET papers_found=?, status='extracting' WHERE id=?",
                    (result["papers_added"], synthesis_run_id)
                )
                db.conn.commit()

            result["synthesis_run_id"] = synthesis_run_id
            result["next_step"] = "Call extract_papers to perform hierarchical extraction"

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "extract_papers":
            synthesis_run_id = arguments.get("synthesis_run_id")
            paper_ids = arguments.get("paper_ids")
            extraction_depth = arguments.get("extraction_depth", "full")

            # If no paper_ids provided, get all papers from database
            if not paper_ids:
                with Database(str(DB_PATH)) as db:
                    cursor = db.conn.execute("SELECT id FROM papers")
                    paper_ids = [row["id"] for row in cursor.fetchall()]

            # Extract papers using rule-based MVP extractor
            # TODO: Future enhancement - use Claude API with prompts/extraction_prompts.py
            extraction_result = extract_multiple_papers(
                paper_ids,
                str(DB_PATH),
                extraction_depth=extraction_depth
            )

            # Update synthesis_run status and count
            with Database(str(DB_PATH)) as db:
                db.conn.execute(
                    """UPDATE synthesis_runs
                       SET papers_extracted=?, status='synthesizing'
                       WHERE id=?""",
                    (extraction_result["successful"], synthesis_run_id)
                )
                db.conn.commit()

            # Prepare response
            result = {
                "synthesis_run_id": synthesis_run_id,
                "papers_extracted": extraction_result["successful"],
                "extraction_summary": extraction_result,
                "extraction_depth": extraction_depth,
                "next_step": "Call synthesize_domains to generate domain syntheses"
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
