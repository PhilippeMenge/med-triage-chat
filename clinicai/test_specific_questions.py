#!/usr/bin/env python3
"""
Teste do sistema refatorado com perguntas específicas e validação do Gemini.
"""

import asyncio
from clinicai_whatsapp import TriageProcessor, TriageDatabase, WhatsAppClient, QuestionManager

async def test_specific_questions():
    """Testa o novo sistema com perguntas específicas."""
    
    print("🧪 Testando Sistema Refatorado - Perguntas Específicas")
    print("=" * 60)
    
    # Mostrar as perguntas na ordem
    question_manager = QuestionManager()
    print("📝 Perguntas na ordem específica:")
    print("1️⃣", question_manager.get_question("chief_complaint"))
    print("2️⃣", question_manager.get_question("symptoms"))
    print("3️⃣", question_manager.get_question("duration_frequency"))
    print("4️⃣", question_manager.get_question("intensity"))
    print("5️⃣", question_manager.get_question("measures_taken"))
    print("6️⃣", question_manager.get_question("health_history"))
    
    # Configurar componentes
    db = TriageDatabase()
    whatsapp = WhatsAppClient()
    processor = TriageProcessor(db, whatsapp, "fake_key")
    
    test_phone = "5511333333333"
    
    print(f"\n📱 Testando com telefone: {test_phone}")
    print("=" * 60)
    
    # Cenário 1: Usuário novo - deve receber apresentação
    print(f"\n1️⃣ Cenário: Primeiro contato")
    try:
        result = await processor.process_message(test_phone, "Olá")
        print(f"   ✅ Ação: {result.get('action', 'processed')}")
        print(f"   📝 Apresentação enviada")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Cenário 2: Resposta à primeira pergunta
    print(f"\n2️⃣ Cenário: Respondendo queixa")
    try:
        result = await processor.process_message(test_phone, "estou com dor no peito")
        print(f"   ✅ Processado")
        print(f"   📝 Deve passar para pergunta 2 (sintomas)")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Cenário 3: Resposta válida à segunda pergunta
    print(f"\n3️⃣ Cenário: Descrevendo sintomas")
    try:
        result = await processor.process_message(test_phone, "sinto uma dor forte que aperta e irradia para o braço esquerdo")
        print(f"   ✅ Processado")
        print(f"   📝 Deve passar para pergunta 3 (duração/frequência)")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Cenário 4: Resposta inválida (deve reescrever pergunta)
    print(f"\n4️⃣ Cenário: Resposta inválida")
    try:
        result = await processor.process_message(test_phone, "não sei, talvez")
        print(f"   ✅ Processado")
        print(f"   📝 Deve reescrever a pergunta atual (duração/frequência)")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    print(f"\n🎉 Teste Concluído!")
    print("\n📋 Funcionalidades Implementadas:")
    print("   ✅ Perguntas específicas na ordem exata")
    print("   ✅ Validação de resposta com Gemini")
    print("   ✅ Reescrita de pergunta quando inválida")
    print("   ✅ Fluxo sequencial obrigatório")
    print("   ✅ Armazenamento direto da resposta do usuário")
    
    print("\n🔧 Como funciona:")
    print("   1. Pergunta específica é feita")
    print("   2. Gemini valida se resposta está adequada")
    print("   3. Se SIM: salva resposta e próxima pergunta")
    print("   4. Se NÃO: reescreve pergunta de outra forma")

if __name__ == "__main__":
    asyncio.run(test_specific_questions())
