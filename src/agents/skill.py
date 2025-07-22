"""Social skills evaluation agent."""

import logging
from typing import Any, Dict, List, Optional

from pydantic_ai import Agent, capture_run_messages

from src.structs import ConversationMessage, SkillJudgement, SkillJudgementFull
from src.utils import format_conversation

# Configuration constants
MASTERY_THRESHOLD = 0.8
RECENCY_ALPHA = 0.7  # Higher values give more weight to recent scores
MIN_SCORES_FOR_MASTERY = 3  # Minimum number of scores needed before considering mastery

# Hardcoded social skills dictionary
SOCIAL_SKILLS = {
    "active_listening": "Shows understanding by paraphrasing, asking clarifying questions, or reflecting back what was heard.",
    "assertiveness": "Expresses opinions, needs, or boundaries clearly and respectfully without being aggressive or passive.",
    "empathy": "Demonstrates understanding and acknowledgment of another person's feelings and perspectives.",
    "conversation_initiation": "Starts conversations naturally and appropriately in social contexts.",
    "conflict_resolution": "Addresses disagreements or tensions constructively and seeks mutually beneficial solutions.",
    "emotional_regulation": "Manages own emotions appropriately in social situations, staying calm under pressure.",
    "social_awareness": "Reads social cues, understands group dynamics, and adapts behavior to social context.",
    "encouragement": "Provides positive support, validation, or motivation to others.",
    "boundary_setting": "Clearly communicates personal limits and respects others' boundaries.",
    "small_talk": "Engages in light, casual conversation to build rapport and maintain social connections.",
}

log = logging.getLogger(__name__)


def create_skill_judge_agent() -> Agent[None, SkillJudgement]:
    """Create a skill evaluation agent in a closure, following chat.py pattern."""
    from src.agents.prompts import PROMPTS

    # TODO: can be refactored to dynamically match social skills using @agent.instructions
    # Build skills list for system prompt
    skills_list = "\n".join(
        [f"- {skill}: {desc}" for skill, desc in SOCIAL_SKILLS.items()]
    )

    # Load prompt template and format with skills list
    prompt_template = PROMPTS["skill_generic.md"]
    if prompt_template is None:
        raise ValueError("skill_generic.md prompt not found")

    system_prompt = prompt_template.format(skills_list=skills_list)

    agent = Agent(
        # "groq:meta-llama/llama-4-scout-17b-16e-instruct",
        "google-gla:gemini-2.5-flash-lite-preview-06-17",
        output_type=SkillJudgement,
        instructions=system_prompt,
    )

    return agent


async def evaluate_conversation(
    agent: Agent[None, SkillJudgement],
    messages: List[ConversationMessage],
    user_profile: Optional[Dict[str, Any]] = None,
) -> SkillJudgementFull:
    """Evaluate a conversation for social skill demonstration.

    Args:
        agent: The skill judge agent to use for evaluation
        messages: List of conversation messages to evaluate
        user_profile: Optional user profile context

    Returns:
        SkillJudgementFull containing the evaluation results
    """
    # Format conversation for analysis
    conversation_text = format_conversation(messages)

    # Add user profile context if available
    profile_context = ""
    if user_profile:
        profile_context = f"\nUser Profile Context: {user_profile.get('notes', 'No specific profile notes')}"

    prompt = f"""Analyze this conversation for social skill demonstration:

{conversation_text}{profile_context}

Focus on the user's behavior and provide your evaluation."""

    with capture_run_messages() as dbg_msgs:
        try:
            # Use await instead of streaming for full output
            result = await agent.run(prompt)
            output = result.output
            skill_type = output.skill_type
            if skill_type is not None and skill_type.lower() in {
                "null",
                "none",
                "na",
                "nil",
                "n/a",
            }:
                skill_type = None
            wrapped = SkillJudgementFull(
                skill_type=skill_type,
                score=output.score,
                reason=output.reason,
                confidence=output.confidence,
                conversation_context="\n".join(m.model_dump_json() for m in messages),
            )
            return wrapped

        except Exception as e:
            log.error(f"Messages: {dbg_msgs}", exc_info=e)
            return SkillJudgementFull(
                skill_type=None,
                reason=f"Evaluation error: {e}",
            )
