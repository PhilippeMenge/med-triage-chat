#!/usr/bin/env python3
"""
Script para executar ClinicAI em modo desenvolvimento.
"""

import uvicorn
import os

# Configurações mínimas para desenvolvimento
os.environ.setdefault("GEMINI_API_KEY", "fake_key_for_testing")
os.environ.setdefault("WHATSAPP_ACCESS_TOKEN", "fake_token")
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "fake_id")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "test_verify_token")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")

if __name__ == "__main__":
    print("🏥 Iniciando ClinicAI em modo desenvolvimento...")
    print("📡 Servidor: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("❤️  Health: http://localhost:8000/health")
    print("\n⚠️  AVISO: Usando configurações de desenvolvimento!")
    print("   Configure suas chaves reais no arquivo .env\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
