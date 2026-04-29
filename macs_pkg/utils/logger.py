"""Logging utilities for MACS."""

from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger
import sys


class MACSLogger:
    """Logger for MACS with structured logging capabilities."""

    def __init__(
        self,
        name: str = "macs",
        level: str = "INFO",
        format_string: Optional[str] = None,
    ):
        self.name = name
        self._setup_logger(level, format_string)

    def _setup_logger(self, level: str, format_string: Optional[str]) -> None:
        """Setup logger with custom format."""
        # Remove default handler
        logger.remove()

        # Default format
        if format_string is None:
            format_string = (
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            )

        # Add console handler
        logger.add(
            sys.stderr,
            format=format_string,
            level=level,
            colorize=True,
        )

    def add_file_handler(
        self,
        file_path: str,
        level: str = "DEBUG",
        rotation: str = "10 MB",
        retention: str = "7 days",
    ) -> None:
        """Add a file handler for logging.

        Args:
            file_path: Path to log file.
            level: Log level.
            rotation: When to rotate the log file.
            retention: How long to keep log files.
        """
        logger.add(
            file_path,
            level=level,
            rotation=rotation,
            retention=retention,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        )

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        logger.debug(f"{message} | {kwargs}")

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        logger.info(f"{message} | {kwargs}")

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        logger.warning(f"{message} | {kwargs}")

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        logger.error(f"{message} | {kwargs}")

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        logger.critical(f"{message} | {kwargs}")


class CollaborationLogger:
    """Logger specifically for collaboration events."""

    def __init__(self, logger: MACSLogger):
        self.logger = logger

    def log_agent_action(
        self,
        agent_name: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an agent action.

        Args:
            agent_name: Name of the agent.
            action: Action performed.
            details: Additional details.
        """
        self.logger.info(
            f"Agent action: {agent_name} - {action}",
            agent=agent_name,
            action=action,
            details=details or {},
        )

    def log_message_sent(
        self,
        sender: str,
        receiver: str,
        message_type: str,
        message_id: str,
    ) -> None:
        """Log a message being sent between agents.

        Args:
            sender: Sender agent name.
            receiver: Receiver agent name.
            message_type: Type of message.
            message_id: Message ID.
        """
        self.logger.debug(
            f"Message sent: {sender} -> {receiver}",
            sender=sender,
            receiver=receiver,
            msg_type=message_type,
            msg_id=message_id,
        )

    def log_mode_selection(
        self,
        mode: str,
        reason: Optional[str] = None,
    ) -> None:
        """Log collaboration mode selection.

        Args:
            mode: Selected mode name.
            reason: Reason for selection.
        """
        self.logger.info(
            f"Mode selected: {mode}",
            mode=mode,
            reason=reason,
        )

    def log_task_start(self, task_id: str, task_type: str) -> None:
        """Log task start.

        Args:
            task_id: Task identifier.
            task_type: Type of task.
        """
        self.logger.info(
            f"Task started: {task_id}",
            task_id=task_id,
            task_type=task_type,
        )

    def log_task_complete(
        self,
        task_id: str,
        duration: float,
        result_summary: Optional[str] = None,
    ) -> None:
        """Log task completion.

        Args:
            task_id: Task identifier.
            duration: Execution duration in seconds.
            result_summary: Brief summary of result.
        """
        self.logger.info(
            f"Task completed: {task_id} (took {duration:.2f}s)",
            task_id=task_id,
            duration=duration,
            result=result_summary,
        )

    def log_task_failure(
        self,
        task_id: str,
        error: str,
        traceback: Optional[str] = None,
    ) -> None:
        """Log task failure.

        Args:
            task_id: Task identifier.
            error: Error message.
            traceback: Error traceback.
        """
        self.logger.error(
            f"Task failed: {task_id} - {error}",
            task_id=task_id,
            error=error,
            traceback=traceback,
        )


# Global logger instance
_macs_logger: Optional[MACSLogger] = None


def get_logger(name: str = "macs", level: str = "INFO") -> MACSLogger:
    """Get or create the global MACS logger.

    Args:
        name: Logger name.
        level: Log level.

    Returns:
        MACSLogger instance.
    """
    global _macs_logger
    if _macs_logger is None:
        _macs_logger = MACSLogger(name, level)
    return _macs_logger


def get_collaboration_logger() -> CollaborationLogger:
    """Get a collaboration logger.

    Returns:
        CollaborationLogger instance.
    """
    return CollaborationLogger(get_logger())
