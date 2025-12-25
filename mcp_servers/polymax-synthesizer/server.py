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
from domain_synthesizer import synthesize_multiple_domains
from section_generator import generate_section, detect_field_from_domains, assemble_manuscript

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

        elif name == "synthesize_domains":
            synthesis_run_id = arguments.get("synthesis_run_id")
            domain_ids = arguments.get("domain_ids", [])

            # Synthesize domains using rule-based MVP synthesizer
            # TODO: Future enhancement - use Claude Opus 4.5 API with prompts/synthesis_prompts.py
            synthesis_result = synthesize_multiple_domains(
                synthesis_run_id,
                domain_ids,
                str(DB_PATH)
            )

            # Update synthesis_run status and count
            with Database(str(DB_PATH)) as db:
                db.conn.execute(
                    """UPDATE synthesis_runs
                       SET domains_synthesized=?, status='writing'
                       WHERE id=?""",
                    (synthesis_result["successful"], synthesis_run_id)
                )
                db.conn.commit()

            # Prepare response
            result = {
                "synthesis_run_id": synthesis_run_id,
                "domains_synthesized": synthesis_result["successful"],
                "synthesis_summary": synthesis_result,
                "next_step": "Call generate_section to write individual manuscript sections or generate_manuscript for full orchestration"
            }

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "generate_section":
            synthesis_run_id = arguments.get("synthesis_run_id")
            section = arguments.get("section")
            mode = arguments.get("mode")

            # Get detected domains to determine field
            with Database(str(DB_PATH)) as db:
                cursor = db.conn.execute(
                    "SELECT detected_domains FROM synthesis_runs WHERE id=?",
                    (synthesis_run_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return [TextContent(type="text", text=f"Synthesis run {synthesis_run_id} not found")]
                detected_domains = json.loads(row["detected_domains"])

            # Detect field
            field = detect_field_from_domains(detected_domains)

            # Generate section
            section_text = generate_section(
                synthesis_run_id=synthesis_run_id,
                section=section,
                manuscript_mode=mode,
                db_path=str(DB_PATH)
            )

            # Store section in manuscripts table
            # Map mode to manuscript mode (manuscripts table uses different enum)
            manuscript_mode_map = {
                "primary_research": "research",
                "review": "review"
            }
            manuscript_mode = manuscript_mode_map.get(mode, "research")

            with Database(str(DB_PATH)) as db:
                # Check if manuscript record exists
                cursor = db.conn.execute(
                    "SELECT id FROM manuscripts WHERE synthesis_run_id=?",
                    (synthesis_run_id,)
                )
                row = cursor.fetchone()

                if row:
                    # Update existing manuscript
                    manuscript_id = row["id"]
                    db.conn.execute(
                        f"UPDATE manuscripts SET {section}=? WHERE id=?",
                        (section_text, manuscript_id)
                    )
                else:
                    # Create new manuscript record
                    db.conn.execute(
                        f"""INSERT INTO manuscripts
                           (synthesis_run_id, mode, {section})
                           VALUES (?, ?, ?)""",
                        (synthesis_run_id, manuscript_mode, section_text)
                    )
                db.conn.commit()

            # Prepare response
            result = {
                "synthesis_run_id": synthesis_run_id,
                "section": section,
                "mode": mode,
                "field": field,
                "preview": section_text[:200] if len(section_text) > 200 else section_text,
                "next_step": "Call generate_section for other sections or generate_manuscript for full orchestration"
            }

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "generate_manuscript":
            synthesis_run_id = arguments.get("synthesis_run_id")
            mode = arguments.get("mode")
            output_path = arguments.get("output_path")

            # Get synthesis run data
            with Database(str(DB_PATH)) as db:
                cursor = db.conn.execute(
                    "SELECT detected_domains, mode as detected_mode FROM synthesis_runs WHERE id=?",
                    (synthesis_run_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return [TextContent(type="text", text=f"Synthesis run {synthesis_run_id} not found")]

                detected_domains = json.loads(row["detected_domains"])
                detected_mode = row["detected_mode"]

            # Detect field for template selection
            field = detect_field_from_domains(detected_domains)

            # Map mode to manuscript_mode for database
            mode_map = {
                "research": "research",
                "review": "review",
                "extended-review": "review",
                "hypothesis": "research"
            }
            manuscript_mode = mode_map.get(mode, "research")

            # Determine section generation mode
            section_mode = "primary_research" if mode in ["research", "hypothesis"] else "review"

            # Check if manuscript already exists
            with Database(str(DB_PATH)) as db:
                cursor = db.conn.execute(
                    "SELECT id FROM manuscripts WHERE synthesis_run_id=?",
                    (synthesis_run_id,)
                )
                existing = cursor.fetchone()
                if existing:
                    manuscript_id = existing["id"]
                else:
                    # Create new manuscript record
                    cursor = db.conn.execute(
                        "INSERT INTO manuscripts (synthesis_run_id, mode) VALUES (?, ?)",
                        (synthesis_run_id, manuscript_mode)
                    )
                    db.conn.commit()
                    manuscript_id = cursor.lastrowid

            # Generate sections in sequence
            sections = ["abstract", "introduction", "methods", "results", "discussion"]

            for i, section in enumerate(sections, 1):
                # Generate section
                section_text = generate_section(
                    synthesis_run_id=synthesis_run_id,
                    section=section,
                    manuscript_mode=section_mode,
                    db_path=str(DB_PATH)
                )

                # Update manuscript with this section
                with Database(str(DB_PATH)) as db:
                    db.conn.execute(
                        f"UPDATE manuscripts SET {section}=? WHERE id=?",
                        (section_text, manuscript_id)
                    )
                    db.conn.commit()

            # Assemble full LaTeX document
            latex_document = assemble_manuscript(
                synthesis_run_id=synthesis_run_id,
                db_path=str(DB_PATH),
                title="Generated Manuscript",
                authors="PolyMaX Synthesizer"
            )

            # Store latex_content in database
            with Database(str(DB_PATH)) as db:
                db.conn.execute(
                    "UPDATE manuscripts SET latex_content=? WHERE id=?",
                    (latex_document, manuscript_id)
                )
                db.conn.commit()

            # Update synthesis_run status to complete
            with Database(str(DB_PATH)) as db:
                db.conn.execute(
                    "UPDATE synthesis_runs SET status='complete' WHERE id=?",
                    (synthesis_run_id,)
                )
                db.conn.commit()

            # Optionally save to file
            if output_path:
                Path(output_path).write_text(latex_document)

            # Prepare response
            result = {
                "status": "complete",
                "manuscript_id": manuscript_id,
                "synthesis_run_id": synthesis_run_id,
                "field": field,
                "mode": mode,
                "latex_preview": latex_document[:500] if len(latex_document) > 500 else latex_document,
                "next_step": "Use pdflatex to compile LaTeX or inspect individual sections"
            }

            if output_path:
                result["output_file"] = output_path

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
