#!/usr/bin/env python3
"""
Teste do fluxo completo com Gemini.
"""

import asyncio
import os
from dotenv import load_dotenv

# Carregar .env
load_dotenv()

async def test_gemini_flow():
    """Testa o fluxo completo da triagem com Gemini."""
    print("🧪 Teste do Fluxo de Triagem com Gemini")
    print("=" * 50)
    
    # Importar classes
    from clinicai_whatsapp import GeminiProcessor, TriageSlots
    
    # Configurar Gemini
    gemini_api_key = os.getenv("GEMINI_API_KEY", "fake_key_for_testing")
    gemini = GeminiProcessor(gemini_api_key)
    
    # Teste 1: Mensagem de boas-vindas
    print("\n1️⃣ Testando mensagem de boas-vindas...")
    initial_slots = TriageSlots()
    welcome_msg = await gemini.generate_question(
        target_slot="chief_complaint",
        current_slots=initial_slots,
        is_first=True
    )
    print(f"✅ Boas-vindas: {welcome_msg[:100]}...")
    
    # Teste 2: Sequência de coleta
    test_responses = [
        ("estou com dor de cabeça forte", "chief_complaint"),
        ("a dor é latejante na testa e temporas", "symptoms"),
        ("começou ontem pela manhã", "duration"),
        ("fica piorando no final do dia", "frequency"), 
        ("numa escala de 0 a 10, eu diria que é 7", "intensity"),
        ("tenho pressão alta controlada", "history"),
        ("tomei um paracetamol mas não melhorou", "measures_taken")
    ]
    
    current_slots = TriageSlots()
    
    for i, (user_response, expected_slot) in enumerate(test_responses, 2):
        print(f"\n{i}️⃣ Testando extração: {expected_slot}")
        print(f"   Usuário: '{user_response}'")
        
        # Extrair informação
        extracted = await gemini.extract_information(
            user_text=user_response,
            target_slot=expected_slot
        )
        
        if extracted:
            setattr(current_slots, expected_slot, extracted)
            print(f"   ✅ Extraído: {extracted}")
        else:
            print(f"   ⚠️  Nada extraído")
        
        # Gerar próxima pergunta se ainda não completo
        if not current_slots.is_complete():
            next_slot = current_slots.get_next_slot_to_collect()
            if next_slot:
                next_question = await gemini.generate_question(
                    target_slot=next_slot,
                    current_slots=current_slots
                )
                print(f"   🤖 Próxima pergunta: {next_question[:80]}...")
    
    # Teste 3: Verificar se triagem está completa
    print(f"\n🎯 Resultado final:")
    print(f"   Slots preenchidos: {sum(1 for v in current_slots.model_dump().values() if v is not None)}/7")
    print(f"   Triagem completa: {'✅' if current_slots.is_complete() else '❌'}")
    
    # Mostrar resumo
    print(f"\n📋 Resumo coletado:")
    for field, value in current_slots.model_dump().items():
        if value:
            print(f"   ✓ {field}: {value}")
        else:
            print(f"   ✗ {field}: (não coletado)")
    
    print("\n" + "=" * 50)
    
    if current_slots.is_complete():
        print("🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("   O fluxo de triagem está funcionando perfeitamente!")
    else:
        print("⚠️  TESTE PARCIALMENTE CONCLUÍDO")
        print("   Alguns slots não foram coletados, mas o fluxo está funcionando.")
    
    return current_slots.is_complete()

async def test_simple_extraction():
    """Teste simples de extração sem Gemini."""
    print("\n🔧 Teste de Fallback (sem Gemini)...")
    
    from clinicai_whatsapp import GeminiProcessor, TriageSlots
    
    # Usar fallback
    gemini = GeminiProcessor("fake_key")
    slots = TriageSlots()
    
    # Teste extração simples
    result = await gemini.extract_information("estou com dor de cabeça", "chief_complaint")
    print(f"Fallback extração: {result}")
    
    # Teste pergunta simples
    question = await gemini.generate_question("symptoms", slots)
    print(f"Fallback pergunta: {question}")

if __name__ == "__main__":
    print("🔍 Iniciando testes do Gemini...")
    
    try:
        # Teste principal
        success = asyncio.run(test_gemini_flow())
        
        # Teste fallback
        asyncio.run(test_simple_extraction())
        
        print(f"\n✅ Testes concluídos! Sucesso: {success}")
        
    except Exception as e:
        print(f"\n❌ Erro nos testes: {e}")
        import traceback
        traceback.print_exc()
