#!/usr/bin/env python3
"""
Script para configurar e testar Gemini API.
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_gemini_api():
    """Testa a API do Gemini."""
    print("🤖 Configuração do Gemini API")
    print("=" * 40)
    
    # Verificar se a chave existe
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key or api_key == "fake_key_for_testing":
        print("❌ GEMINI_API_KEY não configurada!")
        print("\n🔧 Como obter sua chave:")
        print("1. Acesse: https://makersuite.google.com/app/apikey")
        print("2. Faça login com sua conta Google")
        print("3. Clique em 'Create API Key'")
        print("4. Copie a chave gerada")
        print("5. Adicione no arquivo .env:")
        print("   GEMINI_API_KEY=sua_chave_aqui")
        return False
    
    print(f"✅ API Key encontrada: {api_key[:20]}...")
    
    # Testar conexão
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Listar modelos disponíveis
        print("\n📋 Modelos disponíveis:")
        models = genai.list_models()
        available_models = []
        
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                available_models.append(model.name)
                print(f"   ✅ {model.name}")
        
        if not available_models:
            print("   ❌ Nenhum modelo disponível para generateContent")
            return False
        
        # Testar modelo gemini-flash-latest (Gemini 1.5 Flash)
        if "models/gemini-flash-latest" in available_models:
            print(f"\n🧪 Testando gemini-flash-latest (Gemini 1.5 Flash)...")
            model = genai.GenerativeModel("gemini-flash-latest")
            
            response = model.generate_content("Diga apenas 'OK' se você está funcionando")
            print(f"   Resposta: {response.text.strip()}")
            print("   ✅ Gemini 1.5 Flash funcionando!")
            return True
        else:
            print("\n❌ Modelo gemini-flash-latest não disponível")
            print("   Modelos disponíveis:", available_models[:5])  # Mostrar apenas os primeiros 5
            return False
            
    except Exception as e:
        print(f"\n❌ Erro ao testar Gemini: {e}")
        return False

def update_env_file():
    """Atualiza arquivo .env com nova chave."""
    print("\n🔑 Configuração da chave API:")
    
    new_key = input("Digite sua chave do Gemini API: ").strip()
    
    if not new_key:
        print("❌ Chave não fornecida")
        return False
    
    # Ler arquivo .env atual
    env_lines = []
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            env_lines = f.readlines()
    
    # Atualizar ou adicionar chave
    updated = False
    for i, line in enumerate(env_lines):
        if line.startswith("GEMINI_API_KEY="):
            env_lines[i] = f"GEMINI_API_KEY={new_key}\n"
            updated = True
            break
    
    if not updated:
        env_lines.append(f"GEMINI_API_KEY={new_key}\n")
    
    # Salvar arquivo
    with open(".env", "w") as f:
        f.writelines(env_lines)
    
    print("✅ Chave salva no arquivo .env")
    return True

if __name__ == "__main__":
    success = test_gemini_api()
    
    if not success:
        print("\n" + "=" * 40)
        choice = input("Deseja configurar a chave agora? (s/n): ").lower()
        
        if choice == 's':
            if update_env_file():
                print("\n🔄 Testando novamente...")
                # Recarregar .env
                load_dotenv(override=True)
                success = test_gemini_api()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 Gemini API configurado e funcionando!")
        print("   A aplicação pode usar IA para triagem agora.")
    else:
        print("⚠️  Gemini não configurado")
        print("   A aplicação funcionará com fallback (perguntas fixas)")
    print("=" * 40)
