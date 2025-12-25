"""Database management for PolyMaX Synthesizer."""
import sqlite3
from pathlib import Path
from typing import Optional

SCHEMA_FILE = Path(__file__).parent / "schema.sql"

def init_database(db_path: str) -> None:
    """Initialize database with schema."""
    schema = SCHEMA_FILE.read_text()
    conn = sqlite3.connect(db_path)
    conn.executescript(schema)
    conn.commit()
    conn.close()

class Database:
    """Database context manager."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
