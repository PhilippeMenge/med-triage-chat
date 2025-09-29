#!/usr/bin/env python3
"""
Teste específico para diferenciar quando é Gemini vs Fallback.
"""

import asyncio
from clinicai_mongodb_fixed import GeminiTriageAgent, TriageSlots, connect_mongodb

async def test_gemini_vs_fallback():
    """Testa se conseguimos distinguir Gemini de Fallback."""
    
    print("🔍 TESTE: Gemini vs Fallback - Identificação")
    print("=" * 60)
    
    await connect_mongodb()
    gemini = GeminiTriageAgent()
    
    if not gemini.client:
        print("❌ Gemini não configurado")
        return
    
    print("✅ Gemini configurado - testando diferenciação")
    
    # Teste com diferentes mensagens que devem gerar respostas diferentes
    test_scenarios = [
        {
            "message": "Olá, preciso de ajuda",
            "expected_type": "Saudação inicial"
        },
        {
            "message": "Estou com dor de cabeça há 3 dias",
            "expected_type": "Sintoma específico - deveria gerar pergunta sobre sintomas"
        },
        {
            "message": "A dor começou ontem e é muito forte",
            "expected_type": "Informação temporal - deveria focar em duração"
        },
        {
            "message": "Numa escala de 1 a 10, é uns 8",
            "expected_type": "Resposta sobre intensidade - deveria perguntar medidas tomadas"
        },
        {
            "message": "Já tomei paracetamol",
            "expected_type": "Medidas tomadas - deveria perguntar histórico"
        }
    ]
    
    print(f"\n📊 TESTANDO {len(test_scenarios)} CENÁRIOS DIFERENTES")
    print("="*60)
    
    responses = []
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}️⃣ CENÁRIO: {scenario['expected_type']}")
        print(f"   👤 Mensagem: '{scenario['message']}'")
        
        # Criar slots progressivos para simular conversa em andamento
        current_slots = TriageSlots()
        if i >= 2:
            current_slots.chief_complaint = "dor de cabeça"
        if i >= 3:
            current_slots.symptoms = "dor forte na cabeça"
        if i >= 4:
            current_slots.duration_frequency = "começou ontem"
        if i >= 5:
            current_slots.intensity = "8 de 10"
        
        conversation_history = []
        if i > 1:
            conversation_history = [
                "ClinicAI: Para começarmos, pode me contar qual é o motivo do seu contato hoje?",
                "Usuário: Estou com dor de cabeça há 3 dias"
            ]
        
        try:
            result = await gemini.process_conversation(
                user_message=scenario['message'],
                current_slots=current_slots,
                conversation_history=conversation_history
            )
            
            if result:
                response_msg = result['message']
                print(f"   💬 Resposta: {response_msg[:100]}...")
                
                # Verificar se é resposta de fallback (sempre igual)
                fallback_indicators = [
                    "Para começarmos, pode me contar qual é o motivo",
                    "Entendi. Agora pode me descrever com mais detalhes",
                    "Obrigada por compartilhar. Desde quando",
                    "Compreendo. Em uma escala de 0 a 10",
                    "Entendo. Você já tentou fazer alguma coisa",
                    "Por último, você tem algum histórico"
                ]
                
                is_fallback = any(indicator in response_msg for indicator in fallback_indicators)
                
                if is_fallback:
                    print(f"   🔄 FONTE: Fallback (resposta padrão)")
                else:
                    print(f"   🤖 FONTE: Gemini (resposta personalizada)")
                
                responses.append({
                    'scenario': i,
                    'message': scenario['message'],
                    'response': response_msg,
                    'is_fallback': is_fallback,
                    'collected_info': result.get('collected_info', {}),
                    'is_emergency': result.get('is_emergency', False)
                })
                
            else:
                print(f"   ❌ FALHA: Nenhuma resposta obtida")
                responses.append({
                    'scenario': i,
                    'message': scenario['message'],
                    'response': None,
                    'is_fallback': True,
                    'collected_info': {},
                    'is_emergency': False
                })
                
        except Exception as e:
            print(f"   ❌ ERRO: {e}")
            responses.append({
                'scenario': i,
                'message': scenario['message'],
                'response': None,
                'is_fallback': True,
                'collected_info': {},
                'is_emergency': False
            })
        
        # Pausa entre testes
        await asyncio.sleep(0.5)
    
    print(f"\n" + "="*60)
    print("📊 ANÁLISE DOS RESULTADOS")
    print("="*60)
    
    gemini_count = sum(1 for r in responses if not r['is_fallback'] and r['response'])
    fallback_count = sum(1 for r in responses if r['is_fallback'])
    unique_responses = len(set(r['response'] for r in responses if r['response']))
    
    print(f"📈 ESTATÍSTICAS:")
    print(f"   🤖 Respostas do Gemini: {gemini_count}/{len(responses)}")
    print(f"   🔄 Respostas do Fallback: {fallback_count}/{len(responses)}")
    print(f"   🎯 Respostas únicas: {unique_responses}/{len(responses)}")
    
    print(f"\n📝 RESPOSTAS DETALHADAS:")
    for i, resp in enumerate(responses, 1):
        if resp['response']:
            print(f"   {i}. {'🤖 GEMINI' if not resp['is_fallback'] else '🔄 FALLBACK'}: {resp['response'][:80]}...")
        else:
            print(f"   {i}. ❌ SEM RESPOSTA")
    
    print(f"\n🎯 DIAGNÓSTICO:")
    if gemini_count == 0:
        print(f"   ❌ PROBLEMA: Gemini NUNCA está funcionando - sempre fallback")
        print(f"   🔧 AÇÃO: Investigar filtros de segurança ou configurações")
    elif gemini_count == len(responses):
        print(f"   ✅ PERFEITO: Gemini funcionando em todos os casos")
    else:
        print(f"   ⚠️ PARCIAL: Gemini funciona em {gemini_count}/{len(responses)} casos")
        print(f"   🔧 AÇÃO: Otimizar prompts para reduzir fallbacks")
    
    if unique_responses <= 2:
        print(f"   ⚠️ ALERTA: Muito poucas respostas únicas - possível problema")
    else:
        print(f"   ✅ VARIEDADE: Boa diversidade de respostas")

if __name__ == "__main__":
    print("🚀 INICIANDO TESTE GEMINI vs FALLBACK")
    
    asyncio.run(test_gemini_vs_fallback())
    
    print(f"\n🎉 TESTE CONCLUÍDO!")
    print("✅ Análise de diferenciação realizada")
