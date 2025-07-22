"""User study logging for psychological analysis of conversations."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.structs import SkillJudgementFull


class UserStudyLogger:
    """Logger for user study conversations focused on psychological analysis."""

    def __init__(self, base_dir: str = "data"):
        """Initialize the user study logger.

        Args:
            base_dir: Base directory for storing user logs
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self._loggers = {}  # Cache for session loggers

    def _get_session_logger(self, user_id: str, session_id: str) -> logging.Logger:
        """Get or create a logger for a specific session.

        Args:
            user_id: The user ID
            session_id: The session ID

        Returns:
            Logger instance for the session
        """
        logger_key = f"{user_id}_{session_id}"

        if logger_key in self._loggers:
            return self._loggers[logger_key]

        # Create user directory
        user_dir = self.base_dir / "users" / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        # Create session log file
        log_file = user_dir / f"{session_id}.log"

        # Create logger
        logger = logging.getLogger(f"user_study.{logger_key}")
        logger.setLevel(logging.INFO)

        # Remove any existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Create file handler
        handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")

        # Create human-readable formatter
        formatter = logging.Formatter(
            "[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.propagate = False  # Don't propagate to root logger

        self._loggers[logger_key] = logger
        return logger

    def log_session_start(self, user_id: str, session_id: str):
        """Log the start of a conversation session."""
        logger = self._get_session_logger(user_id, session_id)
        logger.info(f"=== SESSION START ===")
        logger.info(f"User ID: {user_id}")
        logger.info(f"Session ID: {session_id}")
        logger.info("")

    def log_user_message(self, user_id: str, session_id: str, message: str):
        """Log a user message."""
        logger = self._get_session_logger(user_id, session_id)
        # Clean up the message for readability
        clean_message = message.strip().replace("\n", " [NEWLINE] ")
        logger.info(f"USER: {clean_message}")

    def log_assistant_message(self, user_id: str, session_id: str, message: str):
        """Log an assistant message."""
        logger = self._get_session_logger(user_id, session_id)
        # Clean up the message and remove session_id comments
        clean_message = message.strip()
        # Remove session_id comment from the end
        if "<!-- session_id:" in clean_message:
            clean_message = clean_message.split("<!-- session_id:")[0].strip()
        clean_message = clean_message.replace("\n", " [NEWLINE] ")
        logger.info(f"ASSISTANT: {clean_message}")

    def log_tool_call(self, user_id: str, session_id: str, tool_name: str, **kwargs):
        """Log when a tool is called by the agent."""
        logger = self._get_session_logger(user_id, session_id)
        args_str = ", ".join([f"{k}={v}" for k, v in kwargs.items() if v is not None])
        logger.info(f"TOOL CALL: {tool_name}({args_str})")

    def log_skill_judgement(
        self, user_id: str, session_id: str, judgement: SkillJudgementFull
    ):
        """Log when a skill judgement is made and saved."""
        logger = self._get_session_logger(user_id, session_id)
        logger.info(f"SKILL JUDGEMENT:")
        logger.info(f"  Skill Type: {judgement.skill_type or 'None'}")
        logger.info(f"  Score: {judgement.score}")
        logger.info(f"  Confidence: {judgement.confidence}")
        logger.info(f"  Reason: {judgement.reason}")
        logger.info("")

    def log_error(self, user_id: str, session_id: str, error_msg: str):
        """Log an error that occurred during the conversation."""
        logger = self._get_session_logger(user_id, session_id)
        logger.info(f"ERROR: {error_msg}")

    def log_session_event(self, user_id: str, session_id: str, event: str):
        """Log a general session event."""
        logger = self._get_session_logger(user_id, session_id)
        logger.info(f"EVENT: {event}")


# Global logger instance
_user_study_logger: Optional[UserStudyLogger] = None


def get_user_study_logger() -> Optional[UserStudyLogger]:
    """Get the global user study logger instance."""
    return _user_study_logger


def init_user_study_logger(
    enabled: bool = True, base_dir: str = "data"
) -> Optional[UserStudyLogger]:
    """Initialize the user study logger.

    Args:
        enabled: Whether to enable logging
        base_dir: Base directory for logs

    Returns:
        Logger instance if enabled, None otherwise
    """
    global _user_study_logger

    if enabled:
        _user_study_logger = UserStudyLogger(base_dir)
    else:
        _user_study_logger = None

    return _user_study_logger
