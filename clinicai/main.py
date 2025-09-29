#!/usr/bin/env python3
"""
ClinicAI MongoDB - Versão Corrigida
Baseado no clinicai_whatsapp.py funcionando, mas com MongoDB
"""

import os
import json
import hashlib
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import uvicorn
import httpx
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
# MongoTriageDatabase está definida neste arquivo

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

# MongoDB
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "clinicai_db")

# Log das configurações carregadas
logger.info("🔧 Configurações carregadas:")
logger.info(f"   Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID}")
logger.info(f"   Access Token: {WHATSAPP_ACCESS_TOKEN[:10]}...{WHATSAPP_ACCESS_TOKEN[-5:] if len(WHATSAPP_ACCESS_TOKEN) > 15 else WHATSAPP_ACCESS_TOKEN}")
logger.info(f"   Verify Token: {WHATSAPP_VERIFY_TOKEN}")
logger.info(f"   MongoDB URI: {'✅ Configurado' if MONGODB_URI else '❌ Não configurado'}")

# ================================
# MONGODB SETUP
# ================================

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    MONGODB_AVAILABLE = True
    logger.info("✅ Motor (MongoDB driver) disponível")
except ImportError:
    MONGODB_AVAILABLE = False
    logger.warning("❌ Motor não disponível - usando fallback")

# Cliente MongoDB global
mongo_client = None
mongo_db = None

async def connect_mongodb():
    """Conecta ao MongoDB."""
    global mongo_client, mongo_db
    
    if not MONGODB_AVAILABLE or not MONGODB_URI:
        logger.warning("⚠️ MongoDB não configurado")
        return False
    
    try:
        mongo_client = AsyncIOMotorClient(MONGODB_URI)
        mongo_db = mongo_client[MONGODB_DB]
        
        # Testar conexão
        await mongo_client.admin.command('ping')
        logger.info(f"✅ MongoDB conectado: {MONGODB_DB}")
        
        # Criar índices básicos
        await mongo_db.messages.create_index("phone_hash")
        await mongo_db.triages.create_index("phone_hash")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro MongoDB: {e}")
        return False

async def disconnect_mongodb():
    """Desconecta do MongoDB."""
    global mongo_client
    if mongo_client:
        mongo_client.close()
        logger.info("🍃 MongoDB desconectado")

# ================================
# MODELOS DE DADOS
# ================================

class IncomingWhatsAppPayload(BaseModel):
    object: str
    entry: List[Dict[str, Any]]

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
# BANCO DE DADOS MONGODB
# ================================

