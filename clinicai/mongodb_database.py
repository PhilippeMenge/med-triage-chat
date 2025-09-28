#!/usr/bin/env python3
"""
Classe de banco de dados MongoDB para ClinicAI.
Substitui a implementação SQLite.
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logger = logging.getLogger(__name__)

class TriageSlots(BaseModel):
    """Slots de informações para triagem médica - ordem específica."""
    chief_complaint: Optional[str] = None      # 1. Qual a sua queixa?
    symptoms: Optional[str] = None             # 2. Pode descrever tudo que você está sentindo...
    duration_frequency: Optional[str] = None  # 3. Desde quando... e com que frequência...
    intensity: Optional[str] = None           # 4. Qual a intensidade da dor (0-10)...
    measures_taken: Optional[str] = None      # 5. Você já fez algo para aliviar...
    health_history: Optional[str] = None      # 6. Você tem algum histórico de saúde...
    
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

class MongoTriageDatabase:
    """Classe de banco de dados MongoDB para ClinicAI."""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.connected = False
        
        # Configuração MongoDB
        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.mongodb_db = os.getenv("MONGODB_DB", "clinicai_db")
        
        if not self.mongodb_uri:
            logger.error("MONGODB_URI não configurado no .env")
            raise ValueError("MONGODB_URI é obrigatório")
    
    async def connect(self):
        """Conecta ao MongoDB."""
        if self.connected:
            return
        
        try:
            logger.info(f"🍃 Conectando ao MongoDB: {self.mongodb_db}")
            self.client = AsyncIOMotorClient(self.mongodb_uri)
            self.db = self.client[self.mongodb_db]
            
            # Testar conexão
            await self.client.admin.command('ping')
            
            # Criar índices
            await self._create_indexes()
            
            self.connected = True
            logger.info("✅ MongoDB conectado com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar MongoDB: {e}")
            raise
    
    async def _create_indexes(self):
        """Cria índices necessários no MongoDB."""
        try:
            # Índice para phone_hash nas mensagens
            await self.db.messages.create_index("phone_hash")
            await self.db.messages.create_index("timestamp")
            
            # Índice para phone_hash nas triagens
            await self.db.triages.create_index("phone_hash")
            await self.db.triages.create_index("status")
            await self.db.triages.create_index("created_at")
            
            logger.info("✅ Índices MongoDB criados")
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao criar índices: {e}")
    
    async def disconnect(self):
        """Desconecta do MongoDB."""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("🍃 MongoDB desconectado")
    
    # ================================
    # OPERAÇÕES DE MENSAGENS
    # ================================
    
    async def save_message(self, phone_hash: str, direction: str, message_id: str, 
                          text: str, meta: Dict = None) -> bool:
        """Salva mensagem no MongoDB."""
        if not self.connected:
            await self.connect()
        
        try:
            document = {
                "phone_hash": phone_hash,
                "direction": direction,
                "message_id": message_id,
                "text": text,
                "timestamp": datetime.now(),
                "meta": meta or {}
            }
            
            result = await self.db.messages.insert_one(document)
            logger.info(f"💾 Mensagem salva:")
            logger.info(f"   📞 Hash: {phone_hash[:8]}...")
            logger.info(f"   ↔️ Direção: {direction}")
            logger.info(f"   💬 Texto: '{text[:30]}...'")
            logger.info(f"   🆔 ID: {message_id}")
            return bool(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar mensagem: {e}")
            logger.error(f"   📞 Hash: {phone_hash[:8]}...")
            logger.error(f"   ↔️ Direção: {direction}")
            return False
    
    async def get_messages(self, phone_hash: str, limit: int = 20) -> List[Dict]:
        """Busca mensagens de um usuário."""
        if not self.connected:
            await self.connect()
        
        try:
            cursor = self.db.messages.find(
                {"phone_hash": phone_hash}
            ).sort("timestamp", -1).limit(limit)
            
            messages = await cursor.to_list(length=limit)
            
            # Converter ObjectId para string
            for msg in messages:
                msg["_id"] = str(msg["_id"])
                if isinstance(msg.get("timestamp"), datetime):
                    msg["timestamp"] = msg["timestamp"].isoformat()
            
            return messages
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar mensagens: {e}")
            return []
    
    # ================================
    # OPERAÇÕES DE TRIAGEM
    # ================================
    
    async def create_or_update_triage(self, phone_hash: str, status: str = "open", 
                                    slots: TriageSlots = None, emergency_flag: bool = False,
                                    last_activity: str = None, completed_at: str = None) -> bool:
        """Cria ou atualiza triagem no MongoDB."""
        if not self.connected:
            await self.connect()
        
        try:
            # Dados para atualizar
            update_data = {
                "status": status,
                "emergency_flag": emergency_flag,
                "last_activity": datetime.fromisoformat(last_activity) if last_activity else datetime.now()
            }
            
            # Adicionar slots se fornecidos
            if slots:
                update_data["slots"] = slots.model_dump()
                filled_slots = sum(1 for v in slots.model_dump().values() if v is not None)
                logger.info(f"📝 Slots a salvar: {filled_slots}/6 preenchidos")
            
            # Adicionar completed_at se fornecido
            if completed_at:
                update_data["completed_at"] = datetime.fromisoformat(completed_at)
            
            # Upsert: criar se não existir, atualizar se existir
            result = await self.db.triages.update_one(
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
            logger.info(f"💾 Triagem {action}:")
            logger.info(f"   📞 Hash: {phone_hash[:8]}...")
            logger.info(f"   📊 Status: {status}")
            logger.info(f"   🚨 Emergência: {emergency_flag}")
            if completed_at:
                logger.info(f"   ✅ Finalizada: {completed_at[:19]}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar triagem: {e}")
            logger.error(f"   📞 Hash: {phone_hash[:8]}...")
            logger.error(f"   📊 Status: {status}")
            return False
    
    async def get_active_triage(self, phone_hash: str) -> Optional[Dict]:
        """Busca triagem ativa (não completada) de um usuário."""
        if not self.connected:
            await self.connect()
        
        try:
            triage = await self.db.triages.find_one({
                "phone_hash": phone_hash,
                "status": {"$nin": ["completed", "timeout"]}
            })
            
            if triage:
                # Converter ObjectId e datas
                triage["_id"] = str(triage["_id"])
                for date_field in ["created_at", "last_activity", "completed_at"]:
                    if triage.get(date_field) and isinstance(triage[date_field], datetime):
                        triage[date_field] = triage[date_field].isoformat()
            
            return triage
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar triagem ativa: {e}")
            return None
    
    async def get_triage(self, phone_hash: str) -> Optional[Dict]:
        """Busca triagem mais recente de um usuário."""
        if not self.connected:
            await self.connect()
        
        try:
            triage = await self.db.triages.find_one(
                {"phone_hash": phone_hash},
                sort=[("created_at", -1)]
            )
            
            if triage:
                # Converter ObjectId e datas
                triage["_id"] = str(triage["_id"])
                for date_field in ["created_at", "last_activity", "completed_at"]:
                    if triage.get(date_field) and isinstance(triage[date_field], datetime):
                        triage[date_field] = triage[date_field].isoformat()
            
            return triage
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar triagem: {e}")
            return None
    
    def get_triage_slots(self, phone_hash: str) -> TriageSlots:
        """Busca slots de triagem de um usuário (versão síncrona para compatibilidade)."""
        # Esta é uma versão simplificada para compatibilidade
        # Retorna slots vazios - deve ser chamada via get_triage_slots_async
        return TriageSlots()
    
    async def get_triage_slots_async(self, phone_hash: str) -> TriageSlots:
        """Busca slots de triagem de um usuário (versão assíncrona)."""
        triage = await self.get_active_triage(phone_hash)
        
        if triage and triage.get("slots"):
            try:
                return TriageSlots(**triage["slots"])
            except Exception as e:
                logger.error(f"❌ Erro ao carregar slots: {e}")
        
        return TriageSlots()
    
    async def get_user_triages(self, phone_hash: str) -> List[Dict]:
        """Busca todas as triagens de um usuário."""
        if not self.connected:
            await self.connect()
        
        try:
            cursor = self.db.triages.find(
                {"phone_hash": phone_hash}
            ).sort("created_at", -1)
            
            triages = await cursor.to_list(length=None)
            
            # Converter ObjectId e datas
            for triage in triages:
                triage["_id"] = str(triage["_id"])
                for date_field in ["created_at", "last_activity", "completed_at"]:
                    if triage.get(date_field) and isinstance(triage[date_field], datetime):
                        triage[date_field] = triage[date_field].isoformat()
            
            return triages
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar triagens do usuário: {e}")
            return []
    
    # ================================
    # MÉTODOS DE UTILIDADE
    # ================================
    
    async def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas do banco."""
        if not self.connected:
            await self.connect()
        
        try:
            messages_count = await self.db.messages.count_documents({})
            triages_count = await self.db.triages.count_documents({})
            active_triages = await self.db.triages.count_documents({"status": "open"})
            
            return {
                "messages": messages_count,
                "triages": triages_count,
                "active_triages": active_triages
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar estatísticas: {e}")
            return {"messages": 0, "triages": 0, "active_triages": 0}

# ================================
# FUNÇÕES DE COMPATIBILIDADE
# ================================

def extract_phone_from_whatsapp(whatsapp_phone: str) -> str:
    """Extrai número limpo do formato WhatsApp."""
    return ''.join(filter(str.isdigit, whatsapp_phone))

def hash_phone_number(phone: str) -> str:
    """Gera hash do número de telefone."""
    import hashlib
    salt = os.getenv("PHONE_HASH_SALT", "default_salt")
    return hashlib.sha256(f"{phone}{salt}".encode()).hexdigest()

# ================================
# INSTÂNCIA GLOBAL
# ================================

# Instância global para compatibilidade
_mongo_db_instance = None

def get_mongo_database() -> MongoTriageDatabase:
    """Retorna instância global do banco MongoDB."""
    global _mongo_db_instance
    if _mongo_db_instance is None:
        _mongo_db_instance = MongoTriageDatabase()
    return _mongo_db_instance
