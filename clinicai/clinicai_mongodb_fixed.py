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

class GeminiProcessor:
    """Processador Gemini para validação e reescrita."""
    
    def __init__(self):
        self.client = None
        if GEMINI_API_KEY and GEMINI_API_KEY != "fake_key_for_testing":
            try:
                import google.generativeai as genai
                genai.configure(api_key=GEMINI_API_KEY)
                self.client = genai.GenerativeModel("gemini-flash-latest")
                logger.info("✅ Gemini configurado")
            except Exception as e:
                logger.error(f"❌ Erro Gemini: {e}")
    
    async def validate_response(self, user_text: str, question: str, target_slot: str) -> bool:
        """Valida se resposta é adequada."""
        if not self.client:
            return True
        
        try:
            prompt = f"""
Pergunta: "{question}"
Resposta: "{user_text}"

A resposta responde adequadamente à pergunta?
Responda apenas "SIM" ou "NAO".
"""
            
            import asyncio
            response = await asyncio.to_thread(
                self.client.generate_content,
                prompt,
                generation_config={"temperature": 0.1, "max_output_tokens": 10}
            )
            
            validation = response.text.strip().upper()
            is_valid = "SIM" in validation
            logger.info(f"🤖 Gemini validação {target_slot}: {'✅' if is_valid else '❌'}")
            return is_valid
            
        except Exception as e:
            logger.error(f"❌ Erro validação: {e}")
            return True
    
    async def rewrite_question(self, original_question: str, target_slot: str) -> str:
        """Reescreve pergunta."""
        if not self.client:
            return f"Vou perguntar de outro jeito: {original_question}"
        
        try:
            prompt = f"""
Pergunta original: "{original_question}"

Reescreva de forma diferente mantendo o mesmo objetivo.
Máximo 20 palavras.
"""
            
            import asyncio
            response = await asyncio.to_thread(
                self.client.generate_content,
                prompt,
                generation_config={"temperature": 0.7, "max_output_tokens": 50}
            )
            
            rewritten = response.text.strip()
            logger.info(f"🤖 Gemini reescreveu {target_slot}")
            return rewritten
            
        except Exception as e:
            logger.error(f"❌ Erro reescrita: {e}")
            return f"Vou perguntar de outro jeito: {original_question}"

# ================================
# QUESTION MANAGER
# ================================

