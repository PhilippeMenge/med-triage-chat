#!/usr/bin/env python3
"""
Verificar se as credenciais estão sendo carregadas corretamente.
"""

import os

print("🔍 Verificando Credenciais Carregadas")
print("=" * 50)

# Verificar variáveis de ambiente
access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "fake_token")
phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "fake_id")
verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "ClinicAI_Test_Token_123")

print(f"📱 Phone Number ID: {phone_id}")
print(f"🔐 Access Token: {access_token[:20]}...{access_token[-10:] if len(access_token) > 30 else access_token}")
print(f"🔒 Verify Token: {verify_token}")

print("\n🔍 Análise:")

if access_token == "fake_token":
    print("❌ PROBLEMA: Access token ainda é 'fake_token'")
    print("   Solução: Configure a variável WHATSAPP_ACCESS_TOKEN")
elif len(access_token) < 100:
    print("⚠️  WARNING: Access token parece muito curto")
else:
    print("✅ Access token parece válido")

if phone_id == "fake_id":
    print("❌ PROBLEMA: Phone ID ainda é 'fake_id'")
    print("   Solução: Configure a variável WHATSAPP_PHONE_NUMBER_ID")
elif not phone_id.isdigit():
    print("⚠️  WARNING: Phone ID deve ser apenas números")
elif len(phone_id) < 10:
    print("⚠️  WARNING: Phone ID parece muito curto")
else:
    print("✅ Phone Number ID parece válido")

print("\n📁 Verificando arquivo .env:")
if os.path.exists(".env"):
    print("✅ Arquivo .env existe")
    with open(".env", "r") as f:
        content = f.read()
        if "WHATSAPP_ACCESS_TOKEN=" in content and not "fake_token" in content:
            print("✅ .env contém access token real")
        else:
            print("❌ .env não contém access token válido")
else:
    print("❌ Arquivo .env não existe")

print("\n🔧 Como corrigir:")
print("1. Crie/edite o arquivo .env:")
print("   WHATSAPP_ACCESS_TOKEN=seu_token_real_aqui")
print("   WHATSAPP_PHONE_NUMBER_ID=seu_phone_id_aqui")
print("2. Reinicie a aplicação")
print("3. Teste novamente")
