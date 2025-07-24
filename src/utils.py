"""Utility functions for the hikkinomore-buddy-server."""

import logging
from typing import List, Optional

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse

from src.structs import ConversationMessage

log = logging.getLogger(__name__)


def convert_model_messages_to_conversation(
    message_history: List[ModelMessage],
    recent_messages: Optional[int] = None,
    skip_system_messages: bool = True,
    skip_tool_messages: bool = True,
) -> List[ConversationMessage]:
    """Convert PydanticAI ModelMessage objects to ConversationMessage objects.

    Args:
        message_history: List of PydanticAI ModelMessage objects
        recent_messages: If specified, only process the last N messages
        skip_system_messages: Whether to skip system prompt parts (default: True)
        skip_tool_messages: Whether to skip tool-related messages (default: True)

    Returns:
        List of ConversationMessage objects suitable for skill evaluation
    """
    conversation_messages = []

    # Take the last N messages for evaluation if specified
    if recent_messages is not None:
        messages_to_process = (
            message_history[-recent_messages:]
            if len(message_history) >= recent_messages
            else message_history
        )
    else:
        messages_to_process = message_history

    for msg in messages_to_process:
        if not hasattr(msg, "parts") or not msg.parts:
            continue

        # Determine the role based on the message type
        if isinstance(msg, ModelRequest):
            # This is a message from the user to the model
            role = "user"  # Default for request messages
        elif isinstance(msg, ModelResponse):
            # This is a message from the model to the user
            role = "assistant"
        else:
            # Fallback - shouldn't happen with current PydanticAI structure
            log.warning(f"Unknown message type: {type(msg)}")
            continue

        for part in msg.parts:
            content = None
            part_role = role  # Start with the message-level role

            # Extract content based on part type using part_kind discriminator
            part_kind = getattr(part, "part_kind", None)

            if part_kind == "system-prompt":
                if skip_system_messages:
                    continue
                part_role = "system"
                content = getattr(part, "content", None)

            elif part_kind == "user-prompt":
                part_role = "user"
                raw_content = getattr(part, "content", None)

                # Handle both string and sequence content
                if isinstance(raw_content, str):
                    content = raw_content
                else:
                    # For multimodal content, extract text parts only
                    # This is a sequence of UserContent items
                    text_parts = []
                    if raw_content and hasattr(raw_content, "__iter__"):
                        for content_item in raw_content:
                            if isinstance(content_item, str):
                                text_parts.append(content_item)
                            # Note: We're skipping binary content, URLs, etc. for now
                            # as they're not relevant for text-based skill evaluation
                    content = " ".join(text_parts) if text_parts else None

            elif part_kind == "text":
                # This is a text response from the model
                part_role = "assistant"
                content = getattr(part, "content", None)

            elif part_kind == "thinking":
                # Thinking parts are internal model reasoning - skip for skill evaluation
                continue

            elif part_kind in ("tool-call", "tool-return", "retry-prompt"):
                # TODO: lol this is skipped either ways, maybe we can return a special message type
                # that is used to display what tools were called
                if skip_tool_messages:
                    continue
                # For tool messages, we could extract the content if needed
                # but for skill evaluation, we typically skip these
                continue

            else:
                log.debug(f"Unhandled part kind: {part_kind}")
                continue

            # Only add messages with actual content
            if content and content.strip():
                conversation_messages.append(
                    ConversationMessage(
                        role=part_role,
                        content=content,
                        timestamp=getattr(part, "timestamp", None),
                    )
                )

    return conversation_messages


def format_conversation(messages: List[ConversationMessage]) -> str:
    """Format conversation messages for analysis.

    Args:
        messages: List of conversation messages to format

    Returns:
        Formatted conversation text
    """
    formatted = []
    for msg in messages:
        timestamp_str = ""
        if msg.timestamp:
            timestamp_str = f" [{msg.timestamp.strftime('%H:%M:%S')}]"
        formatted.append(f"{msg.role.upper()}{timestamp_str}: {msg.content}")

    return "\n".join(formatted)
