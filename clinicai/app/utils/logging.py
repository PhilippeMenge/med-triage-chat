"""Logging configuration and utilities for ClinicAI."""

import logging
import sys
from datetime import datetime
from typing import Any, Dict

from ..config import settings
from .security import sanitize_log_data


class SanitizedFormatter(logging.Formatter):
    """Custom log formatter that sanitizes sensitive information."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with sanitization."""
        # Create a copy to avoid modifying the original record
        record_copy = logging.makeLogRecord(record.__dict__)
        
        # Sanitize the message
        if hasattr(record_copy, 'msg') and record_copy.msg:
            record_copy.msg = sanitize_log_data(str(record_copy.msg))
        
        # Sanitize any args
        if hasattr(record_copy, 'args') and record_copy.args:
            sanitized_args = []
            for arg in record_copy.args:
                if isinstance(arg, str):
                    sanitized_args.append(sanitize_log_data(arg))
                else:
                    sanitized_args.append(arg)
            record_copy.args = tuple(sanitized_args)
        
        return super().format(record_copy)


def setup_logging() -> None:
    """Configure application logging."""
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Create sanitized formatter
    formatter = SanitizedFormatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # Create application logger
    app_logger = logging.getLogger("clinicai")
    app_logger.info("Logging configured successfully")


def log_user_interaction(
    phone_hash: str,
    direction: str,
    message: str,
    metadata: Dict[str, Any] = None
) -> None:
    """
    Log user interaction with sanitization.
    
    Args:
        phone_hash: Hashed phone number
        direction: 'in' or 'out'
        message: Message content
        metadata: Additional metadata
    """
    logger = logging.getLogger("clinicai.interaction")
    
    log_data = {
        "phone_hash": phone_hash[:8] + "...",  # Partial hash for debugging
        "direction": direction,
        "message_length": len(message),
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if metadata:
        # Sanitize metadata
        safe_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                safe_metadata[key] = sanitize_log_data(value)
            else:
                safe_metadata[key] = value
        log_data["metadata"] = safe_metadata
    
    logger.info(f"User interaction: {log_data}")


def log_llm_interaction(
    prompt_type: str,
    input_length: int,
    output_length: int,
    processing_time: float,
    success: bool = True,
    error: str = None
) -> None:
    """
    Log LLM interaction for monitoring.
    
    Args:
        prompt_type: Type of prompt (extract_slots, next_prompt)
        input_length: Length of input text
        output_length: Length of output text
        processing_time: Time taken in seconds
        success: Whether the interaction was successful
        error: Error message if any
    """
    logger = logging.getLogger("clinicai.llm")
    
    log_data = {
        "prompt_type": prompt_type,
        "input_length": input_length,
        "output_length": output_length,
        "processing_time_seconds": round(processing_time, 3),
        "success": success,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if error:
        log_data["error"] = sanitize_log_data(error)
    
    level = logging.INFO if success else logging.ERROR
    logger.log(level, f"LLM interaction: {log_data}")


def log_emergency_detection(
    phone_hash: str,
    message: str,
    detection_method: str,
    keywords_found: list[str] = None
) -> None:
    """
    Log emergency detection for monitoring and audit.
    
    Args:
        phone_hash: Hashed phone number
        message: Original message (will be sanitized)
        detection_method: How emergency was detected
        keywords_found: Emergency keywords that triggered detection
    """
    logger = logging.getLogger("clinicai.emergency")
    
    log_data = {
        "phone_hash": phone_hash[:8] + "...",
        "message_length": len(message),
        "detection_method": detection_method,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if keywords_found:
        log_data["keywords_found"] = keywords_found
    
    logger.warning(f"EMERGENCY DETECTED: {log_data}")


def log_triage_completion(
    phone_hash: str,
    slots_filled: int,
    total_slots: int,
    conversation_length: int,
    completion_time_minutes: float
) -> None:
    """
    Log triage completion for analytics.
    
    Args:
        phone_hash: Hashed phone number
        slots_filled: Number of slots filled
        total_slots: Total number of slots
        conversation_length: Number of messages exchanged
        completion_time_minutes: Time taken to complete
    """
    logger = logging.getLogger("clinicai.triage")
    
    log_data = {
        "phone_hash": phone_hash[:8] + "...",
        "slots_filled": slots_filled,
        "total_slots": total_slots,
        "completion_rate": round(slots_filled / total_slots * 100, 1),
        "conversation_length": conversation_length,
        "completion_time_minutes": round(completion_time_minutes, 1),
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    logger.info(f"Triage completed: {log_data}")


def log_whatsapp_error(
    error_type: str,
    error_message: str,
    phone_number: str = None,
    response_status: int = None
) -> None:
    """
    Log WhatsApp API errors.
    
    Args:
        error_type: Type of error (send_failed, webhook_error, etc.)
        error_message: Error message
        phone_number: Phone number (will be hashed)
        response_status: HTTP response status code
    """
    logger = logging.getLogger("clinicai.whatsapp")
    
    log_data = {
        "error_type": error_type,
        "error_message": sanitize_log_data(error_message),
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if phone_number:
        from .security import hash_phone_number
        log_data["phone_hash"] = hash_phone_number(phone_number)[:8] + "..."
    
    if response_status:
        log_data["response_status"] = response_status
    
    logger.error(f"WhatsApp error: {log_data}")

