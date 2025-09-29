#!/usr/bin/env python3
"""
Debug específico para identificar por que a primeira pergunta está se repetindo.
"""

import asyncio
from clinicai_mongodb_fixed import TriageProcessor, get_welcome_message, connect_mongodb, hash_phone_number

async def debug_first_question_flow():
    """Debug detalhado do fluxo da primeira pergunta."""
    
    print("🔍 DEBUG: Fluxo da Primeira Pergunta")
    print("=" * 60)
    
    # Conectar ao MongoDB
    await connect_mongodb()
    
    processor = TriageProcessor()
    test_phone = "+5511888888888"
    phone_hash = hash_phone_number(test_phone.replace("+", ""))
    
    # Limpar dados de teste
    print("🧹 Limpando dados de teste...")
    try:
        from clinicai_mongodb_fixed import mongo_db
        if mongo_db is not None:
            await mongo_db.messages.delete_many({"phone_hash": phone_hash})
            await mongo_db.triages.delete_many({"phone_hash": phone_hash})
    except:
        pass
    
    print("\n" + "="*60)
    print("🎬 SIMULAÇÃO PASSO A PASSO")
    print("="*60)
    
    # PASSO 1: Primeira mensagem do usuário
    print("\n1️⃣ PRIMEIRA MENSAGEM: 'Olá'")
    print("   👤 Usuário envia primeira mensagem")
    
    # Verificar estado inicial
    current_triage = await processor.db.get_active_triage(phone_hash)
    print(f"   📊 Triagem ativa antes: {bool(current_triage)}")
    
    # Processar primeira mensagem
    result1 = await processor.process_message(test_phone, "Olá")
    print(f"   ✅ Resultado: {result1.get('action', 'unknown')}")
    
    # Verificar histórico após primeira mensagem
    history1 = processor.conversation_histories.get(phone_hash, [])
    print(f"   📚 Histórico após 1ª msg ({len(history1)} itens):")
    for i, msg in enumerate(history1, 1):
        print(f"      {i}. {msg[:60]}...")
    
    # Verificar mensagens no MongoDB
    try:
        from clinicai_mongodb_fixed import mongo_db
        if mongo_db is not None:
            messages = await mongo_db.messages.find({"phone_hash": phone_hash}).to_list(length=10)
            print(f"   💾 Mensagens no MongoDB ({len(messages)} itens):")
            for i, msg in enumerate(messages, 1):
                direction = "📤" if msg['direction'] == 'out' else "📥"
                print(f"      {i}. {direction} {msg['text'][:60]}...")
    except Exception as e:
        print(f"   ❌ Erro ao buscar mensagens: {e}")
    
    # PASSO 2: Segunda mensagem do usuário
    print(f"\n2️⃣ SEGUNDA MENSAGEM: 'Estou com dor'")
    print("   👤 Usuário responde à primeira pergunta")
    
    # Verificar estado antes da segunda mensagem
    current_triage = await processor.db.get_active_triage(phone_hash)
    print(f"   📊 Triagem ativa antes: {bool(current_triage)}")
    
    # Processar segunda mensagem
    result2 = await processor.process_message(test_phone, "Estou com dor")
    print(f"   ✅ Resultado: Processado")
    
    # Verificar histórico após segunda mensagem
    history2 = processor.conversation_histories.get(phone_hash, [])
    print(f"   📚 Histórico após 2ª msg ({len(history2)} itens):")
    for i, msg in enumerate(history2, 1):
        print(f"      {i}. {msg[:60]}...")
    
    # Verificar mensagens no MongoDB após segunda
    try:
        if mongo_db is not None:
            messages = await mongo_db.messages.find({"phone_hash": phone_hash}).to_list(length=20)
            print(f"   💾 Mensagens no MongoDB ({len(messages)} itens):")
            for i, msg in enumerate(messages, 1):
                direction = "📤" if msg['direction'] == 'out' else "📥"
                print(f"      {i}. {direction} {msg['text'][:60]}...")
    except Exception as e:
        print(f"   ❌ Erro ao buscar mensagens: {e}")
    
    print(f"\n" + "="*60)
    print("🔍 ANÁLISE DO PROBLEMA")
    print("="*60)
    
    # Contar perguntas sobre motivo/queixa
    welcome_count = 0
    first_question_count = 0
    
    for msg in history2:
        if "Olá! Sou a ClinicAI" in msg:
            welcome_count += 1
        if any(word in msg.lower() for word in ["motivo", "queixa", "contato", "trouxe"]):
            first_question_count += 1
    
    print(f"📊 CONTADORES:")
    print(f"   🏥 Mensagens de boas-vindas: {welcome_count}")
    print(f"   ❓ Perguntas sobre motivo/queixa: {first_question_count}")
    
    # Identificar problema
    if first_question_count > 1:
        print(f"\n❌ PROBLEMA IDENTIFICADO:")
        print(f"   🔄 Pergunta sobre motivo repetida {first_question_count} vezes")
        print(f"   📍 Localização das repetições:")
        
        for i, msg in enumerate(history2, 1):
            if any(word in msg.lower() for word in ["motivo", "queixa", "contato", "trouxe"]):
                print(f"      {i}. {msg}")
    else:
        print(f"\n✅ NENHUM PROBLEMA DETECTADO")
        print(f"   ✅ Pergunta sobre motivo aparece apenas {first_question_count} vez(es)")
    
    # PASSO 3: Simular reconexão
    print(f"\n3️⃣ SIMULAÇÃO DE RECONEXÃO")
    print("   🔌 Limpando histórico da memória...")
    
    processor.conversation_histories = {}
    
    print("   👤 Usuário envia nova mensagem após reconexão: 'Continuo aqui'")
    
    result3 = await processor.process_message(test_phone, "Continuo aqui")
    
    # Verificar histórico recarregado
    history3 = processor.conversation_histories.get(phone_hash, [])
    print(f"   📚 Histórico recarregado ({len(history3)} itens):")
    for i, msg in enumerate(history3, 1):
        print(f"      {i}. {msg[:60]}...")
    
    # Verificar se há repetição após reconexão
    first_question_count_after = sum(1 for msg in history3 if any(word in msg.lower() for word in ["motivo", "queixa", "contato", "trouxe"]))
    
    if first_question_count_after > 0:
        print(f"\n⚠️ APÓS RECONEXÃO:")
        print(f"   🔄 Perguntas sobre motivo no histórico: {first_question_count_after}")
    else:
        print(f"\n✅ APÓS RECONEXÃO:")
        print(f"   ✅ Histórico carregado sem repetições")
    
    # Limpar dados de teste
    print(f"\n🧹 Limpando dados de teste...")
    try:
        if mongo_db is not None:
            await mongo_db.messages.delete_many({"phone_hash": phone_hash})
            await mongo_db.triages.delete_many({"phone_hash": phone_hash})
    except:
        pass

if __name__ == "__main__":
    print("🚀 INICIANDO DEBUG DA PRIMEIRA PERGUNTA")
    
    asyncio.run(debug_first_question_flow())
    
    print(f"\n🎯 DEBUG CONCLUÍDO!")
    print("✅ Análise detalhada do fluxo realizada")
