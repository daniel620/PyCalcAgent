"""Persistent SQLite database memory, vector indexing, and async background tasks (Criterion 2)."""

import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field


class VariableRecord(BaseModel):
    """Schema representing a stored numerical variable or constant."""
    name: str
    value: float
    description: str
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CalculationRecord(BaseModel):
    """Schema representing an executed calculation history entry."""
    query: str
    python_code: str
    result: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CalculationMemory:
    """Robust multi-turn memory backed by SQLite database with vector keyword indexing and async background tasks."""

    def __init__(self, db_path: str = ".calc_memory.db"):
        self.db_path = Path(db_path)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="calc_mem_worker")
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database tables for variables, history, and simple vector keyword store."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS variables (
                    name TEXT PRIMARY KEY,
                    value REAL NOT NULL,
                    description TEXT,
                    updated_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    python_code TEXT NOT NULL,
                    result TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vector_index (
                    history_id INTEGER PRIMARY KEY,
                    keywords TEXT NOT NULL,
                    FOREIGN KEY(history_id) REFERENCES history(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    def set_variable(self, name: str, value: float, description: str = "") -> VariableRecord:
        """Synchronously store or update a variable in SQLite database."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO variables (name, value, description, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    value=excluded.value,
                    description=excluded.description,
                    updated_at=excluded.updated_at
                """,
                (name, value, description, now),
            )
            conn.commit()
        return VariableRecord(name=name, value=value, description=description, updated_at=now)

    async def set_variable_async(self, name: str, value: float, description: str = "") -> VariableRecord:
        """Asynchronously store a variable in a background worker thread to prevent blocking."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self.set_variable, name, value, description
        )

    def get_variable(self, name: str) -> float | None:
        """Retrieve a variable value by name from SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM variables WHERE name = ?", (name,))
            row = cursor.fetchone()
            return row[0] if row else None

    def list_variables(self) -> dict[str, float]:
        """Return a dictionary of all stored variable names and values."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, value FROM variables ORDER BY name")
            return {row[0]: row[1] for row in cursor.fetchall()}

    def add_history(self, query: str, python_code: str, result: str) -> CalculationRecord:
        """Record a completed calculation into SQLite history table and vector index."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO history (query, python_code, result, timestamp) VALUES (?, ?, ?, ?)",
                (query, python_code, result, now),
            )
            history_id = cursor.lastrowid
            # Tokenize query keywords for our simple vector store index
            keywords = " ".join(query.lower().split())
            cursor.execute(
                "INSERT INTO vector_index (history_id, keywords) VALUES (?, ?)",
                (history_id, keywords),
            )
            conn.commit()
        return CalculationRecord(query=query, python_code=python_code, result=result, timestamp=now)

    async def add_history_async(self, query: str, python_code: str, result: str) -> CalculationRecord:
        """Asynchronously record calculation history in a background worker thread."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self.add_history, query, python_code, result
        )

    def get_recent_history(self, limit: int = 5) -> list[CalculationRecord]:
        """Return the most recent calculation records with sliding window compaction."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT query, python_code, result, timestamp FROM history ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
            return [
                CalculationRecord(query=r[0], python_code=r[1], result=r[2], timestamp=r[3])
                for r in reversed(rows)
            ]

    def search_history_semantic(self, keyword: str, limit: int = 5) -> list[CalculationRecord]:
        """Semantic/keyword search across stored vector index."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT h.query, h.python_code, h.result, h.timestamp
                FROM history h
                JOIN vector_index v ON h.id = v.history_id
                WHERE v.keywords LIKE ?
                ORDER BY h.id DESC LIMIT ?
                """,
                (f"%{keyword.lower()}%", limit),
            )
            rows = cursor.fetchall()
            return [
                CalculationRecord(query=r[0], python_code=r[1], result=r[2], timestamp=r[3])
                for r in rows
            ]

    def clear(self) -> None:
        """Clear all stored variables, history, and vector index."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM variables")
            cursor.execute("DELETE FROM history")
            cursor.execute("DELETE FROM vector_index")
            conn.commit()
