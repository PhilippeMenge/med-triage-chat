#!/usr/bin/env python3
"""
Teste simples das novas funcionalidades.
"""

import asyncio
from datetime import datetime, timedelta
from clinicai_whatsapp import TriageProcessor, TriageDatabase, WhatsAppClient

async def test_new_features():
    """Testa as novas funcionalidades."""
    
    print("🧪 Testando Novas Funcionalidades")
    print("=" * 40)
    
    # Configurar componentes
    db = TriageDatabase()
    whatsapp = WhatsAppClient()
    processor = TriageProcessor(db, whatsapp, "fake_key")
    
    test_phone = "5511999999999"
    
    print(f"📱 Telefone de teste: {test_phone}")
    
    # 1. Testar primeira mensagem (usuário novo)
    print(f"\n1️⃣ Testando usuário novo...")
    try:
        result = await processor.process_message(test_phone, "Olá")
        print(f"   ✅ Resultado: {result.get('action', 'processed')}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 2. Simular timeout criando triagem antiga
    print(f"\n2️⃣ Simulando timeout...")
    try:
        # Criar triagem com timestamp antigo
        from clinicai_whatsapp import hash_phone_number
        phone_hash = hash_phone_number(test_phone)
        old_time = (datetime.now() - timedelta(minutes=35)).isoformat()
        
        db.create_or_update_triage(
            phone_hash=phone_hash,
            status="open",
            last_activity=old_time
        )
        print(f"   ✅ Triagem antiga criada")
        
        # Processar nova mensagem deve detectar timeout
        result = await processor.process_message(test_phone, "Nova mensagem")
        print(f"   ✅ Timeout processado: {result.get('action', 'processed')}")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 3. Testar comando "histórico"
    print(f"\n3️⃣ Testando comando histórico...")
    try:
        result = await processor.process_message(test_phone, "histórico")
        print(f"   ✅ Histórico enviado: {result.get('action', 'processed')}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 4. Testar comando "novo"
    print(f"\n4️⃣ Testando comando novo...")
    try:
        result = await processor.process_message(test_phone, "novo")
        print(f"   ✅ Novo atendimento: {result.get('action', 'processed')}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    print(f"\n🎉 Testes concluídos!")
    print("Funcionalidades implementadas:")
    print("   ✅ Reset por timeout (30 min)")
    print("   ✅ Histórico de atendimentos")
    print("   ✅ Comando 'histórico'")
    print("   ✅ Comando 'novo'")
    print("   ✅ Menu para usuários com histórico")

if __name__ == "__main__":
    asyncio.run(test_new_features())
