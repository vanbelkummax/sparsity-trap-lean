"""Tests for database module."""
import pytest
import sqlite3
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
