#!/usr/bin/env python3
"""
Health check simples para verificar se a aplicação está configurada corretamente.
"""

import os
import sys
from dotenv import load_dotenv

def check_environment():
    """Verifica se as variáveis de ambiente estão configuradas."""
    load_dotenv()
    
    required_vars = [
        'MONGODB_URI',
        'MONGODB_DB', 
        'GEMINI_API_KEY',
        'WHATSAPP_ACCESS_TOKEN',
        'WHATSAPP_PHONE_NUMBER_ID',
        'WHATSAPP_VERIFY_TOKEN'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Variáveis de ambiente faltando: {', '.join(missing)}")
        return False
    else:
        print("✅ Todas as variáveis de ambiente configuradas")
        return True

def check_dependencies():
    """Verifica se as dependências estão instaladas."""
    try:
        import fastapi
        import uvicorn
        import motor
        import google.generativeai
        import pymongo
        print("✅ Todas as dependências instaladas")
        return True
    except ImportError as e:
        print(f"❌ Dependência faltando: {e}")
        return False

def main():
    """Executa verificação completa."""
    print("🔍 VERIFICAÇÃO DE SAÚDE DA APLICAÇÃO")
    print("=" * 50)
    
    checks = [
        ("Variáveis de ambiente", check_environment),
        ("Dependências Python", check_dependencies)
    ]
    
    all_good = True
    for name, check_func in checks:
        print(f"\n📋 Verificando: {name}")
        if not check_func():
            all_good = False
    
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 APLICAÇÃO PRONTA PARA EXECUÇÃO!")
        print("\n🚀 Para iniciar:")
        print("   python main.py")
    else:
        print("❌ CONFIGURAÇÃO INCOMPLETA")
        print("\n🔧 Configure o arquivo .env e instale dependências:")
        print("   pip install -r requirements.txt")
        sys.exit(1)

if __name__ == "__main__":
    main()
