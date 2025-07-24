"""Main app."""

from dotenv import load_dotenv

load_dotenv()

import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic_ai import capture_run_messages

from src.agents.chat import create_chat_agent
from src.db import Database
from src.skills import get_user_skill_summary
from src.structs import ChatDeps, ChatRequest, ConversationMessage
from src.user_study_logger import get_user_study_logger, init_user_study_logger
from src.utils import convert_model_messages_to_conversation

__all__ = ["create_app"]
log = logging.getLogger(__name__)


def create_app():
    """App factory.

    Creating the app within a function prevents mishaps if using multiprocessing.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Put only heavy loading or cleanup tasks here."""
        # Initialize user study logging
        import os

        logging_enabled = os.getenv("USER_STUDY_LOGGING", "true").lower() == "true"
        init_user_study_logger(enabled=logging_enabled)

        async with Database.connect("db.sqlite") as db:
            yield dict(db=db)
        # cleanup tasks

    app = FastAPI(lifespan=lifespan)

    chat_agent = create_chat_agent()

    async def get_db(request: Request) -> Database:
        return request.state.db

    # TODO: Artificially split into several chat bubbles for readability.
    @app.post("/chat")
    async def chat(req: ChatRequest, db: Database = Depends(get_db)):
        msg = req.msg
        session_id = req.session_id
        user_id = req.user_id
        preset = req.preset
        is_bot_gen_req = msg is None or msg == ""

        # Get user study logger
        study_logger = get_user_study_logger()

        await db.ensure_user(user_id)
        await db.ensure_session(session_id, user_id)

        # Log session start for new sessions
        if study_logger:
            hist = await db.get_messages(session_id)
            if not hist:  # New session
                study_logger.log_session_start(user_id, session_id)

            # Log user message
            if is_bot_gen_req:
                study_logger.log_session_event(user_id, session_id, f"Preset: {preset}")
            else:
                study_logger.log_user_message(user_id, session_id, msg or "")

        hist = await db.get_messages(session_id)

        # Create proper dependencies for the agent
        # TODO: Preset should be set once then persisted in the database, rather than
        # letting the frontend change it every time.
        deps = ChatDeps(
            db=db,
            user_id=user_id,
            session_id=session_id,
            preset=preset,
            is_first_message=is_bot_gen_req,
        )

        with capture_run_messages() as dbg_msgs:
            try:
                async with chat_agent.run_stream(
                    msg, message_history=hist, deps=deps
                ) as result:
                    # NOTE: Evaluating the conversation is done by agent tool call, not here.
                    async def stream_text():
                        # delta=False since history tracking is done in the backend, and True
                        # breaks pydantic_ai's history tracking (and they wontfix it).
                        full_response = ""
                        async for update in result.stream_text(delta=False):
                            full_response = update  # Keep the latest full response
                            yield update

                        # Log assistant response
                        if study_logger and full_response:
                            study_logger.log_assistant_message(
                                user_id, session_id, full_response
                            )

                        # Once done, save new messages to the database.
                        await db.add_messages(session_id, result.new_messages())

                    return StreamingResponse(stream_text(), media_type="text/plain")
            except Exception as e:
                log.error(f"Messages: {dbg_msgs}", exc_info=e)
                if study_logger:
                    study_logger.log_error(user_id, session_id, f"Chat error: {str(e)}")
                raise

    @app.get("/chat/{session_id}")
    async def get_chat_history(
        session_id: str,
        db: Database = Depends(get_db),
    ) -> List[ConversationMessage]:
        """Get chat history for a session."""
        try:
            messages = await db.get_messages(session_id)
            return convert_model_messages_to_conversation(messages)
        except Exception as e:
            log.error(
                f"Error retrieving chat history for {session_id}: {e}", exc_info=e
            )
            raise HTTPException(500, detail="Failed to retrieve chat history")

    @app.get("/skills/{user_id}/summary")
    async def get_skill_progress(user_id: str, db: Database = Depends(get_db)):
        """Get skill development progress for a user."""
        try:
            deps = ChatDeps(db=db, user_id=user_id, session_id="", preset="")
            progress = await get_user_skill_summary(deps)
            return progress
        except Exception as e:
            log.error(f"Error retrieving skill progress for {user_id}: {e}", exc_info=e)
            raise HTTPException(500, detail="Failed to retrieve skill progress")

    @app.get("/skills/{user_id}/history")
    async def get_skill_history(
        user_id: str,
        skill_type: Optional[str] = None,
        session_id: Optional[str] = None,
        db: Database = Depends(get_db),
    ):
        """Get skill evaluation history for a user."""
        try:
            # Get all skill evaluations for the user (optionally filtered by session)
            skill_history = await db.get_skill_history(user_id, session_id)

            # Filter by skill_type if specified
            if skill_type:
                skill_history = [
                    evaluation
                    for evaluation in skill_history
                    if evaluation.skill_type == skill_type
                ]

            # Return flat list of evaluations
            return {
                "user_id": user_id,
                "skill_type": skill_type,
                "session_id": session_id,
                "evaluations": [
                    {
                        "skill_type": evaluation.skill_type,
                        "score": evaluation.score,
                        "reason": evaluation.reason,
                        "confidence": evaluation.confidence,
                        "timestamp": evaluation.timestamp.isoformat()
                        if evaluation.timestamp
                        else None,
                    }
                    for evaluation in skill_history
                    if evaluation.skill_type is not None
                ],
            }
        except Exception as e:
            log.error(f"Error retrieving skill history for {user_id}: {e}", exc_info=e)
            raise HTTPException(
                status_code=500, detail="Failed to retrieve skill history"
            )

    return app