class QuestionManager:
    """Gerenciador de perguntas específicas."""
    
    QUESTIONS = {
        "chief_complaint": "Qual a sua queixa?",
        "symptoms": "Pode descrever tudo que você está sentindo de maneira detalhada, por favor?",
        "duration_frequency": "Desde quando os sintomas começaram e com que frequência ocorrem?",
        "intensity": "Qual a intensidade da dor em uma escala de 0 a 10? Sendo 0 sem dor e 10 uma dor insuportável.",
        "measures_taken": "Você já fez algo para tentar aliviar os sintomas?",
        "health_history": "Você tem algum histórico de saúde relevante?"
    }
    
    @classmethod
    def get_question(cls, slot: str) -> str:
        return cls.QUESTIONS.get(slot, "Pode me fornecer mais informações?")

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
    """Processador principal de triagem."""
    
    def __init__(self):
        self.db = MongoTriageDatabase()
        self.gemini = GeminiProcessor()
        self.question_manager = QuestionManager()
        self.conversation_histories = {}
        self.TIMEOUT_MINUTES = 30
    
    def _check_timeout(self, last_activity: datetime) -> bool:
        """Verifica timeout."""
        now = datetime.now()
        time_diff = now - last_activity
        return time_diff.total_seconds() > (self.TIMEOUT_MINUTES * 60)
    
    async def process_message(self, phone: str, message_text: str, message_id: str = None) -> Dict[str, Any]:
        """Processa mensagem principal."""
        try:
            # Normalizar telefone
            normalized_phone = extract_phone_from_whatsapp(phone)
            phone_hash = hash_phone_number(normalized_phone)
            
            logger.info(f"📱 Processando: {phone_hash[:8]}... - '{message_text[:30]}...'")
            
            # Buscar triagem ativa
            current_triage = await self.db.get_active_triage(phone_hash)
            
            # Verificar timeout
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
                            current_triage = None
                    except:
                        pass
            
            # Se não há triagem ativa - iniciar nova
            if not current_triage:
                await self.db.create_or_update_triage(
                    phone_hash=phone_hash,
                    status="open",
                    last_activity=datetime.now().isoformat()
                )
                
                # Enviar introdução + primeira pergunta
                intro_message = (
                    "🏥 *Olá! Sou a ClinicAI*\n\n"
                    "Sou seu assistente virtual e vou ajudar a organizar suas informações para agilizar seu atendimento.\n\n"
                    "⚠️ *Importante:* Sou um assistente virtual e não substituo uma avaliação médica.\n\n"
                    "Para começarmos, qual é a sua queixa?"
                )
                
                message_id = await WhatsAppClient.send_text_message(normalized_phone, intro_message)
                
                if message_id:
                    await self.db.save_message(
                        phone_hash=phone_hash,
                        direction="out",
                        message_id=message_id,
                        text=intro_message
                    )
                
                return {
                    "success": True,
                    "action": "first_question_sent", 
                    "phone_hash": phone_hash
                }
            
            # Salvar mensagem recebida
            await self.db.save_message(
                phone_hash=phone_hash,
                direction="in",
                message_id=message_id or f"in_{datetime.now().timestamp()}",
                text=message_text,
                meta={"source": "whatsapp"}
            )
            
            # Verificar emergência
            if is_emergency(message_text):
                logger.warning(f"🚨 Emergência: {phone_hash[:8]}...")
                
                await self.db.create_or_update_triage(
                    phone_hash=phone_hash,
                    status="emergency",
                    emergency_flag=True,
                    last_activity=datetime.now().isoformat()
                )
                
                emergency_response = get_emergency_response()
                message_id = await WhatsAppClient.send_text_message(normalized_phone, emergency_response)
                
                if message_id:
                    await self.db.save_message(
                        phone_hash=phone_hash,
                        direction="out",
                        message_id=message_id,
                        text=emergency_response
                    )
                
                return {
                    "success": True,
                    "status": "emergency",
                    "emergency": True,
                    "response_sent": bool(message_id)
                }
            
            # Buscar slots atuais
            current_slots = await self.db.get_triage_slots(phone_hash)
            current_slot = current_slots.get_next_slot_to_collect()
            
            if current_slot:
                # Obter pergunta
                current_question = self.question_manager.get_question(current_slot)
                
                # Validar resposta
                logger.info(f"🔍 Validando {current_slot}: '{message_text[:30]}...'")
                is_valid_response = await self.gemini.validate_response(
                    user_text=message_text,
                    question=current_question,
                    target_slot=current_slot
                )
                
                if is_valid_response:
                    # Resposta válida - salvar e avançar
                    setattr(current_slots, current_slot, message_text.strip())
                    logger.info(f"✅ Coletado {current_slot}")
                    
                    await self.db.create_or_update_triage(
                        phone_hash=phone_hash,
                        slots=current_slots,
                        status="open",
                        last_activity=datetime.now().isoformat()
                    )
                    
                    # Verificar se completo
                    next_slot = current_slots.get_next_slot_to_collect()
                    if next_slot:
                        response_text = self.question_manager.get_question(next_slot)
                    else:
                        # Triagem completa
                        response_text = await self._get_completion_message(current_slots)
                        await self.db.create_or_update_triage(
                            phone_hash=phone_hash,
                            slots=current_slots,
                            status="completed",
                            last_activity=datetime.now().isoformat(),
                            completed_at=datetime.now().isoformat()
                        )
                        logger.info(f"🎉 Triagem completa: {phone_hash[:8]}...")
                else:
                    # Resposta inválida - reescrever
                    logger.info(f"❌ Resposta inválida {current_slot}")
                    response_text = await self.gemini.rewrite_question(
                        original_question=current_question,
                        target_slot=current_slot
                    )
            else:
                # Triagem já completa
                response_text = (
                    "🏥 *Olá! Sou a ClinicAI*\n\n"
                    "Vejo que você já concluiu uma triagem recente. Para um novo atendimento, "
                    "qual é o motivo principal do seu contato hoje?"
                )
            
            # Enviar resposta
            message_id = await WhatsAppClient.send_text_message(normalized_phone, response_text)
            
            if message_id:
                await self.db.save_message(
                    phone_hash=phone_hash,
                    direction="out",
                    message_id=message_id,
                    text=response_text
                )
            
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
            logger.error(f"❌ Erro processamento: {e}")
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
