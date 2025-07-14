"""Gradio UI to test the API server."""

from typing import List

import gradio as gr
import httpx


async def chat(msg: str, hist: List[gr.MessageDict]):
    """Process the message as necessary."""
    full = ""
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST", "http://localhost:3000/chat", json={"msg": msg}
        ) as res:
            async for chunk in res.aiter_bytes():
                full += chunk.decode()
                yield full


demo = gr.ChatInterface(
    fn=chat,
    type="messages",
    title="Buddy",
    description="_Now with additional **Buddying**!_",
    editable=True,
    save_history=True,
)

# NOTE: gradio chat.py breaks the chat interface after refresh for some reason.
if __name__ == "__main__":
    demo.launch()
