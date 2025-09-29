#!/usr/bin/env python3
"""
Demonstração do Sistema de Fallback dos Filtros de Segurança do Gemini
"""

import asyncio
import json
from typing import Dict, Any, List
from clinicai_mongodb_fixed import GeminiTriageAgent, TriageSlots

class FallbackDemo:
    """Demonstra como funciona o sistema de fallback."""
    
    def __init__(self):
        self.gemini = GeminiTriageAgent()
    
    async def demo_complete_fallback_system(self):
        """Demonstra todo o sistema de fallback em ação."""
        
        print("🛡️ DEMONSTRAÇÃO: Sistema de Fallback dos Filtros de Segurança")
        print("=" * 70)
        
        # Cenários que podem ser bloqueados
        test_scenarios = [
            {
                "name": "Consulta Médica Normal",
                "message": "Estou com dor de cabeça há 3 dias",
                "expected": "Deve funcionar normalmente"
            },
            {
                "name": "Sintomas Detalhados", 
                "message": "Tenho dor abdominal, náusea e febre de 38°C",
                "expected": "Pode ser bloqueado por conteúdo médico"
            },
            {
                "name": "Emergência Médica",
                "message": "Estou com dor no peito muito forte e falta de ar",
                "expected": "Pode ser bloqueado, mas fallback detecta emergência"
            },
            {
                "name": "Pergunta sobre Medicamento",
                "message": "Que remédio devo tomar para dor?",
                "expected": "Pode ser bloqueado por conteúdo farmacêutico"
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n{'='*20} CENÁRIO {i}: {scenario['name']} {'='*20}")
            print(f"👤 USUÁRIO: {scenario['message']}")
            print(f"🎯 ESPERADO: {scenario['expected']}")
            
            await self._test_scenario(scenario['message'])
    
    async def _test_scenario(self, message: str):
        """Testa um cenário específico."""
        current_slots = TriageSlots()
        
        try:
            # Tentar processar com Gemini
            result = await self.gemini.process_conversation(
                user_message=message,
                current_slots=current_slots,
                conversation_history=[]
            )
            
            # Analisar resultado
            if result:
                print(f"\n📊 RESULTADO:")
                print(f"   💬 Resposta: {result['message'][:80]}...")
                print(f"   🚨 Emergência: {result.get('is_emergency', False)}")
                print(f"   🔄 Fonte: {'Gemini' if self.gemini.client else 'Fallback'}")
                
                # Verificar se foi fallback
                if "Olá! Sou a ClinicAI" in result['message']:
                    print(f"   ⚠️ FALLBACK ATIVADO: Resposta padrão usada")
                else:
                    print(f"   ✅ GEMINI OK: Resposta personalizada")
            else:
                print(f"   ❌ ERRO: Nenhuma resposta obtida")
                
        except Exception as e:
            print(f"   ❌ EXCEÇÃO: {e}")

def explain_fallback_architecture():
    """Explica a arquitetura do sistema de fallback."""
    
    print("\n" + "="*70)
    print("🏗️ ARQUITETURA DO SISTEMA DE FALLBACK")
    print("="*70)
    
    print("""
🔄 FLUXO DE PROCESSAMENTO:

1️⃣ TENTATIVA PRINCIPAL - Gemini API
   ├── 📤 Envia prompt com contexto completo
   ├── ⚙️ Configurações de segurança: BLOCK_NONE
   ├── 🛡️ Gemini aplica filtros internos
   └── 📥 Recebe resposta ou bloqueio

2️⃣ DETECÇÃO DE BLOQUEIO
   ├── ❌ response.candidates vazio
   ├── ❌ response.candidates[0].content.parts vazio  
   ├── ❌ JSON malformado/incompleto
   └── ❌ Exceções de API

3️⃣ ATIVAÇÃO DO FALLBACK
   ├── 🚨 Detecção de emergência (palavras-chave)
   ├── 📋 Lógica de perguntas sequenciais
   ├── 💾 Extração básica de informações
   └── 📤 Resposta estruturada garantida

🛡️ TIPOS DE PROTEÇÃO:

NÍVEL 1 - Configuração de Segurança:
```python
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"}, 
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]
```

NÍVEL 2 - Detecção de Bloqueio:
```python
if not response.candidates or not response.candidates[0].content.parts:
    logger.warning("⚠️ Resposta Gemini bloqueada por filtro de segurança")
    return self._fallback_response(user_message, current_slots)
```

NÍVEL 3 - Parser Robusto:
```python
try:
    result = json.loads(response_text)
    return result
except json.JSONDecodeError:
    return self._fallback_response(user_message, current_slots)
```

NÍVEL 4 - Fallback Completo:
```python
def _fallback_response(self, user_message: str, current_slots: TriageSlots):
    # 1. Detectar emergência
    emergency_detected = is_emergency(user_message)
    
    # 2. Lógica de perguntas
    next_slot = current_slots.get_next_slot_to_collect()
    
    # 3. Resposta estruturada
    return {"message": "...", "collected_info": {...}, ...}
```

🎯 VANTAGENS DO SISTEMA:

✅ ROBUSTEZ: Nunca falha completamente
✅ SEGURANÇA: Detecta emergências mesmo sem Gemini  
✅ CONTINUIDADE: Mantém fluxo de triagem
✅ TRANSPARÊNCIA: Logs indicam quando fallback é usado
✅ FLEXIBILIDADE: Funciona com ou sem Gemini

⚠️ LIMITAÇÕES DO FALLBACK:

❌ Menos inteligente que Gemini
❌ Perguntas mais rígidas/sequenciais
❌ Extração de informações mais básica
❌ Menos empático/conversacional
""")

async def demo_emergency_fallback():
    """Demonstra fallback específico para emergências."""
    
    print("\n" + "="*70)
    print("🚨 DEMONSTRAÇÃO: Fallback de Emergência")
    print("="*70)
    
    demo = FallbackDemo()
    
    emergency_cases = [
        "Estou com dor no peito muito forte",
        "Não consigo respirar direito", 
        "Acho que vou desmaiar",
        "Estou sangrando muito"
    ]
    
    print("🎯 OBJETIVO: Mesmo se Gemini for bloqueado, emergências devem ser detectadas")
    
    for case in emergency_cases:
        print(f"\n👤 CASO: {case}")
        
        # Simular fallback direto (como se Gemini fosse bloqueado)
        current_slots = TriageSlots()
        result = demo.gemini._fallback_response(case, current_slots)
        
        print(f"🚨 Emergência detectada: {result['is_emergency']}")
        print(f"💬 Resposta: {result['message'][:60]}...")

async def demo_json_parsing_fallback():
    """Demonstra fallback para erros de parsing JSON."""
    
    print("\n" + "="*70) 
    print("🔧 DEMONSTRAÇÃO: Fallback de Parsing JSON")
    print("="*70)
    
    # Simular respostas JSON problemáticas que o Gemini pode retornar
    problematic_responses = [
        '{"message": "Olá! Como posso ajudar?", "collected_info": {',  # JSON incompleto
        '{"message": "Resposta com "aspas" problemáticas"}',  # Aspas não escapadas
        'Resposta sem JSON',  # Texto puro
        '```json\n{"message": "Com markdown"}\n```',  # Com formatação markdown
    ]
    
    print("🎯 OBJETIVO: Parser robusto deve lidar com JSON malformado")
    
    for i, response in enumerate(problematic_responses, 1):
        print(f"\n{i}. RESPOSTA PROBLEMÁTICA:")
        print(f"   📄 Raw: {response[:50]}...")
        
        try:
            # Simular limpeza que o sistema faz
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned.replace("```json", "").replace("```", "").strip()
            elif cleaned.startswith("```"):
                cleaned = cleaned.replace("```", "").strip()
            
            result = json.loads(cleaned)
            print(f"   ✅ SUCESSO: JSON parseado")
        except json.JSONDecodeError as e:
            print(f"   ❌ FALHA: {e}")
            print(f"   🔄 FALLBACK: Sistema usaria resposta padrão")

async def main():
    """Função principal da demonstração."""
    print("🧪 INICIANDO DEMONSTRAÇÃO DO SISTEMA DE FALLBACK")
    
    # Explicar arquitetura
    explain_fallback_architecture()
    
    # Demonstrar cenários
    demo = FallbackDemo()
    await demo.demo_complete_fallback_system()
    
    # Demonstrar emergências
    await demo_emergency_fallback()
    
    # Demonstrar parsing
    await demo_json_parsing_fallback()
    
    print(f"\n🎉 DEMONSTRAÇÃO CONCLUÍDA!")
    print("✅ Sistema de fallback robusto e confiável")
    print("✅ Garante funcionamento mesmo com bloqueios")
    print("✅ Mantém detecção de emergência sempre ativa")

if __name__ == "__main__":
    asyncio.run(main())
