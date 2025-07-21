"""Dependencies for PydanticAI agents."""

from dataclasses import dataclass

from src.db import Database


@dataclass
class ChatDeps:
    """Dependencies for the chat agent."""

    db: Database
    user_id: str
    session_id: str
