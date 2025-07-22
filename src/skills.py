"""Social skills detection and tracking."""

import logging
from datetime import datetime
from typing import List

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage

from src.agents.skill import (
    MASTERY_THRESHOLD,
    MIN_SCORES_FOR_MASTERY,
    RECENCY_ALPHA,
    SOCIAL_SKILLS,
    evaluate_conversation,
)
from src.structs import (
    ChatDeps,
    SkillJudgement,
    SkillJudgementFull,
    SkillStatus,
    UserSkillSummary,
)
from src.utils import convert_model_messages_to_conversation

log = logging.getLogger(__name__)


def calculate_weighted_score(
    scores: List[tuple[float, datetime]], alpha: float = RECENCY_ALPHA
) -> float:
    """Calculate weighted recency score from a list of (score, timestamp) tuples."""
    if not scores:
        return 0.0

    # Sort by timestamp (oldest first)
    sorted_scores = sorted(scores, key=lambda x: x[1])

    # Calculate weighted average using exponential decay
    weighted_score = sorted_scores[0][0]  # Start with first score

    for score, _ in sorted_scores[1:]:
        weighted_score = alpha * score + (1 - alpha) * weighted_score

    return weighted_score


def is_skill_mastered(
    scores: List[tuple[float, datetime]], threshold: float = MASTERY_THRESHOLD
) -> bool:
    """Determine if a skill is mastered based on weighted recency scoring."""
    if len(scores) < MIN_SCORES_FOR_MASTERY:
        return False

    weighted_score = calculate_weighted_score(scores)
    return weighted_score >= threshold


async def evaluate_recent_conversation(
    skill_judge_agent: Agent[None, SkillJudgement],
    message_history: List[ModelMessage],
    recent_messages: int,
) -> SkillJudgementFull:
    """Evaluate recent conversation for social skill demonstration.

    This method only performs the evaluation and returns the judgement.
    It does not store the evaluation in the database - that should be
    done explicitly by the caller if needed.

    Args:
        skill_judge_agent: Agent used to evaluate the conversation for skill demonstration.
        message_history: List of PydanticAI ModelMessage objects.
        recent_messages: Number of recent messages to analyze.

    Returns:
        SkillJudgementFull containing the evaluation results.
    """
    if not message_history or len(message_history) < 2:
        return SkillJudgementFull(
            skill_type=None,
            reason="Insufficient conversation history for evaluation",
        )

    # Convert PydanticAI messages to our ConversationMessage format
    conversation_messages = convert_model_messages_to_conversation(
        message_history=message_history,
        recent_messages=recent_messages if recent_messages > 0 else None,
        skip_system_messages=True,
        skip_tool_messages=True,
    )

    if not conversation_messages:
        return SkillJudgementFull(
            skill_type=None,
            reason="No valid conversation content found for evaluation",
        )

    # Get user profile for additional context (placeholder for now)
    user_profile = None  # We removed user_profiles table for now

    # Evaluate the conversation using the refactored function
    judgement = await evaluate_conversation(
        skill_judge_agent, conversation_messages, user_profile
    )

    return judgement


async def get_user_skill_summary(deps: ChatDeps) -> UserSkillSummary:
    """Get a summary of the user's skill development progress."""
    db = deps.db
    user_id = deps.user_id

    mastery_status = await db.get_skill_mastery_status(user_id)

    # Convert raw dict data to SkillStatus models
    skill_details = {
        skill_type: SkillStatus(**status_data)
        for skill_type, status_data in mastery_status.items()
    }

    summary = UserSkillSummary(
        total_skills=len(SOCIAL_SKILLS),
        mastered_skills=sum(
            1 for status in mastery_status.values() if status["is_mastered"]
        ),
        skills_in_progress=sum(
            1
            for status in mastery_status.values()
            if status["total_evaluations"] > 0 and not status["is_mastered"]
        ),
        skill_details=skill_details,
    )

    return summary
