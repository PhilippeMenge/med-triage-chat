#!/usr/bin/env python3
"""
Script direto para limpar MongoDB Atlas (sem confirmação interativa).
"""

import asyncio
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

async def clean_mongodb_direct():
    """Limpa MongoDB diretamente."""
    
    print("🍃 Limpando MongoDB Atlas")
    print("=" * 40)
    
    MONGODB_URI = os.getenv("MONGODB_URI")
    MONGODB_DB = os.getenv("MONGODB_DB", "clinicai_db")
    
    if not MONGODB_URI:
        print("❌ MONGODB_URI não configurado")
        return
    
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        # Conectar
        client = AsyncIOMotorClient(MONGODB_URI)
        db = client[MONGODB_DB]
        
        # Testar conexão
        await client.admin.command('ping')
        print(f"✅ Conectado: {MONGODB_DB}")
        
        # Listar collections
        collections = await db.list_collection_names()
        print(f"📁 Collections: {collections}")
        
        if not collections:
            print("📭 Database já está vazio")
            client.close()
            return
        
        # Contar documentos
        total_before = 0
        for collection_name in collections:
            count = await db[collection_name].count_documents({})
            print(f"   📄 {collection_name}: {count} docs")
            total_before += count
        
        print(f"🗑️ Total a remover: {total_before}")
        
        if total_before == 0:
            print("✅ Já está limpo!")
            client.close()
            return
        
        # Limpar collections
        print("🧹 Limpando...")
        for collection_name in collections:
            result = await db[collection_name].delete_many({})
            print(f"   ✅ {collection_name}: {result.deleted_count} removidos")
        
        # Verificar
        total_after = 0
        for collection_name in collections:
            count = await db[collection_name].count_documents({})
            total_after += count
        
        client.close()
        
        print(f"\n🎉 LIMPEZA CONCLUÍDA!")
        print(f"✅ Removidos: {total_before} documentos")
        print(f"✅ Restantes: {total_after} documentos")
        print(f"✅ MongoDB limpo e pronto!")
        
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    asyncio.run(clean_mongodb_direct())
