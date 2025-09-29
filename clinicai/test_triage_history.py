#!/usr/bin/env python3
"""
Teste específico para verificar se o histórico está sendo filtrado por triagem.
"""

import asyncio
from datetime import datetime, timedelta
from clinicai_mongodb_fixed import TriageProcessor, connect_mongodb, mongo_db

async def test_triage_specific_history():
    """Testa se o histórico está sendo filtrado por triagem específica."""
    
    print("🔍 TESTE: Histórico Específico por Triagem")
    print("=" * 60)
    
    await connect_mongodb()
    
    if mongo_db is None:
        print("❌ MongoDB não conectado")
        return
    
    processor = TriageProcessor()
    test_phone = "+5511999999999"
    
    print("✅ Configuração pronta - iniciando teste")
    
    # Limpar dados de teste existentes
    from clinicai_mongodb_fixed import hash_phone_number
    phone_hash = hash_phone_number(test_phone)
    
    print(f"\n🧹 LIMPANDO dados de teste para {phone_hash[:8]}...")
    try:
        await mongo_db.messages.delete_many({"phone_hash": phone_hash})
        await mongo_db.triages.delete_many({"phone_hash": phone_hash})
        print("✅ Dados limpos")
    except Exception as e:
        print(f"⚠️ Erro na limpeza: {e}")
    
    print(f"\n📊 SIMULANDO MÚLTIPLAS TRIAGENS")
    print("="*60)
    
    # Simular triagem antiga (completada há 2 horas)
    old_time = datetime.now() - timedelta(hours=2)
    
    print(f"1️⃣ SIMULANDO TRIAGEM ANTIGA ({old_time.strftime('%H:%M')})")
    
    # Inserir triagem antiga diretamente no MongoDB
    await mongo_db.triages.insert_one({
        "phone_hash": phone_hash,
        "status": "completed",
        "created_at": old_time,
        "completed_at": old_time + timedelta(minutes=10),
        "slots": {
            "chief_complaint": "dor antiga",
            "symptoms": "sintomas antigos"
        }
    })
    
    # Inserir mensagens da triagem antiga
    old_messages = [
        "Olá, estou com dor de estômago",
        "A dor começou há 1 semana",
        "Numa escala de 1 a 10, é uns 6",
        "Já tomei omeprazol",
        "Não tenho histórico de problemas"
    ]
    
    for i, msg in enumerate(old_messages):
        await mongo_db.messages.insert_one({
            "phone_hash": phone_hash,
            "direction": "in",
            "message_id": f"old_msg_{i}",
            "text": msg,
            "timestamp": old_time + timedelta(minutes=i)
        })
        
        # Resposta do sistema
        await mongo_db.messages.insert_one({
            "phone_hash": phone_hash,
            "direction": "out", 
            "message_id": f"old_reply_{i}",
            "text": f"Resposta antiga {i}",
            "timestamp": old_time + timedelta(minutes=i, seconds=30)
        })
    
    print(f"   📝 Inseridas {len(old_messages)*2} mensagens antigas")
    
    # Agora iniciar uma nova triagem
    print(f"\n2️⃣ INICIANDO NOVA TRIAGEM (AGORA)")
    
    # Simular primeira mensagem da nova triagem
    result1 = await processor.process_message(
        phone=test_phone,
        message_text="Olá, agora estou com dor de cabeça",
        message_id="new_msg_1"
    )
    
    print(f"   ✅ Primeira mensagem processada: {result1.get('action', 'N/A')}")
    
    # Verificar o histórico carregado
    if phone_hash in processor.conversation_histories:
        current_history = processor.conversation_histories[phone_hash]
        print(f"   📚 Histórico atual: {len(current_history)} mensagens")
        
        # Verificar se contém mensagens antigas
        has_old_messages = any("dor de estômago" in msg or "omeprazol" in msg for msg in current_history)
        has_new_messages = any("dor de cabeça" in msg for msg in current_history)
        
        print(f"   🔍 ANÁLISE DO HISTÓRICO:")
        print(f"      🔴 Contém mensagens antigas: {'SIM' if has_old_messages else 'NÃO'}")
        print(f"      🟢 Contém mensagens novas: {'SIM' if has_new_messages else 'NÃO'}")
        
        if not has_old_messages and has_new_messages:
            print(f"   ✅ SUCESSO: Histórico filtrado corretamente!")
        elif has_old_messages:
            print(f"   ❌ PROBLEMA: Histórico contém mensagens da triagem antiga!")
        else:
            print(f"   ⚠️ INDETERMINADO: Histórico muito pequeno para avaliar")
        
        # Mostrar primeiras mensagens do histórico
        print(f"\n   📝 HISTÓRICO ATUAL (primeiras 5 mensagens):")
        for i, msg in enumerate(current_history[:5]):
            print(f"      {i+1}. {msg[:80]}...")
    else:
        print(f"   ❌ Nenhum histórico encontrado")
    
    # Processar mais algumas mensagens para testar continuidade
    print(f"\n3️⃣ CONTINUANDO A NOVA TRIAGEM")
    
    test_messages = [
        "A dor começou hoje de manhã",
        "É uma dor pulsante, muito forte",
        "Numa escala de 1 a 10, é uns 9"
    ]
    
    for i, msg in enumerate(test_messages, 2):
        result = await processor.process_message(
            phone=test_phone,
            message_text=msg,
            message_id=f"new_msg_{i}"
        )
        print(f"   💬 Mensagem {i}: '{msg[:40]}...' → {result.get('action', 'N/A')}")
    
    # Verificar histórico final
    final_history = processor.conversation_histories.get(phone_hash, [])
    print(f"\n📊 HISTÓRICO FINAL: {len(final_history)} mensagens")
    
    # Contar mensagens antigas vs novas
    old_count = sum(1 for msg in final_history if any(word in msg for word in ["estômago", "omeprazol", "antiga"]))
    new_count = sum(1 for msg in final_history if any(word in msg for word in ["cabeça", "pulsante", "manhã"]))
    
    print(f"   🔴 Mensagens antigas: {old_count}")
    print(f"   🟢 Mensagens novas: {new_count}")
    
    # Resultado final
    print(f"\n" + "="*60)
    print("🎯 RESULTADO DO TESTE")
    print("="*60)
    
    if old_count == 0 and new_count > 0:
        print("✅ SUCESSO COMPLETO: Histórico filtrado por triagem atual")
        print("   🎉 O Gemini está recebendo apenas o contexto relevante!")
    elif old_count > 0:
        print("❌ FALHA: Histórico contém mensagens de triagens antigas") 
        print("   🔧 Necessário ajustar o filtro de mensagens")
    else:
        print("⚠️ INDETERMINADO: Não há histórico suficiente para avaliar")
    
    # Limpeza final
    print(f"\n🧹 Limpando dados de teste...")
    await mongo_db.messages.delete_many({"phone_hash": phone_hash})
    await mongo_db.triages.delete_many({"phone_hash": phone_hash})

if __name__ == "__main__":
    print("🚀 INICIANDO TESTE DE HISTÓRICO POR TRIAGEM")
    
    asyncio.run(test_triage_specific_history())
    
    print(f"\n🎉 TESTE CONCLUÍDO!")
    print("✅ Análise de filtro de histórico realizada")
