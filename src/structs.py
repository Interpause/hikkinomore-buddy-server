"""Data structures."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel

from src.db import Database


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    msg: str
    session_id: str
    user_id: str


# TODO: May be deleted, seems not useful.
class SkillStatus(BaseModel):
    """Status of a single skill for a user."""

    weighted_score: float
    is_mastered: bool
    total_evaluations: int
    latest_score: Optional[float]


# TODO: May be deleted, seems not useful.
class UserSkillSummary(BaseModel):
    """Summary of a user's skill development progress."""

    total_skills: int
    mastered_skills: int
    skills_in_progress: int
    skill_details: Dict[str, SkillStatus]


@dataclass
class ChatDeps:
    """Dependencies for the chat agent."""

    db: Database
    user_id: str
    session_id: str


# NOTE: This is used as an output tool by the skill agent, so the docstrings are important.
class SkillJudgment(BaseModel):
    """Result of skill evaluation."""

    skill_type: Optional[str] = None
    score: float = 0.0
    reason: str = ""
    confidence: float = 1.0  # How confident the judge is in this assessment
    # conversation_context: Optional[str] = None
    # timestamp alr stored in DB via sql CURRENT_TIMESTAMP
    # timestamp: Optional[datetime] = None


class SkillJudgmentFull(SkillJudgment):
    """Full skill judgment with additional context."""

    conversation_context: Optional[str] = None
    timestamp: datetime = datetime.now()  # Default to current time if not provided


class ConversationMessage(BaseModel):
    """Simplified message structure for skill evaluation."""

    role: Literal["system", "user", "assistant"]
    content: str
    timestamp: Optional[datetime] = None
