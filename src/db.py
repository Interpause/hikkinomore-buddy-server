"""Handles storing and retrieving chat history."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

import aiosqlite
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

# TODO: Probably switch to SQLAlchemy when the expected worst case scenario occurs.
# Actually key-document databases are better...


# TODO: caching if it turns out to be a bottleneck.
class Database:
    """Database to manage chat sessions."""

    def __init__(self, conn: aiosqlite.Connection):
        """Initialize the database with a connection."""
        self.conn = conn

    @classmethod
    @asynccontextmanager
    async def connect(cls, path: str | Path):
        """Connect to the database."""
        async with aiosqlite.connect(path) as conn:
            # Initialize the database schema as necessary.
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                ON messages (session_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id
                ON sessions (user_id)
            """)
            await conn.commit()

            yield cls(conn)

    # TODO: session_id by right should be allocated by server, not client.
    async def ensure_session(self, session_id: str, user_id: str):
        """Create a new session."""
        conn = self.conn
        # Check if session_id already exists.
        cur = await conn.execute(
            """SELECT 1 FROM sessions WHERE id = ?""", (session_id,)
        )
        if await cur.fetchone() is not None:
            return  # Don't waste time to INSERT OR IGNORE then commit.

        await conn.execute(
            """INSERT INTO sessions (id, user_id) VALUES (?, ?)""",
            (session_id, user_id),
        )
        await conn.commit()

    async def ensure_user(self, user_id: str):
        """Create a new user if it doesn't exist."""
        conn = self.conn
        # Check if user_id already exists.
        cur = await conn.execute("""SELECT 1 FROM users WHERE id = ?""", (user_id,))
        if await cur.fetchone() is not None:
            return  # Don't waste time to INSERT OR IGNORE then commit.

        await conn.execute("""INSERT INTO users (id) VALUES (?)""", (user_id,))
        await conn.commit()

    async def get_user_sessions(self, user_id: str) -> List[str]:
        """Get all session IDs for a user."""
        conn = self.conn
        cur = await conn.execute(
            """SELECT id FROM sessions WHERE user_id = ?""",
            (user_id,),
        )
        rows = await cur.fetchall()
        return [row[0] for row in rows]

    # NOTE: The messages are saved & retrieved in chunks of several messages.
    async def get_messages(self, session_id: str) -> List[ModelMessage]:
        """Retrieve messages for a session."""
        conn = self.conn
        cur = await conn.execute(
            """SELECT data FROM messages WHERE session_id = ? ORDER BY id ASC""",
            (session_id,),
        )
        messages = []
        rows = await cur.fetchall()
        for row in rows:
            messages.extend(ModelMessagesTypeAdapter.validate_json(row[0]))
        return messages

    async def add_messages(self, session_id: str, messages: List[ModelMessage]):
        """Add messages to a session."""
        conn = self.conn
        data = ModelMessagesTypeAdapter.dump_json(messages)
        await conn.execute(
            """INSERT INTO messages (session_id, data) VALUES (?, ?)""",
            (session_id, data),
        )
        await conn.commit()
