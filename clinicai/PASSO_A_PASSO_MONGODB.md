# 🚀 Passo a Passo: MongoDB para ClinicAI

## 📋 **O QUE VOCÊ VAI FAZER:**

1. ✅ **Criar conta no MongoDB Atlas** (gratuito)
2. ✅ **Configurar cluster** na nuvem
3. ✅ **Obter string de conexão**
4. ✅ **Testar conexão**
5. ✅ **Migrar dados** do SQLite

---

## 🎯 **PASSO 1: Criar Conta MongoDB Atlas**

### **1.1 Registrar:**
1. Vá em: **https://www.mongodb.com/atlas**
2. Clique **"Try Free"**
3. Preencha email, senha, nome
4. Confirme email

### **1.2 Criar Cluster:**
1. Clique **"Build a Database"**
2. Escolha **"M0 Sandbox"** (GRATUITO)
3. Provider: **AWS**
4. Region: **São Paulo** (sa-east-1)
5. Cluster Name: **`clinicai-cluster`**
6. Clique **"Create"**

---

## 🔐 **PASSO 2: Configurar Segurança**

### **2.1 Criar Usuário:**
1. Username: **`clinicai_user`**
2. Clique **"Autogenerate Secure Password"**
3. **🚨 COPIE E SALVE A SENHA!** RPD1Sj9HJSf3JxZa
4. Clique **"Create User"**

### **2.2 Liberar Acesso:**
1. Clique **"Add My Current IP Address"**
2. Para desenvolvimento, adicione também:
   - **"Add IP Address"**
   - IP: **`0.0.0.0/0`**
   - Description: **`Development`**
3. Clique **"Finish and Close"**

---

## 🔗 **PASSO 3: Obter String de Conexão**

1. No dashboard, clique **"Connect"**
2. Escolha **"Drivers"**
3. Driver: **Python**, Version: **3.12 or later**
4. **COPIE** a connection string:
   ```
  mongodb+srv://philippemengealima_db_user:<dRPD1Sj9HJSf3JxZa>@med-triage-chat.ndwibsn.mongodb.net/?retryWrites=true&w=majority&appName=med-triage-chat
   ```
5. **SUBSTITUA** `<password>` pela senha que você salvou

---

## ⚙️ **PASSO 4: Configurar Aplicação**

### **4.1 Atualizar .env:**
Abra seu arquivo `.env` e adicione:

```env
# MongoDB Configuration
MONGODB_URI=mongodb+srv://clinicai_user:SUA_SENHA_AQUI@clinicai-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB=clinicai_db
```

**🚨 Substitua:**
- `SUA_SENHA_AQUI` pela senha real
- `xxxxx` pelo ID do seu cluster

### **4.2 Exemplo completo do .env:**
```env
# Servidor
PORT=8080

# MongoDB
MONGODB_URI=mongodb+srv://clinicai_user:minhasenha123@clinicai-cluster.abc123.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB=clinicai_db

# WhatsApp
WHATSAPP_ACCESS_TOKEN=seu_token_aqui
WHATSAPP_PHONE_NUMBER_ID=133042209901442
WHATSAPP_VERIFY_TOKEN=161277587070732

# Gemini
GEMINI_API_KEY=sua_chave_aqui

# Segurança
PHONE_HASH_SALT=clinicai_salt_2024
```

---

## 🧪 **PASSO 5: Testar Conexão**

Execute o script de teste:

```bash
python test_mongodb_connection.py
```

**✅ Se funcionar, você verá:**
```
✅ Conexão estabelecida!
✅ Operações CRUD funcionais
✅ Collections criadas
🎉 MongoDB configurado com sucesso!
```

**❌ Se der erro:**
- Verificar senha na string de conexão
- Verificar se IP está liberado
- Verificar internet

---

## 📦 **PASSO 6: Migrar Dados (Se tiver)**

Se você já tem dados no SQLite:

```bash
python migrate_sqlite_to_mongodb.py
```

---

## 🔄 **PASSO 7: Atualizar App para MongoDB**

### **7.1 Parar servidor atual:**
```bash
# No terminal onde está rodando
Ctrl + C
```

### **7.2 Usar a versão MongoDB:**
```bash
python run_dev.py
```

---

## ✅ **VERIFICAÇÃO FINAL**

### **No MongoDB Atlas:**
1. Vá em **"Browse Collections"**
2. Deve aparecer:
   - Database: `clinicai_db`
   - Collections: `messages`, `triages`

### **No App:**
1. Servidor iniciando sem erros
2. Logs mostrando conexão MongoDB
3. WhatsApp funcionando normalmente

---

## 🆘 **PROBLEMAS COMUNS**

### **Erro: "authentication failed"**
- ✅ Verificar senha na string de conexão
- ✅ Verificar username correto

### **Erro: "timeout" ou "connection refused"**
- ✅ Verificar se IP está na whitelist
- ✅ Verificar internet
- ✅ Verificar firewall

### **String de conexão não funciona:**
- ✅ Verificar se copiou completa
- ✅ Verificar se substituiu `<password>`
- ✅ Verificar se não tem espaços extras

---

## 📞 **PRÓXIMOS PASSOS**

1. ✅ **Testar** conexão MongoDB
2. ✅ **Migrar** dados existentes  
3. ✅ **Atualizar** app para MongoDB
4. ✅ **Testar** fluxo completo no WhatsApp
5. ✅ **Verificar** dados sendo salvos no Atlas

**🎉 Depois disso, seu app estará rodando com MongoDB na nuvem!**
