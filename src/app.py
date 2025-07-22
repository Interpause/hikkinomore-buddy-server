"""Main app."""

from dotenv import load_dotenv

load_dotenv()

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic_ai import capture_run_messages

from src.agents.chat import create_chat_agent
from src.db import Database
from src.skills import get_user_skill_summary
from src.structs import ChatDeps, ChatRequest

__all__ = ["create_app"]
log = logging.getLogger(__name__)


def create_app():
    """App factory.

    Creating the app within a function prevents mishaps if using multiprocessing.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Put only heavy loading or cleanup tasks here."""
        async with Database.connect("db.sqlite") as db:
            yield dict(db=db)
        # cleanup tasks

    app = FastAPI(lifespan=lifespan)

    chat_agent = create_chat_agent()

    async def get_db(request: Request) -> Database:
        return request.state.db

    @app.post("/chat")
    async def chat(req: ChatRequest, db: Database = Depends(get_db)):
        msg = req.msg
        session_id = req.session_id
        user_id = req.user_id

        await db.ensure_user(user_id)
        await db.ensure_session(session_id, user_id)
        hist = await db.get_messages(session_id)

        # Create proper dependencies for the agent
        deps = ChatDeps(db=db, user_id=user_id, session_id=session_id)

        with capture_run_messages() as dbg_msgs:
            try:
                async with chat_agent.run_stream(
                    msg, message_history=hist, deps=deps
                ) as result:
                    # NOTE: Evaluating the conversation is done by agent tool call, not here.
                    async def stream_text():
                        # delta=False since history tracking is done in the backend, and True
                        # breaks pydantic_ai's history tracking (and they wontfix it).
                        async for update in result.stream_text(delta=False):
                            yield update

                        # Once done, save new messages to the database.
                        await db.add_messages(session_id, result.new_messages())

                    return StreamingResponse(stream_text(), media_type="text/plain")
            except Exception as e:
                log.error(f"Messages: {dbg_msgs}", exc_info=e)

    @app.get("/skills/{user_id}/summary")
    async def get_skill_progress(user_id: str, db: Database = Depends(get_db)):
        """Get skill development progress for a user."""
        try:
            deps = ChatDeps(db=db, user_id=user_id, session_id="")
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
