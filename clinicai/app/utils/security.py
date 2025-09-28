"""Security utilities for phone number hashing and data protection."""

import hashlib
import logging
import re
from typing import Pattern

from ..config import settings

logger = logging.getLogger(__name__)


def hash_phone_number(phone: str) -> str:
    """
    Hash a phone number using SHA-256 with salt for privacy protection.
    
    Args:
        phone: Phone number to hash (e.g., "5551999999999")
        
    Returns:
        SHA-256 hash as hexadecimal string
    """
    # Normalize phone number (remove non-digits)
    normalized_phone = re.sub(r"\D", "", phone)
    
    # Create hash with salt
    salted_phone = settings.phone_hash_salt + normalized_phone
    phone_hash = hashlib.sha256(salted_phone.encode("utf-8")).hexdigest()
    
    logger.debug(f"Phone number hashed successfully")
    return phone_hash


def sanitize_log_data(data: str) -> str:
    """
    Sanitize data for logging by removing sensitive information.
    
    Args:
        data: String data to sanitize
        
    Returns:
        Sanitized string safe for logging
    """
    # Phone number patterns
    phone_patterns = [
        r"\b\d{10,15}\b",  # Simple phone number
        r"\+\d{1,3}[\s\-]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,9}",  # International
        r"\(\d{1,3}\)[\s\-]?\d{1,4}[\s\-]?\d{1,9}",  # With area code
    ]
    
    # Token patterns
    token_patterns = [
        r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*",  # Bearer tokens
        r"access_token[\"\':\s]*[A-Za-z0-9\-\._~\+\/]+=*",  # Access tokens
        r"api_key[\"\':\s]*[A-Za-z0-9\-\._~\+\/]+=*",  # API keys
    ]
    
    sanitized = data
    
    # Replace phone numbers
    for pattern in phone_patterns:
        sanitized = re.sub(pattern, "[PHONE_REDACTED]", sanitized, flags=re.IGNORECASE)
    
    # Replace tokens
    for pattern in token_patterns:
        sanitized = re.sub(pattern, "[TOKEN_REDACTED]", sanitized, flags=re.IGNORECASE)
    
    return sanitized


def extract_phone_from_whatsapp(whatsapp_phone: str) -> str:
    """
    Extract clean phone number from WhatsApp format.
    
    Args:
        whatsapp_phone: Phone number from WhatsApp (may include country code)
        
    Returns:
        Normalized phone number
    """
    # Remove all non-digit characters
    phone = re.sub(r"\D", "", whatsapp_phone)
    
    # Remove leading zeros
    phone = phone.lstrip("0")
    
    # Ensure it starts with country code (Brazil = 55)
    if len(phone) >= 10 and not phone.startswith("55"):
        phone = "55" + phone
    
    logger.debug(f"Phone extracted and normalized")
    return phone


# Compiled regex patterns for performance
MEDICAL_DIAGNOSIS_PATTERNS: list[Pattern[str]] = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\b(diagnóstico|diagnostico)\b",
        r"\b(doença|doenca)\b",
        r"\b(síndrome|sindrome)\b", 
        r"\b(patologia)\b",
        r"\b(enfermidade)\b",
        r"\b(infecção|infeccao)\b",
        r"\b(tumor|câncer|cancer)\b",
        r"\b(diabetes|hipertensão|hipertensao)\b",
        r"\bvocê\s+(tem|possui|sofre)\s+de\b",
        r"\bparece\s+ser\b",
        r"\bpode\s+ser\b",
        r"\bprovavelmente\s+(é|e)\b",
    ]
]

MEDICAL_TREATMENT_PATTERNS: list[Pattern[str]] = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\b(tome|tomar|use|usar)\s+\w+\s*(mg|ml|comprimido|cápsula|capsula)\b",
        r"\b(medicamento|remédio|remedio|droga)\b",
        r"\b(posologia|dosagem)\b",
        r"\b(antibiótico|antibiotico|analgésico|analgesico)\b",
        r"\b(prescrevo|recomendo|sugiro)\b",
        r"\b(tratamento|terapia)\b",
        r"\bmg\s*(por\s+dia|diário|diario)\b",
        r"\b\d+\s*(vez|vezes)\s+(ao\s+dia|por\s+dia)\b",
    ]
]


def contains_medical_advice(text: str) -> tuple[bool, str]:
    """
    Check if text contains medical diagnosis or treatment advice.
    
    Args:
        text: Text to analyze
        
    Returns:
        Tuple of (contains_advice, reason)
    """
    # Check for diagnosis patterns
    for pattern in MEDICAL_DIAGNOSIS_PATTERNS:
        if pattern.search(text):
            return True, "Contains potential medical diagnosis"
    
    # Check for treatment patterns
    for pattern in MEDICAL_TREATMENT_PATTERNS:
        if pattern.search(text):
            return True, "Contains potential medical treatment advice"
    
    return False, ""


def sanitize_llm_output(text: str) -> str:
    """
    Sanitize LLM output to remove potential medical advice.
    
    Args:
        text: LLM generated text
        
    Returns:
        Sanitized text
    """
    contains_advice, reason = contains_medical_advice(text)
    
    if contains_advice:
        logger.warning(f"LLM output blocked: {reason}")
        return (
            "Desculpe, não posso fornecer informações diagnósticas ou terapêuticas. "
            "Por favor, procure orientação médica profissional."
        )
    
    return text
