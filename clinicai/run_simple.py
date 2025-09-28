#!/usr/bin/env python3
"""
Versão simplificada do ClinicAI para testar webhooks sem MongoDB.
"""

import os
import uvicorn
from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from datetime import datetime

# Configurar variáveis básicas
os.environ.setdefault("GEMINI_API_KEY", "fake_key")
os.environ.setdefault("WHATSAPP_ACCESS_TOKEN", "fake_token") 
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "fake_id")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "ClinicAI_Test_Token_123")

app = FastAPI(title="ClinicAI - Teste Simples")

@app.get("/health")
async def health():
    """Health check simples."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0-simple",
        "message": "ClinicAI rodando sem MongoDB para teste"
    }

@app.get("/webhook/whatsapp")
async def verify_webhook(
    request: Request,
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    """Verificação do webhook WhatsApp."""
    print(f"🔍 Verificação webhook:")
    print(f"   Mode: {hub_mode}")
    print(f"   Token recebido: {hub_verify_token}")
    print(f"   Token esperado: ClinicAI_Test_Token_123")
    print(f"   Challenge: {hub_challenge}")
    
    if hub_mode == "subscribe" and hub_verify_token == "ClinicAI_Test_Token_123":
        print("✅ Verificação bem-sucedida!")
        return PlainTextResponse(content=hub_challenge)
    else:
        print("❌ Verificação falhou!")
        return JSONResponse(status_code=403, content={"error": "Forbidden"})

@app.post("/webhook/whatsapp")
async def handle_webhook(request: Request):
    """Handler simples para mensagens."""
    try:
        payload = await request.json()
        print(f"📱 Mensagem recebida:")
        print(f"   Payload: {payload}")
        
        # Simular processamento
        return {"status": "ok", "message": "Processado com sucesso (modo teste)"}
    except Exception as e:
        print(f"❌ Erro: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    """Página inicial."""
    return {
        "name": "ClinicAI - Modo Teste Simples",
        "version": "0.1.0-simple",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "webhook_verify": "/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=ClinicAI_Test_Token_123&hub.challenge=test",
            "webhook_post": "/webhook/whatsapp"
        },
        "webhook_config": {
            "url": "https://SEU-NGROK.ngrok-free.app/webhook/whatsapp",
            "verify_token": "ClinicAI_Test_Token_123"
        }
    }

if __name__ == "__main__":
    print("🏥 ClinicAI - Modo Teste Simples")
    print("="*50)
    print("📡 Servidor: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("❤️  Health: http://localhost:8000/health")
    print("🔍 Teste webhook: http://localhost:8000/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=ClinicAI_Test_Token_123&hub.challenge=test")
    print()
    print("🎯 URLs para Meta for Developers:")
    print("   Webhook URL: https://SEU-NGROK.ngrok-free.app/webhook/whatsapp")
    print("   Verify Token: ClinicAI_Test_Token_123")
    print("="*50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
