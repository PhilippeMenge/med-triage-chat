#!/usr/bin/env python3
"""
ClinicAI - Aplicação principal com MongoDB
Versão adaptada para usar MongoDB Atlas
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Importar classes MongoDB
from mongodb_database import MongoTriageDatabase, TriageSlots, extract_phone_from_whatsapp, hash_phone_number

# Carregar variáveis de ambiente
load_dotenv()

# ================================
# CONFIGURAÇÃO E LOGGING
# ================================

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("clinicai_mongodb")

# Configurações
PORT = int(os.getenv("PORT", 8080))
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

logger.info("🔧 Configurações carregadas:")
logger.info(f"   Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID}")
logger.info(f"   Access Token: {WHATSAPP_ACCESS_TOKEN[:12]}..." if WHATSAPP_ACCESS_TOKEN else "   Access Token: não configurado")
logger.info(f"   Verify Token: {WHATSAPP_VERIFY_TOKEN}")

# ================================
# MODELOS PYDANTIC
# ================================

class IncomingWhatsAppPayload(BaseModel):
    object: str
    entry: List[Dict[str, Any]]

class OutgoingWhatsAppMessage(BaseModel):
    messaging_product: str = "whatsapp"
    to: str
    type: str = "text"
    text: Dict[str, str]

# ================================
# CLASSES PRINCIPAIS
# ================================

class WhatsAppClient:
    """Cliente para API do WhatsApp."""
    
    def __init__(self):
        self.access_token = WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = WHATSAPP_PHONE_NUMBER_ID
        self.base_url = f"https://graph.facebook.com/v20.0/{self.phone_number_id}"
    
    def parse_incoming_message(self, payload: Dict) -> Optional[Dict]:
        """Parse de mensagem recebida do WhatsApp."""
        try:
            if not payload.get("entry"):
                return None
            
            entry = payload["entry"][0]
            if not entry.get("changes"):
                return None
            
            change = entry["changes"][0]
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
    
    async def send_text_message(self, to: str, text: str) -> Optional[str]:
        """Envia mensagem de texto via WhatsApp."""
        if not self.access_token:
            logger.warning("⚠️ WhatsApp Access Token não configurado")
            return None
        
        try:
            logger.info(f"Sending WhatsApp message to {to[:8]}...")
            
            message = OutgoingWhatsAppMessage(
                to=to,
                text={"body": text}
            )
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url}/messages"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=message.model_dump(),
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    message_id = result.get("messages", [{}])[0].get("id")
                    logger.info(f"✅ WhatsApp message sent: {message_id}")
                    return message_id
                else:
                    logger.error(f"WhatsApp API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Erro ao enviar mensagem WhatsApp: {e}")
            return None
    
    async def send_text(self, to: str, text: str) -> Optional[str]:
        """Alias para send_text_message (compatibilidade)."""
        return await self.send_text_message(to, text)

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

# ================================
# DETECÇÃO DE EMERGÊNCIA
# ================================

EMERGENCY_KEYWORDS = [
    # Dor severa
    "dor no peito", "dor forte no peito", "peito doendo", "infarto", "ataque cardiaco",
    
    # Respiração
    "falta de ar", "dificuldade respirar", "não consigo respirar", "sufocando",
    
    # Neurológico
    "desmaiei", "vou desmaiar", "convulsão", "avc", "derrame", "paralisia",
    
    # Sangramento
    "muito sangue", "hemorragia", "sangrando muito",
    
    # Consciência
    "desmaiou", "inconsciente", "perdeu consciência",
    
    # Outros
    "emergência", "urgente", "hospital", "ambulancia", "192"
]

def is_emergency(text: str) -> bool:
    """Detecta situações de emergência no texto."""
    text_lower = text.lower()
    for keyword in EMERGENCY_KEYWORDS:
        if keyword in text_lower:
            logger.warning(f"Emergency keyword detected: {keyword}")
            return True
    return False

def get_emergency_response() -> str:
    """Retorna resposta padrão para emergências."""
    return """🚨 **ATENÇÃO - SITUAÇÃO DE EMERGÊNCIA DETECTADA**

Sua situação parece ser urgente. Por favor:

🆘 **LIGUE IMEDIATAMENTE:**
• **192** - SAMU (Emergência Médica)
• **193** - Bombeiros
• Vá ao **Pronto Socorro** mais próximo

⚠️ **IMPORTANTE:** Não espere! Em emergências, cada minuto conta.

