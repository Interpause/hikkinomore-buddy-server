---
applyTo: '**'
---
# Copilot Instructions for hikkinomore-buddy-server

Welcome! This document helps AI coding agents navigate the `hikkinomore-buddy` codebase effectively.

## Project Overview

- **API Server**: FastAPI app defined in `src/app.py`. Exposes a `/chat` endpoint that streams LLM responses.
- **Chat Agent**: Configured via `pydantic_ai.Agent` in `create_chat_agent()` (model: `groq:meta-llama/...`). Located in `src/app.py`.
- **History Storage**: SQLite backend (`db.sqlite`) managed by `src/db.py` using `aiosqlite`. Stores sessions and chunked messages.
- **Frontend**: `chat.py` provides a Gradio UI for local testing. It extracts `session_id` from assistant messages and calls the `/chat` endpoint.
- **Dev Entrypoint**: `dev.py` sets up rich logging and runs Uvicorn with reload on port 3000.
- **Docker**: Root `Dockerfile` builds a container that runs the FastAPI app in production.

## Key Workflows

- **Local Development**: 
  ```bash
  poe dev       # Starts the debug server (calls python dev.py)
  poe chat      # Launches Gradio UI locally (calls python chat.py)
  ```
  Uses Poetry-managed virtual environment.

- **Docker Build & Run**:
  ```bash
  poe build 0.1.0     # Builds image tagged latest and 0.1.0
  poe prod            # Runs latest image locally on port 3000
  ```

- **Testing & Linting**:
  ```bash
  poe test            # Placeholder (not yet implemented)
  poe requirements    # Exports dependencies to requirements.txt
  ruff                # Runs linting (configured in pyproject.toml)
  ```

- **Debugging in VSCode**: Press F5 or run the `Python: Dev` task. Launches `dev.py` with rich tracebacks enabled.

## Project Conventions

- **Session IDs**: Managed by backend (`db.ensure_session`) but surfaced in the assistant’s last output as `<!-- session_id: {id} -->` for frontend extraction.
- **Streaming**: Uses `chat_agent.run_stream(msg, message_history=hist)` → `StreamingResponse(stream_text(), media_type="text/plain")` in `src/app.py`.
- **History Chunks**: Messages are stored/retrieved in JSON chunks via `ModelMessagesTypeAdapter` in `src/db.py`.
- **Environment**: `.env` files are loaded with `python-dotenv` in `src/app.py`. Database path is hard-coded to `db.sqlite` by default.

## Integration Points

- **LLM Model**: Specified by the `Agent` constructor. Change in `src/app.py#create_chat_agent()`.
- **Database Schema**: Defined inline in `Database.connect()`. To evolve, edit SQL DDL in `src/db.py`.
- **Frontend-Backend Contract**: JSON `{ msg: string, session_id: string }` ↔ streaming text payload tagged with session IDs.
- **Dependencies**: Declared in `pyproject.toml` under `[tool.poetry.dependencies]`. Key packages: `fastapi-slim`, `pydantic-ai-slim[groq]`, `aiosqlite`, `gradio`.

## Common Edit Targets

- Update system prompts in `create_chat_agent()`.
- Adjust DB path or schema in `src/db.py` and `Database.connect()`.
- Modify Gradio UI settings in `chat.py` (e.g., title, history behavior).
- Alter Uvicorn settings in `dev.py` if port or logging needs change.

## PydanticAI Model References

- Before updating or selecting models in `create_chat_agent()`, AI agents should consult `llms.txt` at https://ai.pydantic.dev/llms.txt for the full list of supported models and their capabilities.
- For provider-specific details and usage patterns, reference the PydanticAI models docs under https://ai.pydantic.dev/models/ (e.g., `/models/groq` for Groq models).

## Notes on Editing

- **Bite-sized Changes**: Focus on small, incremental edits. Ignore TODOs or comments unless they directly relate to your task or you are explicitly asked to address them.
- **Focused Edits**: If you need to make changes, ensure they are relevant to the current task. Avoid minor edits or broad
refactoring but do search for affected functions or classes and update them as needed to maintain functionality.
- **Context Awareness**: Understand the context of your changes. If unsure, ask for clarification before proceeding.
