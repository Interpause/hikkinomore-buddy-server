"""Main app."""

from dotenv import load_dotenv
from pydantic_ai import UnexpectedModelBehavior, capture_run_messages

load_dotenv()

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Request
from fastapi.responses import StreamingResponse

from src.agents.chat import create_chat_agent
from src.db import Database
from src.skills import (
    get_user_skill_summary,
)
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

        async with chat_agent.run_stream(
            msg, message_history=hist, deps=deps
        ) as result:
            # NOTE: Evaluating the conversation is done by agent tool call, not here.
            async def stream_text():
                # delta=False since history tracking is done in the backend, and True
                # breaks pydantic_ai's history tracking (and they wontfix it).
                with capture_run_messages() as dbg_msgs:
                    try:
                        async for update in result.stream_text(delta=False):
                            yield update

                        # Once done, save new messages to the database.
                        await db.add_messages(session_id, result.new_messages())

                    except UnexpectedModelBehavior as e:
                        log.error(f"Messages: {dbg_msgs}", exc_info=e)

            return StreamingResponse(stream_text(), media_type="text/plain")

    # TODO: AI GENERATED, EVALUATE BELOW
    @app.get("/skills/{user_id}")
    async def get_skill_progress(user_id: str, db: Database = Depends(get_db)):
        """Get skill development progress for a user."""
        try:
            # For the API endpoint, we don't need session_id for skill progress
            # Create a minimal deps with placeholder session_id.
            deps = ChatDeps(db=db, user_id=user_id, session_id="")
            progress = await get_user_skill_summary(deps)
            return progress
        except Exception as e:
            log.error(f"Error retrieving skill progress for {user_id}: {e}")
            return {"error": "Failed to retrieve skill progress"}

    @app.get("/skills/{user_id}/history")
    async def get_skill_history(
        user_id: str,
        skill_type: Optional[str] = None,
        db: Database = Depends(get_db),
    ):
        """Get skill evaluation history for a user."""
        try:
            if skill_type:
                scores = await db.get_skill_scores(user_id, skill_type)
                return {
                    "skill_type": skill_type,
                    "evaluations": [
                        {"score": score, "timestamp": ts.isoformat()}
                        for score, ts in scores
                    ],
                }
            else:
                all_scores = await db.get_all_skill_scores(user_id)
                result = {}
                for skill, scores in all_scores.items():
                    result[skill] = [
                        {"score": score, "timestamp": ts.isoformat()}
                        for score, ts in scores
                    ]
                return result
        except Exception as e:
            log.error(f"Error retrieving skill history for {user_id}: {e}")
            return {"error": "Failed to retrieve skill history"}

    return app
