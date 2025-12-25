"""Section generator for manuscript writing."""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from database import Database


def detect_field_from_domains(domains: List[str]) -> str:
    """
    Detect research field from domain list.

    Maps domains to template choice:
    - medical_imaging: spatial-transcriptomics, medical-imaging, digital-pathology
    - genomics: genomics, sequencing, metagenomics
    - machine_learning: deep-learning, machine-learning, neural-networks

    Args:
        domains: List of domain strings

    Returns:
        Field name: "medical_imaging", "genomics", or "machine_learning"
    """
    # Normalize domains to lowercase
    domains_lower = [d.lower() for d in domains]

    # Medical imaging domains
    medical_imaging_keywords = [
        "spatial-transcriptomics",
        "medical-imaging",
        "digital-pathology",
        "histology",
        "pathology",
        "microscopy"
    ]

    # Genomics domains
    genomics_keywords = [
        "genomics",
        "sequencing",
        "metagenomics",
        "rna-seq",
        "dna-seq",
        "single-cell"
    ]

    # Machine learning domains
    ml_keywords = [
        "deep-learning",
        "machine-learning",
        "neural-networks",
        "computer-vision",
        "artificial-intelligence"
    ]

    # Check for medical imaging
    if any(keyword in domains_lower for keyword in medical_imaging_keywords):
        return "medical_imaging"

    # Check for genomics
    if any(keyword in domains_lower for keyword in genomics_keywords):
        return "genomics"

    # Check for machine learning
    if any(keyword in domains_lower for keyword in ml_keywords):
        return "machine_learning"

    # Default to machine learning
    return "machine_learning"


