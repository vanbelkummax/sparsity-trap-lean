"""Domain synthesis module for PolyMaX Synthesizer.

This module generates 1-page markdown syntheses for each domain by combining
hierarchical paper extractions into structured summaries with cross-field insights.

MVP Implementation Strategy:
- Rule-based template generation from extracted data
- Combine stats, methods, and findings from multiple papers
- Generate structured markdown with proper citations

Future Enhancement:
- Integrate Claude Opus 4.5 API (see prompts/synthesis_prompts.py)
- Semantic clustering of similar findings
- Automatic cross-domain connection identification
- Quality scoring for generated syntheses
"""

import json
from typing import Dict, Any, List
from datetime import datetime
from database import Database


def synthesize_single_domain(
    domain: str,
    paper_extractions: List[Dict[str, Any]],
    db_path: str
) -> str:
    """
    Generate 1-page markdown synthesis for a single domain.

    MVP Strategy:
    - Use template-based approach to structure synthesis
    - Aggregate statistics from mid_level.stats across papers
    - Aggregate methods from mid_level.methods
    - Extract key findings from high_level.main_claim
    - Generate Top Papers list from metadata

    Args:
        domain: Domain name (e.g., "spatial-transcriptomics", "neuroscience")
        paper_extractions: List of dicts containing hierarchical extractions
            Expected structure:
            {
                "paper_id": int,
                "title": str,
                "year": int,
                "pmid": str,
                "high_level": {"main_claim": str, "novelty": str, "contribution": str},
                "mid_level": {"stats": [...], "methods": [...]},
                "low_level": {"quotes": [...]}
            }
        db_path: Path to SQLite database (for future use)

    Returns:
        1-page markdown synthesis string

    TODO: Replace with Claude Opus 4.5 API call using prompts/synthesis_prompts.py
    """
    if not paper_extractions:
        return _generate_empty_synthesis(domain)

    # Extract components
    key_findings = _extract_key_findings(paper_extractions)
    statistical_approaches = _extract_statistical_approaches(paper_extractions)
    cross_field_insights = _generate_cross_field_insights(domain, paper_extractions)
    top_papers = _generate_top_papers_list(paper_extractions)

    # Build markdown synthesis
    synthesis = _build_markdown_synthesis(
        domain=domain,
        key_findings=key_findings,
        statistical_approaches=statistical_approaches,
        cross_field_insights=cross_field_insights,
        top_papers=top_papers
    )

    return synthesis


def _extract_key_findings(paper_extractions: List[Dict[str, Any]]) -> List[str]:
    """
    Extract key findings from paper extractions.

    MVP: Use high_level.contribution + top stats from mid_level.stats
    TODO: Claude API for semantic clustering and synthesis
    """
    findings = []

    for paper in paper_extractions:
        high = paper.get('high_level', {})
        mid = paper.get('mid_level', {})

        contribution = high.get('contribution', '')
        if contribution and contribution != "Not extracted (MVP)":
            # Add PMID and basic citation
            pmid = paper.get('pmid', 'N/A')
            year = paper.get('year', 'N/A')
            finding = f"{contribution} (PMID: {pmid}, {year})"
            findings.append(finding)

        # Add top statistic if available
        stats = mid.get('stats', [])
        if stats:
            # Get first meaningful stat
            stat = stats[0]
            metric = stat.get('metric', 'Unknown')
            value = stat.get('value', 'N/A')
            page = stat.get('page', 'N/A')
            pmid = paper.get('pmid', 'N/A')

            stat_finding = f"Achieved {metric} of {value} (PMID: {pmid}, p.{page})"
            findings.append(stat_finding)

    # Limit to top 4 findings
    return findings[:4]


