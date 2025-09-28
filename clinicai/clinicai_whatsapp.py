#!/usr/bin/env python3
"""
ClinicAI - Agente de Triagem com WhatsApp (versão SQLite)
Foco na integração WhatsApp primeiro, MongoDB depois.
"""

import os
import json
import sqlite3
import hashlib
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

import uvicorn
import httpx
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
load_dotenv()


# ================================
# CONFIGURAÇÃO E LOGGING
# ================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurações via variáveis de ambiente
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "fake_key_for_testing")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "fake_token")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "fake_id")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "ClinicAI_Test_Token_123")
PHONE_HASH_SALT = os.getenv("PHONE_HASH_SALT", "ClinicAI_Salt_2024")

# Log das configurações carregadas (sem mostrar tokens completos por segurança)
logger.info("🔧 Configurações carregadas:")
logger.info(f"   Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID}")
logger.info(f"   Access Token: {WHATSAPP_ACCESS_TOKEN[:10]}...{WHATSAPP_ACCESS_TOKEN[-5:] if len(WHATSAPP_ACCESS_TOKEN) > 15 else WHATSAPP_ACCESS_TOKEN}")
logger.info(f"   Verify Token: {WHATSAPP_VERIFY_TOKEN}")

# Verificar se as credenciais são válidas
if WHATSAPP_ACCESS_TOKEN == "fake_token":
    logger.warning("⚠️  WARNING: Usando access token fake - configure o arquivo .env")
if WHATSAPP_PHONE_NUMBER_ID == "fake_id":
    logger.warning("⚠️  WARNING: Usando phone ID fake - configure o arquivo .env")

# ================================
# MODELOS PYDANTIC
# ================================

class WhatsAppTextMessage(BaseModel):
    body: str

class WhatsAppMessage(BaseModel):
    from_: str = Field(alias="from")
    id: str
    timestamp: str
    text: WhatsAppTextMessage
    type: str = "text"

class WhatsAppValue(BaseModel):
    messaging_product: str
    metadata: Dict[str, Any]
    contacts: Optional[List] = None
    messages: List[WhatsAppMessage]

class WhatsAppEntry(BaseModel):
    id: str
    changes: List[Dict[str, Any]]

class IncomingWhatsAppPayload(BaseModel):
    object: str
    entry: List[WhatsAppEntry]

class TriageSlots(BaseModel):
    """Slots de informações para triagem médica - ordem específica."""
    chief_complaint: Optional[str] = None      # 1. Qual a sua queixa?
    symptoms: Optional[str] = None             # 2. Pode descrever tudo que você está sentindo...
    duration_frequency: Optional[str] = None  # 3. Desde quando... e com que frequência...
    intensity: Optional[str] = None           # 4. Qual a intensidade da dor (0-10)...
    measures_taken: Optional[str] = None      # 5. Você já fez algo para aliviar...
    health_history: Optional[str] = None      # 6. Você tem algum histórico de saúde...

    def is_complete(self) -> bool:
        return all(getattr(self, field) is not None for field in self.__class__.model_fields.keys())

    def get_missing_slots(self) -> List[str]:
        return [field for field in self.__class__.model_fields.keys() if getattr(self, field) is None]
    
    def get_next_slot_to_collect(self) -> Optional[str]:
        """Retorna o próximo slot a ser coletado seguindo a ordem específica."""
        priority_order = [
            "chief_complaint",      # 1. Qual a sua queixa?
            "symptoms",             # 2. Pode descrever tudo que você está sentindo...
            "duration_frequency",   # 3. Desde quando... e com que frequência...
            "intensity",            # 4. Qual a intensidade da dor (0-10)...
            "measures_taken",       # 5. Você já fez algo para aliviar...
            "health_history"        # 6. Você tem algum histórico de saúde...
        ]
        
        for slot in priority_order:
            if getattr(self, slot) is None:
                return slot
        return None

# ================================
# DETECÇÃO DE EMERGÊNCIA
# ================================

EMERGENCY_KEYWORDS = [
    "dor no peito", "dor forte no peito", "falta de ar", "dificuldade para respirar",
    "desmaio", "desmaiei", "vou desmaiar", "inconsciente", "sangramento intenso",
    "hemorragia", "convulsão", "convulsao", "fraqueza súbita", "fraqueza subita",
    "paralisia", "confusão súbita", "confusao subita", "pressão muito baixa",
    "nao consigo respirar", "peito apertado", "vômito com sangue", "febre muito alta"
]

def is_emergency(text: str) -> bool:
    """Detecta palavras-chave de emergência."""
    if not text:
        return False
    
    text_lower = text.lower()
    for keyword in EMERGENCY_KEYWORDS:
        if keyword in text_lower:
            logger.warning(f"Emergency keyword detected: {keyword}")
            return True
    return False

def get_emergency_response() -> str:
    """Retorna mensagem padrão de emergência."""
    return (
        "🚨 Entendi. Seus sintomas podem indicar uma situação de emergência. "
        "Por favor, procure o pronto-socorro mais próximo ou ligue 192 imediatamente."
    )

# ================================
# BANCO DE DADOS SQLite
# ================================

