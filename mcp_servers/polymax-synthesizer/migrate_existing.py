"""Migrate existing Vanderbilt professor papers to database."""
import json
import sqlite3
from pathlib import Path
from database import Database

def migrate_professor_papers(
    db_path: str,
    professor_name: str,
    affiliation: str,
    json_file: str
) -> int:
    """
    Migrate papers from JSON to database.

    Returns:
        professor_id
    """
    with Database(db_path) as db:
        # Insert or get professor
        cursor = db.conn.execute(
            "INSERT OR IGNORE INTO professors (name, affiliation) VALUES (?, ?)",
            (professor_name, affiliation)
        )
        db.conn.commit()

        cursor = db.conn.execute(
            "SELECT id FROM professors WHERE name=? AND affiliation=?",
            (professor_name, affiliation)
        )
        professor_id = cursor.fetchone()["id"]

        # Load papers from JSON
        with open(json_file) as f:
            papers = json.load(f)
            if isinstance(papers, dict):
                papers = list(papers.values())

        # Insert papers
        for paper in papers:
            # Handle both string and list for authors
            authors = paper.get("authors", [])
            if isinstance(authors, str):
                authors = [authors]

            db.conn.execute(
                """INSERT OR IGNORE INTO papers
                   (pmid, title, year, authors, journal, abstract, doi, professor_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    paper.get("pmid"),
                    paper.get("title"),
                    paper.get("year"),
                    json.dumps(authors),
                    paper.get("journal"),
                    paper.get("abstract"),
                    paper.get("doi"),
                    professor_id
                )
            )

        db.conn.commit()
        return professor_id

def migrate_all_professors(db_path: str):
    """Migrate all Vanderbilt professors to database."""
    professors = [
        ("Yuankai Huo", "Vanderbilt University", "/home/user/yuankai_huo_papers/metadata/all_papers.json"),
        ("Ken Lau", "Vanderbilt University", "/home/user/ken_lau_papers/metadata/all_papers.json"),
        ("Bennett Landman", "Vanderbilt University", "/mnt/c/Users/User/Desktop/bennett_landman_papers/metadata.json"),
        ("Tae Hyun Hwang", "Vanderbilt University", "/home/user/vanderbilt_professors_mcp/data/hwang/metadata/all_papers.json"),
        ("Fedaa Najdawi", "Vanderbilt University", "/home/user/vanderbilt_professors_mcp/data/najdawi/metadata/all_papers.json"),
        ("Hirak Sarkar", "Vanderbilt University", "/home/user/vanderbilt_professors_mcp/data/sarkar/metadata/all_papers.json"),
        ("Mary Kay Washington", "Vanderbilt University", "/home/user/vanderbilt_professors_mcp/data/washington/metadata/all_papers.json"),
    ]

    total_papers = 0
    for name, affiliation, json_file in professors:
        if Path(json_file).exists():
            print(f"Migrating {name}...")

            # Count papers in file
            with open(json_file) as f:
                papers = json.load(f)
                if isinstance(papers, dict):
                    paper_count = len(papers)
                else:
                    paper_count = len(papers)

            migrate_professor_papers(db_path, name, affiliation, json_file)
            total_papers += paper_count
            print(f"  ✓ {name} migrated ({paper_count} papers)")
        else:
            print(f"  ✗ {name} - JSON file not found: {json_file}")

    return total_papers

if __name__ == "__main__":
    import sys
    from database import init_database

    db_path = sys.argv[1] if len(sys.argv) > 1 else "/home/user/mcp_servers/polymax-synthesizer/papers.db"

    print("Initializing database...")
    init_database(db_path)

    print("\nMigrating professors...")
    total_papers = migrate_all_professors(db_path)

    # Print summary
    with Database(db_path) as db:
        cursor = db.conn.execute("SELECT COUNT(*) FROM professors")
        prof_count = cursor.fetchone()[0]
        cursor = db.conn.execute("SELECT COUNT(*) FROM papers")
        paper_count = cursor.fetchone()[0]
        print(f"\n✓ Migration complete: {prof_count} professors, {paper_count} papers")
