"""Paper extraction module for PolyMaX Synthesizer.

This module provides hierarchical extraction of paper content.
MVP implementation uses rule-based heuristics; future versions
will integrate Claude API for deeper analysis.
"""

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from database import Database


def extract_single_paper(paper_id: int, db_path: str) -> Dict[str, Any]:
    """
    Extract hierarchical data from a single paper.

    MVP Implementation Strategy:
    - high_level: Extract from title + abstract
    - mid_level: Simple pattern matching for stats/methods
    - low_level: Quote extraction from abstract
    - code_methods: TODO (requires full-text processing)

    Future Enhancement:
    - Integrate Claude API for semantic understanding
    - Process full_text_markdown for deeper extraction
    - Extract mathematical equations and algorithms
    - Identify hyperparameters and experimental setup

    Args:
        paper_id: Database ID of the paper
        db_path: Path to SQLite database

    Returns:
        Dictionary with hierarchical extraction data
    """
    with Database(db_path) as db:
        # Fetch paper data
        cursor = db.conn.execute(
            """SELECT id, title, abstract, full_text_markdown, authors, year, journal
               FROM papers WHERE id = ?""",
            (paper_id,)
        )
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Paper with ID {paper_id} not found")

        paper_data = {
            "id": row["id"],
            "title": row["title"],
            "abstract": row["abstract"] or "",
            "full_text": row["full_text_markdown"] or "",
            "authors": row["authors"],
            "year": row["year"],
            "journal": row["journal"]
        }

    # Perform hierarchical extraction
    extraction = {
        "high_level": _extract_high_level(paper_data),
        "mid_level": _extract_mid_level(paper_data),
        "low_level": _extract_low_level(paper_data),
        "code_methods": _extract_code_methods(paper_data)
    }

    # Store extraction in database
    _store_extraction(paper_id, extraction, db_path)

    return extraction