💙 Este é um assistente virtual e não substitui atendimento médico urgente."""

class TriageProcessor:
    """Processador de triagem com MongoDB e Gemini."""
    
    # Constantes
    TIMEOUT_MINUTES = 30  # Timeout de 30 minutos
    
    def __init__(self, db: MongoTriageDatabase, whatsapp: WhatsAppClient, gemini_api_key: str):
        self.db = db
        self.whatsapp = whatsapp
        self.gemini = GeminiProcessor(gemini_api_key)
        self.question_manager = QuestionManager()
        self.conversation_histories = {}  # Cache de histórico por phone_hash
    
    def _check_timeout(self, last_activity: datetime) -> bool:
        """Verifica se houve timeout na conversa."""
        now = datetime.now()
        time_diff = now - last_activity
        return time_diff.total_seconds() > (self.TIMEOUT_MINUTES * 60)
    
    async def process_message(self, phone: str, message_text: str, message_id: str = None) -> Dict[str, Any]:
        """Processa mensagem de triagem com MongoDB e Gemini."""
        try:
            # Normalizar telefone e criar hash
            normalized_phone = extract_phone_from_whatsapp(phone)
            phone_hash = hash_phone_number(normalized_phone)
            
            logger.info(f"Processing message for phone_hash: {phone_hash[:8]}...")
            
            # Conectar ao banco se necessário
            if not self.db.connected:
                await self.db.connect()
            
            # Buscar triagem ativa
            current_triage = await self.db.get_active_triage(phone_hash)
            
            # Verificar timeout se há triagem ativa
            if current_triage:
                last_activity_str = current_triage.get('last_activity')
                if last_activity_str:
                    try:
                        last_activity = datetime.fromisoformat(last_activity_str)
                        if self._check_timeout(last_activity):
                            logger.info(f"Timeout detected for phone_hash: {phone_hash[:8]}, resetting session")
                            # Marcar triagem como timeout
                            await self.db.create_or_update_triage(
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
                await self.db.create_or_update_triage(
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
            await self.db.save_message(
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
                await self.db.create_or_update_triage(
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
                    await self.db.save_message(
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
            
            # Buscar slots atuais
            current_slots = await self.db.get_triage_slots_async(phone_hash)
            
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
                    await self.db.create_or_update_triage(
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
                        await self.db.create_or_update_triage(
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
                await self.db.save_message(
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
            await self.whatsapp.send_text_message(normalized_phone, 
                "Desculpe, houve um erro ao processar sua mensagem. Por favor, tente novamente."
            )
            return {"success": False, "error": str(e)}
    
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

app = FastAPI(title="ClinicAI - MongoDB", version="2.0.0")

# Instanciar componentes
mongo_db = MongoTriageDatabase()
whatsapp_client = WhatsAppClient()
triage_processor = TriageProcessor(mongo_db, whatsapp_client, GEMINI_API_KEY)

@app.on_event("startup")
async def startup_event():
    """Inicialização da aplicação."""
    logger.info("🚀 Iniciando ClinicAI MongoDB...")
    logger.info("🔧 Configurações:")
    logger.info(f"   📊 Database: {mongo_db.mongodb_db}")
    logger.info(f"   🌐 Cluster: MongoDB Atlas")
    logger.info(f"   🔑 Gemini: {'✅ Configurado' if GEMINI_API_KEY else '❌ Não configurado'}")
    logger.info(f"   📱 WhatsApp: {'✅ Configurado' if WHATSAPP_ACCESS_TOKEN else '❌ Não configurado'}")
    
    await mongo_db.connect()
    stats = await mongo_db.get_stats()
    logger.info(f"📊 Estatísticas MongoDB:")
    logger.info(f"   📨 Mensagens: {stats['messages']}")
    logger.info(f"   🏥 Triagens: {stats['triages']}")
    logger.info(f"   🔄 Triagens ativas: {stats['active_triages']}")
    logger.info("✅ ClinicAI MongoDB pronto!")

@app.on_event("shutdown")
async def shutdown_event():
    """Finalização da aplicação."""
    logger.info("🔽 Finalizando ClinicAI MongoDB...")
    await mongo_db.disconnect()

@app.get("/health")
async def health_check():
    """Health check da aplicação."""
    logger.info("🩺 Health check solicitado")
    
    try:
        stats = await mongo_db.get_stats()
        
        health_data = {
            "status": "healthy",
            "database": "mongodb",
            "connected": mongo_db.connected,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("✅ Health check OK:")
        logger.info(f"   🍃 MongoDB: {'✅ Conectado' if mongo_db.connected else '❌ Desconectado'}")
        logger.info(f"   📊 Mensagens: {stats['messages']}")
        logger.info(f"   🏥 Triagens: {stats['triages']}")
        logger.info(f"   🔄 Ativas: {stats['active_triages']}")
        
        return health_data
        
    except Exception as e:
        logger.error(f"❌ Erro no health check: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
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
        logger.debug(f"📦 Payload: {payload.model_dump()}")
        
        # Parse da mensagem
        parsed_message = whatsapp_client.parse_incoming_message(payload.model_dump())
        
        if not parsed_message:
            logger.info("📭 No valid message in payload")
            return {"status": "ok"}
        
        logger.info(f"📨 Mensagem recebida:")
        logger.info(f"   👤 De: {parsed_message['from'][:8]}...")
        logger.info(f"   💬 Texto: '{parsed_message['text'][:50]}...'")
        logger.info(f"   🆔 ID: {parsed_message['id']}")
        
        # Processar mensagem
        result = await triage_processor.process_message(
            phone=parsed_message["from"],
            message_text=parsed_message["text"],
            message_id=parsed_message["id"]
        )
        
        logger.info(f"🎯 Resultado processamento:")
        logger.info(f"   ✅ Sucesso: {result.get('success', False)}")
        logger.info(f"   📊 Status: {result.get('status', 'unknown')}")
        logger.info(f"   🚨 Emergência: {result.get('emergency', False)}")
        logger.info(f"   📤 Resposta enviada: {result.get('response_sent', False)}")
        
        if 'slots_filled' in result:
            logger.info(f"   📝 Slots preenchidos: {result['slots_filled']}/6")
        
        return {"status": "processed", "result": result}
        
    except Exception as e:
        logger.error(f"❌ Error handling webhook: {e}")
        import traceback
        logger.error(f"🔍 Traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}

@app.get("/triages/{phone_hash}")
async def get_user_triages(phone_hash: str):
    """Busca triagens de um usuário."""
    logger.info(f"📋 Buscando triagens para: {phone_hash[:8]}...")
    
    try:
        triages = await mongo_db.get_user_triages(phone_hash)
        
        logger.info(f"📊 Triagens encontradas:")
        logger.info(f"   👤 Usuário: {phone_hash[:8]}...")
        logger.info(f"   📋 Total: {len(triages)}")
        
        for i, triage in enumerate(triages[:3]):  # Log apenas as 3 mais recentes
            status = triage.get('status', 'unknown')
            created = triage.get('created_at', 'unknown')[:10] if triage.get('created_at') else 'unknown'
            logger.info(f"   {i+1}. Status: {status}, Criada: {created}")
        
        return {
            "phone_hash": phone_hash,
            "triages": triages,
            "count": len(triages)
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar triagens: {e}")
        import traceback
        logger.error(f"🔍 Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# ================================
# MAIN
# ================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("="*60)
    logger.info("🏥 CLINICAI - SISTEMA DE TRIAGEM MÉDICA")
    logger.info("="*60)
    logger.info(f"🚀 Versão: MongoDB 2.0.0")
    logger.info(f"🌐 Servidor: http://localhost:{PORT}")
    logger.info(f"🍃 Database: MongoDB Atlas")
    logger.info(f"📱 WhatsApp Webhook: http://localhost:{PORT}/webhook/whatsapp")
    logger.info(f"🔍 Health Check: http://localhost:{PORT}/health")
    logger.info(f"📋 API Docs: http://localhost:{PORT}/docs")
    logger.info("="*60)
    logger.info("🔧 Configurações:")
    logger.info(f"   🔑 Gemini API: {'✅ Configurado' if GEMINI_API_KEY else '❌ Não configurado'}")
    logger.info(f"   📱 WhatsApp: {'✅ Configurado' if WHATSAPP_ACCESS_TOKEN else '❌ Não configurado'}")
    logger.info(f"   📞 Phone ID: {WHATSAPP_PHONE_NUMBER_ID}")
    logger.info(f"   🔐 Verify Token: {WHATSAPP_VERIFY_TOKEN}")
    logger.info("="*60)
    logger.info("🚀 Iniciando servidor...")
    
    try:
        uvicorn.run(
            "clinicai_mongodb:app",
            host="0.0.0.0",
            port=PORT,
            reload=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("⏹️ Servidor interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar servidor: {e}")
    finally:
        logger.info("👋 ClinicAI finalizado")
