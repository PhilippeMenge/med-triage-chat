"""Emergency detection utilities for medical triage."""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# Emergency keywords that should trigger immediate medical attention
EMERGENCY_KEYWORDS: List[str] = [
    "dor no peito",
    "dor forte no peito",
    "falta de ar",
    "dificuldade para respirar",
    "desmaio",
    "desmaiei",
    "vou desmaiar",
    "inconsciente",
    "sangramento intenso",
    "hemorragia",
    "convulsão",
    "convulsao",
    "torácica intensa",
    "toracica intensa",
    "fraqueza súbita",
    "fraqueza subita",
    "paralisia",
    "confusão súbita",
    "confusao subita",
    "pressão muito baixa",
    "pressao muito baixa",
    "não consigo respirar",
    "nao consigo respirar",
    "peito apertado",
    "dormência no braço",
    "dormencia no braco",
    "visão embaçada súbita",
    "visao embacada subita",
    "vômito com sangue",
    "vomito com sangue",
    "febre muito alta",
    "temperatura muito alta",
    "batimento acelerado",
    "coração acelerado",
    "coracao acelerado",
    "suor frio",
    "tontura intensa",
    "perda de consciência",
    "perda de consciencia",
]

# Synonyms and variations for better detection
EMERGENCY_SYNONYMS: List[str] = [
    "sufocando",
    "sufoco",
    "asfixia",
    "engasgado",
    "engasgo",
    "queimação no peito",
    "queimacao no peito",
    "aperto no peito",
    "formigamento no braço",
    "formigamento no braco",
    "enjoo com dor",
    "náusea intensa",
    "nausea intensa",
    "muito pálido",
    "muito palido",
    "lábios roxos",
    "labios roxos",
    "pele azulada",
    "tremor intenso",
    "calafrio forte",
]

# Compile patterns for better performance
EMERGENCY_PATTERNS = [
    re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
    for keyword in EMERGENCY_KEYWORDS + EMERGENCY_SYNONYMS
]

# Additional pattern-based checks
ADDITIONAL_EMERGENCY_PATTERNS = [
    re.compile(r"\bfebre\s+(acima\s+de\s+)?39", re.IGNORECASE),  # High fever
    re.compile(r"\btemperatura\s+(acima\s+de\s+)?39", re.IGNORECASE),
    re.compile(r"\bdor\s+\d+\s*\/?\s*10", re.IGNORECASE),  # Pain scale 10/10
    re.compile(r"\bdor\s+(nivel\s+)?10", re.IGNORECASE),
    re.compile(r"\bmais\s+de\s+\d+\s+horas?\s+sem\s+respirar\s+bem", re.IGNORECASE),
    re.compile(r"\bperdi\s+a\s+consciência", re.IGNORECASE),
    re.compile(r"\bperdi\s+a\s+consciencia", re.IGNORECASE),
    re.compile(r"\bnão\s+consigo\s+ficar\s+em\s+pé", re.IGNORECASE),
    re.compile(r"\bnao\s+consigo\s+ficar\s+em\s+pe", re.IGNORECASE),
]


def is_emergency(text: str) -> bool:
    """
    Check if the given text contains emergency keywords or patterns.
    
    Args:
        text: User input text to analyze
        
    Returns:
        True if emergency detected, False otherwise
    """
    if not text:
        return False
    
    # Normalize text
    normalized_text = text.lower().strip()
    
    # Check direct keyword matches
    for pattern in EMERGENCY_PATTERNS:
        if pattern.search(normalized_text):
            logger.warning(f"Emergency keyword detected in message")
            return True
    
    # Check additional patterns
    for pattern in ADDITIONAL_EMERGENCY_PATTERNS:
        if pattern.search(normalized_text):
            logger.warning(f"Emergency pattern detected in message")
            return True
    
    return False


def get_emergency_response() -> str:
    """
    Get the standard emergency response message.
    
    Returns:
        Emergency response message for the user
    """
    return (
        "🚨 Entendi. Seus sintomas podem indicar uma situação de emergência. "
        "Por favor, procure o pronto-socorro mais próximo ou ligue 192 imediatamente."
    )


def analyze_emergency_context(text: str) -> dict[str, any]:
    """
    Provide detailed emergency analysis for logging/monitoring.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with analysis details
    """
    analysis = {
        "is_emergency": False,
        "detected_keywords": [],
        "detected_patterns": [],
        "severity_indicators": [],
    }
    
    if not text:
        return analysis
    
    normalized_text = text.lower().strip()
    
    # Check for specific keywords
    for keyword in EMERGENCY_KEYWORDS + EMERGENCY_SYNONYMS:
        if keyword.lower() in normalized_text:
            analysis["detected_keywords"].append(keyword)
    
    # Check patterns
    for i, pattern in enumerate(ADDITIONAL_EMERGENCY_PATTERNS):
        if pattern.search(normalized_text):
            analysis["detected_patterns"].append(f"pattern_{i}")
    
    # Look for severity indicators
    severity_indicators = [
        "muito", "intensa", "forte", "súbita", "subita", 
        "extrema", "insuportável", "insuportavel", "urgente"
    ]
    
    for indicator in severity_indicators:
        if indicator in normalized_text:
            analysis["severity_indicators"].append(indicator)
    
    # Determine if emergency
    analysis["is_emergency"] = (
        len(analysis["detected_keywords"]) > 0 or 
        len(analysis["detected_patterns"]) > 0
    )
    
    if analysis["is_emergency"]:
        logger.warning(f"Emergency analysis: {analysis}")
    
    return analysis


def should_escalate_to_human(text: str, conversation_context: list[str] = None) -> bool:
    """
    Determine if conversation should be escalated to human immediately.
    
    Args:
        text: Current user message
        conversation_context: Previous messages for context
        
    Returns:
        True if should escalate, False otherwise
    """
    # Always escalate for emergencies
    if is_emergency(text):
        return True
    
    # Check conversation context for escalation patterns
    if conversation_context:
        # Look for repeated expressions of urgency
        urgency_words = ["urgente", "rápido", "rapido", "agora", "imediato"]
        urgency_count = sum(
            1 for msg in conversation_context[-3:]  # Last 3 messages
            for word in urgency_words
            if word in msg.lower()
        )
        
        if urgency_count >= 2:
            logger.info("Escalating due to repeated urgency expressions")
            return True
    
    return False
