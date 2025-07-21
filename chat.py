"""Gradio UI to test the API server."""

import re
from typing import List
from uuid import uuid4

import gradio as gr
import httpx

hack_extract = re.compile(r"<!-- session_id: ([a-z0-9]+) -->")


async def chat(msg: str, hist: List[gr.MessageDict], user_id: str):
    """Process the message as necessary."""
    if user_id == "":
        raise gr.Error("User ID cannot be empty.")

    # TODO: backend should validate that it allocated the session_id
    # HACK: Iterate backwards till we find a model message and extract the session_id from it.
    for obj in reversed(hist):
        if obj["role"] != "assistant":
            continue
        if not isinstance(obj["content"], str):
            continue
        last_line = obj["content"].splitlines()[-1]
        match = hack_extract.search(last_line)
        if match is None:
            continue
        session_id = match.group(1)
        break
    else:
        print("No session_id found in history, generating a new one.")
        session_id = uuid4().hex
    print(f"Using session_id: {session_id}, user_id: {user_id}")

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:3000/chat",
            json={"msg": msg, "session_id": session_id, "user_id": user_id},
        ) as res:
            async for update in res.aiter_bytes():
                out = update.decode("utf-8")
                out += f"\n<!-- session_id: {session_id} -->"
                yield out


user_id = gr.Textbox(label="User ID")

demo = gr.ChatInterface(
    fn=chat,
    type="messages",
    title="Buddy",
    description="_Now with additional **Buddying**!_",
    # NVM storing history in backend so can't edit.
    # editable=True,
    # We can still save smth for frontend, but its not the ground truth.
    save_history=True,
    additional_inputs=[user_id],
)

# NOTE: gradio chat.py breaks the chat interface after refresh for some reason.
if __name__ == "__main__":
    demo.launch()
