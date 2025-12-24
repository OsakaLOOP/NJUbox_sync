import sqlite3
import logging
from pathlib import Path
from datetime import datetime

class VideoMappingDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS mappings (
                        source_path TEXT PRIMARY KEY,
                        strm_path TEXT NOT NULL,
                        seafile_url TEXT,
                        last_updated TIMESTAMP
                    )
                """)
                # Add index on strm_path for reverse lookups if needed
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_strm_path ON mappings(strm_path)
                """)
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database initialization failed: {e}")

    def upsert_mapping(self, source_path: Path, strm_path: Path, seafile_url: str = None):
        """Insert or Update a file mapping."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO mappings (source_path, strm_path, seafile_url, last_updated)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(source_path) DO UPDATE SET
                        strm_path=excluded.strm_path,
                        seafile_url=coalesce(excluded.seafile_url, mappings.seafile_url),
                        last_updated=excluded.last_updated
                """, (
                    str(source_path.resolve()),
                    str(strm_path.resolve()),
                    seafile_url,
                    datetime.now()
                ))
                conn.commit()
                logging.debug(f"DB: Mapped {source_path} -> {strm_path}")
        except sqlite3.Error as e:
            logging.error(f"Failed to save mapping for {source_path}: {e}")

    def get_mapping(self, source_path: Path):
        """Retrieve mapping for a source path."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT strm_path, seafile_url FROM mappings WHERE source_path = ?", (str(source_path.resolve()),))
                row = cursor.fetchone()
                if row:
                    return {'strm_path': Path(row[0]), 'seafile_url': row[1]}
                return None
        except sqlite3.Error as e:
            logging.error(f"Failed to get mapping: {e}")
            return None

    def delete_mapping(self, source_path: str):
        """Delete a mapping by source path string (used during iteration)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM mappings WHERE source_path = ?", (source_path,))
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Failed to delete mapping: {e}")

    def get_all_mappings(self):
        """Yields all mappings as (source_path_str, strm_path_str)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT source_path, strm_path FROM mappings")
                while True:
                    rows = cursor.fetchmany(100)
                    if not rows:
                        break
                    for row in rows:
                        yield row
        except sqlite3.Error as e:
            logging.error(f"Failed to fetch mappings: {e}")

    def close(self):
        pass # sqlite3 context manager handles closing, but we keep this for interface
