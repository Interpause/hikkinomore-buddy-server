"""Data structures."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    msg: str
    session_id: str
    user_id: str