def _extract_high_level(paper_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract high-level summary from title and abstract.

    MVP Strategy:
    - main_claim: Use title as primary claim
    - novelty: Extract first sentence from abstract
    - contribution: Extract key phrases about methods/results

    TODO: Replace with Claude API for semantic understanding
    """
    title = paper_data["title"]
    abstract = paper_data["abstract"]

    # Main claim is the title
    main_claim = title.strip()

    # Novelty: extract first meaningful sentence from abstract
    novelty = "No abstract available"
    if abstract:
        # Find first sentence (ending with ., !, or ?)
        match = re.search(r'^(.*?[.!?])', abstract, re.DOTALL)
        if match:
            novelty = match.group(1).strip()

    # Contribution: look for method/result keywords
    contribution = "Not extracted (MVP)"
    if abstract:
        # Simple heuristic: look for sentences with method/result keywords
        keywords = ['propose', 'develop', 'demonstrate', 'show', 'achieve', 'improve']
        sentences = re.split(r'[.!?]', abstract)
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in keywords):
                contribution = sentence.strip()
                break

    return {
        "main_claim": main_claim,
        "novelty": novelty,
        "contribution": contribution
    }


def _extract_mid_level(paper_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract statistics and methods from abstract.

    MVP Strategy:
    - stats: Pattern match numbers with context (accuracy, AUC, p-value, etc.)
    - methods: Extract capitalized method names (e.g., "U-Net", "BERT")

    TODO: Claude API for semantic extraction of experimental results
    """
    abstract = paper_data["abstract"]

    stats = []
    methods = []

    if abstract:
        # Extract statistics: numbers with units/context
        # Pattern: number (possibly with %, decimal) + context word
        stat_patterns = [
            (r'(\w+)\s*[=:]\s*([\d.]+%?)', 'equality'),  # "accuracy = 0.95"
            (r'([\d.]+%?)\s*(\w+)', 'value_first'),  # "95% accuracy"
            (r'p\s*[<>=]\s*([\d.e-]+)', 'p_value'),  # "p < 0.05"
        ]

        for pattern, ptype in stat_patterns:
            matches = re.finditer(pattern, abstract, re.IGNORECASE)
            for match in matches:
                if ptype == 'p_value':
                    stats.append({
                        "type": "p-value",
                        "metric": "statistical significance",
                        "value": match.group(1),
                        "context": match.group(0),
                        "page": "abstract"
                    })
                elif ptype == 'equality':
                    metric, value = match.groups()
                    # Try to parse as float if possible
                    try:
                        numeric_value = float(value.rstrip('%'))
                    except ValueError:
                        numeric_value = value

                    stats.append({
                        "type": "performance",
                        "metric": metric,
                        "value": numeric_value,
                        "context": match.group(0),
                        "page": "abstract"
                    })

        # Extract methods: Look for capitalized technical terms
        # Pattern: words with capital letters (excluding start of sentence)
        method_pattern = r'(?<!^)(?<!\.\s)([A-Z][A-Za-z]*(?:-[A-Z][A-Za-z]*)*)'
        method_matches = re.finditer(method_pattern, abstract)

        seen_methods = set()
        for match in method_matches:
            method_name = match.group(1)
            # Filter out common words (simple heuristic)
            if method_name not in ['The', 'This', 'We', 'Our', 'Results', 'Methods', 'Figure', 'Table']:
                if method_name not in seen_methods:
                    methods.append({
                        "name": method_name,
                        "parameters": {},  # TODO: extract from full text
                        "page": "abstract"
                    })
                    seen_methods.add(method_name)

    return {
        "stats": stats,
        "methods": methods
    }


def _extract_low_level(paper_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract quotes from abstract and full text.

    MVP Strategy:
    - Extract sentences with key findings/claims
    - Use quoted text or sentences with strong claim words

    TODO: Claude API for extracting salient quotes with context
    """
    abstract = paper_data["abstract"]

    quotes = []

    if abstract:
        # Extract sentences with strong claim words
        claim_keywords = ['demonstrate', 'show', 'prove', 'found', 'discovered', 'achieved']
        sentences = re.split(r'(?<=[.!?])\s+', abstract)

        for i, sentence in enumerate(sentences):
            if any(keyword in sentence.lower() for keyword in claim_keywords):
                quotes.append({
                    "text": sentence.strip(),
                    "page": "abstract",
                    "section": "Abstract",
                    "context": f"Sentence {i+1} of abstract"
                })

    return {
        "quotes": quotes
    }


def _extract_code_methods(paper_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract algorithms and equations from full text.

    MVP Strategy:
    - Mark as TODO since requires full-text processing
    - Future: Parse LaTeX equations, pseudocode blocks, hyperparameters

    TODO: Implement full-text parsing for code/methods extraction
    TODO: Claude API for algorithm understanding and equation parsing
    """
    # TODO: This requires full_text_markdown processing
    # For MVP, return empty structures

    return {
        "algorithms": [],  # TODO: extract from Methods section
        "equations": [],   # TODO: parse LaTeX equations
        "hyperparameters": []  # TODO: extract training details
    }


def _store_extraction(paper_id: int, extraction: Dict[str, Any], db_path: str) -> None:
    """
    Store extraction results in paper_extractions table.

    Args:
        paper_id: Database ID of the paper
        extraction: Hierarchical extraction data
        db_path: Path to SQLite database
    """
    with Database(db_path) as db:
        # Check if extraction already exists
        cursor = db.conn.execute(
            "SELECT id FROM paper_extractions WHERE paper_id = ?",
            (paper_id,)
        )
        existing = cursor.fetchone()

        if existing:
            # Update existing extraction
            db.conn.execute(
                """UPDATE paper_extractions
                   SET high_level = ?, mid_level = ?, low_level = ?, code_methods = ?,
                       extraction_model = ?, extracted_at = ?
                   WHERE paper_id = ?""",
                (
                    json.dumps(extraction["high_level"]),
                    json.dumps(extraction["mid_level"]),
                    json.dumps(extraction["low_level"]),
                    json.dumps(extraction["code_methods"]),
                    "rule-based-mvp",  # Mark as MVP implementation
                    datetime.now().isoformat(),
                    paper_id
                )
            )
        else:
            # Insert new extraction
            db.conn.execute(
                """INSERT INTO paper_extractions
                   (paper_id, high_level, mid_level, low_level, code_methods, extraction_model)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    paper_id,
                    json.dumps(extraction["high_level"]),
                    json.dumps(extraction["mid_level"]),
                    json.dumps(extraction["low_level"]),
                    json.dumps(extraction["code_methods"]),
                    "rule-based-mvp"
                )
            )

        db.conn.commit()


def extract_multiple_papers(paper_ids: List[int], db_path: str) -> Dict[str, Any]:
    """
    Extract multiple papers in batch.

    Future Enhancement:
    - Parallelize extractions using asyncio
    - Add progress tracking
    - Batch Claude API calls for efficiency

    Args:
        paper_ids: List of paper IDs to extract
        db_path: Path to SQLite database

    Returns:
        Summary of extractions with success/failure counts
    """
    results = {
        "total": len(paper_ids),
        "successful": 0,
        "failed": 0,
        "errors": []
    }

    for paper_id in paper_ids:
        try:
            extract_single_paper(paper_id, db_path)
            results["successful"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({
                "paper_id": paper_id,
                "error": str(e)
            })

    return results
