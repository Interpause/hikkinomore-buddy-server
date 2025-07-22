"""Handles storing and retrieving chat history and skill tracking."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Tuple

import aiosqlite
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

if TYPE_CHECKING:
    from src.structs import SkillJudgementFull

# TODO: Probably switch to SQLAlchemy when the expected worst case scenario occurs.
# Actually key-document databases are better...

log = logging.getLogger(__name__)


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

            # Social skills tracking table.
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS skill_evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    skill_type TEXT NOT NULL,
                    score REAL NOT NULL,
                    reason TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    conversation_context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_skill_evaluations_user_skill
                ON skill_evaluations (user_id, skill_type)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_skill_evaluations_session_skill
                ON skill_evaluations (session_id, skill_type)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_skill_evaluations_created_at
                ON skill_evaluations (created_at)
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

    # Social skills tracking methods
    async def add_skill_evaluation(
        self,
        user_id: str,
        session_id: str,
        judgement: "SkillJudgementFull",
    ):
        """Add a skill evaluation record."""
        log.info(
            f"Adding skill for user {user_id} in session {session_id}: {judgement.skill_type} = {judgement.score}"
        )
        log.info(judgement.model_dump_json())

        conn = self.conn
        await conn.execute(
            """INSERT INTO skill_evaluations 
               (user_id, session_id, skill_type, score, reason, confidence, conversation_context) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                session_id,
                judgement.skill_type,
                judgement.score,
                judgement.reason,
                judgement.confidence,
                judgement.conversation_context,
            ),
        )
        await conn.commit()

    # TODO: AI GENERATED. EVALUATE BELOW.
    async def get_skill_scores(
        self, user_id: str, skill_type: str
    ) -> List[Tuple[float, datetime]]:
        """Get all scores for a specific skill for a user."""
        conn = self.conn
        cur = await conn.execute(
            """SELECT score, created_at FROM skill_evaluations 
               WHERE user_id = ? AND skill_type = ? 
               ORDER BY created_at ASC""",
            (user_id, skill_type),
        )
        rows = await cur.fetchall()
        return [(row[0], datetime.fromisoformat(row[1])) for row in rows]

    async def get_all_skill_scores(self, user_id: str) -> dict:
        """Get all skill scores for a user, grouped by skill type."""
        conn = self.conn
        cur = await conn.execute(
            """SELECT skill_type, score, created_at FROM skill_evaluations 
               WHERE user_id = ? 
               ORDER BY skill_type, created_at ASC""",
            (user_id,),
        )
        rows = await cur.fetchall()

        result = {}
        for row in rows:
            skill_type = row[0]
            score = row[1]
            created_at = datetime.fromisoformat(row[2])

            if skill_type not in result:
                result[skill_type] = []
            result[skill_type].append((score, created_at))

        return result

    async def get_skill_mastery_status(self, user_id: str) -> dict:
        """Get mastery status for all skills for a user."""
        from src.agents.skill import SOCIAL_SKILLS
        from src.skills import (
            calculate_weighted_score,
            is_skill_mastered,
        )

        all_scores = await self.get_all_skill_scores(user_id)
        mastery_status = {}

        for skill_type in SOCIAL_SKILLS:
            scores = all_scores.get(skill_type, [])
            if scores:
                weighted_score = calculate_weighted_score(scores)
                is_mastered = is_skill_mastered(scores)
                mastery_status[skill_type] = {
                    "weighted_score": weighted_score,
                    "is_mastered": is_mastered,
                    "total_evaluations": len(scores),
                    "latest_score": scores[-1][0] if scores else None,
                }
            else:
                mastery_status[skill_type] = {
                    "weighted_score": 0.0,
                    "is_mastered": False,
                    "total_evaluations": 0,
                    "latest_score": None,
                }

        return mastery_status

    # END OF EVALUATION.
