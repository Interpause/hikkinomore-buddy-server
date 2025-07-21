"""Social skills evaluation agent."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic_ai import Agent, UnexpectedModelBehavior, capture_run_messages

from src.structs import ConversationMessage, SkillJudgment, SkillJudgmentFull
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


def create_skill_judge_agent() -> Agent[None, SkillJudgment]:
    """Create a skill evaluation agent in a closure, following chat.py pattern."""
    # Build skills list for system prompt
    skills_list = "\n".join(
        [f"- {skill}: {desc}" for skill, desc in SOCIAL_SKILLS.items()]
    )

    # TODO: can be refactored to dynamically match social skills using @agent.instructions
    system_prompt = f"""You are an expert social skills evaluator. Your job is to analyze conversations and identify when users demonstrate specific social skills.

Available Social Skills:
{skills_list}

Your task:
1. Review the conversation context provided
2. Identify if the user demonstrated any of the above social skills
3. Rate the demonstration on a scale from -1.0 to 1.0:
   - 1.0: Excellent demonstration of the skill
   - 0.5: Good demonstration with minor room for improvement
   - 0.0: Neutral or no clear demonstration
   - -0.5: Poor demonstration or missed opportunity
   - -1.0: Behavior that contradicts or undermines the skill

4. Provide a brief, specific reason for your rating
5. Indicate your confidence level (0.0 to 1.0) in the assessment

Important guidelines:
- Focus ONLY on the user's messages and behavior, not the assistant's
- Look for specific behaviors that demonstrate skills, not just topic discussion
- Consider context - what might be appropriate in one situation may not be in another
- Be constructive in your feedback
- If multiple skills are demonstrated, choose the most prominent one
- Return null for skill_type if no clear skill demonstration is observed

Respond with a JSON object matching the required format."""

    agent = Agent(
        # "groq:meta-llama/llama-4-scout-17b-16e-instruct",
        "google-gla:gemini-2.5-flash-lite-preview-06-17",
        output_type=SkillJudgment,
        instructions=system_prompt,
    )

    return agent


async def evaluate_conversation(
    agent: Agent[None, SkillJudgment],
    messages: List[ConversationMessage],
    user_profile: Optional[Dict[str, Any]] = None,
) -> SkillJudgmentFull:
    """Evaluate a conversation for social skill demonstration.

    Args:
        agent: The skill judge agent to use for evaluation
        messages: List of conversation messages to evaluate
        user_profile: Optional user profile context

    Returns:
        SkillJudgmentFull containing the evaluation results
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
            wrapped = SkillJudgmentFull(
                skill_type=output.skill_type,
                score=output.score,
                reason=output.reason,
                confidence=output.confidence,
                conversation_context="\n".join(m.model_dump_json() for m in messages),
                # NOTE: This will be reset later in the DB storage step.
                timestamp=datetime.now(),
            )
            return wrapped

        except UnexpectedModelBehavior as e:
            log.error(f"Messages: {dbg_msgs}", exc_info=e)
            return SkillJudgmentFull(
                skill_type=None,
                reason=f"Evaluation error: {e}",
            )
