"""Tests for database module."""
import pytest
import sqlite3
import json
from pathlib import Path
from database import Database, init_database

def test_init_database_creates_tables(tmp_path):
    """Test that init_database creates all required tables."""
    db_path = tmp_path / "test.db"
    init_database(str(db_path))

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check that tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    expected_tables = {
        'professors', 'papers', 'paper_extractions',
        'domains', 'domain_syntheses', 'synthesis_runs', 'manuscripts'
    }

    assert expected_tables.issubset(tables)
    conn.close()

def test_database_context_manager(tmp_path):
    """Test Database class context manager."""
    db_path = tmp_path / "test.db"
    init_database(str(db_path))

    with Database(str(db_path)) as db:
        assert db.conn is not None
        # Test a simple query
        cursor = db.conn.execute("SELECT COUNT(*) FROM professors")
        count = cursor.fetchone()[0]
        assert count == 0

def test_migrate_professor_papers(tmp_path):
    """Test migrating professor papers from JSON to database."""
    from migrate_existing import migrate_professor_papers

    # Create mock JSON data
    papers_data = {
        "12345678": {
            "pmid": "12345678",
            "title": "Test Paper",
            "year": 2023,
            "authors": "Smith J, Doe A"
        }
    }
    json_file = tmp_path / "all_papers.json"
    json_file.write_text(json.dumps(papers_data))

    # Migrate to database
    db_path = tmp_path / "test.db"
    init_database(str(db_path))

    professor_id = migrate_professor_papers(
        str(db_path),
        "Test Professor",
        "Test University",
        str(json_file)
    )

    # Verify migration
    with Database(str(db_path)) as db:
        cursor = db.conn.execute("SELECT COUNT(*) FROM papers")
        assert cursor.fetchone()[0] == 1

        cursor = db.conn.execute("SELECT * FROM papers WHERE pmid=?", ("12345678",))
        paper = cursor.fetchone()
        assert paper["title"] == "Test Paper"
        assert paper["professor_id"] == professor_id
