"""Main app."""

from dotenv import load_dotenv

from src.db import Database

load_dotenv()

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic_ai import Agent

from src.structs import ChatRequest

__all__ = ["create_app"]
log = logging.getLogger(__name__)


# I think youre supposed to create multiple agents, constrain their output type
# and have them work with each other.
def create_chat_agent():
    """Create front-facing chat agent."""
    agent = Agent(
        "groq:meta-llama/llama-4-scout-17b-16e-instruct",
        system_prompt=f"""\
Your name is Buddy.\
""",
    )

    return agent


# NOTE: Proposed structure:
# To simplify the microservice, convo history is sent with each request. This means
# the convo can be locally stored in frontend, or frontend retrieves it from some
# other database service, but essentially its not the concern of this service.

# That said, pydantic_ai's history tracking contains much more info, which is lost
# when receiving only the front-facing convo history. For hikkinomore it should
# be fine, but if I was building smth much more reliant on past tool calls, then
# either I am sending pydantic_ai's history to the frontend, or the tracking has
# to happen here instead.
#
# Ignore the above, I was forced by it being difficult to convert the frontend history
# to pydantic_ai's history format, so I am storing the history in the backend. The
# frontend still keeps its own copy but it is not synced with the backend.


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

        await db.ensure_session(session_id)
        hist = await db.get_messages(session_id)
        async with chat_agent.run_stream(msg, message_history=hist) as result:

            async def stream_text():
                # delta=False since history tracking is done in the backend, and True
                # breaks pydantic_ai's history tracking (and they wontfix it).
                async for update in result.stream_text(delta=False):
                    yield update

                # Once done, save new messages to the database.
                await db.add_messages(session_id, result.new_messages())

            return StreamingResponse(stream_text(), media_type="text/plain")

    return app
