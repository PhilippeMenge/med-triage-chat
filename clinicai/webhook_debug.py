#!/usr/bin/env python3
"""
Debug específico para webhooks WhatsApp.
"""

import json
import logging
import os
from datetime import datetime
from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse
import uvicorn
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
load_dotenv()

# Configurar logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="WhatsApp Webhook Debug", version="1.0.0")

# Configurações carregadas do .env
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "ClinicAI_Test_Token_123")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "fake_token")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "fake_id")

# Log das configurações (sem mostrar tokens completos)
logger.info(f"🔧 Configurações carregadas:")
logger.info(f"   Phone ID: {PHONE_NUMBER_ID}")
logger.info(f"   Access Token: {ACCESS_TOKEN[:10]}...{ACCESS_TOKEN[-5:] if len(ACCESS_TOKEN) > 15 else ACCESS_TOKEN}")
logger.info(f"   Verify Token: {VERIFY_TOKEN}")

@app.get("/")
async def root():
    """Página inicial com informações."""
    return {
        "name": "WhatsApp Webhook Debug",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "health": "/health",
            "webhook_get": "/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=ClinicAI_Test_Token_123&hub.challenge=test",
            "docs": "/docs"
        },
        "config": {
            "verify_token": VERIFY_TOKEN,
            "webhook_url": "https://YOUR-NGROK.ngrok-free.app/webhook/whatsapp"
        }
    }

@app.get("/health")
async def health():
    """Health check detalhado."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "app": "webhook_debug",
        "ready_for_webhook": True
    }

@app.get("/webhook/whatsapp")
async def verify_webhook(
    request: Request,
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    """Verificação do webhook WhatsApp com logs detalhados."""
    
    # Log todos os parâmetros recebidos
    logger.info("=" * 60)
    logger.info("🔍 WEBHOOK VERIFICATION REQUEST")
    logger.info("=" * 60)
    logger.info(f"URL: {request.url}")
    logger.info(f"Method: {request.method}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Query Params: {dict(request.query_params)}")
    logger.info("-" * 40)
    logger.info(f"hub.mode: '{hub_mode}'")
    logger.info(f"hub.verify_token: '{hub_verify_token}'")
    logger.info(f"hub.challenge: '{hub_challenge}'")
    logger.info(f"Expected token: '{VERIFY_TOKEN}'")
    logger.info("-" * 40)
    
    # Verificação
    if hub_mode == "subscribe":
        logger.info("✅ Mode is 'subscribe' - OK")
        
        if hub_verify_token == VERIFY_TOKEN:
            logger.info("✅ Token matches - VERIFICATION SUCCESSFUL!")
            logger.info(f"📤 Returning challenge: '{hub_challenge}'")
            logger.info("=" * 60)
            
            return PlainTextResponse(content=hub_challenge, status_code=200)
        else:
            logger.error(f"❌ Token mismatch!")
            logger.error(f"   Received: '{hub_verify_token}'")
            logger.error(f"   Expected: '{VERIFY_TOKEN}'")
            logger.info("=" * 60)
            
            return PlainTextResponse(content="Forbidden - Invalid token", status_code=403)
    else:
        logger.error(f"❌ Invalid mode: '{hub_mode}' (expected 'subscribe')")
        logger.info("=" * 60)
        
        return PlainTextResponse(content="Bad Request - Invalid mode", status_code=400)

@app.post("/webhook/whatsapp")
async def handle_webhook(request: Request):
    """Handler para mensagens WhatsApp com logs detalhados."""
    
    try:
        # Pegar o body raw
        body = await request.body()
        
        # Log da requisição
        logger.info("=" * 60)
        logger.info("📱 WHATSAPP MESSAGE RECEIVED")
        logger.info("=" * 60)
        logger.info(f"URL: {request.url}")
        logger.info(f"Method: {request.method}")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Body size: {len(body)} bytes")
        logger.info("-" * 40)
        
        # Parse JSON
        try:
            payload = json.loads(body.decode('utf-8'))
            logger.info("📋 Payload JSON:")
            logger.info(json.dumps(payload, indent=2))
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            logger.error(f"Raw body: {body}")
            return {"status": "error", "message": "Invalid JSON"}
        
        # Extrair informações básicas
        logger.info("-" * 40)
        logger.info("🔍 Extracted info:")
        
        try:
            entry = payload.get("entry", [])
            if entry:
                changes = entry[0].get("changes", [])
                if changes:
                    value = changes[0].get("value", {})
                    messages = value.get("messages", [])
                    
                    if messages:
                        message = messages[0]
                        logger.info(f"📞 From: {message.get('from', 'unknown')}")
                        logger.info(f"🆔 Message ID: {message.get('id', 'unknown')}")
                        logger.info(f"📝 Type: {message.get('type', 'unknown')}")
                        
                        if message.get('type') == 'text':
                            text_content = message.get('text', {}).get('body', '')
                            logger.info(f"💬 Text: '{text_content}'")
                            
                            # Simular processamento
                            logger.info("🔄 Processing message...")
                            logger.info("✅ Message processed successfully!")
                        else:
                            logger.info("ℹ️  Non-text message - ignoring")
                    else:
                        logger.info("ℹ️  No messages in payload")
                else:
                    logger.info("ℹ️  No changes in payload")
            else:
                logger.info("ℹ️  No entry in payload")
                
        except Exception as e:
            logger.error(f"❌ Error extracting info: {e}")
        
        logger.info("=" * 60)
        
        return {
            "status": "ok", 
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Webhook received and logged"
        }
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ WEBHOOK ERROR")
        logger.error("=" * 60)
        logger.error(f"Error: {e}")
        logger.error("=" * 60)
        
        return {
            "status": "error", 
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    print("🔍 WhatsApp Webhook Debug Server")
    print("=" * 50)
    print("📡 Servidor: http://localhost:8080")
    print("📚 Docs: http://localhost:8080/docs")
    print("❤️  Health: http://localhost:8080/health")
    print()
    print("🎯 Configure no Meta for Developers:")
    print("   URL: https://YOUR-NGROK.ngrok-free.app/webhook/whatsapp")
    print("   Token: ClinicAI_Test_Token_123")
    print()
    print("📋 Este servidor vai logar TUDO que receber!")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="debug")
