#!/usr/bin/env python3
"""
Teste do webhook com dados simulados do WhatsApp.
"""

import json
import requests

# URL do seu servidor local
SERVER_URL = "http://localhost:8080"

# Payload de exemplo que o WhatsApp enviaria
whatsapp_payload = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "123456789",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "5511999999999",
                            "phone_number_id": "123456789"
                        },
                        "contacts": [
                            {
                                "profile": {
                                    "name": "Usuario Teste"
                                },
                                "wa_id": "5511888888888"
                            }
                        ],
                        "messages": [
                            {
                                "from": "5511888888888",
                                "id": "wamid.test123456",
                                "timestamp": "1677847800",
                                "text": {
                                    "body": "Olá, estou com dor de cabeça"
                                },
                                "type": "text"
                            }
                        ]
                    },
                    "field": "messages"
                }
            ]
        }
    ]
}

def test_webhook_verification():
    """Testa a verificação do webhook."""
    print("🔍 Testando verificação do webhook...")
    
    url = f"{SERVER_URL}/webhook/whatsapp"
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "ClinicAI_Test_Token_123",
        "hub.challenge": "test_challenge_12345"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200 and response.text == "test_challenge_12345":
            print("✅ Verificação do webhook: SUCESSO")
            return True
        else:
            print("❌ Verificação do webhook: FALHOU")
            return False
            
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return False

def test_webhook_message():
    """Testa o recebimento de mensagem."""
    print("\n📱 Testando recebimento de mensagem...")
    
    url = f"{SERVER_URL}/webhook/whatsapp"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "WhatsApp/2.0"
    }
    
    try:
        response = requests.post(
            url, 
            json=whatsapp_payload, 
            headers=headers, 
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Recebimento de mensagem: SUCESSO")
            return True
        else:
            print("❌ Recebimento de mensagem: FALHOU")
            return False
            
    except Exception as e:
        print(f"❌ Erro no recebimento: {e}")
        return False

def test_ngrok_url():
    """Testa se consegue acessar via URL externa."""
    ngrok_url = input("\n🌐 Digite sua URL do ngrok (ex: https://abc123.ngrok-free.app): ").strip()
    
    if not ngrok_url:
        print("❌ URL não fornecida")
        return False
    
    print(f"\n🧪 Testando {ngrok_url}...")
    
    # Teste 1: Health check
    try:
        health_url = f"{ngrok_url}/health"
        response = requests.get(health_url, timeout=10)
        print(f"Health check: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ ngrok funcionando")
        else:
            print("❌ ngrok com problemas")
            return False
            
    except Exception as e:
        print(f"❌ Erro no ngrok: {e}")
        return False
    
    # Teste 2: Webhook verification via ngrok
    try:
        webhook_url = f"{ngrok_url}/webhook/whatsapp"
        params = {
            "hub.mode": "subscribe",
            "hub.verify_token": "ClinicAI_Test_Token_123",
            "hub.challenge": "test_ngrok_12345"
        }
        
        response = requests.get(webhook_url, params=params, timeout=10)
        print(f"Webhook via ngrok: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Webhook via ngrok funcionando")
            print(f"📋 Use esta URL no Meta: {webhook_url}")
            return True
        else:
            print("❌ Webhook via ngrok com problemas")
            return False
            
    except Exception as e:
        print(f"❌ Erro no webhook via ngrok: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Teste Completo do Webhook WhatsApp")
    print("=" * 50)
    
    # Teste 1: Servidor local
    verification_ok = test_webhook_verification()
    message_ok = test_webhook_message()
    
    # Teste 2: ngrok (opcional)
    ngrok_ok = test_ngrok_url()
    
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS TESTES:")
    print(f"   Verificação local: {'✅' if verification_ok else '❌'}")
    print(f"   Mensagem local: {'✅' if message_ok else '❌'}")
    print(f"   ngrok: {'✅' if ngrok_ok else '❌'}")
    
    if verification_ok and message_ok and ngrok_ok:
        print("\n🎉 TUDO FUNCIONANDO!")
        print("📱 Pode testar enviando mensagem do WhatsApp")
    else:
        print("\n🔧 PROBLEMAS DETECTADOS!")
        print("📋 Verifique os erros acima")
    
    print("=" * 50)