def generate_section(
    synthesis_run_id: int,
    section: str,
    manuscript_mode: str,
    db_path: str
) -> str:
    """
    Generate a manuscript section with data grounding.

    Primary Research Mode (Results section):
    - Cite exact values from tables (e.g., "SSIM improved from 0.193 to 0.605 (Table 1)")
    - Reference YOUR figures (e.g., "Figure~\\ref{fig:results}")
    - Constraint checking: All cited values must match ingest_results data

    Review Mode (Discussion section):
    - Synthesize across domain_syntheses
    - Cross-field insights
    - Transfer learning opportunities

    TODO: Future enhancement - use Claude Opus 4.5 API for sophisticated generation
    TODO: This MVP uses template-based generation with placeholder replacement

    Args:
        synthesis_run_id: Synthesis run ID
        section: Section name (introduction, methods, results, discussion, abstract)
        manuscript_mode: "primary_research" or "review"
        db_path: Path to database

    Returns:
        LaTeX-formatted section text
    """
    # Fetch synthesis run data
    with Database(db_path) as db:
        cursor = db.conn.execute(
            "SELECT detected_domains, main_finding FROM synthesis_runs WHERE id=?",
            (synthesis_run_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Synthesis run {synthesis_run_id} not found")

        detected_domains = json.loads(row["detected_domains"])
        main_finding = json.loads(row["main_finding"]) if row["main_finding"] else None

    # Generate section based on mode
    if manuscript_mode == "primary_research":
        return _generate_primary_research_section(
            synthesis_run_id=synthesis_run_id,
            section=section,
            main_finding=main_finding,
            db_path=db_path
        )
    else:  # review mode
        return _generate_review_section(
            synthesis_run_id=synthesis_run_id,
            section=section,
            db_path=db_path
        )


def _generate_primary_research_section(
    synthesis_run_id: int,
    section: str,
    main_finding: Dict[str, Any],
    db_path: str
) -> str:
    """
    Generate section for primary research mode.

    Grounds content in YOUR experimental data from ingest_results.
    Uses proper LaTeX formatting with non-breaking spaces.
    """
    # Section header
    section_title = section.capitalize()
    latex_content = f"\\section{{{section_title}}}\n\n"

    if section == "results" and main_finding:
        # Extract key findings
        key_findings = main_finding.get("key_findings", [])
        tables = main_finding.get("tables", [])
        figures = main_finding.get("figures", [])

        # Generate results text
        latex_content += "% Results grounded in experimental data\n"

        for i, finding in enumerate(key_findings):
            claim = finding.get("claim", "")
            evidence = finding.get("evidence", "")
            value = finding.get("value")

            # Add finding with proper citation
            if value is not None:
                latex_content += f"{claim}"
                if evidence:
                    # Use non-breaking space before citation
                    latex_content += f" ({evidence})"
                latex_content += ".\n\n"
            else:
                latex_content += f"{claim}.\n\n"

        # Reference tables
        if tables:
            latex_content += f"Table~\\ref{{tab:results}} summarizes our key results.\n\n"

        # Reference figures
        if figures:
            latex_content += f"Figure~\\ref{{fig:results}} shows the performance comparison.\n\n"

        # TODO: Future enhancement - use Claude API to generate sophisticated prose
        # TODO: Add constraint verification to ensure all cited values match data

    elif section == "methods" and main_finding:
        latex_content += "% Methods section\n"
        latex_content += "We implemented our approach using standard techniques.\n\n"
        # TODO: Extract methods from repository analysis

    elif section == "introduction":
        latex_content += "% Introduction section\n"
        latex_content += "This work addresses an important problem in the field.\n\n"
        # TODO: Use Claude API to generate compelling introduction

    elif section == "discussion" and main_finding:
        latex_content += "% Discussion section\n"
        latex_content += "Our results demonstrate significant improvements.\n\n"
        # TODO: Use Claude API for insightful discussion

    elif section == "abstract" and main_finding:
        latex_content = ""  # No section header for abstract
        latex_content += "% Abstract\n"
        latex_content += "This paper presents novel findings.\n\n"
        # TODO: Generate concise abstract from key findings

    return latex_content


def _generate_review_section(
    synthesis_run_id: int,
    section: str,
    db_path: str
) -> str:
    """
    Generate section for review mode.

    Grounds content in domain syntheses from literature.
    Synthesizes across papers and domains.
    """
    # Fetch domain syntheses
    with Database(db_path) as db:
        cursor = db.conn.execute(
            """SELECT ds.summary_markdown, d.name
               FROM domain_syntheses ds
               JOIN domains d ON ds.domain_id = d.id
               WHERE ds.synthesis_run_id = ?""",
            (synthesis_run_id,)
        )
        domain_syntheses = cursor.fetchall()

    # Section header
    section_title = section.capitalize()
    latex_content = f"\\section{{{section_title}}}\n\n"

    if section == "discussion" and domain_syntheses:
        latex_content += "% Discussion synthesized from literature\n"

        for synthesis in domain_syntheses:
            domain_name = synthesis["name"]
            summary = synthesis["summary_markdown"]

            # Extract key content from markdown summary
            # Simple extraction: look for Key Findings section
            if "## Key Findings" in summary or "## Key Finding" in summary:
                # Extract text after Key Findings header
                parts = summary.split("##")
                for part in parts:
                    if "Key Finding" in part:
                        # Get content after header
                        content = part.split("\n", 1)
                        if len(content) > 1:
                            # Convert markdown to LaTeX-safe text
                            text = content[1].strip()
                            # Remove markdown formatting
                            text = text.replace("**", "").replace("*", "")
                            latex_content += f"{text}\n\n"

        # TODO: Future enhancement - use Claude Opus 4.5 API for cross-domain synthesis
        # TODO: Generate transfer learning insights

    elif section == "introduction" and domain_syntheses:
        latex_content += "% Introduction synthesized from literature\n"
        latex_content += "This review synthesizes recent advances in the field.\n\n"
        # TODO: Use Claude API for compelling review introduction

    elif section == "results" and domain_syntheses:
        latex_content += "% Results from literature synthesis\n"
        latex_content += "We analyzed multiple studies across domains.\n\n"
        # TODO: Synthesize key results from papers

    elif section == "methods":
        latex_content += "% Review methodology\n"
        latex_content += "We systematically reviewed literature across multiple domains.\n\n"
        # TODO: Describe literature discovery and synthesis approach

    return latex_content


def load_template(field: str) -> str:
    """
    Load LaTeX template for specified field.

    Args:
        field: "medical_imaging", "genomics", or "machine_learning"

    Returns:
        Template content as string
    """
    templates_dir = Path(__file__).parent / "templates"
    template_file = templates_dir / f"{field}.tex"

    if not template_file.exists():
        raise FileNotFoundError(f"Template not found: {template_file}")

    return template_file.read_text()


def generate_figure_block(
    filename: str,
    caption: str,
    label: str,
    wide: bool = False,
    placement: str = "t!"
) -> str:
    """
    Generate LaTeX figure block using Huo Lab IEEE/MICCAI standards.

    Integrates with latex-architect MCP server when available.
    Falls back to template-based generation.

    Args:
        filename: Path to image file (e.g., "figs/results.png")
        caption: Figure caption text
        label: LaTeX label (e.g., "fig:results")
        wide: True for double-column span (figure*), False for single column
        placement: Placement specifier (default: "t!" for top)

    Returns:
        LaTeX figure block with proper formatting
    """
    # TODO: Future enhancement - integrate with latex-architect MCP
    # Try to use mcp__latex-architect__generate_figure_block
    # For now, use template-based generation

    # Figure environment
    fig_env = "figure*" if wide else "figure"
    width = r"0.95\textwidth" if wide else r"0.95\columnwidth"

    # Build LaTeX block
    latex = f"\\begin{{{fig_env}}}[{placement}]\n"
    latex += "\\centering\n"
    latex += f"\\includegraphics[width={width}]{{{filename}}}\n"
    latex += f"\\caption{{{caption}}}\n"
    latex += f"\\label{{{label}}}\n"
    latex += f"\\end{{{fig_env}}}\n"

    return latex


def check_figure_placement(latex_source: str) -> List[str]:
    """
    Validate figure placement in LaTeX source.

    Integrates with latex-architect MCP server when available.
    Falls back to regex-based validation.

    Args:
        latex_source: LaTeX document source

    Returns:
        List of warnings/issues found
    """
    # TODO: Future enhancement - integrate with latex-architect MCP
    # Try to use mcp__latex-architect__check_spatial_inclusion
    # For now, use regex-based validation

    warnings = []

    # Check for bad placement specifiers [h] or [h!]
    bad_placements = re.findall(r'\\begin\{figure\*?\}\[h!?\]', latex_source)
    if bad_placements:
        warnings.append(
            f"Found {len(bad_placements)} figure(s) with [h] placement. "
            "Use [t!] or [b!] for professional typesetting."
        )

    # Check for figures without placement specifiers
    no_placement = re.findall(r'\\begin\{figure\*?\}(?!\[)', latex_source)
    if no_placement:
        warnings.append(
            f"Found {len(no_placement)} figure(s) without placement specifier. "
            "Add [t!] or [b!] for better control."
        )

    # Check for improper figure references (space before \ref)
    bad_refs = re.findall(r'(Figure|Table)\s+\\ref', latex_source)
    if bad_refs:
        warnings.append(
            f"Found {len(bad_refs)} reference(s) without non-breaking space. "
            "Use Figure~\\ref{} not Figure \\ref{}."
        )

    return warnings


def assemble_manuscript(
    synthesis_run_id: int,
    db_path: str,
    title: str = "Manuscript Title",
    authors: str = "Author Names"
) -> str:
    """
    Assemble complete manuscript from sections stored in database.

    TODO: Future enhancement for full manuscript assembly

    Args:
        synthesis_run_id: Synthesis run ID
        db_path: Path to database
        title: Manuscript title
        authors: Author list

    Returns:
        Complete LaTeX document
    """
    # Fetch manuscript sections from database
    with Database(db_path) as db:
        cursor = db.conn.execute(
            """SELECT detected_domains, abstract, introduction, methods, results, discussion
               FROM manuscripts
               JOIN synthesis_runs ON manuscripts.synthesis_run_id = synthesis_runs.id
               WHERE synthesis_run_id = ?
               ORDER BY generated_at DESC
               LIMIT 1""",
            (synthesis_run_id,)
        )
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"No manuscript found for synthesis run {synthesis_run_id}")

        # Detect field
        detected_domains = json.loads(row["detected_domains"])
        field = detect_field_from_domains(detected_domains)

    # Load template
    template = load_template(field)

    # Replace placeholders
    manuscript = template.replace("{{TITLE}}", title)
    manuscript = manuscript.replace("{{AUTHORS}}", authors)
    manuscript = manuscript.replace("{{ABSTRACT}}", row["abstract"] or "")
    manuscript = manuscript.replace("{{INTRODUCTION}}", row["introduction"] or "")
    manuscript = manuscript.replace("{{METHODS}}", row["methods"] or "")
    manuscript = manuscript.replace("{{RESULTS}}", row["results"] or "")
    manuscript = manuscript.replace("{{DISCUSSION}}", row["discussion"] or "")
    manuscript = manuscript.replace("{{BIBLIOGRAPHY}}", "")

    return manuscript
