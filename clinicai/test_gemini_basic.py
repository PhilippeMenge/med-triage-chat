#!/usr/bin/env python3
"""
Teste básico do Gemini com mensagens completamente não-médicas.
"""

import asyncio
from clinicai_mongodb_fixed import GeminiTriageAgent, TriageSlots, connect_mongodb

async def test_basic_gemini():
    """Testa Gemini com mensagens completamente não-médicas."""
    
    print("🧪 TESTE BÁSICO: Gemini com Mensagens Não-Médicas")
    print("=" * 60)
    
    await connect_mongodb()
    gemini = GeminiTriageAgent()
    
    if not gemini.client:
        print("❌ Gemini não configurado")
        return
    
    print("✅ Gemini configurado - testando mensagens básicas")
    
    # Teste com mensagens completamente neutras
    test_messages = [
        "Olá, como você está?",
        "Preciso agendar uma consulta",
        "Gostaria de marcar um horário", 
        "Quero falar com alguém sobre minha situação",
        "Tenho algumas questões para discutir"
    ]
    
    print(f"\n📊 TESTANDO {len(test_messages)} MENSAGENS NEUTRAS")
    print("="*60)
    
    success_count = 0
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}️⃣ TESTE: '{message}'")
        
        current_slots = TriageSlots()
        conversation_history = []
        
        try:
            result = await gemini.process_conversation(
                user_message=message,
                current_slots=current_slots,
                conversation_history=conversation_history
            )
            
            if result and 'message' in result:
                response_msg = result['message']
                print(f"   ✅ SUCESSO: {response_msg[:80]}...")
                
                # Verificar se tem sinais de resposta do Gemini (não fallback)
                is_gemini_response = (
                    len(response_msg) > 50 and  # Resposta substancial
                    not any(phrase in response_msg for phrase in [
                        "Para começarmos, pode me contar qual é o motivo",
                        "Entendi. Agora pode me descrever",
                        "Obrigada por compartilhar"
                    ])
                )
                
                if is_gemini_response:
                    print(f"   🤖 FONTE: Gemini (resposta personalizada)")
                    success_count += 1
                else:
                    print(f"   🔄 FONTE: Fallback (resposta padrão)")
                
            else:
                print(f"   ❌ FALHA: Nenhuma resposta")
                
        except Exception as e:
            print(f"   ❌ ERRO: {e}")
        
        # Pausa entre testes
        await asyncio.sleep(1)
    
    print(f"\n" + "="*60)
    print("📊 RESULTADOS FINAIS")
    print("="*60)
    
    print(f"📈 ESTATÍSTICAS:")
    print(f"   🤖 Sucessos Gemini: {success_count}/{len(test_messages)}")
    print(f"   📊 Taxa de sucesso: {success_count/len(test_messages)*100:.1f}%")
    
    if success_count == 0:
        print(f"\n❌ DIAGNÓSTICO: Gemini está completamente bloqueado")
        print(f"   🔧 POSSÍVEL CAUSA: Filtros muito restritivos ou configuração inválida")
        print(f"   💡 RECOMENDAÇÃO: Verificar configurações da API e safety settings")
    elif success_count == len(test_messages):
        print(f"\n✅ DIAGNÓSTICO: Gemini funcionando perfeitamente")
        print(f"   🎯 CONCLUSÃO: Problema anterior era específico do contexto médico")
    else:
        print(f"\n⚠️ DIAGNÓSTICO: Gemini parcialmente funcional")
        print(f"   🔧 AÇÃO: Otimizar prompts e safety settings")

if __name__ == "__main__":
    print("🚀 INICIANDO TESTE BÁSICO DO GEMINI")
    
    asyncio.run(test_basic_gemini())
    
    print(f"\n🎉 TESTE CONCLUÍDO!")
    print("✅ Análise básica do Gemini realizada")
