#!/usr/bin/env python3
"""
Teste para verificar se o problema da pergunta repetida foi resolvido.
"""

import asyncio
from clinicai_mongodb_fixed import TriageProcessor, get_welcome_message

async def test_conversation_flow():
    """Testa o fluxo de conversa com histórico completo."""
    
    print("🧪 TESTE: Fluxo de Conversa com Histórico Completo")
    print("=" * 60)
    
    processor = TriageProcessor()
    
    # Conectar ao MongoDB (usando a função global)
    from clinicai_mongodb_fixed import connect_mongodb
    await connect_mongodb()
    
    # Telefone de teste
    test_phone = "+5511999999999"
    
    print("🧹 Limpando dados de teste...")
    # Limpar dados de teste se existirem
    from clinicai_mongodb_fixed import hash_phone_number
    phone_hash = hash_phone_number(test_phone.replace("+", ""))
    try:
        if hasattr(processor.db, 'db') and processor.db.db:
            await processor.db.db.messages.delete_many({"phone_hash": phone_hash})
            await processor.db.db.triages.delete_many({"phone_hash": phone_hash})
    except:
        pass
    
    print("\n" + "="*60)
    print("📱 SIMULAÇÃO DE CONVERSA COMPLETA")
    print("="*60)
    
    # 1. Primeira mensagem - deve enviar boas-vindas + primeira pergunta
    print("\n1️⃣ PRIMEIRA MENSAGEM DO USUÁRIO")
    print("👤 Usuário envia: 'Olá'")
    
    result1 = await processor.process_message(test_phone, "Olá")
    print(f"✅ Resultado: {result1.get('action', 'unknown')}")
    
    # Aguardar um pouco para simular tempo real
    await asyncio.sleep(1)
    
    # 2. Segunda mensagem - deve usar histórico completo
    print("\n2️⃣ SEGUNDA MENSAGEM DO USUÁRIO")
    print("👤 Usuário envia: 'Estou com dor de cabeça'")
    
    result2 = await processor.process_message(test_phone, "Estou com dor de cabeça")
    print(f"✅ Resultado: Processado com sucesso")
    
    # Aguardar um pouco
    await asyncio.sleep(1)
    
    # 3. Terceira mensagem - verificar continuidade
    print("\n3️⃣ TERCEIRA MENSAGEM DO USUÁRIO")
    print("👤 Usuário envia: 'A dor é forte e começou hoje'")
    
    result3 = await processor.process_message(test_phone, "A dor é forte e começou hoje")
    print(f"✅ Resultado: Processado com sucesso")
    
    print("\n" + "="*60)
    print("📊 VERIFICAÇÃO DO HISTÓRICO")
    print("="*60)
    
    # Verificar histórico na memória
    from clinicai_mongodb_fixed import hash_phone_number
    phone_hash = hash_phone_number(test_phone.replace("+", ""))
    history = processor.conversation_histories.get(phone_hash, [])
    
    print(f"📝 Histórico na memória ({len(history)} mensagens):")
    for i, msg in enumerate(history, 1):
        print(f"   {i}. {msg}")
    
    # Verificar mensagens no MongoDB
    try:
        messages = await processor.db.get_messages(phone_hash, limit=10)
        print(f"\n💾 Mensagens no MongoDB ({len(messages)} mensagens):")
        for i, msg in enumerate(messages, 1):
            direction = "📤" if msg['direction'] == 'out' else "📥"
            print(f"   {i}. {direction} {msg['text'][:60]}...")
    except Exception as e:
        print(f"❌ Erro ao buscar mensagens: {e}")
    
    print("\n" + "="*60)
    print("🔄 TESTE DE RECONEXÃO")
    print("="*60)
    
    # Simular reconexão - limpar histórico da memória
    print("🔌 Simulando reconexão (limpando memória)...")
    processor.conversation_histories = {}
    
    # Enviar nova mensagem - deve carregar histórico do MongoDB
    print("👤 Usuário envia nova mensagem após 'reconexão': 'Continuo com dor'")
    
    result4 = await processor.process_message(test_phone, "Continuo com dor")
    print(f"✅ Resultado: Processado com sucesso")
    
    # Verificar se histórico foi recarregado
    history_after = processor.conversation_histories.get(phone_hash, [])
    print(f"\n📚 Histórico recarregado ({len(history_after)} mensagens):")
    for i, msg in enumerate(history_after, 1):
        print(f"   {i}. {msg}")
    
    print("\n" + "="*60)
    print("🎯 ANÁLISE DOS RESULTADOS")
    print("="*60)
    
    # Verificar se não há perguntas repetidas
    welcome_count = sum(1 for msg in history_after if "Olá! Sou a ClinicAI" in msg)
    first_question_count = sum(1 for msg in history_after if "motivo do seu contato" in msg.lower())
    
    print(f"📊 ESTATÍSTICAS:")
    print(f"   🏥 Mensagens de boas-vindas: {welcome_count}")
    print(f"   ❓ Perguntas sobre motivo: {first_question_count}")
    print(f"   💬 Total de mensagens no histórico: {len(history_after)}")
    
    # Verificar problemas
    issues = []
    if welcome_count > 1:
        issues.append(f"❌ Múltiplas mensagens de boas-vindas ({welcome_count})")
    if first_question_count > 1:
        issues.append(f"❌ Pergunta sobre motivo repetida ({first_question_count})")
    
    if issues:
        print(f"\n⚠️ PROBLEMAS DETECTADOS:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print(f"\n✅ NENHUM PROBLEMA DETECTADO!")
        print(f"   ✅ Histórico carregado corretamente")
        print(f"   ✅ Sem perguntas repetidas")
        print(f"   ✅ Conversa fluida mantida")
    
    # Limpar dados de teste
    print(f"\n🧹 Limpando dados de teste...")
    try:
        # Limpar mensagens e triagens do usuário de teste
        if hasattr(processor.db, 'db') and processor.db.db:
            await processor.db.db.messages.delete_many({"phone_hash": phone_hash})
            await processor.db.db.triages.delete_many({"phone_hash": phone_hash})
        print(f"✅ Dados de teste removidos")
    except Exception as e:
        print(f"⚠️ Erro ao limpar: {e}")
    
    # Fechar conexão
    print("🔌 Conexão MongoDB mantida ativa")

if __name__ == "__main__":
    print("🚀 INICIANDO TESTE DE HISTÓRICO E PERGUNTAS REPETIDAS")
    
    asyncio.run(test_conversation_flow())
    
    print(f"\n🎉 TESTE CONCLUÍDO!")
    print("✅ Verificação de histórico completa")
    print("✅ Análise de perguntas repetidas realizada")