def _extract_statistical_approaches(paper_extractions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract and aggregate statistical methods across papers.

    MVP: Aggregate mid_level.methods and associated stats
    TODO: Claude API for semantic method grouping
    """
    # Collect all methods
    methods_dict = {}  # method_name -> {stats, params, papers}

    for paper in paper_extractions:
        mid = paper.get('mid_level', {})
        methods = mid.get('methods', [])
        stats = mid.get('stats', [])
        pmid = paper.get('pmid', 'N/A')

        for method in methods:
            name = method.get('name', 'Unknown')

            if name not in methods_dict:
                methods_dict[name] = {
                    'name': name,
                    'parameters': {},
                    'stats': [],
                    'pmids': []
                }

            # Aggregate parameters
            params = method.get('parameters', {})
            methods_dict[name]['parameters'].update(params)

            # Add PMID
            if pmid not in methods_dict[name]['pmids']:
                methods_dict[name]['pmids'].append(pmid)

        # Associate stats with methods
        for stat in stats:
            # Try to associate with first method (simple heuristic)
            if methods:
                first_method = methods[0].get('name', 'Unknown')
                if first_method in methods_dict:
                    methods_dict[first_method]['stats'].append(stat)

    # Convert to list and limit to top 3
    approaches = list(methods_dict.values())[:3]
    return approaches


def _generate_cross_field_insights(domain: str, paper_extractions: List[Dict[str, Any]]) -> str:
    """
    Generate cross-field transfer insights.

    MVP: Template-based insight generation
    TODO: Claude API for semantic similarity analysis across domains
    """
    # Simple template for MVP
    # TODO: This should analyze domain characteristics and identify similar domains

    if not paper_extractions:
        return "No cross-field insights available (insufficient data)."

    # Extract key characteristics from first few papers
    characteristics = []

    for paper in paper_extractions[:3]:
        mid = paper.get('mid_level', {})
        stats = mid.get('stats', [])

        for stat in stats:
            metric = stat.get('metric', '').lower()
            if 'sparse' in metric or 'sparsity' in metric:
                characteristics.append("sparse data")
            if 'overdispers' in metric:
                characteristics.append("overdispersion")

    if not characteristics:
        characteristics = ["statistical modeling"]

    # Deduplicate and limit to 2 characteristics
    unique_characteristics = list(set(characteristics))[:2]

    # Generate insight
    insight = f"""**Similarity**: {domain} exhibits {', '.join(unique_characteristics)}, which is common in other domains with similar data structures.

**Transferable**:
- Statistical methods and loss functions developed for {domain}
- Parameter estimation approaches
- Validation strategies

**Expected Impact**: Methods showing 15-30% improvement in {domain} may transfer to domains with similar statistical properties.

<!-- TODO: Replace with Claude Opus 4.5 API for semantic cross-domain analysis -->"""

    return insight


def _generate_top_papers_list(paper_extractions: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Generate ranked list of top papers.

    MVP: Simple chronological + contribution-based ranking
    TODO: Claude API for semantic importance ranking
    """
    papers = []

    for paper in paper_extractions:
        title = paper.get('title', 'Unknown')
        year = paper.get('year', 'N/A')
        pmid = paper.get('pmid', 'N/A')
        high = paper.get('high_level', {})
        contribution = high.get('contribution', 'N/A')

        papers.append({
            'title': title,
            'year': year,
            'pmid': pmid,
            'contribution': contribution
        })

    # Sort by year (descending) - prefer recent papers
    papers.sort(key=lambda x: x['year'] if isinstance(x['year'], int) else 0, reverse=True)

    # Limit to top 5
    return papers[:5]


def _build_markdown_synthesis(
    domain: str,
    key_findings: List[str],
    statistical_approaches: List[Dict[str, Any]],
    cross_field_insights: str,
    top_papers: List[Dict[str, str]]
) -> str:
    """
    Build complete markdown synthesis from components.
    """
    # Title
    title = f"# {domain.replace('-', ' ').title()}: Domain Synthesis\n\n"

    # Key Findings section
    findings_section = "## Key Findings\n\n"
    if key_findings:
        for finding in key_findings:
            findings_section += f"- {finding}\n"
    else:
        findings_section += "- No key findings extracted (MVP limitation)\n"
    findings_section += "\n"

    # Statistical Approaches section
    stats_section = "## Statistical Approaches\n\n"
    if statistical_approaches:
        for i, approach in enumerate(statistical_approaches, 1):
            name = approach['name']
            params = approach.get('parameters', {})
            stats = approach.get('stats', [])
            pmids = approach.get('pmids', [])

            stats_section += f"{i}. **{name}**\n"

            if params:
                param_str = ", ".join(f"{k}={v}" for k, v in params.items())
                stats_section += f"   - Parameters: {param_str}\n"

            if stats:
                for stat in stats[:2]:  # Top 2 stats per method
                    metric = stat.get('metric', 'Unknown')
                    value = stat.get('value', 'N/A')
                    page = stat.get('page', 'N/A')
                    stats_section += f"   - **Key stat**: {metric} = {value} (p.{page})\n"

            if pmids:
                stats_section += f"   - References: PMIDs {', '.join(pmids)}\n"

            stats_section += "\n"
    else:
        stats_section += "No statistical approaches extracted (MVP limitation)\n\n"

    # Cross-Field Transfer section
    transfer_section = "## Cross-Field Transfer\n\n"
    transfer_section += cross_field_insights + "\n\n"

    # Top Papers section
    papers_section = "## Top Papers\n\n"
    if top_papers:
        for i, paper in enumerate(top_papers, 1):
            paper_title = paper['title']
            paper_year = paper['year']
            paper_pmid = paper['pmid']
            paper_contribution = paper['contribution']

            papers_section += f"{i}. **{paper_title}** ({paper_year})\n"
            papers_section += f"   - PMID: {paper_pmid}\n"
            if paper_contribution and paper_contribution != "N/A":
                papers_section += f"   - {paper_contribution}\n"
            papers_section += "\n"
    else:
        papers_section += "No papers available\n\n"

    # Footer note
    footer = "---\n\n"
    footer += "*Generated using rule-based MVP synthesizer. "
    footer += "Future versions will use Claude Opus 4.5 for semantic synthesis.*\n"
    footer += f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"

    # Combine all sections
    synthesis = title + findings_section + stats_section + transfer_section + papers_section + footer

    return synthesis


def _generate_empty_synthesis(domain: str) -> str:
    """Generate placeholder synthesis when no papers available."""
    return f"""# {domain.replace('-', ' ').title()}: Domain Synthesis

## Key Findings

No papers available for this domain.

## Statistical Approaches

No statistical approaches extracted.

## Cross-Field Transfer

No cross-field insights available.

## Top Papers

No papers available.

---

*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""


def synthesize_multiple_domains(
    synthesis_run_id: int,
    domain_ids: List[int],
    db_path: str
) -> Dict[str, Any]:
    """
    Synthesize multiple domains for a synthesis run.

    Args:
        synthesis_run_id: ID of the synthesis run
        domain_ids: List of domain IDs to synthesize (if empty, synthesize all)
        db_path: Path to SQLite database

    Returns:
        Summary dict with synthesis results
    """
    results = {
        "total": 0,
        "successful": 0,
        "failed": 0,
        "errors": []
    }

    with Database(db_path) as db:
        # Get detected domains from synthesis_run if domain_ids not provided
        if not domain_ids:
            cursor = db.conn.execute(
                "SELECT detected_domains FROM synthesis_runs WHERE id=?",
                (synthesis_run_id,)
            )
            row = cursor.fetchone()
            if row:
                domain_names = json.loads(row["detected_domains"])
                # Get or create domain IDs
                domain_ids = []
                for domain_name in domain_names:
                    cursor = db.conn.execute(
                        "INSERT OR IGNORE INTO domains (name) VALUES (?)",
                        (domain_name,)
                    )
                    db.conn.commit()

                    cursor = db.conn.execute(
                        "SELECT id FROM domains WHERE name=?",
                        (domain_name,)
                    )
                    domain_id = cursor.fetchone()["id"]
                    domain_ids.append(domain_id)

        results["total"] = len(domain_ids)

        # Process each domain
        for domain_id in domain_ids:
            try:
                # Get domain name
                cursor = db.conn.execute(
                    "SELECT name FROM domains WHERE id=?",
                    (domain_id,)
                )
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"Domain {domain_id} not found")
                domain_name = row["name"]

                # Get papers for this domain with extractions
                cursor = db.conn.execute(
                    """SELECT p.id, p.title, p.year, p.pmid,
                              pe.high_level, pe.mid_level, pe.low_level
                       FROM papers p
                       JOIN paper_extractions pe ON p.id = pe.paper_id
                       WHERE p.domain = ?""",
                    (domain_name,)
                )
                papers = cursor.fetchall()

                # Format paper extractions
                paper_extractions = []
                for paper in papers:
                    paper_extractions.append({
                        "paper_id": paper["id"],
                        "title": paper["title"],
                        "year": paper["year"],
                        "pmid": paper["pmid"],
                        "high_level": json.loads(paper["high_level"]) if paper["high_level"] else {},
                        "mid_level": json.loads(paper["mid_level"]) if paper["mid_level"] else {},
                        "low_level": json.loads(paper["low_level"]) if paper["low_level"] else {}
                    })

                # Generate synthesis
                synthesis_markdown = synthesize_single_domain(
                    domain_name,
                    paper_extractions,
                    db_path
                )

                # Store in domain_syntheses table
                cursor = db.conn.execute(
                    """INSERT OR REPLACE INTO domain_syntheses
                       (synthesis_run_id, domain_id, summary_markdown, papers_analyzed, paper_ids)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        synthesis_run_id,
                        domain_id,
                        synthesis_markdown,
                        len(paper_extractions),
                        json.dumps([p["paper_id"] for p in paper_extractions])
                    )
                )
                db.conn.commit()

                results["successful"] += 1

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "domain_id": domain_id,
                    "error": str(e)
                })

    return results