class MongoTriageDatabase:
    """Banco de dados MongoDB para triagens."""
    
    async def save_message(self, phone_hash: str, direction: str, message_id: str, 
                          text: str, meta: Dict = None) -> bool:
        """Salva mensagem no MongoDB."""
        if mongo_db is None:
            logger.warning("⚠️ MongoDB não conectado")
            return False
        
        try:
            document = {
                "phone_hash": phone_hash,
                "direction": direction,
                "message_id": message_id,
                "text": text,
                "timestamp": datetime.now(),
                "meta": meta or {}
            }
            
            result = await mongo_db.messages.insert_one(document)
            logger.info(f"💾 Mensagem MongoDB: {message_id} ({direction})")
            return bool(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar mensagem: {e}")
            return False
    
    async def get_messages(self, phone_hash: str, limit: int = 20) -> List[Dict]:
        """Busca mensagens de um usuário."""
        if mongo_db is None:
            logger.warning("⚠️ MongoDB não conectado")
            return []
        
        try:
            cursor = mongo_db.messages.find(
                {"phone_hash": phone_hash}
            ).sort("timestamp", -1).limit(limit)
            
            messages = await cursor.to_list(length=limit)
            
            # Converter ObjectId para string e timestamps
            for msg in messages:
                msg["_id"] = str(msg["_id"])
                if isinstance(msg.get("timestamp"), datetime):
                    msg["timestamp"] = msg["timestamp"].isoformat()
            
            return messages
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar mensagens: {e}")
            return []
    
    async def get_messages_since(self, phone_hash: str, since_timestamp: datetime, limit: int = 50) -> List[Dict]:
        """Busca mensagens do MongoDB a partir de um timestamp específico."""
        if mongo_db is None:
            logger.warning("⚠️ MongoDB não conectado")
            return []
        
        try:
            # Garantir que since_timestamp seja datetime
            if isinstance(since_timestamp, str):
                since_timestamp = datetime.fromisoformat(since_timestamp.replace('Z', '+00:00'))
            
            cursor = mongo_db.messages.find({
                "phone_hash": phone_hash,
                "timestamp": {"$gte": since_timestamp}
            }).sort("timestamp", -1).limit(limit)
            
            messages = await cursor.to_list(length=limit)
            
            # Converter ObjectId para string e timestamps
            for msg in messages:
                msg["_id"] = str(msg["_id"])
                if isinstance(msg.get("timestamp"), datetime):
                    msg["timestamp"] = msg["timestamp"].isoformat()
            
            logger.info(f"📊 Encontradas {len(messages)} mensagens desde {since_timestamp} para {phone_hash[:8]}...")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar mensagens desde timestamp: {e}")
            return []
    
    async def create_or_update_triage(self, phone_hash: str, slots: TriageSlots = None, 
                                    status: str = "open", emergency_flag: bool = False,
                                    last_activity: str = None, completed_at: str = None) -> bool:
        """Cria ou atualiza triagem no MongoDB."""
        if mongo_db is None:
            logger.warning("⚠️ MongoDB não conectado")
            return False
        
        try:
            update_data = {
                "status": status,
                "emergency_flag": emergency_flag,
                "last_activity": datetime.fromisoformat(last_activity) if last_activity else datetime.now()
            }
            
            if slots:
                update_data["slots"] = slots.model_dump()
            
            if completed_at:
                update_data["completed_at"] = datetime.fromisoformat(completed_at)
            
            result = await mongo_db.triages.update_one(
                {"phone_hash": phone_hash, "status": {"$ne": "completed"}},
                {
                    "$set": update_data,
                    "$setOnInsert": {
                        "phone_hash": phone_hash,
                        "created_at": datetime.now()
                    }
                },
                upsert=True
            )
            
            action = "criada" if result.upserted_id else "atualizada"
            logger.info(f"💾 Triagem MongoDB {action}: {phone_hash[:8]}... ({status})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar triagem: {e}")
            return False
    
    async def get_active_triage(self, phone_hash: str) -> Optional[Dict]:
        """Busca triagem ativa no MongoDB."""
        if mongo_db is None:
            return None
        
        try:
            triage = await mongo_db.triages.find_one({
                "phone_hash": phone_hash,
                "status": {"$nin": ["completed", "timeout"]}
            })
            
            if triage:
                # Converter datas para string
                for field in ["created_at", "last_activity", "completed_at"]:
                    if triage.get(field):
                        triage[field] = triage[field].isoformat()
            
            return triage
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar triagem: {e}")
            return None
    
    async def get_triage_slots(self, phone_hash: str) -> TriageSlots:
        """Busca slots de triagem do MongoDB."""
        triage = await self.get_active_triage(phone_hash)
        
        if triage and triage.get("slots"):
            try:
                return TriageSlots(**triage["slots"])
            except Exception as e:
                logger.error(f"❌ Erro ao carregar slots: {e}")
        
        return TriageSlots()

# ================================
# UTILITÁRIOS
# ================================

def extract_phone_from_whatsapp(whatsapp_phone: str) -> str:
    """Extrai número limpo do formato WhatsApp."""
    return ''.join(filter(str.isdigit, whatsapp_phone))

def hash_phone_number(phone: str) -> str:
    """Gera hash do número de telefone."""
    return hashlib.sha256(f"{phone}{PHONE_HASH_SALT}".encode()).hexdigest()

# ================================
# WHATSAPP CLIENT
# ================================

class WhatsAppClient:
    """Cliente para envio de mensagens WhatsApp."""
    
    @staticmethod
    def parse_incoming_message(payload: Dict) -> Optional[Dict]:
        """Parse de mensagem recebida."""
        try:
            if not payload.get("entry"):
                return None
            
            entry = payload["entry"][0]
            changes = entry.get("changes", [])
            
            if not changes:
                return None
            
            change = changes[0]
            if change.get("field") != "messages":
                return None
            
            value = change.get("value", {})
            messages = value.get("messages", [])
            
            if not messages:
                return None
            
            message = messages[0]
            
            return {
                "from": message.get("from"),
                "id": message.get("id"),
                "text": message.get("text", {}).get("body", ""),
                "timestamp": message.get("timestamp")
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao fazer parse da mensagem: {e}")
            return None
    
    @staticmethod
    async def send_text_message(to: str, text: str) -> Optional[str]:
        """Envia mensagem de texto via WhatsApp."""
        if WHATSAPP_ACCESS_TOKEN == "fake_token":
            logger.warning(f"⚠️ WhatsApp fake mode: {text[:50]}...")
            return f"fake_msg_{datetime.now().timestamp()}"
        
        try:
            url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
            
            headers = {
                "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            
            data = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text}
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers, timeout=10.0)
                
                if response.status_code == 200:
                    result = response.json()
                    message_id = result.get("messages", [{}])[0].get("id")
                    logger.info(f"✅ WhatsApp enviado: {message_id}")
                    return message_id
                else:
                    logger.error(f"❌ WhatsApp API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Erro ao enviar WhatsApp: {e}")
            return None

# ================================
# GEMINI INTEGRATION
# ================================

class GeminiTriageAgent:
    """Agente Gemini para triagem conversacional natural."""
    
    def __init__(self):
        self.client = None
        if GEMINI_API_KEY and GEMINI_API_KEY != "fake_key_for_testing":
            try:
                import google.generativeai as genai
                genai.configure(api_key=GEMINI_API_KEY)
                self.client = genai.GenerativeModel("gemini-2.5-pro")
                logger.info("✅ Gemini configurado")
            except Exception as e:
                logger.error(f"❌ Erro Gemini: {e}")
    
    def _get_system_prompt(self) -> str:
        """Retorna o prompt do sistema para o agente de triagem."""
        return """Você é um assistente virtual de triagem. Sua missão é conduzir uma conversa acolhedora e empática para coletar informações que ajudem a agilizar o atendimento médico do usuário.

PERSONA E COMPORTAMENTO:
- Seja acolhedor, empático, calmo e profissional
- Use linguagem clara, simples e direta
- Seja humanizado mas profissional
- Guie o usuário de forma paciente
- Faça-o se sentir seguro para compartilhar informações

MISSÃO - COLETAR ESTAS 6 INFORMAÇÕES:
1. Queixa Principal: O motivo central do contato
2. Sintomas Detalhados: Descrição de tudo que está sentindo
3. Duração e Frequência: Desde quando começou e frequência
4. Intensidade: Escala de dor/desconforto (0 a 10)
5. Histórico Relevante: Condições pré-existentes ou episódios anteriores
6. Medidas Tomadas: O que já fez para aliviar os sintomas

IMPORTANTE:
- Você só coleta informações, não dá conselhos
- Seja apenas um organizador de dados
- Mantenha conversa focada na coleta
- Não interprete nem analise nada

CASOS URGENTES:
Se mencionar "peito", "respiração difícil", "desmaio" ou "sangramento", diga:
"Sua situação parece necessitar atenção imediata. Procure o pronto-socorro ou ligue 192."

SEMPRE RESPONDA EM JSON:
{
  "message": "sua resposta empática aqui",
  "collected_info": {
    "chief_complaint": "valor ou null",
    "symptoms": "valor ou null", 
    "duration_frequency": "valor ou null",
    "intensity": "valor ou null",
    "history": "valor ou null",
    "measures_taken": "valor ou null"
  },
  "is_emergency": false,
  "is_complete": false,
  "next_focus": "próximo dado ou null"
}"""

    async def process_conversation(self, user_message: str, current_slots: TriageSlots, conversation_history: List[str] = None) -> Dict[str, Any]:
        """Processa conversa e coleta informações de triagem."""
        if not self.client:
            # Fallback sem Gemini
            return self._fallback_response(user_message, current_slots, conversation_history)
        
        try:
            # Construir contexto da conversa
            history_text = ""
            if conversation_history:
                history_text = "\n".join(conversation_history[-6:])  # Últimas 6 mensagens
            
            # Informações já coletadas
            collected_info = {
                "chief_complaint": current_slots.chief_complaint,
                "symptoms": current_slots.symptoms,
                "duration_frequency": current_slots.duration_frequency,
                "intensity": current_slots.intensity,
                "history": current_slots.health_history,
                "measures_taken": current_slots.measures_taken
            }
            
            # Verificar se é início da conversa
            is_conversation_start = user_message == "[INÍCIO DA CONVERSA]"
            
            if is_conversation_start:
                user_prompt = f"""
CONTEXTO DA CONVERSA:
{history_text}

SITUAÇÃO: Este é o INÍCIO de uma nova triagem. O usuário acabou de receber a mensagem de boas-vindas.

INSTRUÇÕES:
1. Faça a primeira pergunta para iniciar a coleta de informações
2. Comece perguntando sobre a queixa principal de forma acolhedora
3. Seja empático e profissional
4. Retorne no formato JSON especificado

IMPORTANTE: Esta é a PRIMEIRA pergunta da triagem. Seja acolhedor e direto.
"""
            else:
                user_prompt = f"""
CONTEXTO DA CONVERSA:
{history_text}

INFORMAÇÕES JÁ COLETADAS:
{json.dumps(collected_info, indent=2, ensure_ascii=False)}

NOVA MENSAGEM DO USUÁRIO:
"{user_message}"

INSTRUÇÕES:
1. Analise a mensagem do usuário no contexto da conversa
2. Extraia/atualize informações relevantes para os 6 tópicos da triagem
3. Detecte sinais de emergência
4. Responda de forma empática e natural
5. Se necessário, faça uma pergunta para coletar informação faltante
6. Retorne no formato JSON especificado

Se todas as 6 informações estiverem coletadas, marque "is_complete": true e faça um resumo acolhedor.
"""

            import asyncio
            
            # Configurações de segurança mais permissivas (apenas categorias válidas)
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
            
            # Configurações de geração otimizadas
            generation_config = {
                "temperature": 0.3,  # Mais determinístico
                "max_output_tokens": 400,
                "top_p": 0.8,
                "top_k": 40,
                "candidate_count": 1
            }
            
            response = await asyncio.to_thread(
                self.client.generate_content,
                f"{self._get_system_prompt()}\n\n{user_prompt}",
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            # Verificar se a resposta foi bloqueada
            if not response.candidates or not response.candidates[0].content.parts:
                logger.warning("⚠️ Resposta Gemini bloqueada por filtro de segurança")
                return self._fallback_response(user_message, current_slots, conversation_history)
            
            # Parse do JSON
            response_text = response.text.strip()
            
            # Limpar possíveis caracteres extras do JSON
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()
            
            try:
                result = json.loads(response_text)
                logger.info(f"🤖 Gemini processou conversa: {'emergência' if result.get('is_emergency') else 'normal'}")
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Erro JSON Gemini: {e}")
                logger.error(f"📄 Resposta raw: {response_text}")
                return self._fallback_response(user_message, current_slots, conversation_history)
            
        except Exception as e:
            logger.error(f"❌ Erro processamento Gemini: {e}")
            return self._fallback_response(user_message, current_slots, conversation_history)
    
    def _fallback_response(self, user_message: str, current_slots: TriageSlots, conversation_history: List[str] = None) -> Dict[str, Any]:
        """Resposta fallback quando Gemini não está disponível."""
        # Detectar emergência básica
        emergency_detected = is_emergency(user_message)
        
        if emergency_detected:
            return {
                "message": "Entendi. Seus sintomas podem indicar uma situação de emergência. Por favor, procure o pronto-socorro mais próximo ou ligue para o 192 imediatamente.",
                "collected_info": current_slots.model_dump(),
                "is_emergency": True,
                "is_complete": False,
                "next_focus": None
            }
        
        # Verificar se já foi feita a primeira pergunta no histórico
        conversation_history = conversation_history or []
        first_question_already_asked = any(
            "motivo do seu contato" in msg.lower() or "qual a sua queixa" in msg.lower() 
            for msg in conversation_history
        )
        
        # Lógica simples para próxima pergunta
        next_slot = current_slots.get_next_slot_to_collect()
        
        if next_slot == "chief_complaint":
            if first_question_already_asked:
                # Se primeira pergunta já foi feita, assumir que usuário está respondendo
                message = "Entendi. Agora pode me descrever com mais detalhes tudo o que você está sentindo?"
                # Atualizar slots com a resposta do usuário
                updated_slots = current_slots.model_dump()
                updated_slots["chief_complaint"] = user_message.strip()
                # Avançar para próximo slot
                next_slot = "symptoms"
            else:
                message = "Para começarmos, pode me contar qual é o motivo do seu contato hoje?"
                updated_slots = current_slots.model_dump()
        elif next_slot == "symptoms":
            message = "Entendi. Agora pode me descrever com mais detalhes tudo o que você está sentindo?"
            updated_slots = current_slots.model_dump()
            updated_slots[next_slot] = user_message.strip()
        elif next_slot == "duration_frequency":
            message = "Obrigada por compartilhar. Desde quando você está sentindo isso e com que frequência acontece?"
            updated_slots = current_slots.model_dump()
            updated_slots[next_slot] = user_message.strip()
        elif next_slot == "intensity":
            message = "Compreendo. Em uma escala de 0 a 10, onde 0 é sem dor e 10 é uma dor insuportável, como você classificaria a intensidade?"
            updated_slots = current_slots.model_dump()
            updated_slots[next_slot] = user_message.strip()
        elif next_slot == "measures_taken":
            message = "Entendo. Você já tentou fazer alguma coisa para aliviar esses sintomas?"
            updated_slots = current_slots.model_dump()
            updated_slots[next_slot] = user_message.strip()
        elif next_slot == "health_history":
            message = "Por último, você tem algum histórico de saúde que considera relevante compartilhar?"
            updated_slots = current_slots.model_dump()
            updated_slots[next_slot] = user_message.strip()
        else:
            message = "Obrigada por todas as informações. Um profissional analisará seu caso e você receberá retorno em breve."
            updated_slots = current_slots.model_dump()
        
        return {
            "message": message,
            "collected_info": updated_slots,
            "is_emergency": False,
            "is_complete": next_slot is None,
            "next_focus": next_slot
        }

# ================================
# CONVERSATION HELPER
# ================================

def get_welcome_message() -> str:
    """Mensagem de boas-vindas inicial."""
    return """🏥 *Olá! Sou seu assistente virtual e vou ajudar a organizar suas informações para agilizar seu atendimento."""

# ================================
# EMERGENCY DETECTION
# ================================

EMERGENCY_KEYWORDS = [
    "dor no peito", "dor forte no peito", "peito doendo", "infarto", "ataque cardiaco",
    "falta de ar", "dificuldade respirar", "não consigo respirar", "sufocando",
    "desmaiei", "vou desmaiar", "convulsão", "avc", "derrame", "paralisia",
    "muito sangue", "hemorragia", "sangrando muito",
    "desmaiou", "inconsciente", "perdeu consciência",
    "emergência", "urgente", "hospital", "ambulancia", "192"
]

def is_emergency(text: str) -> bool:
    """Detecta emergências."""
    text_lower = text.lower()
    for keyword in EMERGENCY_KEYWORDS:
        if keyword in text_lower:
            logger.warning(f"🚨 Emergência detectada: {keyword}")
            return True
    return False

def get_emergency_response() -> str:
    """Resposta para emergências."""
    return """🚨 **ATENÇÃO - SITUAÇÃO DE EMERGÊNCIA DETECTADA**

Sua situação parece ser urgente. Por favor:

🆘 **LIGUE IMEDIATAMENTE:**
• **192** - SAMU (Emergência Médica)
• **193** - Bombeiros
• Vá ao **Pronto Socorro** mais próximo

⚠️ **IMPORTANTE:** Não espere! Em emergências, cada minuto conta.

💙 Este é um assistente virtual e não substitui atendimento médico urgente."""

# ================================
# PROCESSADOR PRINCIPAL
# ================================

class TriageProcessor:
    """Processador principal de triagem conversacional."""
    
    def __init__(self):
        self.db = MongoTriageDatabase()
        self.gemini = GeminiTriageAgent()
        self.conversation_histories = {}
        self.TIMEOUT_MINUTES = 30
    
    def _check_timeout(self, last_activity: datetime) -> bool:
        """Verifica timeout."""
        now = datetime.now()
        time_diff = now - last_activity
        return time_diff.total_seconds() > (self.TIMEOUT_MINUTES * 60)
    
    async def _load_conversation_history(self, phone_hash: str):
        """Carrega histórico apenas da triagem atual do MongoDB."""
        try:
            # Buscar triagem ativa para obter created_at
            current_triage = await self.db.get_active_triage(phone_hash)
            if not current_triage:
                self.conversation_histories[phone_hash] = []
                return
            
            triage_start = current_triage.get('created_at')
            if not triage_start:
                # Fallback para últimas mensagens se não tiver created_at
                messages = await self.db.get_messages(phone_hash, limit=10)
                logger.info(f"📚 Usando fallback: últimas 10 mensagens para {phone_hash[:8]}...")
            else:
                # Buscar mensagens apenas a partir do início da triagem atual
                messages = await self.db.get_messages_since(phone_hash, triage_start, limit=30)
                logger.info(f"📚 Carregando mensagens desde {triage_start} para {phone_hash[:8]}...")
            
            # Reconstruir histórico em ordem cronológica
            history = []
            for msg in reversed(messages):  # Reverter para ordem cronológica
                direction = msg.get("direction", "in")
                text = msg.get("text", "")
                
                if direction == "in":
                    history.append(f"Usuário: {text}")
                elif direction == "out":
                    history.append(f"ClinicAI: {text}")
            
            # Atualizar histórico na memória
            self.conversation_histories[phone_hash] = history
            
            logger.info(f"📚 Histórico da triagem atual carregado: {phone_hash[:8]}... ({len(history)} mensagens)")
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar histórico da triagem: {e}")
            # Manter histórico vazio em caso de erro
            self.conversation_histories[phone_hash] = []
    
    async def process_message(self, phone: str, message_text: str, message_id: str = None) -> Dict[str, Any]:
        """Processa mensagem com conversa natural Gemini."""
        try:
            # Normalizar telefone
            normalized_phone = extract_phone_from_whatsapp(phone)
            phone_hash = hash_phone_number(normalized_phone)
            
            logger.info(f"💬 Conversando: {phone_hash[:8]}... - '{message_text[:30]}...'")
            
            # Inicializar histórico se não existir
            if phone_hash not in self.conversation_histories:
                self.conversation_histories[phone_hash] = []
            
            # Buscar triagem ativa
            current_triage = await self.db.get_active_triage(phone_hash)
            
            # Verificar timeout e carregar histórico se há triagem ativa
            if current_triage:
                last_activity_str = current_triage.get('last_activity')
                if last_activity_str:
                    try:
                        last_activity = datetime.fromisoformat(last_activity_str)
                        if self._check_timeout(last_activity):
                            logger.info(f"⏰ Timeout detectado: {phone_hash[:8]}...")
                            await self.db.create_or_update_triage(
                                phone_hash=phone_hash,
                                status="timeout",
                                completed_at=datetime.now().isoformat()
                            )
                            # Limpar histórico
                            self.conversation_histories[phone_hash] = []
                            current_triage = None
                        else:
                            # Carregar histórico completo do MongoDB se triagem ativa
                            await self._load_conversation_history(phone_hash)
                    except:
                        pass
            
            # Se não há triagem ativa - iniciar nova
            if not current_triage:
                await self.db.create_or_update_triage(
                    phone_hash=phone_hash,
                    status="open",
                    last_activity=datetime.now().isoformat()
                )
                
                # Enviar mensagem de boas-vindas
                welcome_message = get_welcome_message()
                
                message_id = await WhatsAppClient.send_text_message(normalized_phone, welcome_message)
                
                if message_id:
                    await self.db.save_message(
                        phone_hash=phone_hash,
                        direction="out",
                        message_id=message_id,
                        text=welcome_message
                    )
                
                # Limpar e inicializar histórico
                self.conversation_histories[phone_hash] = []
                self.conversation_histories[phone_hash].append(f"ClinicAI: {welcome_message}")
                
                # Agora fazer Gemini gerar a primeira pergunta
                logger.info(f"🤖 Gerando primeira pergunta com Gemini...")
                current_slots = TriageSlots()
                
                first_question_result = await self.gemini.process_conversation(
                    user_message="[INÍCIO DA CONVERSA]",
                    current_slots=current_slots,
                    conversation_history=self.conversation_histories[phone_hash]
                )
                
                # Enviar primeira pergunta do Gemini
                first_question = first_question_result["message"]
                question_message_id = await WhatsAppClient.send_text_message(normalized_phone, first_question)
                
                # SEMPRE salvar a primeira pergunta, mesmo se WhatsApp falhar
                await self.db.save_message(
                    phone_hash=phone_hash,
                    direction="out",
                    message_id=question_message_id or f"out_{datetime.now().timestamp()}",
                    text=first_question
                )
                self.conversation_histories[phone_hash].append(f"ClinicAI: {first_question}")
                
                logger.info(f"✅ Primeira pergunta enviada e registrada: '{first_question[:50]}...'")
                
                return {
                    "success": True,
                    "action": "welcome_and_first_question_sent", 
                    "phone_hash": phone_hash
                }
            
            # Adicionar mensagem do usuário ao histórico
            self.conversation_histories[phone_hash].append(f"Usuário: {message_text}")
            
            # Salvar mensagem recebida
            await self.db.save_message(
                phone_hash=phone_hash,
                direction="in",
                message_id=message_id or f"in_{datetime.now().timestamp()}",
                text=message_text,
                meta={"source": "whatsapp"}
            )
            
            # Buscar slots atuais
            current_slots = await self.db.get_triage_slots(phone_hash)
            
            # Processar conversa com Gemini
            logger.info(f"🤖 Enviando para Gemini: '{message_text[:50]}...'")
            conversation_result = await self.gemini.process_conversation(
                user_message=message_text,
                current_slots=current_slots,
                conversation_history=self.conversation_histories[phone_hash]
            )
            
            # Verificar se é emergência
            if conversation_result.get("is_emergency", False):
                logger.warning(f"🚨 Emergência detectada: {phone_hash[:8]}...")
                
                await self.db.create_or_update_triage(
                    phone_hash=phone_hash,
                    status="emergency",
                    emergency_flag=True,
                    last_activity=datetime.now().isoformat()
                )
                
                emergency_message = conversation_result["message"]
                message_id = await WhatsAppClient.send_text_message(normalized_phone, emergency_message)
                
                if message_id:
                    await self.db.save_message(
                        phone_hash=phone_hash,
                        direction="out",
                        message_id=message_id,
                        text=emergency_message
                    )
                    self.conversation_histories[phone_hash].append(f"ClinicAI: {emergency_message}")
                
                return {
                    "success": True,
                    "status": "emergency",
                    "emergency": True,
                    "response_sent": bool(message_id)
                }
            
            # Atualizar slots com informações coletadas
            collected_info = conversation_result.get("collected_info", {})
            updated_slots = TriageSlots(**collected_info)
            
            # Salvar slots atualizados
            current_time = datetime.now().isoformat()
            status = "completed" if conversation_result.get("is_complete", False) else "open"
            completed_at = current_time if status == "completed" else None
            
            await self.db.create_or_update_triage(
                phone_hash=phone_hash,
                slots=updated_slots,
                status=status,
                last_activity=current_time,
                completed_at=completed_at
            )
            
            # Enviar resposta do Gemini
            response_message = conversation_result["message"]
            message_id = await WhatsAppClient.send_text_message(normalized_phone, response_message)
            
            if message_id:
                await self.db.save_message(
                    phone_hash=phone_hash,
                    direction="out",
                    message_id=message_id,
                    text=response_message
                )
                self.conversation_histories[phone_hash].append(f"ClinicAI: {response_message}")
                
                # Manter histórico limitado
                if len(self.conversation_histories[phone_hash]) > 12:
                    self.conversation_histories[phone_hash] = self.conversation_histories[phone_hash][-8:]
            
            # Log do progresso
            slots_filled = sum(1 for v in updated_slots.model_dump().values() if v is not None)
            logger.info(f"📊 Progresso triagem: {slots_filled}/6 slots coletados")
            
            if status == "completed":
                logger.info(f"🎉 Triagem completa: {phone_hash[:8]}...")
            
            return {
                "success": True,
                "status": status,
                "emergency": False,
                "response_sent": bool(message_id),
                "phone_hash": phone_hash,
                "slots_filled": slots_filled,
                "next_focus": conversation_result.get("next_focus"),
                "is_complete": conversation_result.get("is_complete", False)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro processamento conversa: {e}")
            import traceback
            logger.error(f"🔍 Traceback: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}
    
    async def _get_completion_message(self, slots: TriageSlots) -> str:
        """Mensagem de finalização."""
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
        
        return f"""🎉 **Triagem Concluída com Sucesso!**

Registrei todas as suas informações:

{summary}

✅ **Próximos passos:**
• Um profissional da nossa clínica analisará seu caso
• Você receberá retorno em breve
• Suas informações estão seguras e organizadas

💙 Obrigada pela colaboração! Desejamos sua melhora!

📞 *Em caso de emergência, ligue 192 ou procure o pronto-socorro mais próximo.*"""

# ================================
# FASTAPI APPLICATION
# ================================

app = FastAPI(title="ClinicAI MongoDB", version="2.0.0")

# Instâncias globais
triage_processor = TriageProcessor()

@app.on_event("startup")
async def startup_event():
    """Startup da aplicação."""
    logger.info("🚀 Iniciando ClinicAI MongoDB...")
    
    # Conectar MongoDB
    mongodb_connected = await connect_mongodb()
    
    if mongodb_connected:
        logger.info("✅ ClinicAI MongoDB pronto!")
    else:
        logger.warning("⚠️ ClinicAI iniciado sem MongoDB (modo fallback)")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown da aplicação."""
    logger.info("🔽 Finalizando ClinicAI...")
    await disconnect_mongodb()

@app.get("/health")
async def health_check():
    """Health check."""
    mongodb_status = mongo_db is not None
    
    stats = {"messages": 0, "triages": 0}
    if mongo_db is not None:
        try:
            stats["messages"] = await mongo_db.messages.count_documents({})
            stats["triages"] = await mongo_db.triages.count_documents({})
        except:
            pass
    
    return {
        "status": "healthy",
        "database": "mongodb" if mongodb_status else "none",
        "connected": mongodb_status,
        "stats": stats,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/webhook/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    """Verificação webhook WhatsApp."""
    logger.info(f"📋 Verificação webhook: {hub_verify_token[:10]}...")
    
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("✅ Webhook verificado!")
        return PlainTextResponse(content=hub_challenge)
    else:
        logger.warning("❌ Webhook verificação falhou!")
        raise HTTPException(status_code=403, detail="Forbidden")

@app.post("/webhook/whatsapp")
async def handle_whatsapp_webhook(request: Request, payload: IncomingWhatsAppPayload):
    """Handler webhook WhatsApp."""
    try:
        logger.info("📱 Webhook recebido")
        
        # Parse mensagem
        parsed_message = WhatsAppClient.parse_incoming_message(payload.model_dump())
        
        if not parsed_message:
            logger.info("📭 Nenhuma mensagem válida")
            return {"status": "ok"}
        
        logger.info(f"💬 De: {parsed_message['from'][:8]}... - '{parsed_message['text'][:30]}...'")
        
        # Processar mensagem
        result = await triage_processor.process_message(
            phone=parsed_message["from"],
            message_text=parsed_message["text"],
            message_id=parsed_message["id"]
        )
        
        logger.info(f"🎯 Processado: {result.get('success', False)} - {result.get('status', 'unknown')}")
        
        return {"status": "processed", "result": result}
        
    except Exception as e:
        logger.error(f"❌ Erro webhook: {e}")
        return {"status": "error", "message": str(e)}

# ================================
# MAIN
# ================================

if __name__ == "__main__":
    print("=" * 60)
    print("🏥 CLINICAI MONGODB - SISTEMA DE TRIAGEM")
    print("=" * 60)
    print("🚀 Versão: MongoDB 2.0.0 (Corrigida)")
    print("🌐 Servidor: http://localhost:8080")
    print("🍃 Database: MongoDB Atlas")
    print("📱 WhatsApp: /webhook/whatsapp")
    print("🔍 Health: /health")
    print("📋 Docs: /docs")
    print("=" * 60)
    print("🔧 Configurações:")
    print(f"   📱 WhatsApp: {'✅' if WHATSAPP_ACCESS_TOKEN != 'fake_token' else '❌'}")
    print(f"   🔑 Gemini: {'✅' if GEMINI_API_KEY != 'fake_key_for_testing' else '❌'}")
    print(f"   🍃 MongoDB: {'✅' if MONGODB_URI else '❌'}")
    print("=" * 60)
    
    if WHATSAPP_ACCESS_TOKEN == "fake_token":
        print("⚠️ ATENÇÃO: Usando credenciais fake!")
        print("   Configure .env com credenciais reais")
    
    print("🚀 Iniciando servidor...")
    
    uvicorn.run(app, host="0.0.0.0", port=8080)
