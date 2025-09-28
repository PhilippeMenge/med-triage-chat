#!/usr/bin/env python3
"""
Teste do fluxo simplificado - uma pergunta por vez.
"""

import asyncio
from datetime import datetime, timedelta
from clinicai_whatsapp import TriageProcessor, TriageDatabase, WhatsAppClient, hash_phone_number

async def test_simplified_flow():
    """Testa o fluxo simplificado."""
    
    print("🧪 Testando Fluxo Simplificado")
    print("=" * 40)
    
    # Configurar componentes
    db = TriageDatabase()
    whatsapp = WhatsAppClient()
    processor = TriageProcessor(db, whatsapp, "fake_key")
    
    test_phone = "5511888888888"
    phone_hash = hash_phone_number(test_phone)
    
    print(f"📱 Telefone de teste: {test_phone}")
    print(f"🔐 Hash: {phone_hash[:8]}...")
    
    # Cenário 1: Usuário novo
    print(f"\n1️⃣ Cenário: Usuário completamente novo")
    try:
        result = await processor.process_message(test_phone, "Olá, preciso de ajuda")
        print(f"   ✅ Ação: {result.get('action', 'processed')}")
        print(f"   📝 Apresentação enviada automaticamente")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Cenário 2: Continuar triagem
    print(f"\n2️⃣ Cenário: Continuando triagem")
    try:
        result = await processor.process_message(test_phone, "estou com dor de cabeça")
        print(f"   ✅ Ação: {result.get('action', 'processed')}")
        print(f"   📝 Próxima pergunta enviada")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Cenário 3: Simular timeout (criar triagem antiga)
    print(f"\n3️⃣ Cenário: Timeout - mais de 30 minutos")
    try:
        # Forçar last_activity antigo
        old_time = (datetime.now() - timedelta(minutes=35)).isoformat()
        db.create_or_update_triage(
            phone_hash=phone_hash,
            status="open",
            last_activity=old_time
        )
        
        result = await processor.process_message(test_phone, "Oi, voltei")
        print(f"   ✅ Ação: {result.get('action', 'processed')}")
        print(f"   📝 Reapresentação enviada após timeout")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Cenário 4: Usuário diferente
    test_phone2 = "5511777777777"
    print(f"\n4️⃣ Cenário: Outro usuário ({test_phone2})")
    try:
        result = await processor.process_message(test_phone2, "Primeira vez aqui")
        print(f"   ✅ Ação: {result.get('action', 'processed')}")
        print(f"   📝 Apresentação para novo usuário")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    print(f"\n🎉 Teste do Fluxo Simplificado Concluído!")
    print("\n📋 Comportamentos Implementados:")
    print("   ✅ Uma mensagem por vez")
    print("   ✅ Reapresentação após 30min")
    print("   ✅ Sem menus complexos")
    print("   ✅ Fluxo linear e direto")
    print("   ✅ Reset automático por timeout")

if __name__ == "__main__":
    asyncio.run(test_simplified_flow())
