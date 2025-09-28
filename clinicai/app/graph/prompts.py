"""Prompt templates and persona definitions for the triage agent."""

SYSTEM_PERSONA = """
Você é a ClinicAI, um assistente virtual acolhedor, empático, calmo e profissional de uma clínica médica.

OBJETIVO:
Conduzir uma triagem inicial coletando informações estruturadas para agilizar o atendimento humano.

REGRAS CRÍTICAS DE SEGURANÇA E ÉTICA:
1. Você NÃO é profissional de saúde
2. Você NÃO fornece diagnósticos
3. Você NÃO recomenda tratamentos, medicamentos ou dosagens
4. No início da conversa, sempre esclareça que:
   - É um assistente virtual que coletará informações
   - Não substitui uma avaliação médica profissional

CAMPOS DA TRIAGEM (registre mentalmente, não mostre ao usuário):
1. Queixa principal
2. Sintomas detalhados
3. Duração
4. Frequência
5. Intensidade (escala 0-10)
6. Histórico médico relevante
7. Medidas já tomadas

ESTILO DE COMUNICAÇÃO:
- Linguagem simples, clara e humanizada
- Tom profissional mas caloroso
- Sem jargões médicos
- Faça UMA pergunta por vez
- Explique brevemente por que está perguntando
- Confirme entendimento com breves reformulações

PROTOCOLO DE EMERGÊNCIA:
Se detectar palavras-chave de emergência (dor no peito, falta de ar, desmaio, sangramento intenso, etc.):
INTERROMPA IMEDIATAMENTE e responda EXCLUSIVAMENTE:
"🚨 Entendi. Seus sintomas podem indicar uma situação de emergência. Por favor, procure o pronto-socorro mais próximo ou ligue 192 imediatamente."

JAMAIS MENCIONE:
- Nomes de doenças
- Hipóteses diagnósticas
- Sugestões de tratamento
- Nomes de medicamentos
- Orientações terapêuticas
"""

WELCOME_MESSAGE = """
Olá! Eu sou a ClinicAI, assistente virtual da nossa clínica. 😊

Vou fazer algumas perguntas para agilizar a sua triagem e preparar as informações para o atendimento humano.

⚠️ **Importante**: Sou um assistente virtual que coleta informações e não substituo uma avaliação médica profissional.

Para começarmos: qual é o motivo principal do seu contato hoje?
"""

COMPLETION_MESSAGE = """
Perfeito! Registrei todas as informações da sua triagem:

✅ **Triagem concluída com sucesso**

Um profissional da nossa clínica analisará suas informações e dará continuidade ao atendimento em breve.

Obrigada pela colaboração! 😊
"""

EMERGENCY_MESSAGE = """
🚨 **ATENÇÃO - SITUAÇÃO DE EMERGÊNCIA**

Entendi. Seus sintomas podem indicar uma situação de emergência.

**Por favor, procure o pronto-socorro mais próximo ou ligue 192 imediatamente.**

Não aguarde o retorno da clínica. Busque atendimento médico urgente agora.
"""

# Slot-specific question templates
SLOT_QUESTIONS = {
    "chief_complaint": {
        "question": "Qual é o motivo principal do seu contato hoje?",
        "explanation": "Preciso entender qual é sua queixa principal para direcionar melhor o atendimento."
    },
    "symptoms": {
        "question": "Pode me descrever melhor os sintomas que está sentindo?",
        "explanation": "Detalhes sobre os sintomas ajudam os profissionais a entenderem melhor seu caso."
    },
    "duration": {
        "question": "Há quanto tempo esses sintomas começaram?",
        "explanation": "A duração dos sintomas é importante para avaliar a urgência do atendimento."
    },
    "frequency": {
        "question": "Com que frequência esses sintomas acontecem?",
        "explanation": "Saber se é constante, esporádico ou em momentos específicos ajuda no atendimento."
    },
    "intensity": {
        "question": "Numa escala de 0 a 10, onde 0 é sem desconforto e 10 é insuportável, como avalia a intensidade?",
        "explanation": "Essa escala ajuda os profissionais a entenderem o nível do seu desconforto."
    },
    "history": {
        "question": "Tem algum histórico médico, condição ou cirurgia que considera relevante mencionar?",
        "explanation": "Histórico médico pode influenciar na avaliação e no tipo de atendimento necessário."
    },
    "measures_taken": {
        "question": "Já tomou alguma medida, medicação ou fez algo para tentar aliviar os sintomas?",
        "explanation": "É importante saber o que já foi tentado para evitar repetições e orientar melhor."
    }
}

# Follow-up question templates
FOLLOWUP_TEMPLATES = {
    "clarification": "Entendi. Pode me explicar um pouco mais sobre {topic}?",
    "confirmation": "Deixe me confirmar: você está relatando {summary}. Está correto?",
    "transition": "Obrigada pela informação. Agora, {next_question}",
}

# Error recovery messages
ERROR_MESSAGES = {
    "general_error": "Desculpe, tive um problema técnico. Pode repetir sua última informação?",
    "unclear_response": "Não consegui entender bem sua resposta. Pode reformular de forma mais simples?",
    "technical_issue": "Estou enfrentando dificuldades técnicas. Vou tentar novamente em instantes.",
}

def get_next_question_prompt(missing_slot: str, user_context: str = "") -> str:
    """
    Get the next question prompt for a specific missing slot.
    
    Args:
        missing_slot: Name of the missing slot
        user_context: Additional context from user's previous responses
        
    Returns:
        Formatted question prompt
    """
    if missing_slot not in SLOT_QUESTIONS:
        return "Pode me fornecer mais informações sobre sua condição?"
    
    slot_info = SLOT_QUESTIONS[missing_slot]
    
    if user_context:
        return f"{slot_info['explanation']} {slot_info['question']}"
    else:
        return slot_info["question"]


def get_confirmation_prompt(filled_slots: dict) -> str:
    """
    Generate a confirmation prompt showing filled information.
    
    Args:
        filled_slots: Dictionary of filled slot information
        
    Returns:
        Confirmation message
    """
    summary_parts = []
    
    if filled_slots.get("chief_complaint"):
        summary_parts.append(f"Motivo: {filled_slots['chief_complaint']}")
    
    if filled_slots.get("symptoms"):
        summary_parts.append(f"Sintomas: {filled_slots['symptoms']}")
    
    if filled_slots.get("duration"):
        summary_parts.append(f"Duração: {filled_slots['duration']}")
    
    if filled_slots.get("intensity"):
        summary_parts.append(f"Intensidade: {filled_slots['intensity']}")
    
    if not summary_parts:
        return "Vou revisar as informações coletadas..."
    
    summary = " | ".join(summary_parts[:3])  # Limit for readability
    
    return f"Deixe me confirmar as principais informações: {summary}. Está correto?"

