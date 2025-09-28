#!/usr/bin/env python3
"""
Setup script para ClinicAI - configura o ambiente automaticamente.
"""

import os
import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Verifica se a versão do Python é adequada."""
    if sys.version_info < (3, 11):
        print("❌ Python 3.11+ é necessário")
        print(f"   Versão atual: {sys.version}")
        print("   Baixe em: https://www.python.org/downloads/")
        return False
    print(f"✅ Python {sys.version.split()[0]} está adequado")
    return True


def install_dependencies():
    """Instala as dependências do projeto."""
    print("\n📦 Instalando dependências...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True, capture_output=True)
        print("✅ Dependências instaladas com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar dependências: {e}")
        print("   Tente manualmente: pip install -r requirements.txt")
        return False


def create_env_file():
    """Cria arquivo .env se não existir."""
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if env_file.exists():
        print("✅ Arquivo .env já existe")
        return True
    
    if not env_example.exists():
        print("❌ Arquivo env.example não encontrado")
        return False
    
    try:
        # Copia env.example para .env
        with open(env_example, 'r') as src:
            content = src.read()
        
        with open(env_file, 'w') as dst:
            dst.write(content)
        
        print("✅ Arquivo .env criado (copie de env.example)")
        print("⚠️  CONFIGURE suas chaves API no arquivo .env")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar .env: {e}")
        return False


def check_mongodb():
    """Verifica se MongoDB está disponível."""
    try:
        import pymongo
        # Tenta conectar no MongoDB local
        client = pymongo.MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
        client.server_info()  # Força conexão
        print("✅ MongoDB local detectado")
        return True
    except:
        print("⚠️  MongoDB local não detectado")
        print("   Opções:")
        print("   1. Instale MongoDB Community: https://www.mongodb.com/try/download/community")
        print("   2. Use MongoDB Atlas (Cloud): https://www.mongodb.com/atlas")
        print("   3. Configure MONGODB_URI no .env para seu cluster")
        return False


def test_basic_functionality():
    """Testa funcionalidades básicas."""
    print("\n🧪 Testando funcionalidades básicas...")
    
    try:
        # Testa imports básicos
        sys.path.insert(0, 'app')
        
        from app.utils.emergency import is_emergency
        from app.utils.security import hash_phone_number
        from app.schemas import TriageSlots
        
        # Testa detecção de emergência
        assert is_emergency("dor no peito")
        assert not is_emergency("dor de cabeça leve")
        
        # Testa hash de telefone
        hash1 = hash_phone_number("5511999999999")
        assert len(hash1) == 64
        
        # Testa schemas
        slots = TriageSlots(chief_complaint="teste")
        assert not slots.is_complete()
        
        print("✅ Testes básicos passaram")
        return True
        
    except Exception as e:
        print(f"❌ Erro nos testes básicos: {e}")
        return False


def show_next_steps():
    """Mostra próximos passos."""
    print("\n" + "="*50)
    print("🎉 Setup concluído!")
    print("="*50)
    
    print("\n📝 PRÓXIMOS PASSOS:")
    
    print("\n1. Configure suas chaves API no arquivo .env:")
    print("   GEMINI_API_KEY=sua_chave_gemini")
    print("   WHATSAPP_ACCESS_TOKEN=seu_token_whatsapp")
    print("   WHATSAPP_PHONE_NUMBER_ID=seu_phone_id")
    print("   WHATSAPP_VERIFY_TOKEN=seu_token_verificacao")
    
    print("\n2. Execute a aplicação:")
    print("   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
    print("   # OU: make dev")
    
    print("\n3. Configure ngrok (em outro terminal):")
    print("   ngrok http 8000")
    
    print("\n4. URLs para Meta for Developers:")
    print("   Webhook URL: https://SEU-NGROK.ngrok-free.app/webhook/whatsapp")
    print("   Verify Token: [valor do WHATSAPP_VERIFY_TOKEN]")
    
    print("\n5. Teste:")
    print("   curl http://localhost:8000/health")
    print("   Abra: http://localhost:8000/docs")
    
    print("\n📚 Documentação:")
    print("   README.md - Documentação completa")
    print("   QUICK_START.md - Guia rápido")
    print("   DEPLOYMENT.md - Deploy em produção")


def main():
    """Função principal do setup."""
    print("🏥 ClinicAI - Setup Automático")
    print("="*40)
    
    # Verificações e configurações
    checks = [
        ("Versão do Python", check_python_version),
        ("Dependências", install_dependencies),
        ("Arquivo .env", create_env_file),
        ("MongoDB", check_mongodb),
        ("Funcionalidades", test_basic_functionality),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n🔍 Verificando: {name}")
        result = check_func()
        results.append((name, result))
    
    # Resumo
    print("\n" + "="*40)
    print("📊 RESUMO:")
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"   {status} {name}")
    
    # Próximos passos
    if any(result for _, result in results):
        show_next_steps()
    else:
        print("\n❌ Setup falhou. Verifique os erros acima.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
