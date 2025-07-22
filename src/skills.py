"""Social skills detection and tracking."""
# Man this is the most AI generated file, but I don't know anything about how one
# would define mastery of social skills anyways.

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
    """Calculate weighted recency score from a list of (score, timestamp) tuples.

    The timestamp is only used to order the scores, not for time decay.
    """
    if not scores:
        return 0.0

    # Sort by timestamp (oldest first)
    sorted_scores = sorted(scores, key=lambda x: x[1])

    # Calculate weighted average using exponential decay
    weighted_score = sorted_scores[0][0]  # Start with first score

    for score, _ in sorted_scores[1:]:
        weighted_score = alpha * score + (1 - alpha) * weighted_score

    return weighted_score


def calculate_time_weighted_score(
    scores: List[tuple[float, datetime]],
    time_decay_days: float = 30.0,
    min_weight: float = 0.1,
) -> float:
    """Calculate time-weighted score that factors in time deltas between evaluations.

    This version gives more weight to recent scores based on how much time has passed
    since each evaluation, with exponential decay over time.

    Args:
        scores: List of (score, timestamp) tuples
        time_decay_days: Number of days for weight to decay to ~37% (1/e)
        min_weight: Minimum weight to assign to very old scores

    Returns:
        Time-weighted average score
    """
    if not scores:
        return 0.0

    if len(scores) == 1:
        return scores[0][0]

    # Sort by timestamp (oldest first)
    sorted_scores = sorted(scores, key=lambda x: x[1])

    # Use the most recent timestamp as reference point
    latest_time = sorted_scores[-1][1]

    # Calculate time-based weights and weighted sum
    weighted_sum = 0.0
    total_weight = 0.0

    for score, timestamp in sorted_scores:
        # Calculate days since this score relative to the latest score
        days_ago = (latest_time - timestamp).total_seconds() / (24 * 3600)

        # Exponential decay: weight = e^(-days_ago / time_decay_days)
        # This gives full weight (1.0) to the latest score and decays older ones
        import math

        weight = max(min_weight, math.exp(-days_ago / time_decay_days))

        weighted_sum += score * weight
        total_weight += weight

    return weighted_sum / total_weight if total_weight > 0 else 0.0


def is_skill_mastered(
    scores: List[tuple[float, datetime]], threshold: float = MASTERY_THRESHOLD
) -> bool:
    """Determine if a skill is mastered based on weighted recency scoring."""
    if len(scores) < MIN_SCORES_FOR_MASTERY:
        return False

    weighted_score = calculate_weighted_score(scores)
    return weighted_score >= threshold


def is_skill_mastered_time_aware(
    scores: List[tuple[float, datetime]],
    threshold: float = MASTERY_THRESHOLD,
    use_time_weighting: bool = True,
    time_decay_days: float = 30.0,
) -> bool:
    """Determine if a skill is mastered using time-aware weighted scoring.

    Args:
        scores: List of (score, timestamp) tuples
        threshold: Minimum weighted score required for mastery
        use_time_weighting: Whether to use time-based weighting or simple recency weighting
        time_decay_days: Number of days for time weight decay (only used if use_time_weighting=True)

    Returns:
        True if the skill is considered mastered
    """
    if len(scores) < MIN_SCORES_FOR_MASTERY:
        return False

    if use_time_weighting:
        weighted_score = calculate_time_weighted_score(scores, time_decay_days)
    else:
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
    # Convert PydanticAI messages to our ConversationMessage format
    conversation_messages = convert_model_messages_to_conversation(
        message_history=message_history,
        recent_messages=recent_messages if recent_messages > 0 else None,
        skip_system_messages=True,
        skip_tool_messages=True,
    )

    if len(conversation_messages) < 2:
        return SkillJudgementFull(
            skill_type=None,
            reason="Insufficient conversation history for evaluation",
        )

    # Get user profile for additional context (placeholder for now)
    # TODO: user_profile is ideally a merge of the chatbot's notes, user input, and skill history.
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

    # Get all skill evaluations for this user
    skill_history = await db.get_skill_history(user_id)

    # Group evaluations by skill type
    scores_by_skill = {}
    for evaluation in skill_history:
        if evaluation.skill_type is not None:  # Skip evaluations with no skill type
            if evaluation.skill_type not in scores_by_skill:
                scores_by_skill[evaluation.skill_type] = []
            scores_by_skill[evaluation.skill_type].append(
                (evaluation.score, evaluation.timestamp)
            )

    # Calculate mastery status using business logic
    skill_details = {}
    mastered_count = 0
    in_progress_count = 0

    for skill_type in SOCIAL_SKILLS:
        scores = scores_by_skill.get(skill_type, [])
        if scores:
            weighted_score = calculate_weighted_score(scores)
            is_mastered = is_skill_mastered(scores)

            skill_details[skill_type] = SkillStatus(
                weighted_score=weighted_score,
                is_mastered=is_mastered,
                total_evaluations=len(scores),
                latest_score=scores[-1][0] if scores else None,
            )

            if is_mastered:
                mastered_count += 1
            elif len(scores) > 0:
                in_progress_count += 1
        else:
            skill_details[skill_type] = SkillStatus(
                weighted_score=0.0,
                is_mastered=False,
                total_evaluations=0,
                latest_score=None,
            )

    summary = UserSkillSummary(
        total_skills=len(SOCIAL_SKILLS),
        mastered_skills=mastered_count,
        skills_in_progress=in_progress_count,
        skill_details=skill_details,
    )

    return summary
