#!/usr/bin/env python3
"""
Debug da aplicação ClinicAI para identificar problemas.
"""

import sys
import traceback

print("🔍 ClinicAI Debug Mode")
print("=" * 40)

try:
    print("📦 Testando imports...")
    
    import os
    print("✅ os")
    
    import json
    print("✅ json")
    
    import sqlite3
    print("✅ sqlite3")
    
    import hashlib
    print("✅ hashlib")
    
    import asyncio
    print("✅ asyncio")
    
    import logging
    print("✅ logging")
    
    from datetime import datetime
    print("✅ datetime")
    
    from typing import Optional, Dict, Any, List
    print("✅ typing")
    
    from pathlib import Path
    print("✅ pathlib")
    
    import uvicorn
    print("✅ uvicorn")
    
    import httpx
    print("✅ httpx")
    
    from fastapi import FastAPI, HTTPException, Request, Query
    print("✅ fastapi")
    
    from fastapi.responses import PlainTextResponse, JSONResponse
    print("✅ fastapi.responses")
    
    from pydantic import BaseModel, Field
    print("✅ pydantic")
    
    print("\n🚀 Testando aplicação básica...")
    
    # Criar app mínima
    app = FastAPI(title="ClinicAI Debug")
    
    @app.get("/")
    def root():
        return {"status": "debug_ok", "message": "App funcionando"}
    
    @app.get("/health")
    def health():
        return {"status": "ok", "debug": True}
    
    print("✅ App FastAPI criada")
    
    print("\n🌐 Iniciando servidor debug na porta 8081...")
    print("📡 Teste em: http://localhost:8081")
    print("❤️  Health: http://localhost:8081/health")
    print("⚠️  Pressione Ctrl+C para parar")
    
    uvicorn.run(app, host="0.0.0.0", port=8081, log_level="debug")
    
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    print("\n🔍 Detalhes do erro:")
    traceback.print_exc()
    
    print(f"\n📊 Informações do sistema:")
    print(f"   Python: {sys.version}")
    print(f"   Plataforma: {sys.platform}")
    
    print(f"\n💡 Possíveis soluções:")
    print(f"   1. Reinstale dependências: pip install -r requirements.txt")
    print(f"   2. Verifique se não há conflitos de porta")
    print(f"   3. Execute como administrador se necessário")
