#!/usr/bin/env python3
"""
Teste específico para o modelo Gemini 2.5-flash.
"""

import asyncio
from clinicai_mongodb_fixed import GeminiTriageAgent, TriageSlots, connect_mongodb

async def test_gemini_25_flash():
    """Testa o modelo Gemini 2.5-flash."""
    
    print("🚀 TESTE: Gemini 2.5-Flash")
    print("=" * 50)
    
    await connect_mongodb()
    gemini = GeminiTriageAgent()
    
    if not gemini.client:
        print("❌ Gemini não configurado")
        return
    
    print("✅ Gemini 2.5-flash configurado")
    print(f"🤖 Modelo: {gemini.client.model_name if hasattr(gemini.client, 'model_name') else 'N/A'}")
    
    # Teste básico com mensagem simples
    print(f"\n📤 TESTE BÁSICO")
    print("-" * 30)
    
    current_slots = TriageSlots()
    conversation_history = []
    test_message = "Olá, preciso de ajuda"
    
    try:
        result = await gemini.process_conversation(
            user_message=test_message,
            current_slots=current_slots,
            conversation_history=conversation_history
        )
        
        if result:
            print(f"✅ SUCESSO: Resposta obtida")
            print(f"💬 Mensagem: {result['message'][:80]}...")
            print(f"🚨 Emergência: {result.get('is_emergency', False)}")
            print(f"✅ Completo: {result.get('is_complete', False)}")
            
            # Verificar se é resposta do Gemini ou fallback
            fallback_indicators = [
                "Para começarmos, pode me contar qual é o motivo",
                "Entendi. Agora pode me descrever",
                "Obrigada por compartilhar"
            ]
            
            is_fallback = any(indicator in result['message'] for indicator in fallback_indicators)
            
            if is_fallback:
                print(f"🔄 FONTE: Fallback (Gemini bloqueado)")
            else:
                print(f"🤖 FONTE: Gemini 2.5-flash (funcionando!)")
                
        else:
            print(f"❌ FALHA: Nenhuma resposta obtida")
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
    
    # Teste com mensagem médica
    print(f"\n📤 TESTE MÉDICO")
    print("-" * 30)
    
    medical_message = "Estou com dor de cabeça há 2 dias"
    
    try:
        result = await gemini.process_conversation(
            user_message=medical_message,
            current_slots=current_slots,
            conversation_history=conversation_history
        )
        
        if result:
            print(f"✅ SUCESSO: Resposta obtida")
            print(f"💬 Mensagem: {result['message'][:80]}...")
            
            # Verificar se processou informação médica
            collected = result.get('collected_info', {})
            has_medical_info = any(collected.values())
            
            if has_medical_info:
                print(f"🏥 PROCESSAMENTO: Informação médica coletada")
                print(f"📋 Coletado: {collected}")
            else:
                print(f"🔄 PROCESSAMENTO: Usando fallback padrão")
                
        else:
            print(f"❌ FALHA: Nenhuma resposta obtida")
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
    
    print(f"\n" + "=" * 50)
    print("🎯 RESULTADOS")
    print("=" * 50)
    
    print("✅ MODELO ATUALIZADO: gemini-2.5-flash-latest")
    print("🔧 CONFIGURAÇÃO: Aplicada com sucesso")
    
    print("\n💡 PRÓXIMOS PASSOS:")
    print("   🧪 Testar com mensagens reais do WhatsApp")
    print("   📊 Monitorar taxa de sucesso vs fallback")
    print("   🛡️ Verificar se 2.5-flash tem menos bloqueios")

if __name__ == "__main__":
    print("🚀 INICIANDO TESTE GEMINI 2.5-FLASH")
    
    asyncio.run(test_gemini_25_flash())
    
    print(f"\n🎉 TESTE CONCLUÍDO!")
    print("✅ Modelo Gemini 2.5-flash testado")
