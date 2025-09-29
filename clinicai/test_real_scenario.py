#!/usr/bin/env python3
"""
Teste do cenário real onde a primeira pergunta se repete.
"""

import asyncio
from clinicai_mongodb_fixed import TriageProcessor, connect_mongodb, hash_phone_number

async def test_real_repetition_scenario():
    """Testa o cenário real onde pode haver repetição."""
    
    print("🎯 TESTE: Cenário Real de Repetição da Primeira Pergunta")
    print("=" * 70)
    
    await connect_mongodb()
    processor = TriageProcessor()
    test_phone = "+5511777777777"
    phone_hash = hash_phone_number(test_phone.replace("+", ""))
    
    # Limpar dados
    try:
        from clinicai_mongodb_fixed import mongo_db
        if mongo_db is not None:
            await mongo_db.messages.delete_many({"phone_hash": phone_hash})
            await mongo_db.triages.delete_many({"phone_hash": phone_hash})
    except:
        pass
    
    print("\n📱 SIMULAÇÃO COMPLETA DE CONVERSA")
    print("="*70)
    
    # Simular exatamente o que acontece no WhatsApp
    messages_sent = []
    
    # 1. Primeira mensagem do usuário
    print("\n1️⃣ Usuário envia: 'Oi'")
    result1 = await processor.process_message(test_phone, "Oi")
    
    # Capturar histórico após primeira mensagem
    history1 = processor.conversation_histories.get(phone_hash, [])
    print(f"📚 Histórico após 1ª interação ({len(history1)} mensagens):")
    for i, msg in enumerate(history1, 1):
        print(f"   {i}. {msg}")
        messages_sent.append(msg)
    
    # 2. Segunda mensagem - resposta do usuário
    print(f"\n2️⃣ Usuário responde: 'Estou com dor de cabeça'")
    result2 = await processor.process_message(test_phone, "Estou com dor de cabeça")
    
    # Capturar histórico após segunda mensagem
    history2 = processor.conversation_histories.get(phone_hash, [])
    print(f"📚 Histórico após 2ª interação ({len(history2)} mensagens):")
    for i, msg in enumerate(history2, 1):
        print(f"   {i}. {msg}")
        if msg not in messages_sent:
            messages_sent.append(msg)
    
    # 3. Terceira mensagem - continuação
    print(f"\n3️⃣ Usuário continua: 'É uma dor forte'")
    result3 = await processor.process_message(test_phone, "É uma dor forte")
    
    # Capturar histórico após terceira mensagem
    history3 = processor.conversation_histories.get(phone_hash, [])
    print(f"📚 Histórico após 3ª interação ({len(history3)} mensagens):")
    for i, msg in enumerate(history3, 1):
        print(f"   {i}. {msg}")
        if msg not in messages_sent:
            messages_sent.append(msg)
    
    print(f"\n" + "="*70)
    print("🔍 ANÁLISE DE REPETIÇÕES")
    print("="*70)
    
    # Analisar todas as mensagens enviadas pelo sistema
    system_messages = [msg for msg in messages_sent if msg.startswith("ClinicAI:")]
    
    print(f"📤 MENSAGENS ENVIADAS PELO SISTEMA ({len(system_messages)}):")
    for i, msg in enumerate(system_messages, 1):
        print(f"   {i}. {msg}")
    
    # Procurar por perguntas sobre motivo/queixa
    first_questions = []
    for i, msg in enumerate(system_messages, 1):
        msg_lower = msg.lower()
        if any(word in msg_lower for word in ["motivo", "queixa", "contato", "trouxe", "qual é"]):
            first_questions.append((i, msg))
    
    print(f"\n❓ PERGUNTAS SOBRE MOTIVO/QUEIXA ({len(first_questions)}):")
    for pos, msg in first_questions:
        print(f"   Posição {pos}: {msg}")
    
    # Verificar repetições
    if len(first_questions) > 1:
        print(f"\n❌ PROBLEMA DETECTADO!")
        print(f"   🔄 {len(first_questions)} perguntas sobre motivo encontradas")
        print(f"   📍 Isso indica repetição da primeira pergunta")
        
        # Mostrar diferenças
        for i, (pos, msg) in enumerate(first_questions):
            print(f"\n   Pergunta {i+1} (posição {pos}):")
            print(f"   {msg}")
    else:
        print(f"\n✅ NENHUMA REPETIÇÃO DETECTADA!")
        if first_questions:
            print(f"   ✅ Apenas 1 pergunta sobre motivo encontrada")
        else:
            print(f"   ⚠️ Nenhuma pergunta sobre motivo encontrada (pode ser problema)")
    
    # Verificar mensagens de boas-vindas
    welcome_messages = [msg for msg in system_messages if "Olá! Sou a ClinicAI" in msg]
    print(f"\n🏥 MENSAGENS DE BOAS-VINDAS: {len(welcome_messages)}")
    
    if len(welcome_messages) > 1:
        print(f"   ⚠️ Múltiplas mensagens de boas-vindas detectadas")
    
    # Verificar mensagens no MongoDB
    print(f"\n💾 VERIFICAÇÃO NO MONGODB:")
    try:
        if mongo_db is not None:
            messages = await mongo_db.messages.find({"phone_hash": phone_hash}).to_list(length=50)
            out_messages = [msg for msg in messages if msg['direction'] == 'out']
            
            print(f"   📤 Mensagens 'out' no MongoDB: {len(out_messages)}")
            for i, msg in enumerate(out_messages, 1):
                print(f"      {i}. {msg['text'][:80]}...")
            
            # Contar perguntas no MongoDB
            mongo_first_questions = 0
            for msg in out_messages:
                text_lower = msg['text'].lower()
                if any(word in text_lower for word in ["motivo", "queixa", "contato", "trouxe", "qual é"]):
                    mongo_first_questions += 1
            
            print(f"   ❓ Perguntas sobre motivo no MongoDB: {mongo_first_questions}")
            
            if mongo_first_questions > 1:
                print(f"   ❌ REPETIÇÃO CONFIRMADA NO MONGODB!")
            else:
                print(f"   ✅ Sem repetições no MongoDB")
                
    except Exception as e:
        print(f"   ❌ Erro ao verificar MongoDB: {e}")
    
    # Limpar dados
    try:
        if mongo_db is not None:
            await mongo_db.messages.delete_many({"phone_hash": phone_hash})
            await mongo_db.triages.delete_many({"phone_hash": phone_hash})
    except:
        pass

if __name__ == "__main__":
    print("🚀 INICIANDO TESTE DE CENÁRIO REAL")
    
    asyncio.run(test_real_repetition_scenario())
    
    print(f"\n🎉 TESTE CONCLUÍDO!")
    print("✅ Análise completa do cenário real realizada")
