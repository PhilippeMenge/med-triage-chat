#!/usr/bin/env python3
"""
Script para configurar credenciais reais do WhatsApp.
"""

import os

print("🔑 Configurador de Credenciais WhatsApp")
print("=" * 50)

print("""
Para usar o WhatsApp Cloud API, você precisa:

1. 📱 Acesse: https://developers.facebook.com
2. 🏗️  Crie um App WhatsApp Business
3. 📋 Vá em: WhatsApp → Getting Started
4. 🔑 Copie suas credenciais

""")

# Pedir credenciais
print("📝 Digite suas credenciais:")

access_token = input("🔐 WhatsApp Access Token: ").strip()
phone_number_id = input("📱 Phone Number ID: ").strip()
verify_token = input("🔒 Verify Token (ou deixe em branco para usar padrão): ").strip()

if not verify_token:
    verify_token = "ClinicAI_Test_Token_123"

print("\n✅ Credenciais coletadas!")

# Criar arquivo de configuração
env_content = f"""# ClinicAI - Credenciais WhatsApp Reais
# Configurado em {os.getenv('COMPUTERNAME', 'sistema')}

# WhatsApp Cloud API - CREDENCIAIS REAIS
WHATSAPP_ACCESS_TOKEN={access_token}
WHATSAPP_PHONE_NUMBER_ID={phone_number_id}
WHATSAPP_VERIFY_TOKEN={verify_token}

# Opcional
GEMINI_API_KEY=your_gemini_api_key_here
PHONE_HASH_SALT=ClinicAI_Super_Secure_Salt_2024
LOG_LEVEL=INFO
"""

# Salvar arquivo
with open(".env", "w") as f:
    f.write(env_content)

print(f"💾 Arquivo .env criado com suas credenciais!")

# Verificar se as credenciais parecem válidas
print("\n🔍 Verificando credenciais...")

if len(access_token) < 100:
    print("⚠️  WARNING: Access token parece muito curto")
    print("   Tokens normalmente têm 100+ caracteres")

if not phone_number_id.isdigit():
    print("⚠️  WARNING: Phone Number ID deve ser apenas números")

if len(phone_number_id) < 10:
    print("⚠️  WARNING: Phone Number ID parece muito curto")

print("\n🚀 Próximos passos:")
print("1. Reinicie sua aplicação:")
print("   python webhook_debug.py")
print("2. Teste enviando mensagem do WhatsApp")
print("3. Verifique os logs para confirmar se funciona")

print("\n📋 Para testar manualmente:")
print("curl -X POST \\")
print(f'  -H "Authorization: Bearer {access_token[:20]}..." \\')
print(f'  "https://graph.facebook.com/v20.0/{phone_number_id}/messages"')
