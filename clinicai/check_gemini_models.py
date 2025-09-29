#!/usr/bin/env python3
"""
Verificar modelos Gemini disponíveis.
"""

import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()

def check_available_models():
    """Verifica modelos Gemini disponíveis."""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY não encontrada")
        return
    
    print("🔍 VERIFICANDO MODELOS GEMINI DISPONÍVEIS")
    print("=" * 50)
    
    try:
        genai.configure(api_key=api_key)
        
        print("✅ API configurada - listando modelos...")
        
        models = genai.list_models()
        
        flash_models = []
        all_models = []
        
        for model in models:
            model_name = model.name
            all_models.append(model_name)
            
            if "flash" in model_name.lower():
                flash_models.append(model_name)
                
        print(f"\n🚀 MODELOS FLASH DISPONÍVEIS ({len(flash_models)}):")
        for model in flash_models:
            print(f"   - {model}")
            
        print(f"\n📊 TODOS OS MODELOS ({len(all_models)}):")
        for model in all_models[:10]:  # Primeiros 10
            print(f"   - {model}")
        if len(all_models) > 10:
            print(f"   ... e mais {len(all_models) - 10} modelos")
            
        # Testar modelos Flash específicos
        test_models = [
            "models/gemini-2.5-flash",
            "models/gemini-1.5-flash", 
            "models/gemini-flash-latest",
            "models/gemini-2.5-flash-latest"
        ]
        
        print(f"\n🧪 TESTANDO MODELOS ESPECÍFICOS:")
        
        for test_model in test_models:
            try:
                model = genai.GenerativeModel(test_model)
                print(f"   ✅ {test_model} - DISPONÍVEL")
            except Exception as e:
                print(f"   ❌ {test_model} - ERRO: {str(e)[:80]}...")
                
    except Exception as e:
        print(f"❌ Erro ao verificar modelos: {e}")

if __name__ == "__main__":
    check_available_models()
