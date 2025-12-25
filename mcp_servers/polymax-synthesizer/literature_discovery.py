"""Literature discovery (targeted and broad modes)."""
import json
from database import Database
from typing import List, Dict, Any

def discover_targeted_literature(queries: List[str], db_path: str) -> Dict[str, Any]:
    """
    Targeted literature discovery (for primary research mode).

    Searches existing database for papers matching queries.
    In production, would also use WebSearch + PubMed APIs.

    Args:
        queries: List of search queries (e.g., "Yuankai Huo Img2ST")
        db_path: Path to database

    Returns:
        {
            "professors_added": int,
            "papers_added": int,
            "targeted_matches": [...]
        }
    """
    targeted_matches = []
    professors_found = set()
    papers_found = set()

    with Database(db_path) as db:
        for query in queries:
            query_lower = query.lower()
            terms = query_lower.split()

            # Search papers by title
            cursor = db.conn.execute(
                "SELECT p.*, prof.name as professor_name FROM papers p LEFT JOIN professors prof ON p.professor_id = prof.id"
            )

            for row in cursor.fetchall():
                title = (row["title"] or "").lower()
                professor = row["professor_name"] or ""

                # Score by number of matching terms
                score = sum(1 for term in terms if term in title or term in professor.lower())

                if score > 0:
                    professors_found.add(row["professor_id"])
                    papers_found.add(row["id"])

                    # Record match
                    if not any(m["query"] == query and m["paper_id"] == row["id"] for m in targeted_matches):
                        targeted_matches.append({
                            "query": query,
                            "professor": professor,
                            "paper_id": row["id"],
                            "paper_title": row["title"],
                            "pmid": row["pmid"],
                            "score": score
                        })

    # Sort matches by score
    for match_group in targeted_matches:
        if "score" in match_group:
            pass  # Already has score

    return {
        "professors_added": len(professors_found),
        "papers_added": len(papers_found),
        "breakdown_by_domain": {},  # TODO: implement domain breakdown
        "targeted_matches": sorted(targeted_matches, key=lambda x: x.get("score", 0), reverse=True)[:20]
    }

def discover_broad_literature(domains: List[str], db_path: str) -> Dict[str, Any]:
    """
    Broad literature discovery (for review mode).

    TODO: Implement web search + PubMed for each domain.
    For now, just searches existing database.
    """
    # Stub for now
    return {
        "professors_added": 0,
        "papers_added": 0,
        "breakdown_by_domain": {}
    }
