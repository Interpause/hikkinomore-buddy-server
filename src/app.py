"""Main app."""

from dotenv import load_dotenv
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

import logging

from fastapi import FastAPI
from pydantic_ai import Agent

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


class ChatRequest(BaseModel):
    msg: str


def create_app():
    """App factory.

    Creating the app within a function prevents mishaps if using multiprocessing.
    """
    app = FastAPI()

    chat_agent = create_chat_agent()

    # TODO: idk lol what params to have lololol how to cache msg history anyways
    # especially since if the frontend messages are editable we need to sync and
    # invalidate.
    @app.post("/chat")
    async def chat(req: ChatRequest):
        async with chat_agent.run_stream(req.msg) as res:
            return StreamingResponse(res.stream_text(delta=True))

    return app