class TriageDatabase:
    """Banco de dados SQLite para triagens (temporário)."""
    
    def __init__(self, db_path: str = "clinicai.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializa as tabelas do banco."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_hash TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    message_id TEXT UNIQUE,
                    text TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    meta_json TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS triages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_hash TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'open',
                    slots_json TEXT,
                    emergency_flag BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_activity DATETIME,
                    completed_at DATETIME
                )
            """)
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_phone_hash ON messages(phone_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_triage_phone ON triages(phone_hash)")
    
    def save_message(self, phone_hash: str, direction: str, message_id: str, text: str, meta: dict = None):
        """Salva uma mensagem no banco."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO messages (phone_hash, direction, message_id, text, meta_json)
                VALUES (?, ?, ?, ?, ?)
            """, (phone_hash, direction, message_id, text, json.dumps(meta or {})))
    
    def get_triage(self, phone_hash: str) -> Optional[Dict]:
        """Busca triagem por phone_hash."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM triages WHERE phone_hash = ?", (phone_hash,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def create_or_update_triage(self, phone_hash: str, slots: TriageSlots = None, 
                               status: str = "open", emergency_flag: bool = False,
                               last_activity: str = None, completed_at: str = None):
        """Cria ou atualiza uma triagem."""
        slots_json = json.dumps(slots.model_dump() if slots else {})
        current_time = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            if completed_at:
                conn.execute("""
                    INSERT OR REPLACE INTO triages 
                    (phone_hash, status, slots_json, emergency_flag, last_activity, completed_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (phone_hash, status, slots_json, emergency_flag, last_activity or current_time, completed_at))
            else:
                conn.execute("""
                    INSERT OR REPLACE INTO triages 
                    (phone_hash, status, slots_json, emergency_flag, last_activity, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (phone_hash, status, slots_json, emergency_flag, last_activity or current_time))
    
    def get_active_triage(self, phone_hash: str) -> Optional[Dict]:
        """Busca triagem ativa (não concluída) do usuário."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM triages 
                WHERE phone_hash = ? AND status IN ('open', 'emergency')
                ORDER BY created_at DESC LIMIT 1
            """, (phone_hash,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def get_triage_slots(self, phone_hash: str) -> TriageSlots:
        """Busca slots da triagem."""
        triage = self.get_triage(phone_hash)
        if triage and triage["slots_json"]:
            slots_data = json.loads(triage["slots_json"])
            return TriageSlots(**slots_data)
        return TriageSlots()

# ================================
# UTILITÁRIOS
# ================================

def hash_phone_number(phone: str) -> str:
    """Hash do número de telefone para privacidade."""
    normalized_phone = ''.join(filter(str.isdigit, phone))
    salted_phone = PHONE_HASH_SALT + normalized_phone
    return hashlib.sha256(salted_phone.encode()).hexdigest()

def extract_phone_from_whatsapp(whatsapp_phone: str) -> str:
    """Extrai número limpo do WhatsApp."""
    phone = ''.join(filter(str.isdigit, whatsapp_phone))
    phone = phone.lstrip('0')
    if len(phone) >= 10 and not phone.startswith('55'):
        phone = '55' + phone
    return phone

# ================================
# WHATSAPP CLIENT
# ================================

class WhatsAppClient:
    """Cliente para WhatsApp Cloud API."""
    
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v20.0"
        self.phone_number_id = WHATSAPP_PHONE_NUMBER_ID
        self.access_token = WHATSAPP_ACCESS_TOKEN
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def send_text_message(self, to_phone: str, message_text: str) -> Optional[str]:
        """Envia mensagem de texto via WhatsApp."""
        if not message_text.strip():
            return None
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"preview_url": False, "body": message_text}
        }
        
        try:
            logger.info(f"Sending WhatsApp message to {to_phone[:8]}...")
            response = await self.http_client.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                message_id = response_data.get("messages", [{}])[0].get("id")
                logger.info(f"Message sent successfully: {message_id}")
                return message_id
            else:
                logger.error(f"WhatsApp API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return None
    
    async def send_text(self, to_phone: str, message_text: str) -> Optional[str]:
        """Alias para send_text_message para compatibilidade."""
        return await self.send_text_message(to_phone, message_text)
    
    def parse_incoming_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse mensagem recebida do WhatsApp."""
        try:
            entry = payload.get("entry", [])
            if not entry:
                return None
            
            changes = entry[0].get("changes", [])
            if not changes:
                return None
            
            value = changes[0].get("value", {})
            messages = value.get("messages", [])
            
            if not messages:
                return None
            
            message = messages[0]
            if message.get("type") != "text":
                return None
            
            return {
                "message_id": message.get("id"),
                "from_phone": message.get("from"),
                "timestamp": message.get("timestamp"),
                "text": message.get("text", {}).get("body", ""),
                "raw_payload": payload,
            }
        except Exception as e:
            logger.error(f"Error parsing WhatsApp message: {e}")
            return None

# ================================
# INTEGRAÇÃO GEMINI
# ================================

class QuestionManager:
    """Gerenciador de perguntas específicas na ordem correta."""
    
    # Perguntas específicas na ordem exata
    QUESTIONS = {
        "chief_complaint": "Qual a sua queixa?",
        "symptoms": "Pode descrever tudo que você está sentindo de maneira detalhada, por favor?",
        "duration_frequency": "Desde quando os sintomas começaram e com que frequência ocorrem?",
        "intensity": "Qual a intensidade da dor em uma escala de 0 a 10? Sendo 0 sem dor e 10 uma dor insuportável.",
        "measures_taken": "Você já fez algo para tentar aliviar os sintomas?",
        "health_history": "Você tem algum histórico de saúde relevante?"
    }
    
    def get_question(self, slot: str) -> str:
        """Retorna a pergunta específica para o slot."""
        return self.QUESTIONS.get(slot, "Pode me fornecer mais informações?")

class GeminiProcessor:
    """Processador Gemini apenas para validação de respostas."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None
        if api_key and api_key != "fake_key_for_testing":
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.client = genai.GenerativeModel("gemini-flash-latest")
                logger.info("✅ Gemini configurado com sucesso")
            except Exception as e:
                logger.error(f"❌ Erro ao configurar Gemini: {e}")
                self.client = None
        else:
            logger.warning("⚠️  Gemini não configurado - usando fallback")
    
    async def validate_response(self, user_text: str, question: str, target_slot: str) -> bool:
        """Valida se a resposta do usuário está de acordo com a pergunta."""
        if not self.client:
            logger.warning("⚠️ Gemini não disponível - assumindo resposta válida")
            return True  # Se não há Gemini, assume que está ok
        
        logger.info(f"📤 Enviando para Gemini - Pergunta: '{question}'")
        logger.info(f"📤 Enviando para Gemini - Resposta: '{user_text}'")
        
        try:
            prompt = f"""
Pergunta feita: "{question}"
Resposta do usuário: "{user_text}"

A resposta do usuário responde adequadamente à pergunta feita?

Responda apenas "SIM" se a resposta está relacionada e adequada à pergunta.
Responda apenas "NAO" se a resposta não está relacionada ou é inadequada.

Resposta:"""
            
            import asyncio
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
            
            response = await asyncio.to_thread(
                self.client.generate_content,
                prompt,
                generation_config={"temperature": 0.1, "max_output_tokens": 10},
                safety_settings=safety_settings
            )
            
            # Verificar se a resposta foi bloqueada por segurança
            if not response.candidates or not response.candidates[0].content.parts:
                logger.warning(f"⚠️ Validação bloqueada por filtro de segurança")
                return True  # Assume que está ok se Gemini não pode validar
            
            validation = response.text.strip().upper()
            is_valid = "SIM" in validation
            logger.info(f"🤖 Validação Gemini para {target_slot}: {'✅ Válida' if is_valid else '❌ Inválida'}")
            return is_valid
            
        except Exception as e:
            logger.error(f"❌ Erro na validação Gemini: {e}")
            return True  # Se erro, assume que está ok
    
    async def rewrite_question(self, original_question: str, target_slot: str) -> str:
        """Reescreve a pergunta de outra forma quando a resposta não foi adequada."""
        if not self.client:
            logger.warning("⚠️ Gemini não disponível - usando fallback para reescrita")
            return f"Vou perguntar de outro jeito: {original_question}"
        
        logger.info(f"🔄 Solicitando reescrita para {target_slot}")
        
        try:
            prompt = f"""
Pergunta original: "{original_question}"

O usuário não respondeu adequadamente a esta pergunta. Reescreva a pergunta de forma diferente, mas mantendo o mesmo objetivo.

Regras:
1. Mantenha o mesmo significado e objetivo
2. Use palavras diferentes ou estrutura diferente
3. Seja claro e direto
4. Máximo 20 palavras

Pergunta reescrita:"""
            
            import asyncio
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
            
            response = await asyncio.to_thread(
                self.client.generate_content,
                prompt,
                generation_config={"temperature": 0.7, "max_output_tokens": 50},
                safety_settings=safety_settings
            )
            
            # Verificar se a resposta foi bloqueada por segurança
            if not response.candidates or not response.candidates[0].content.parts:
                logger.warning(f"⚠️ Reescrita bloqueada por filtro de segurança")
                return f"Vou perguntar de outro jeito: {original_question}"
            
            rewritten = response.text.strip()
            logger.info(f"🤖 Pergunta reescrita para {target_slot}")
            return rewritten
            
        except Exception as e:
            logger.error(f"❌ Erro na reescrita: {e}")
            return f"Vou perguntar de outro jeito: {original_question}"
    
    async def generate_question(self, target_slot: str, current_slots: TriageSlots, is_first: bool = False) -> str:
        """Gera pergunta personalizada para o próximo slot."""
        if not self.client:
            return self._get_fallback_question(target_slot, is_first)
        
        try:
            prompt = self._build_question_prompt(target_slot, current_slots, is_first)
            
            import asyncio
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
            
            response = await asyncio.to_thread(
                self.client.generate_content,
                prompt,
                generation_config={"temperature": 0.7, "max_output_tokens": 300},
                safety_settings=safety_settings
            )
            
            # Verificar se a resposta foi bloqueada por segurança
            if not response.candidates or not response.candidates[0].content.parts:
                logger.warning(f"⚠️ Pergunta bloqueada por filtro de segurança (finish_reason: {response.candidates[0].finish_reason if response.candidates else 'unknown'})")
                return self._get_fallback_question(target_slot, is_first)
            
            question = response.text.strip()
            logger.info(f"🤖 Gemini gerou pergunta para {target_slot}")
            return question
            
        except Exception as e:
            logger.error(f"❌ Erro na geração de pergunta: {e}")
            return self._get_fallback_question(target_slot, is_first)
    
    def _build_extraction_prompt(self, user_text: str, target_slot: str, conversation_history: List[str] = None) -> str:
        """Constrói prompt para extração de informação específica."""
        
        slot_descriptions = {
            "chief_complaint": "o motivo principal do contato",
            "symptoms": "descrição detalhada da situação",
            "duration": "quando começou (tempo)",
            "frequency": "frequência (quantas vezes acontece)",
            "intensity": "intensidade numa escala de 0 a 10",
            "history": "histórico pessoal relevante",
            "measures_taken": "ações já realizadas"
        }
        
        context = ""
        if conversation_history:
            context = f"Histórico da conversa:\n" + "\n".join(conversation_history[-3:]) + "\n\n"
        
        question_context = {
            "chief_complaint": "Pergunta: 'Qual é o motivo do seu contato hoje?'",
            "symptoms": "Pergunta: 'Pode me contar mais detalhes sobre o que está acontecendo?'", 
            "duration": "Pergunta: 'Quando isso começou?'",
            "frequency": "Pergunta: 'Com que frequência isso acontece?' (aceitar também padrões temporais)",
            "intensity": "Pergunta: 'Numa escala de 0 a 10, como você classificaria?'",
            "history": "Pergunta: 'Há algo do seu histórico que considera importante mencionar?'",
            "measures_taken": "Pergunta: 'Já tentou fazer alguma coisa para ajudar com isso?'"
        }
        
        return f"""
{question_context.get(target_slot, "Pergunta feita")}

Resposta: "{user_text}"

A resposta contém informação para a pergunta?
Se SIM: copie a parte relevante
Se NÃO: responda "não mencionado"

Resultado:"""

    def _build_question_prompt(self, target_slot: str, current_slots: TriageSlots, is_first: bool) -> str:
        """Constrói prompt para gerar pergunta personalizada."""
        
        if is_first:
            return """
Crie uma mensagem de boas-vindas simples e direta para um assistente de atendimento.

Inclua:
- Saudação amigável
- Explicar que vai fazer algumas perguntas
- Pedir o motivo do contato

Resposta:"""

        slot_questions = {
            "chief_complaint": {
                "pergunta": "qual é o motivo do seu contato hoje",
                "explicacao": "Para organizar as informações"
            },
            "symptoms": {
                "pergunta": "pode me contar mais detalhes sobre o que está acontecendo",
                "explicacao": "Para entender melhor a situação"
            },
            "duration": {
                "pergunta": "quando isso começou",
                "explicacao": "Para organizar a linha do tempo"
            },
            "frequency": {
                "pergunta": "com que frequência isso acontece",
                "explicacao": "Para entender se é constante ou esporádico"
            },
            "intensity": {
                "pergunta": "numa escala de 0 a 10, como você classificaria",
                "explicacao": "Para ter uma medida objetiva"
            },
            "history": {
                "pergunta": "há algo do seu histórico que considera importante mencionar",
                "explicacao": "Para contextualizar as informações"
            },
            "measures_taken": {
                "pergunta": "já tentou fazer alguma coisa para ajudar com isso",
                "explicacao": "Para completar o registro"
            }
        }
        
        filled_info = []
        for field, value in current_slots.model_dump().items():
            if value:
                filled_info.append(f"- {field}: {value}")
        
        filled_context = "\n".join(filled_info) if filled_info else "Nenhuma informação coletada ainda"
        
        slot_info = slot_questions.get(target_slot, {"pergunta": "mais informações", "explicacao": "Precisamos de mais detalhes"})
        
        next_questions = {
            "chief_complaint": "Pergunte qual é o motivo do contato de hoje",
            "symptoms": "Peça mais detalhes sobre a situação",
            "duration": "Pergunte quando começou",
            "frequency": "Pergunte com que frequência acontece",
            "intensity": "Peça uma classificação de 0 a 10",
            "history": "Pergunte sobre histórico pessoal relevante",
            "measures_taken": "Pergunte sobre ações já realizadas"
        }
        
        return f"""
Tarefa: {next_questions.get(target_slot, "Faça uma pergunta para obter mais informações")}

Crie uma pergunta simples e direta:"""

    def _extract_fallback(self, user_text: str, target_slot: str) -> Optional[str]:
        """Extração simples sem Gemini."""
        text_lower = user_text.lower()
        
        # Lógica simples para cada slot
        if target_slot == "chief_complaint" and not hasattr(self, '_chief_collected'):
            self._chief_collected = True
            return user_text[:100]  # Primeiras palavras como queixa
        
        if target_slot == "symptoms":
            symptoms_words = ["dor", "doendo", "machuca", "sinto", "latejante", "queimando", "formiga"]
            if any(word in text_lower for word in symptoms_words):
                return user_text[:100]
        
        if target_slot == "duration":
            duration_words = ["dias", "dia", "horas", "hora", "semanas", "semana", "meses", "mês", "ontem", "hoje", "manhã", "tarde", "noite"]
            if any(word in text_lower for word in duration_words):
                return user_text
        
        if target_slot == "frequency":
            frequency_words = ["sempre", "todo", "toda", "vez", "vezes", "diário", "final", "manhã", "tarde", "noite", "constante", "esporádico"]
            if any(word in text_lower for word in frequency_words):
                return user_text
        
        if target_slot == "intensity":
            for i in range(1, 11):
                if str(i) in user_text:
                    return str(i)
            intensity_words = ["forte", "fraca", "muito", "pouco", "insuportável", "leve"]
            if any(word in text_lower for word in intensity_words):
                return user_text
        
        if target_slot == "history":
            history_words = ["tenho", "tive", "pressão", "diabetes", "problema", "condição", "médico", "cirurgia", "remédio"]
            if any(word in text_lower for word in history_words):
                return user_text
        
        if target_slot == "measures_taken":
            action_words = ["tomei", "usei", "fiz", "tentei", "medicamento", "remédio", "paracetamol", "ibuprofeno", "descanso"]
            if any(word in text_lower for word in action_words):
                return user_text
        
        return None
    
    def _get_fallback_question(self, target_slot: str, is_first: bool) -> str:
        """Perguntas de fallback sem Gemini."""
        if is_first:
            return (
                "🏥 *Olá! Sou a ClinicAI*\n\n"
                "Sou seu assistente virtual e vou ajudar a organizar suas informações para agilizar seu atendimento.\n\n"
                "⚠️ *Importante:* Sou um assistente virtual e não substituo uma avaliação médica.\n\n"
                "Para começarmos, qual é o motivo principal do seu contato hoje?"
            )
        
        # Usar o QuestionManager para perguntas específicas
        return self.question_manager.get_question(target_slot)

# ================================
# PROCESSAMENTO DE TRIAGEM
# ================================

class TriageProcessor:
    """Processador de triagem com Gemini."""
    
    # Constantes
    TIMEOUT_MINUTES = 30  # Timeout de 30 minutos
    
    def __init__(self, db: TriageDatabase, whatsapp: WhatsAppClient, gemini_api_key: str):
        self.db = db
        self.whatsapp = whatsapp
        self.gemini = GeminiProcessor(gemini_api_key)
        self.question_manager = QuestionManager()
        self.conversation_histories = {}  # Cache de histórico por phone_hash
    
    def _check_timeout(self, last_activity: datetime) -> bool:
        """Verifica se passou do timeout de 30 minutos."""
        if not last_activity:
            return False
        
        timeout_limit = datetime.now() - timedelta(minutes=self.TIMEOUT_MINUTES)
        return last_activity < timeout_limit
    
    async def _get_user_triages(self, phone_hash: str) -> List[Dict]:
        """Busca histórico de atendimentos do usuário."""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, created_at, status, slots_json, completed_at 
                FROM triages 
                WHERE phone_hash = ? 
                ORDER BY created_at DESC
            """, (phone_hash,))
            
            triages = []
            for row in cursor.fetchall():
                # Extrair chief_complaint do JSON
                slots_json = row[3] or "{}"
                try:
                    slots_data = json.loads(slots_json)
                    chief_complaint = slots_data.get('chief_complaint', 'Não informado')
                except:
                    chief_complaint = 'Não informado'
                
                triages.append({
                    'id': row[0],
                    'created_at': row[1],
                    'status': row[2],
                    'chief_complaint': chief_complaint,
                    'completed_at': row[4]
                })
            
            conn.close()
            return triages
            
        except Exception as e:
            logger.error(f"Erro ao buscar triagens do usuário: {e}")
            return []
    
    async def _send_history_menu(self, phone: str, triages: List[Dict]) -> bool:
        """Envia menu com histórico de atendimentos."""
        try:
            if not triages:
                welcome_msg = (
                    "🏥 *Bem-vindo à ClinicAI!*\n\n"
                    "Sou seu assistente virtual e vou ajudar a organizar suas informações para agilizar seu atendimento.\n\n"
                    "⚠️ *Importante:* Sou um assistente virtual e não substituo uma avaliação médica.\n\n"
                    "Para começarmos, qual é o motivo principal do seu contato hoje?"
                )
                await self.whatsapp.send_text(phone, welcome_msg)
                return True
            
            # Usuário tem histórico - mostrar opções
            history_text = "🏥 *Bem-vindo de volta à ClinicAI!*\n\n"
            history_text += "Vejo que você já teve atendimentos conosco. O que gostaria de fazer?\n\n"
            
            history_text += "*📋 Atendimentos anteriores:*\n"
            for i, triage in enumerate(triages[:3], 1):  # Mostrar até 3 últimos
                date = datetime.fromisoformat(triage['created_at']).strftime('%d/%m/%Y %H:%M')
                status = "✅ Concluído" if triage['status'] == 'completed' else "⏳ Em andamento"
                chief = triage['chief_complaint'][:30] + "..." if len(triage['chief_complaint']) > 30 else triage['chief_complaint']
                history_text += f"{i}. {date} - {chief} ({status})\n"
            
            if len(triages) > 3:
                history_text += f"... e mais {len(triages) - 3} atendimento(s)\n"
            
            history_text += "\n*Como posso ajudar?*\n"
            history_text += "• Digite *'novo'* para iniciar um novo atendimento\n"
            history_text += "• Digite *'histórico'* para ver todos os atendimentos\n"
            history_text += "• Ou me conte diretamente o motivo do seu contato"
            
            await self.whatsapp.send_text(phone, history_text)
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar menu de histórico: {e}")
            return False
    
    async def _send_full_history(self, phone: str, triages: List[Dict]) -> bool:
        """Envia histórico completo de atendimentos."""
        try:
            if not triages:
                await self.whatsapp.send_text(phone, "Você ainda não possui atendimentos anteriores.")
                return True
            
            history_text = f"📋 *Seu Histórico Completo* ({len(triages)} atendimento(s))\n\n"
            
            for i, triage in enumerate(triages, 1):
                date = datetime.fromisoformat(triage['created_at']).strftime('%d/%m/%Y às %H:%M')
                status = "✅ Concluído" if triage['status'] == 'completed' else "⏳ Em andamento"
                chief = triage['chief_complaint'] or "Não informado"
                
                history_text += f"*{i}. Atendimento {date}*\n"
                history_text += f"   Status: {status}\n"
                history_text += f"   Motivo: {chief}\n"
                
                if triage['completed_at']:
                    completed_date = datetime.fromisoformat(triage['completed_at']).strftime('%d/%m/%Y às %H:%M')
                    history_text += f"   Finalizado: {completed_date}\n"
                
                history_text += "\n"
            
            history_text += "Para iniciar um novo atendimento, digite *'novo'* ou me conte o motivo do seu contato."
            
            await self.whatsapp.send_text(phone, history_text)
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar histórico completo: {e}")
            return False
    
    async def process_message(self, phone: str, message_text: str, message_id: str = None) -> Dict[str, Any]:
        """Processa mensagem de triagem com Gemini."""
        try:
            # Normalizar telefone e criar hash
            normalized_phone = extract_phone_from_whatsapp(phone)
            phone_hash = hash_phone_number(normalized_phone)
            
            logger.info(f"Processing message for phone_hash: {phone_hash[:8]}...")
            
            # Verificar se é comando especial
            message_lower = message_text.lower().strip()
            
            # Processar mensagem normalmente (sem comandos especiais)
            
            # Buscar triagem ativa
            current_triage = self.db.get_active_triage(phone_hash)
            
            # Verificar timeout se há triagem ativa
            if current_triage:
                last_activity_str = current_triage.get('last_activity') or current_triage.get('created_at')
                if last_activity_str:
                    try:
                        last_activity = datetime.fromisoformat(last_activity_str)
                        if self._check_timeout(last_activity):
                            logger.info(f"Timeout detected for phone_hash: {phone_hash[:8]}, resetting session")
                            # Marcar triagem como timeout
                            self.db.create_or_update_triage(
                                phone_hash=phone_hash,
                                status="timeout",
                                completed_at=datetime.now().isoformat(),
                                last_activity=last_activity.isoformat()
                            )
                            # Limpar cache
                            if phone_hash in self.conversation_histories:
                                del self.conversation_histories[phone_hash]
                            current_triage = None
                    except Exception as e:
                        logger.error(f"Erro ao verificar timeout: {e}")
                        # Continuar sem resetar
            
            # Se não há triagem ativa ou houve timeout - iniciar nova triagem
            if not current_triage:
                # Criar nova triagem
                self.db.create_or_update_triage(
                    phone_hash=phone_hash,
                    status="open",
                    last_activity=datetime.now().isoformat()
                )
                
                # Resetar histórico de conversa
                self.conversation_histories[phone_hash] = []
                
                # Enviar introdução + primeira pergunta
                intro_message = (
                    "🏥 *Olá! Sou a ClinicAI*\n\n"
                    "Sou seu assistente virtual e vou ajudar a organizar suas informações para agilizar seu atendimento.\n\n"
                    "⚠️ *Importante:* Sou um assistente virtual e não substituo uma avaliação médica.\n\n"
                    "Para começarmos, qual é a sua queixa?"
                )
                await self.whatsapp.send_text(normalized_phone, intro_message)
                
                return {
                    "success": True,
                    "action": "first_question_sent", 
                    "phone_hash": phone_hash
                }
            
            # Inicializar histórico se não existir
            if phone_hash not in self.conversation_histories:
                self.conversation_histories[phone_hash] = []
            
            # Adicionar mensagem ao histórico
            self.conversation_histories[phone_hash].append(f"Usuario: {message_text}")
            
            # Salvar mensagem recebida
            self.db.save_message(
                phone_hash=phone_hash,
                direction="in",
                message_id=message_id or f"in_{datetime.now().timestamp()}",
                text=message_text,
                meta={"source": "whatsapp"}
            )
            
            # Verificar emergência
            if is_emergency(message_text):
                logger.warning(f"Emergency detected for phone_hash: {phone_hash[:8]}...")
                
                # Atualizar triagem como emergência
                self.db.create_or_update_triage(
                    phone_hash=phone_hash,
                    status="emergency",
                    emergency_flag=True,
                    last_activity=datetime.now().isoformat()
                )
                
                # Enviar resposta de emergência
                emergency_response = get_emergency_response()
                message_id = await self.whatsapp.send_text_message(normalized_phone, emergency_response)
                
                # Salvar resposta e histórico
                if message_id:
                    self.db.save_message(
                        phone_hash=phone_hash,
                        direction="out",
                        message_id=message_id,
                        text=emergency_response
                    )
                    self.conversation_histories[phone_hash].append(f"ClinicAI: {emergency_response}")
                
                return {
                    "success": True,
                    "status": "emergency",
                    "emergency": True,
                    "response_sent": bool(message_id)
                }
            
            # Buscar triagem atual
            current_slots = self.db.get_triage_slots(phone_hash)
            triage_data = self.db.get_triage(phone_hash)
            is_first_interaction = triage_data is None
            
            # Determinar qual slot estamos coletando
            current_slot = current_slots.get_next_slot_to_collect()
            
            if current_slot:
                # Obter pergunta específica para este slot
                current_question = self.question_manager.get_question(current_slot)
                
                # Validar se a resposta está de acordo com a pergunta
                logger.info(f"🔍 Validando resposta para {current_slot}: '{message_text[:50]}...'")
                is_valid_response = await self.gemini.validate_response(
                    user_text=message_text,
                    question=current_question,
                    target_slot=current_slot
                )
                logger.info(f"🎯 Resultado validação: {'✅ APROVADA' if is_valid_response else '❌ REJEITADA'}")
                
                if is_valid_response:
                    # Resposta válida - salvar e avançar
                    setattr(current_slots, current_slot, message_text.strip())
                    logger.info(f"✅ Coletado {current_slot}: {message_text[:30]}...")
                    
                    # Salvar slots atualizados
                    current_time = datetime.now().isoformat()
                    self.db.create_or_update_triage(
                        phone_hash=phone_hash,
                        slots=current_slots,
                        status="open",
                        last_activity=current_time
                    )
                    
                    # Verificar se triagem está completa
                    next_slot = current_slots.get_next_slot_to_collect()
                    if next_slot:
                        # Fazer próxima pergunta
                        response_text = self.question_manager.get_question(next_slot)
                    else:
                        # Triagem completa
                        response_text = await self._get_completion_message(current_slots)
                        completion_time = datetime.now().isoformat()
                        self.db.create_or_update_triage(
                            phone_hash=phone_hash,
                            slots=current_slots,
                            status="completed",
                            last_activity=current_time,
                            completed_at=completion_time
                        )
                        logger.info(f"🎉 Triagem completa para {phone_hash[:8]}...")
                else:
                    # Resposta inválida - reescrever pergunta
                    logger.info(f"❌ Resposta INVÁLIDA para {current_slot} - solicitando nova pergunta ao Gemini")
                    logger.info(f"📝 Pergunta original: '{current_question}'")
                    response_text = await self.gemini.rewrite_question(
                        original_question=current_question,
                        target_slot=current_slot
                    )
                    logger.info(f"📝 Pergunta reescrita: '{response_text}'")
                
            else:
                # Triagem já completa - reapresentar
                response_text = (
                    "🏥 *Olá! Sou a ClinicAI*\n\n"
                    "Vejo que você já concluiu uma triagem recente. Para um novo atendimento, "
                    "qual é o motivo principal do seu contato hoje?"
                )
                # Resetar para nova triagem
                self.conversation_histories[phone_hash] = []
            
            # Enviar resposta
            message_id = await self.whatsapp.send_text_message(normalized_phone, response_text)
            
            # Salvar resposta e atualizar histórico
            if message_id:
                self.db.save_message(
                    phone_hash=phone_hash,
                    direction="out",
                    message_id=message_id,
                    text=response_text
                )
                self.conversation_histories[phone_hash].append(f"ClinicAI: {response_text}")
                
                # Manter histórico limitado
                if len(self.conversation_histories[phone_hash]) > 20:
                    self.conversation_histories[phone_hash] = self.conversation_histories[phone_hash][-10:]
            
            return {
                "success": True,
                "status": "open",
                "emergency": False,
                "response_sent": bool(message_id),
                "phone_hash": phone_hash,
                "current_slot": current_slot,
                "slots_filled": sum(1 for v in current_slots.model_dump().values() if v is not None)
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "error",
                "emergency": False,
                "response_sent": False
            }
    
    async def _get_completion_message(self, slots: TriageSlots) -> str:
        """Mensagem de finalização da triagem com resumo."""
        
        # Criar resumo das informações coletadas
        summary_parts = []
        
        if slots.chief_complaint:
            summary_parts.append(f"✓ Queixa: {slots.chief_complaint}")
        if slots.symptoms:
            summary_parts.append(f"✓ Sintomas: {slots.symptoms}")
        if slots.duration_frequency:
            summary_parts.append(f"✓ Duração/Frequência: {slots.duration_frequency}")
        if slots.intensity:
            summary_parts.append(f"✓ Intensidade: {slots.intensity}")
        if slots.measures_taken:
            summary_parts.append(f"✓ Medidas tomadas: {slots.measures_taken}")
        if slots.health_history:
            summary_parts.append(f"✓ Histórico de saúde: {slots.health_history}")
        
        summary = "\n".join(summary_parts)
        
        completion_message = f"""🎉 **Triagem Concluída com Sucesso!**

Registrei todas as suas informações:

{summary}

✅ **Próximos passos:**
• Um profissional da nossa clínica analisará seu caso
• Você receberá retorno em breve
• Suas informações estão seguras e organizadas

💙 Obrigada pela colaboração! Desejamos sua melhora!

📞 *Em caso de emergência, ligue 192 ou procure o pronto-socorro mais próximo.*"""

        return completion_message

# ================================
# FASTAPI APPLICATION
# ================================

app = FastAPI(title="ClinicAI WhatsApp", version="1.0.0")

# Instâncias globais
db = TriageDatabase()
whatsapp_client = WhatsAppClient()
triage_processor = TriageProcessor(db, whatsapp_client, GEMINI_API_KEY)

@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0-whatsapp",
        "database": "SQLite (temporary)",
        "features": ["WhatsApp", "Emergency Detection", "Basic Triage"]
    }

@app.get("/webhook/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    """Verificação do webhook WhatsApp."""
    logger.info(f"Webhook verification: mode={hub_mode}, token={hub_verify_token[:10]}...")
    
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("✅ Webhook verification successful!")
        return PlainTextResponse(content=hub_challenge)
    else:
        logger.warning("❌ Webhook verification failed!")
        raise HTTPException(status_code=403, detail="Forbidden")

@app.post("/webhook/whatsapp")
async def handle_whatsapp_webhook(request: Request, payload: IncomingWhatsAppPayload):
    """Handler para mensagens do WhatsApp."""
    try:
        logger.info("📱 Received WhatsApp webhook")
        
        # Parse da mensagem
        parsed_message = whatsapp_client.parse_incoming_message(payload.model_dump())
        
        if not parsed_message:
            logger.info("No valid message in payload")
            return {"status": "ok"}
        
        # Processar através do sistema de triagem
        result = await triage_processor.process_message(
            phone=parsed_message["from_phone"],
            message_text=parsed_message["text"],
            message_id=parsed_message["message_id"]
        )
        
        logger.info(f"Message processed: {result}")
        return {"status": "ok", "message_id": parsed_message["message_id"]}
        
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/triages/{phone_hash}")
async def get_triage_info(phone_hash: str):
    """Busca informações de triagem."""
    triage = db.get_triage(phone_hash)
    if not triage:
        raise HTTPException(status_code=404, detail="Triage not found")
    
    return {
        "phone_hash": phone_hash,
        "status": triage["status"],
        "emergency_flag": bool(triage["emergency_flag"]),
        "slots": json.loads(triage["slots_json"]) if triage["slots_json"] else {},
        "created_at": triage["created_at"],
        "updated_at": triage["updated_at"]
    }

@app.get("/")
async def root():
    """Página inicial com informações de configuração."""
    return {
        "name": "ClinicAI WhatsApp Integration",
        "version": "1.0.0",
        "status": "running",
        "database": "SQLite (temporary)",
        "webhook_config": {
            "url": "https://YOUR-NGROK.ngrok-free.app/webhook/whatsapp",
            "verify_token": WHATSAPP_VERIFY_TOKEN,
            "note": "Configure este URL no Meta for Developers"
        },
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "webhook": "/webhook/whatsapp",
            "triages": "/triages/{phone_hash}"
        }
    }

# ================================
# MAIN
# ================================

if __name__ == "__main__":
    print("🏥 ClinicAI - WhatsApp Integration")
    print("=" * 50)
    print("📡 Servidor: http://localhost:8080")
    print("📚 Docs: http://localhost:8080/docs")
    print("❤️  Health: http://localhost:8080/health")
    print()
    print("🔧 Configurações:")
    print(f"   Phone ID: {WHATSAPP_PHONE_NUMBER_ID}")
    print(f"   Access Token: {WHATSAPP_ACCESS_TOKEN[:10]}...{WHATSAPP_ACCESS_TOKEN[-5:] if len(WHATSAPP_ACCESS_TOKEN) > 15 else WHATSAPP_ACCESS_TOKEN}")
    print(f"   Verify Token: {WHATSAPP_VERIFY_TOKEN}")
    print()
    print("🎯 Configure no Meta for Developers:")
    print(f"   URL: https://YOUR-NGROK.ngrok-free.app/webhook/whatsapp")
    print(f"   Token: {WHATSAPP_VERIFY_TOKEN}")
    print()
    print("📱 Funcionalidades:")
    print("   ✅ Webhook WhatsApp")
    print("   ✅ Detecção de emergência")
    print("   ✅ Triagem básica")
    print("   ✅ SQLite (temporário)")
    print("   🔄 MongoDB (próximo passo)")
    
    # Avisos se usando credenciais fake
    if WHATSAPP_ACCESS_TOKEN == "fake_token" or WHATSAPP_PHONE_NUMBER_ID == "fake_id":
        print()
        print("⚠️  ATENÇÃO: Usando credenciais fake!")
        print("   Configure suas credenciais reais no arquivo .env")
        print("   Caso contrário, receberá erro 401 ao enviar mensagens")
    else:
        print()
        print("✅ Credenciais reais configuradas!")
    
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8080)
