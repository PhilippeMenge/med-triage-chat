#!/usr/bin/env python3
"""
Script para testar conexão com MongoDB Atlas ou Local.
"""

import asyncio
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

async def test_mongodb_connection():
    """Testa conexão com MongoDB."""
    
    print("🍃 Testando Conexão MongoDB")
    print("=" * 40)
    
    # Verificar se motor está instalado
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        print("✅ Motor (driver MongoDB) instalado")
    except ImportError:
        print("❌ Motor não instalado!")
        print("📦 Execute: pip install motor pymongo")
        return
    
    # Obter URI de conexão
    mongodb_uri = os.getenv("MONGODB_URI")
    mongodb_db = os.getenv("MONGODB_DB", "clinicai_db")
    
    if not mongodb_uri:
        print("❌ MONGODB_URI não configurado no .env")
        print("📝 Adicione no .env:")
        print("   MONGODB_URI=mongodb+srv://user:pass@cluster.xxxxx.mongodb.net/...")
        return
    
    print(f"🔗 URI: {mongodb_uri[:50]}...")
    print(f"📊 Database: {mongodb_db}")
    
    try:
        # Criar cliente
        print("\n🔌 Conectando...")
        client = AsyncIOMotorClient(mongodb_uri)
        
        # Testar ping
        await client.admin.command('ping')
        print("✅ Conexão estabelecida!")
        
        # Listar databases
        dbs = await client.list_database_names()
        print(f"📊 Databases disponíveis: {dbs}")
        
        # Verificar/criar database
        db = client[mongodb_db]
        collections = await db.list_collection_names()
        print(f"📁 Collections em '{mongodb_db}': {collections}")
        
        # Criar collections se não existirem
        required_collections = ["messages", "triages"]
        for collection_name in required_collections:
            if collection_name not in collections:
                print(f"➕ Criando collection: {collection_name}")
                await db.create_collection(collection_name)
            else:
                print(f"✅ Collection '{collection_name}' já existe")
        
        # Testar inserção simples
        print("\n🧪 Testando operações...")
        test_collection = db.test
        
        # Inserir documento teste
        result = await test_collection.insert_one({"test": "hello", "timestamp": "2025-09-28"})
        print(f"✅ Inserção teste: {result.inserted_id}")
        
        # Buscar documento
        doc = await test_collection.find_one({"test": "hello"})
        print(f"✅ Busca teste: {doc}")
        
        # Deletar teste
        await test_collection.delete_one({"test": "hello"})
        print("✅ Remoção teste: OK")
        
        # Remover collection teste
        await db.drop_collection("test")
        print("✅ Limpeza teste: OK")
        
        # Fechar conexão
        client.close()
        
        print("\n🎉 MongoDB configurado com sucesso!")
        print("✅ Conexão funcional")
        print("✅ Operações CRUD funcionais")
        print("✅ Collections criadas")
        
    except Exception as e:
        print(f"\n❌ Erro na conexão: {e}")
        print("\n🔧 Possíveis soluções:")
        print("1. Verificar MONGODB_URI no .env")
        print("2. Verificar username/password")
        print("3. Verificar se IP está liberado (Atlas)")
        print("4. Verificar internet")
        
        if "authentication failed" in str(e).lower():
            print("\n🔑 Erro de autenticação:")
            print("- Verificar username e password na URI")
            print("- Verificar se usuário foi criado no Atlas")
        
        if "timeout" in str(e).lower():
            print("\n⏰ Erro de timeout:")
            print("- Verificar firewall")
            print("- Verificar se cluster está ativo (Atlas)")
            print("- Verificar se IP está na whitelist")

if __name__ == "__main__":
    asyncio.run(test_mongodb_connection())
