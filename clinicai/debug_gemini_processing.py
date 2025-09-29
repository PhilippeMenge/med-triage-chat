#!/usr/bin/env python3
"""
Debug específico para identificar por que o Gemini está entrando em fallback.
"""

import asyncio
import json
from clinicai_mongodb_fixed import GeminiTriageAgent, TriageSlots, connect_mongodb

async def debug_gemini_processing():
    """Debug detalhado do processamento do Gemini."""
    
    print("🔍 DEBUG: Processamento do Gemini")
    print("=" * 60)
    
    await connect_mongodb()
    gemini = GeminiTriageAgent()
    
    if not gemini.client:
        print("❌ Gemini não configurado")
        return
    
    print("✅ Gemini configurado - iniciando debug detalhado")
    
    # Teste simples
    test_message = "Estou com dor de cabeça"
    current_slots = TriageSlots()
    conversation_history = []
    
    print(f"\n📤 TESTE SIMPLES")
    print(f"   👤 Mensagem: '{test_message}'")
    print(f"   📋 Slots atuais: {current_slots.model_dump()}")
    print(f"   💬 Histórico: {conversation_history}")
    
    try:
        print(f"\n🔧 CONFIGURAÇÕES DO GEMINI:")
        print(f"   🤖 Modelo: {gemini.client.model_name if hasattr(gemini.client, 'model_name') else 'N/A'}")
        print(f"   🔑 API Key configurada: {'Sim' if gemini.client else 'Não'}")
        
        # Testar chamada direta ao Gemini
        print(f"\n🧪 TESTANDO CHAMADA DIRETA AO GEMINI...")
        
        # Construir prompt manualmente como no código
        history_text = ""
        if conversation_history:
            history_text = "\n".join(conversation_history[-6:])
        
        collected_info = {
            "chief_complaint": current_slots.chief_complaint,
            "symptoms": current_slots.symptoms,
            "duration_frequency": current_slots.duration_frequency,
            "intensity": current_slots.intensity,
            "history": current_slots.health_history,
            "measures_taken": current_slots.measures_taken
        }
        
        is_conversation_start = test_message == "[INÍCIO DA CONVERSA]"
        
        if is_conversation_start:
            user_prompt = f"""
CONTEXTO DA CONVERSA:
{history_text}

SITUAÇÃO: Este é o INÍCIO de uma nova triagem. O usuário acabou de receber a mensagem de boas-vindas.

INSTRUÇÕES:
1. Faça a primeira pergunta para iniciar a coleta de informações
2. Comece perguntando sobre a queixa principal de forma acolhedora
3. Seja empático e profissional
4. Retorne no formato JSON especificado

IMPORTANTE: Esta é a PRIMEIRA pergunta da triagem. Seja acolhedor e direto.
"""
        else:
            user_prompt = f"""
CONTEXTO DA CONVERSA:
{history_text}

INFORMAÇÕES JÁ COLETADAS:
{json.dumps(collected_info, indent=2, ensure_ascii=False)}

NOVA MENSAGEM DO USUÁRIO:
"{test_message}"

INSTRUÇÕES:
1. Analise a mensagem do usuário no contexto da conversa
2. Extraia/atualize informações relevantes para os 6 tópicos da triagem
3. Detecte sinais de emergência
4. Responda de forma empática e natural
5. Se necessário, faça uma pergunta para coletar informação faltante
6. Retorne no formato JSON especificado

Se todas as 6 informações estiverem coletadas, marque "is_complete": true e faça um resumo acolhedor.
"""
        
        print(f"📝 PROMPT CONSTRUÍDO:")
        print(f"   📏 Tamanho do prompt: {len(user_prompt)} caracteres")
        print(f"   🔤 Primeiras 200 chars: {user_prompt[:200]}...")
        
        # Configurações como no código (apenas categorias válidas)
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
        
        generation_config = {
            "temperature": 0.3,
            "max_output_tokens": 400,
            "top_p": 0.8,
            "top_k": 40,
            "candidate_count": 1
        }
        
        print(f"\n⚙️ CONFIGURAÇÕES:")
        print(f"   🌡️ Temperature: {generation_config['temperature']}")
        print(f"   📊 Max tokens: {generation_config['max_output_tokens']}")
        print(f"   🛡️ Safety settings: {len(safety_settings)} categorias")
        
        # Fazer chamada real
        print(f"\n🚀 FAZENDO CHAMADA PARA GEMINI...")
        
        import google.generativeai as genai
        
        full_prompt = f"{gemini._get_system_prompt()}\n\n{user_prompt}"
        print(f"📏 Prompt completo: {len(full_prompt)} caracteres")
        
        response = await asyncio.to_thread(
            gemini.client.generate_content,
            full_prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        print(f"✅ RESPOSTA RECEBIDA!")
        print(f"   📊 Candidates: {len(response.candidates) if response.candidates else 0}")
        
        if response.candidates:
            candidate = response.candidates[0]
            print(f"   🎯 Finish reason: {candidate.finish_reason}")
            print(f"   🛡️ Safety ratings: {len(candidate.safety_ratings) if candidate.safety_ratings else 0}")
            
            if candidate.safety_ratings:
                for rating in candidate.safety_ratings:
                    print(f"      - {rating.category}: {rating.probability}")
            
            if candidate.content and candidate.content.parts:
                response_text = response.text.strip()
                print(f"   📝 Texto da resposta: {len(response_text)} caracteres")
                print(f"   🔤 Primeiros 200 chars: {response_text[:200]}...")
                
                # Tentar fazer parse do JSON
                try:
                    # Limpar JSON como no código
                    if response_text.startswith("```json"):
                        response_text = response_text.replace("```json", "").replace("```", "").strip()
                    elif response_text.startswith("```"):
                        response_text = response_text.replace("```", "").strip()
                    
                    result = json.loads(response_text)
                    print(f"   ✅ JSON VÁLIDO!")
                    print(f"   💬 Mensagem: {result.get('message', 'N/A')[:100]}...")
                    print(f"   🚨 Emergência: {result.get('is_emergency', 'N/A')}")
                    print(f"   ✅ Completo: {result.get('is_complete', 'N/A')}")
                    
                except json.JSONDecodeError as e:
                    print(f"   ❌ ERRO JSON: {e}")
                    print(f"   📄 JSON problemático: {response_text}")
                    
            else:
                print(f"   ❌ SEM CONTEÚDO: Resposta bloqueada")
        else:
            print(f"   ❌ SEM CANDIDATES: Resposta completamente bloqueada")
            
        # Verificar se há prompt feedback
        if hasattr(response, 'prompt_feedback'):
            print(f"   📋 Prompt feedback: {response.prompt_feedback}")
            
    except Exception as e:
        print(f"❌ ERRO NA CHAMADA DIRETA: {e}")
        print(f"   🔍 Tipo do erro: {type(e).__name__}")
        print(f"   📄 Detalhes: {str(e)}")
        
        # Verificar se é erro de quota
        if "quota" in str(e).lower():
            print(f"   💰 PROBLEMA DE QUOTA: API atingiu limite")
        elif "safety" in str(e).lower():
            print(f"   🛡️ PROBLEMA DE SEGURANÇA: Filtros bloquearam")
        elif "medical" in str(e).lower():
            print(f"   🏥 PROBLEMA MÉDICO: Categoria médica bloqueada")
    
    print(f"\n🔄 TESTANDO MÉTODO PROCESS_CONVERSATION...")
    
    try:
        result = await gemini.process_conversation(
            user_message=test_message,
            current_slots=current_slots,
            conversation_history=conversation_history
        )
        
        if result:
            print(f"✅ PROCESS_CONVERSATION FUNCIONOU!")
            print(f"   💬 Mensagem: {result['message'][:100]}...")
        else:
            print(f"❌ PROCESS_CONVERSATION RETORNOU NONE")
            
    except Exception as e:
        print(f"❌ ERRO EM PROCESS_CONVERSATION: {e}")

if __name__ == "__main__":
    print("🚀 INICIANDO DEBUG DO PROCESSAMENTO GEMINI")
    
    asyncio.run(debug_gemini_processing())
    
    print(f"\n🎯 DEBUG CONCLUÍDO!")
    print("✅ Análise detalhada do Gemini realizada")
