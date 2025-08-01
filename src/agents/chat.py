"""Front-facing conversational agent."""

import logging

from pydantic_ai import Agent, RunContext

from src.agents.skill import create_skill_judge_agent
from src.skills import evaluate_recent_conversation, get_user_skill_summary
from src.structs import ChatDeps
from src.user_study_logger import get_user_study_logger

log = logging.getLogger(__name__)


def create_chat_agent():
    """Create front-facing chat agent."""
    from src.agents.prompts import PROMPTS

    agent = Agent(
        # "groq:meta-llama/llama-4-scout-17b-16e-instruct",
        "google-gla:gemini-2.5-flash-lite-preview-06-17",
        deps_type=ChatDeps,
    )

    @agent.instructions
    def instructions(ctx: RunContext[ChatDeps]) -> str:
        """Instructions for the chat agent."""
        preset = ctx.deps.preset
        if preset == "GENERAL_BOT":
            prompt = PROMPTS["chat_generic.md"]
            assert prompt is not None, f"Prompt template not found for {prompt}."
        elif preset == "NERVY_BOT":
            prompt = PROMPTS["chat_nervy.md"]
            assert prompt is not None, f"Prompt template not found for {prompt}."
            if ctx.deps.is_first_message:
                prompt += f"""

Start the conversation with the following introduction:
```
Hey… thanks for choosing me. I totally get what it’s like to overthink every word. Wanna practice chatting with someone who won’t judge you at all? 😊 What kind of social situations make you feel nervous?
```
"""
        elif preset == "AVOI_BOT":
            prompt = PROMPTS["chat_avoi.md"]
            assert prompt is not None, f"Prompt template not found for {prompt}."
            if ctx.deps.is_first_message:
                prompt += f"""

Start the conversation with the following introduction:
```
Hi there. I know small talk can feel… weird. You can talk to me like a colleague, or like a friend—no pressure. Want to start by telling me how your day’s been, casually?
```
"""
        elif preset == "ENTHU_BOT":
            prompt = PROMPTS["chat_enthu.md"]
            assert prompt is not None, f"Prompt template not found for {prompt}."
            if ctx.deps.is_first_message:
                prompt += f"""

Start the conversation with the following introduction:
```
Hi! I’m all ears if you’ve got something cool to share—I love when people are passionate. Want to tell me about something you’re really into lately? Then I’ll help you figure out how to keep others interested too!
```
"""
        elif preset == "ISO_BOT":
            prompt = PROMPTS["chat_iso.md"]
            assert prompt is not None, f"Prompt template not found for {prompt}."
            if ctx.deps.is_first_message:
                prompt += f"""

Start the conversation with the following introduction:
```
Hey. You don’t have to be super social to want connection—I’m here for small steps. Maybe we could just talk about something simple. What’s something you enjoy doing alone?
```
"""
        else:
            raise ValueError(f"Unknown preset: {preset}")
        return prompt

    skill_judge_agent = create_skill_judge_agent()

    # TODO: Maybe this tool should return some judgement info for steering the convo?
    @agent.tool(retries=2, require_parameter_descriptions=True)
    async def judge_conversation(
        ctx: RunContext[ChatDeps],
        recent_messages: int = -1,
    ) -> str:
        """Evaluate recent conversation for social skill demonstration.

        If recent_messages is -1, it will use all messages in the session.

        Args:
            ctx (RunContext[ChatDeps]): The agent context containing database access and session info.
            recent_messages (int): Number of recent messages to analyze (default: -1).

        Returns:
            str: Confirmation message indicating the evaluation was performed.
        """
        log.info(f"Agent called: judge_conversation(recent_messages={recent_messages})")

        db = ctx.deps.db
        session_id = ctx.deps.session_id
        user_id = ctx.deps.user_id
        study_logger = get_user_study_logger()

        # Log tool call
        if study_logger:
            study_logger.log_tool_call(
                user_id,
                session_id,
                "judge_conversation",
                recent_messages=recent_messages,
            )

        # Perform skill evaluation.
        try:
            skill_evaluation = await evaluate_recent_conversation(
                skill_judge_agent=skill_judge_agent,
                message_history=ctx.messages,
                recent_messages=recent_messages,
            )

            # Explicitly store the evaluation if we have a valid skill type and score
            if skill_evaluation.skill_type is not None:
                await db.add_skill_evaluation(
                    user_id=ctx.deps.user_id,
                    session_id=session_id,
                    judgement=skill_evaluation,
                )

                # Log skill judgement
                if study_logger:
                    study_logger.log_skill_judgement(
                        user_id, session_id, skill_evaluation
                    )

                log.info(
                    f"Recorded skill evaluation for user {ctx.deps.user_id} in session {session_id}: {skill_evaluation.skill_type} = {skill_evaluation.score}"
                )
                return "Skill evaluation performed."
            else:
                log.info(f"Reason for no evaluation: {skill_evaluation.reason}")
                return (
                    f"Skill evaluation rejected for reason: {skill_evaluation.reason}"
                )
        except Exception as e:
            log.error(f"Error in judge_conversation tool: {e}", exc_info=e)
            if study_logger:
                study_logger.log_error(
                    user_id, session_id, f"Judge conversation error: {str(e)}"
                )
            return f"Error evaluating conversation."

    # TODO: This was generated by Copilot, it isn't exactly what I want, but close enough to adapt later.
    # @agent.tool
    async def get_user_progress(ctx: RunContext[ChatDeps]) -> str:
        """Get a summary of the user's skill development progress."""
        user_id = ctx.deps.user_id
        session_id = ctx.deps.session_id
        study_logger = get_user_study_logger()

        # Log tool call
        if study_logger:
            study_logger.log_tool_call(user_id, session_id, "get_user_progress")

        try:
            progress = await get_user_skill_summary(ctx.deps)

            # Format the progress into a readable summary
            mastered_count = progress.mastered_skills
            total_count = progress.total_skills
            in_progress_count = progress.skills_in_progress

            summary = f"Progress Summary for this session:\n"
            summary += f"- Mastered skills: {mastered_count}/{total_count}\n"
            summary += f"- Skills in progress: {in_progress_count}\n"

            # Add details about top performing skills
            skill_details = progress.skill_details
            top_skills = sorted(
                [
                    (skill, details)
                    for skill, details in skill_details.items()
                    if details.total_evaluations > 0
                ],
                key=lambda x: x[1].weighted_score,
                reverse=True,
            )[:3]

            if top_skills:
                summary += "\nTop performing skills:\n"
                for skill, details in top_skills:
                    summary += f"- {skill}: {details.weighted_score:.2f} (mastered: {'yes' if details.is_mastered else 'no'})\n"

            return summary

        except Exception as e:
            log.error(f"Error in get_user_progress tool: {e}", exc_info=e)
            if study_logger:
                study_logger.log_error(
                    user_id, session_id, f"Get user progress error: {str(e)}"
                )
            return f"Unable to retrieve progress: {str(e)}"

    return agent
