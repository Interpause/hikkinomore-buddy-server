"""Gradio UI to test the API server."""

import base64
import binascii
import json
import re
from typing import List
from uuid import uuid4

import gradio as gr
import httpx

hack_extract = re.compile(r"<!-- session_info: ([A-Za-z0-9+/=]+) -->")


async def chat(msg: str, hist: List[gr.MessageDict], user_id: str):
    """Process the message as necessary."""
    if user_id == "":
        raise gr.Error("User ID cannot be empty.")
    preset = None
    if msg.startswith("%PRESET%\t"):
        preset = msg.split("\t", 1)[1]
        msg = None  # type: ignore

    # TODO: backend should validate that it allocated the session_id
    # HACK: Iterate backwards till we find a model message and extract the session_info from it.
    session_id = None
    for obj in reversed(hist):
        if obj["role"] != "assistant":
            continue
        if not isinstance(obj["content"], str):
            continue
        last_line = obj["content"].splitlines()[-1]
        match = hack_extract.search(last_line)
        if match is None:
            continue
        try:
            # Decode base64 JSON
            encoded_info = match.group(1)
            decoded_bytes = base64.b64decode(encoded_info)
            session_info = json.loads(decoded_bytes.decode("utf-8"))
            session_id = session_info.get("session_id")
            if preset is not None:
                raise gr.Error("Preset cannot be set in the middle of a conversation.")
            preset = session_info.get("preset")
            break
        except (json.JSONDecodeError, binascii.Error, UnicodeDecodeError):
            continue

    if session_id is None:
        print("No session_id found in history, generating a new one.")
        session_id = uuid4().hex
    print(f"Using session_id: {session_id}, user_id: {user_id}")

    preset = "GENERAL_BOT" if preset is None else preset
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:3000/chat",
            json={
                "msg": msg,
                "session_id": session_id,
                "user_id": user_id,
                "preset": preset,
            },
            timeout=None,
        ) as res:
            async for update in res.aiter_bytes():
                out = update.decode("utf-8")
                # Create session info JSON and encode as base64
                session_info = {"session_id": session_id, "preset": preset}
                session_info_json = json.dumps(session_info)
                session_info_b64 = base64.b64encode(
                    session_info_json.encode("utf-8")
                ).decode("utf-8")
                out += f"\n<!-- session_info: {session_info_b64} -->"
                yield out


# Additional outputs and inputs have to be declared before gr.ChatInterface, which
# will mount them.
user_id_widget = gr.Textbox(label="User ID")

demo = gr.ChatInterface(
    fn=chat,
    type="messages",
    title="Buddy",
    description="_Now with additional **Buddying**!_",
    # NVM storing history in backend so can't edit.
    # editable=True,
    # We can still save smth for frontend, but its not the ground truth.
    save_history=True,
    additional_inputs=[user_id_widget],
    additional_inputs_accordion=gr.Accordion("SET THESE BEFORE CHATTING", open=True),
)

# I'll be iterating quite a bit still, so don't reset the state due to lost secret
# when gradio app is restarted. State might still be lost if code is changed in
# some ways.
demo.saved_conversations.secret = "not-secret"


with demo:
    user_id_store = gr.BrowserState(
        default_value="",
        storage_key="user_id",
        secret="not-secret",
    )
    with gr.Row():
        btn_p1 = gr.Button("Use General")
        btn_p2 = gr.Button("Use Nervy")
        btn_p1.click(
            fn=lambda: "%PRESET%\tGENERAL_BOT",
            inputs=[],
            outputs=[demo.textbox],
        )
        btn_p2.click(
            fn=lambda: "%PRESET%\tNERVY_BOT",
            inputs=[],
            outputs=[demo.textbox],
        )

    with gr.Accordion(label="Skill Judgement", open=False):
        refresh_button = gr.Button("Refresh Skill Summary", variant="secondary")
        skill_summary_display = gr.JSON(label="Skill Progress", value=None)

        async def refresh_skill_summary(user_id: str):
            """Fetch and display the user's skill summary."""
            if not user_id:
                return {"error": "User ID is required"}

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"http://localhost:3000/skills/{user_id}/summary", timeout=10.0
                    )
                    if response.status_code == 200:
                        return response.json()
                    else:
                        return {"error": f"API error: {response.status_code}"}
            except Exception as e:
                return {"error": f"Failed to fetch skill summary: {str(e)}"}

        refresh_button.click(
            refresh_skill_summary,
            inputs=[user_id_widget],
            outputs=[skill_summary_display],
        )

    @gr.on([user_id_widget.change], inputs=[user_id_widget], outputs=[user_id_store])
    def update_user_id(value: str):
        """Update the user_id in the browser state."""
        return value

    @demo.load(inputs=[user_id_store], outputs=[user_id_widget])
    def load_user_id(value: str):
        """Load the user_id from the browser state."""
        return "" if value is None else value


# NOTE: gradio chat.py breaks the chat interface after refresh for some reason.
if __name__ == "__main__":
    demo.launch(share=True)
