#!/usr/bin/env python3
"""
Script para limpar banco de dados MongoDB Atlas.
"""

import asyncio
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

async def clean_mongodb():
    """Limpa todas as collections do MongoDB."""
    
    print("🍃 Limpando MongoDB Atlas")
    print("=" * 40)
    
    # Configurações MongoDB
    MONGODB_URI = os.getenv("MONGODB_URI")
    MONGODB_DB = os.getenv("MONGODB_DB", "clinicai_db")
    
    if not MONGODB_URI:
        print("❌ MONGODB_URI não configurado no .env")
        return
    
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        print("✅ Driver MongoDB disponível")
    except ImportError:
        print("❌ Motor não instalado!")
        print("📦 Execute: pip install motor pymongo")
        return
    
    try:
        # Conectar ao MongoDB
        print(f"🔌 Conectando ao MongoDB...")
        client = AsyncIOMotorClient(MONGODB_URI)
        db = client[MONGODB_DB]
        
        # Testar conexão
        await client.admin.command('ping')
        print(f"✅ Conectado ao database: {MONGODB_DB}")
        
        # Listar collections existentes
        collections = await db.list_collection_names()
        print(f"📁 Collections encontradas: {collections}")
        
        if not collections:
            print("📭 Nenhuma collection para limpar")
            client.close()
            return
        
        # Contar documentos antes da limpeza
        print(f"\n📊 Contagem antes da limpeza:")
        total_docs_before = 0
        for collection_name in collections:
            count = await db[collection_name].count_documents({})
            print(f"   📄 {collection_name}: {count} documentos")
            total_docs_before += count
        
        print(f"\n🗑️ Total de documentos a serem removidos: {total_docs_before}")
        
        if total_docs_before == 0:
            print("✅ Database já está limpo!")
            client.close()
            return
        
        # Confirmar limpeza
        print(f"\n⚠️ ATENÇÃO: Isso irá remover TODOS os dados!")
        print(f"   Database: {MONGODB_DB}")
        print(f"   Collections: {', '.join(collections)}")
        print(f"   Total documentos: {total_docs_before}")
        
        # Limpar cada collection
        print(f"\n🧹 Iniciando limpeza...")
        
        for collection_name in collections:
            print(f"   🗑️ Limpando {collection_name}...")
            result = await db[collection_name].delete_many({})
            print(f"   ✅ {collection_name}: {result.deleted_count} documentos removidos")
        
        # Verificar limpeza
        print(f"\n📊 Verificação pós-limpeza:")
        total_docs_after = 0
        for collection_name in collections:
            count = await db[collection_name].count_documents({})
            print(f"   📄 {collection_name}: {count} documentos")
            total_docs_after += count
        
        # Fechar conexão
        client.close()
        
        print(f"\n🎉 LIMPEZA CONCLUÍDA!")
        print(f"✅ Documentos removidos: {total_docs_before}")
        print(f"✅ Documentos restantes: {total_docs_after}")
        print(f"✅ MongoDB Atlas limpo e pronto para uso")
        
    except Exception as e:
        print(f"\n❌ Erro na limpeza: {e}")
        
        # Diagnóstico de erro
        error_str = str(e).lower()
        
        if "authentication failed" in error_str:
            print(f"\n🔑 ERRO DE AUTENTICAÇÃO:")
            print(f"   ❌ Credenciais incorretas")
            print(f"   🔧 Verificar MONGODB_URI no .env")
            
        elif "timeout" in error_str:
            print(f"\n⏰ ERRO DE TIMEOUT:")
            print(f"   ❌ Não conseguiu conectar")
            print(f"   🔧 Verificar internet e firewall")
            
        else:
            print(f"\n🔧 SOLUÇÕES:")
            print(f"   1. Verificar se cluster está ativo")
            print(f"   2. Verificar credenciais no .env")
            print(f"   3. Verificar conexão com internet")

if __name__ == "__main__":
    print("🚨 AVISO: Este script irá LIMPAR TODOS os dados do MongoDB!")
    print("   Pressione Ctrl+C para cancelar ou Enter para continuar...")
    
    try:
        input()  # Aguardar confirmação do usuário
        asyncio.run(clean_mongodb())
    except KeyboardInterrupt:
        print("\n❌ Operação cancelada pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
