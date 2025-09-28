#!/usr/bin/env python3
"""
Teste simples para verificar as dependências.
"""

import os
import sys

print("🏥 ClinicAI - Teste de Dependências")
print("=" * 40)

# Teste 1: Python
print(f"✅ Python: {sys.version}")

# Teste 2: Dependências básicas
try:
    import fastapi
    print(f"✅ FastAPI: {fastapi.__version__}")
except ImportError as e:
    print(f"❌ FastAPI: {e}")

try:
    import uvicorn
    print(f"✅ Uvicorn: {uvicorn.__version__}")
except ImportError as e:
    print(f"❌ Uvicorn: {e}")

try:
    import httpx
    print(f"✅ HTTPX: {httpx.__version__}")
except ImportError as e:
    print(f"❌ HTTPX: {e}")

try:
    import pydantic
    print(f"✅ Pydantic: {pydantic.__version__}")
except ImportError as e:
    print(f"❌ Pydantic: {e}")

try:
    import sqlite3
    print(f"✅ SQLite3: {sqlite3.sqlite_version}")
except ImportError as e:
    print(f"❌ SQLite3: {e}")

# Teste 3: Aplicação básica
print("\n🚀 Testando FastAPI básica...")

try:
    from fastapi import FastAPI
    
    app = FastAPI()
    
    @app.get("/")
    def root():
        return {"message": "Hello World"}
    
    print("✅ FastAPI app criada com sucesso")
    
    # Teste de execução
    import uvicorn
    print("🌐 Iniciando servidor de teste...")
    print("📡 Acesse: http://localhost:8001")
    print("⚠️  Pressione Ctrl+C para parar")
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
    
except Exception as e:
    print(f"❌ Erro na aplicação: {e}")
    import traceback
    traceback.print_exc()
