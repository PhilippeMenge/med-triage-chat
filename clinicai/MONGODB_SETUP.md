# 🍃 Guia Completo: MongoDB para ClinicAI

## 📋 Opções de MongoDB

### ✅ **Recomendado: MongoDB Atlas (Nuvem - Gratuito)**
- ✅ Fácil configuração
- ✅ Grátis até 512MB
- ✅ Backup automático
- ✅ Interface web
- ✅ Não precisa instalar nada

### 🔧 **Alternativa: MongoDB Local**
- ⚠️ Mais complexo
- ⚠️ Precisa gerenciar manualmente
- ✅ Controle total

---

## 🚀 **MÉTODO 1: MongoDB Atlas (Recomendado)**

### **Passo 1: Criar Conta**
1. Acesse: https://www.mongodb.com/atlas
2. Clique em **"Try Free"**
3. Crie conta com:
   - Email
   - Senha
   - Nome/Sobrenome

### **Passo 2: Criar Cluster**
1. Após login, clique **"Build a Database"**
2. Escolha **"M0 Sandbox"** (GRATUITO)
3. Selecione:
   - **Provider**: AWS
   - **Region**: São Paulo (sa-east-1) ou mais próximo
4. **Cluster Name**: `clinicai-cluster`
5. Clique **"Create"**

### **Passo 3: Configurar Segurança**

#### **3.1 Usuário do Banco**
1. Na tela "Security Quickstart"
2. **Username**: `clinicai_user`
3. **Password**: Clique "Autogenerate Secure Password" e **COPIE A SENHA**
4. Clique **"Create User"**

#### **3.2 Acesso de Rede**
1. Na próxima tela "Where would you like to connect from?"
2. Clique **"Add My Current IP Address"**
3. Para desenvolvimento, adicione também: **"Allow Access from Anywhere"**
   - IP: `0.0.0.0/0`
   - Description: `Development Access`
4. Clique **"Finish and Close"**

### **Passo 4: Obter String de Conexão**
1. No dashboard, clique **"Connect"** no seu cluster
2. Escolha **"Drivers"**
3. Selecione:
   - **Driver**: Python
   - **Version**: 3.12 or later
4. **COPIE** a connection string (algo como):
   ```
   mongodb+srv://clinicai_user:<password>@clinicai-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
5. **SUBSTITUA** `<password>` pela senha que você copiou no passo 3.1

### **Passo 5: Criar Banco e Coleções**
1. No dashboard, clique **"Browse Collections"**
2. Clique **"Add My Own Data"**
3. **Database name**: `clinicai_db`
4. **Collection name**: `messages`
5. Clique **"Create"**

6. Adicione mais coleções:
   - Clique no **"+"** ao lado de `clinicai_db`
   - Crie: `triages`
   - Crie: `users` (opcional)

---

## 🔧 **MÉTODO 2: MongoDB Local (Alternativo)**

### **Passo 1: Baixar e Instalar**

#### **Windows:**
1. Acesse: https://www.mongodb.com/try/download/community
2. Selecione:
   - **Version**: 7.0.x (Latest)
   - **Platform**: Windows
   - **Package**: msi
3. Baixe e execute o instalador
4. Durante instalação:
   - ✅ Marque "Install MongoDB as a Service"
   - ✅ Marque "Install MongoDB Compass" (interface gráfica)

#### **Configuração:**
1. Após instalação, abra **MongoDB Compass**
2. Conecte em: `mongodb://localhost:27017`
3. Crie database: `clinicai_db`
4. Crie collections: `messages`, `triages`, `users`

---

## 🔌 **Configurar Aplicação**

### **Atualizar .env**
```env
# MongoDB Atlas (Método 1)
MONGODB_URI=mongodb+srv://clinicai_user:SUA_SENHA_AQUI@clinicai-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB=clinicai_db

# OU MongoDB Local (Método 2)
# MONGODB_URI=mongodb://localhost:27017
# MONGODB_DB=clinicai_db
```

### **Instalar Dependências**
```bash
pip install motor pymongo
```

---

## 📊 **Schema das Coleções**

### **Collection: `messages`**
```json
{
  "_id": "ObjectId",
  "phone_hash": "string",
  "direction": "in|out", 
  "message_id": "string",
  "text": "string",
  "timestamp": "datetime",
  "meta": {}
}
```

### **Collection: `triages`**
```json
{
  "_id": "ObjectId",
  "phone_hash": "string",
  "status": "open|completed|timeout|emergency",
  "slots": {
    "chief_complaint": "string",
    "symptoms": "string", 
    "duration_frequency": "string",
    "intensity": "string",
    "measures_taken": "string",
    "health_history": "string"
  },
  "emergency_flag": "boolean",
  "created_at": "datetime",
  "last_activity": "datetime", 
  "completed_at": "datetime"
}
```

---

## ✅ **Verificação**

### **Testar Conexão:**
```python
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def test_connection():
    uri = "SUA_CONNECTION_STRING_AQUI"
    client = AsyncIOMotorClient(uri)
    
    # Testar conexão
    await client.admin.command('ping')
    print("✅ Conectado ao MongoDB!")
    
    # Listar databases
    dbs = await client.list_database_names()
    print(f"📊 Databases: {dbs}")
    
    client.close()

asyncio.run(test_connection())
```

---

## 🆘 **Problemas Comuns**

### **Erro de Conexão:**
- ✅ Verificar se IP está liberado no Atlas
- ✅ Verificar username/password na string
- ✅ Verificar internet

### **Erro de Autenticação:**
- ✅ Verificar se usuário foi criado corretamente
- ✅ Verificar se senha está correta na string

### **Timeout:**
- ✅ Verificar firewall
- ✅ Verificar se cluster está ativo

---

## 🎯 **Próximos Passos**

1. ✅ **Escolher método** (Atlas recomendado)
2. ✅ **Configurar** seguindo passos acima
3. ✅ **Testar conexão** 
4. ✅ **Migrar dados** do SQLite
5. ✅ **Atualizar aplicação**

**Recomendação**: Comece com MongoDB Atlas - é muito mais simples para iniciantes!
