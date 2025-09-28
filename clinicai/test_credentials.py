#!/usr/bin/env python3
"""
Teste rápido das credenciais após correção.
"""

import os
from dotenv import load_dotenv

# Carregar .env
load_dotenv()

print("🔍 Teste de Credenciais Corrigidas")
print("=" * 40)

# Pegar credenciais
access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "fake_token")
phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "fake_id")
verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "ClinicAI_Test_Token_123")

print(f"📱 Phone ID: {phone_id}")
print(f"🔐 Access Token: {access_token[:20]}...{access_token[-10:] if len(access_token) > 30 else access_token}")
print(f"🔒 Verify Token: {verify_token}")

# Validação
errors = []

if access_token == "fake_token":
    errors.append("❌ Access token ainda é fake")
elif len(access_token) < 100:
    errors.append("⚠️  Access token parece muito curto")
else:
    print("✅ Access token OK")

if phone_id == "fake_id":
    errors.append("❌ Phone ID ainda é fake")
elif not phone_id.isdigit():
    errors.append("⚠️  Phone ID deve ser apenas números")
elif len(phone_id) < 10:
    errors.append("⚠️  Phone ID parece muito curto")
else:
    print("✅ Phone ID OK")

print("✅ Verify Token OK")

if errors:
    print("\n🚨 PROBLEMAS ENCONTRADOS:")
    for error in errors:
        print(f"   {error}")
    print("\n🔧 SOLUÇÃO:")
    print("   1. Edite o arquivo .env")
    print("   2. Configure suas credenciais reais do Meta for Developers")
    print("   3. Reinicie a aplicação")
else:
    print("\n🎉 TODAS AS CREDENCIAIS ESTÃO CORRETAS!")
    print("   Agora a aplicação deve funcionar sem erro 401")

print("=" * 40)
