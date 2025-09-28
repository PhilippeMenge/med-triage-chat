"""Gemini LLM integration for natural language processing."""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

import google.generativeai as genai

from .config import settings
from .schemas import LLMExtraction, TriageSlots
from .utils.logging import log_llm_interaction
from .utils.security import sanitize_llm_output

logger = logging.getLogger(__name__)


class GeminiLLMClient:
    """Google Gemini LLM client for triage processing."""

    def __init__(self) -> None:
        """Initialize Gemini client."""
        try:
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
            logger.info("Gemini LLM client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise

    async def extract_slots(
        self, 
        user_text: str,
        conversation_history: list[str] = None
    ) -> LLMExtraction:
        """
        Extract structured triage information from user text.
        
        Args:
            user_text: User's input message
            conversation_history: Previous conversation messages for context
            
        Returns:
            Extracted slot information
        """
        start_time = time.time()
        
        try:
            prompt = self._build_extraction_prompt(user_text, conversation_history)
            
            # Generate response
            response = await asyncio.to_thread(
                self.model.generate_content, 
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=1024,
                )
            )
            
            # Parse JSON response
            response_text = response.text.strip()
            
            # Try to extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end <= json_start:
                raise ValueError("No valid JSON found in response")
            
            json_text = response_text[json_start:json_end]
            extracted_data = json.loads(json_text)
            
            # Validate and create extraction object
            extraction = LLMExtraction(**extracted_data)
            
            processing_time = time.time() - start_time
            log_llm_interaction(
                prompt_type="extract_slots",
                input_length=len(user_text),
                output_length=len(response_text),
                processing_time=processing_time,
                success=True
            )
            
            logger.debug(f"Slots extracted successfully in {processing_time:.2f}s")
            return extraction
            
        except json.JSONDecodeError as e:
            processing_time = time.time() - start_time
            logger.error(f"JSON parsing error: {e}")
            
            log_llm_interaction(
                prompt_type="extract_slots",
                input_length=len(user_text),
                output_length=0,
                processing_time=processing_time,
                success=False,
                error=f"JSON parsing error: {e}"
            )
            
            # Return empty extraction on error
            return LLMExtraction()
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error extracting slots: {e}")
            
            log_llm_interaction(
                prompt_type="extract_slots",
                input_length=len(user_text),
                output_length=0,
                processing_time=processing_time,
                success=False,
                error=str(e)
            )
            
            return LLMExtraction()

    async def generate_next_prompt(
        self,
        current_slots: TriageSlots,
        conversation_history: list[str] = None,
        is_first_interaction: bool = False
    ) -> str:
        """
        Generate the next prompt/question for the user.
        
        Args:
            current_slots: Currently filled slots
            conversation_history: Previous messages for context
            is_first_interaction: Whether this is the first interaction
            
        Returns:
            Next prompt/question for the user
        """
        start_time = time.time()
        
        try:
            prompt = self._build_next_prompt_template(
                current_slots, 
                conversation_history, 
                is_first_interaction
            )
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    top_p=0.9,
                    top_k=40,
                    max_output_tokens=512,
                )
            )
            
            generated_text = response.text.strip()
            
            # Sanitize output to ensure no medical advice
            sanitized_text = sanitize_llm_output(generated_text)
            
            processing_time = time.time() - start_time
            log_llm_interaction(
                prompt_type="next_prompt",
                input_length=len(prompt),
                output_length=len(sanitized_text),
                processing_time=processing_time,
                success=True
            )
            
            logger.debug(f"Next prompt generated in {processing_time:.2f}s")
            return sanitized_text
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error generating next prompt: {e}")
            
            log_llm_interaction(
                prompt_type="next_prompt",
                input_length=len(str(current_slots)),
                output_length=0,
                processing_time=processing_time,
                success=False,
                error=str(e)
            )
            
            # Return fallback prompt
            return self._get_fallback_prompt(current_slots)

    def _build_extraction_prompt(
        self, 
        user_text: str, 
        conversation_history: list[str] = None
    ) -> str:
        """Build prompt for slot extraction."""
        
        context = ""
        if conversation_history:
            context = "\n".join(f"- {msg}" for msg in conversation_history[-5:])
        
        prompt = f"""
Você é um assistente de triagem médica. Extraia informações estruturadas da conversa do usuário.

CONTEXTO DA CONVERSA (últimas 5 mensagens):
{context}

MENSAGEM ATUAL DO USUÁRIO:
{user_text}

INSTRUÇÕES:
1. Extraia informações para os seguintes campos de triagem:
   - chief_complaint: queixa principal
   - symptoms: sintomas detalhados
   - duration: há quanto tempo (duração)
   - frequency: frequência dos sintomas
   - intensity: intensidade (escala 0-10 se mencionada)
   - history: histórico médico relevante
   - measures_taken: medidas já tomadas

2. Para campos não mencionados, use null.
3. Normalize a intensidade para escala 0-10 quando possível.
4. Detecte emergência por palavras-chave: dor no peito, falta de ar, desmaio, sangramento intenso, etc.

RESPONDA APENAS COM JSON VÁLIDO:
{{
  "chief_complaint": "string|null",
  "symptoms": "string|null", 
  "duration": "string|null",
  "frequency": "string|null",
  "intensity": "string|null",
  "history": "string|null",
  "measures_taken": "string|null",
  "found_emergency": false
}}
"""
        return prompt.strip()

    def _build_next_prompt_template(
        self,
        current_slots: TriageSlots,
        conversation_history: list[str] = None,
        is_first_interaction: bool = False
    ) -> str:
        """Build prompt for generating next question."""
        
        missing_slots = current_slots.get_missing_slots()
        filled_slots = {
            field: value for field, value in current_slots.model_dump().items()
            if value is not None
        }
        
        context = ""
        if conversation_history:
            context = "\n".join(f"- {msg}" for msg in conversation_history[-3:])
        
        if is_first_interaction:
            instruction = "Gere a mensagem de boas-vindas inicial."
        elif not missing_slots:
            instruction = "Todas as informações foram coletadas. Gere mensagem de finalização."
        else:
            instruction = f"Faça a próxima pergunta para coletar: {missing_slots[0]}"

        prompt = f"""
Você é a ClinicAI, assistente virtual acolhedor e empático de uma clínica médica.

PERSONA:
- Linguagem simples, clara e humanizada
- Tom profissional mas caloroso
- Sem jargões médicos
- JAMAIS forneça diagnósticos ou tratamentos

CONTEXTO DA CONVERSA:
{context}

INFORMAÇÕES JÁ COLETADAS:
{json.dumps(filled_slots, ensure_ascii=False, indent=2)}

INFORMAÇÕES FALTANTES:
{missing_slots}

INSTRUÇÃO: {instruction}

REGRAS CRÍTICAS:
1. Se for primeira interação, inclua aviso: "Sou assistente virtual que coletará informações para agilizar seu atendimento. Não substituo avaliação médica."
2. Faça UMA pergunta por vez
3. Explique brevemente por que está perguntando
4. NUNCA mencione diagnósticos, doenças ou tratamentos
5. Se finalização, agradeça e informe que um profissional dará continuidade

Responda apenas a mensagem para o usuário:
"""
        return prompt.strip()

    def _get_fallback_prompt(self, current_slots: TriageSlots) -> str:
        """Get fallback prompt when LLM fails."""
        missing_slots = current_slots.get_missing_slots()
        
        if not missing_slots:
            return (
                "Obrigada! Registrei todas as informações da sua triagem. "
                "Um profissional da nossa clínica dará continuidade em breve."
            )
        
        # Map slot names to Portuguese questions
        slot_questions = {
            "chief_complaint": "Qual é o motivo principal do seu contato hoje?",
            "symptoms": "Pode me descrever melhor os sintomas que está sentindo?",
            "duration": "Há quanto tempo esses sintomas começaram?",
            "frequency": "Com que frequência esses sintomas acontecem?",
            "intensity": "Numa escala de 0 a 10, qual a intensidade do desconforto?",
            "history": "Tem algum histórico médico que considera relevante?",
            "measures_taken": "Já tomou alguma medida ou medicação para aliviar?"
        }
        
        next_slot = missing_slots[0]
        return slot_questions.get(
            next_slot, 
            "Pode me fornecer mais informações sobre sua condição?"
        )


# Global LLM client instance
llm_client = GeminiLLMClient()


# Convenience functions for backward compatibility
async def llm_extract_slots(user_text: str) -> LLMExtraction:
    """
    Extract slots from user text using LLM.
    
    Args:
        user_text: User input text
        
    Returns:
        Extracted slot information
    """
    return await llm_client.extract_slots(user_text)


async def llm_next_prompt(
    current_slots: TriageSlots,
    is_first: bool = False
) -> str:
    """
    Generate next prompt for user.
    
    Args:
        current_slots: Current triage state
        is_first: Whether this is the first interaction
        
    Returns:
        Next prompt text
    """
    return await llm_client.generate_next_prompt(
        current_slots=current_slots,
        is_first_interaction=is_first
    )

