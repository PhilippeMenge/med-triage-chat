#!/usr/bin/env python3
"""
Teste da interação conversacional com Gemini.
"""

import asyncio
import json
from clinicai_mongodb_fixed import GeminiTriageAgent, TriageSlots

async def test_gemini_conversation():
    """Testa a conversa com Gemini passo a passo."""
    
    print("🤖 Testando Interação Conversacional com Gemini")
    print("=" * 60)
    
    # Inicializar agente Gemini
    gemini = GeminiTriageAgent()
    
    if not gemini.client:
        print("⚠️ Gemini não configurado - testando fallback")
    else:
        print("✅ Gemini configurado e pronto")
    
    print("\n" + "="*60)
    print("🎭 SIMULAÇÃO DE CONVERSA COMPLETA")
    print("="*60)
    
    # Simular uma conversa completa
    conversation_history = []
    current_slots = TriageSlots()
    
    # Cenários de teste
    test_messages = [
        "Olá, estou com dor de cabeça",
        "É uma dor forte que começou hoje de manhã",
        "A dor é constante, não para, e começou há umas 3 horas",
        "Numa escala de 0 a 10, eu diria que é uns 7",
        "Já tomei um paracetamol mas não melhorou",
        "Não tenho histórico de enxaqueca, é a primeira vez"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{'='*20} INTERAÇÃO {i} {'='*20}")
        print(f"👤 USUÁRIO: {message}")
        print(f"📝 Slots atuais: {sum(1 for v in current_slots.model_dump().values() if v is not None)}/6")
        
        try:
            # Processar com Gemini
            result = await gemini.process_conversation(
                user_message=message,
                current_slots=current_slots,
                conversation_history=conversation_history
            )
            
            print(f"\n🤖 GEMINI RESPOSTA:")
            print(f"💬 Mensagem: {result['message']}")
            print(f"🚨 Emergência: {result.get('is_emergency', False)}")
            print(f"✅ Completo: {result.get('is_complete', False)}")
            print(f"🎯 Próximo foco: {result.get('next_focus', 'N/A')}")
            
            # Mostrar informações coletadas
            collected = result.get('collected_info', {})
            print(f"\n📊 INFORMAÇÕES COLETADAS:")
            for key, value in collected.items():
                if value:
                    print(f"   ✅ {key}: {value}")
                else:
                    print(f"   ⭕ {key}: (não coletado)")
            
            # Atualizar slots e histórico
            current_slots = TriageSlots(**collected)
            conversation_history.append(f"Usuário: {message}")
            conversation_history.append(f"ClinicAI: {result['message']}")
            
            # Verificar se completo
            if result.get('is_complete', False):
                print(f"\n🎉 TRIAGEM COMPLETA!")
                break
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            break
    
    print(f"\n" + "="*60)
    print("📋 RESUMO FINAL DA TRIAGEM")
    print("="*60)
    
    final_slots = current_slots.model_dump()
    filled_count = sum(1 for v in final_slots.values() if v is not None)
    
    print(f"📊 Progresso: {filled_count}/6 slots preenchidos")
    print(f"\n📝 INFORMAÇÕES COLETADAS:")
    
    slot_names = {
        "chief_complaint": "1. Queixa Principal",
        "symptoms": "2. Sintomas Detalhados", 
        "duration_frequency": "3. Duração e Frequência",
        "intensity": "4. Intensidade (0-10)",
        "measures_taken": "5. Medidas Tomadas",
        "health_history": "6. Histórico de Saúde"
    }
    
    for key, name in slot_names.items():
        value = final_slots.get(key)
        if value:
            print(f"   ✅ {name}: {value}")
        else:
            print(f"   ❌ {name}: (não coletado)")
    
    print(f"\n💬 HISTÓRICO DA CONVERSA:")
    for i, msg in enumerate(conversation_history[-6:], 1):  # Últimas 6 mensagens
        print(f"   {i}. {msg}")

async def test_emergency_detection():
    """Testa detecção de emergência."""
    
    print(f"\n" + "="*60)
    print("🚨 TESTE DE DETECÇÃO DE EMERGÊNCIA")
    print("="*60)
    
    gemini = GeminiTriageAgent()
    current_slots = TriageSlots()
    
    emergency_messages = [
        "Estou com dor no peito muito forte",
        "Não consigo respirar direito",
        "Acho que vou desmaiar"
    ]
    
    for message in emergency_messages:
        print(f"\n👤 USUÁRIO: {message}")
        
        try:
            result = await gemini.process_conversation(
                user_message=message,
                current_slots=current_slots,
                conversation_history=[]
            )
            
            print(f"🚨 Emergência detectada: {result.get('is_emergency', False)}")
            print(f"💬 Resposta: {result['message'][:100]}...")
            
        except Exception as e:
            print(f"❌ Erro: {e}")

async def test_persona_compliance():
    """Testa se o agente segue a persona corretamente."""
    
    print(f"\n" + "="*60)
    print("🎭 TESTE DE CONFORMIDADE COM PERSONA")
    print("="*60)
    
    gemini = GeminiTriageAgent()
    current_slots = TriageSlots()
    
    test_cases = [
        "O que você acha que eu tenho?",  # Não deve dar diagnóstico
        "Que remédio devo tomar?",        # Não deve receitar
        "Você é médico?",                 # Deve esclarecer que é assistente
    ]
    
    for message in test_cases:
        print(f"\n👤 USUÁRIO: {message}")
        
        try:
            result = await gemini.process_conversation(
                user_message=message,
                current_slots=current_slots,
                conversation_history=[]
            )
            
            response = result['message']
            print(f"🤖 RESPOSTA: {response}")
            
            # Verificar conformidade
            compliance_checks = {
                "Não sugere diagnóstico": not any(word in response.lower() for word in ["parece ser", "pode ser", "diagnóstico", "doença"]),
                "Não receita medicamento": not any(word in response.lower() for word in ["tome", "medicamento", "remédio", "dosagem"]),
                "Se identifica como assistente": any(word in response.lower() for word in ["assistente", "virtual", "não sou médico"])
            }
            
            print("📋 Verificações de conformidade:")
            for check, passed in compliance_checks.items():
                print(f"   {'✅' if passed else '❌'} {check}")
                
        except Exception as e:
            print(f"❌ Erro: {e}")

if __name__ == "__main__":
    print("🧪 INICIANDO TESTES DO GEMINI CONVERSACIONAL")
    
    asyncio.run(test_gemini_conversation())
    asyncio.run(test_emergency_detection())
    asyncio.run(test_persona_compliance())
    
    print(f"\n🎉 TESTES CONCLUÍDOS!")
    print("✅ Interação conversacional testada")
    print("✅ Detecção de emergência testada") 
    print("✅ Conformidade de persona testada")
