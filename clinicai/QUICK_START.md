# 🚀 Quick Start - ClinicAI

Como o Docker Desktop está apresentando problemas, aqui estão as instruções para rodar localmente:

## Opção 1: Executar sem Docker (Recomendado para desenvolvimento)

### 1. Instale o MongoDB localmente

**Windows:**
```bash
# Baixe e instale MongoDB Community Edition
# https://www.mongodb.com/try/download/community

# Ou use Chocolatey:
choco install mongodb

# Inicie o MongoDB
mongod
```

**Ou use MongoDB Atlas (Cloud - Grátis):**
1. Acesse: https://www.mongodb.com/atlas
2. Crie uma conta gratuita
3. Crie um cluster
4. Obtenha a connection string

### 2. Configure o ambiente

```bash
# Instale Python 3.11+ se não tiver
# https://www.python.org/downloads/

# Instale as dependências
pip install -r requirements.txt

# Configure variáveis
cp env.example .env
```

### 3. Configure o arquivo .env

```bash
# .env
PORT=8000
BASE_URL=http://localhost:8000

# MongoDB Local
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=clinicai

# OU MongoDB Atlas
# MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/clinicai?retryWrites=true&w=majority

# Segurança
PHONE_HASH_SALT=meu_salt_super_secreto_123

# APIs (OBRIGATÓRIO - obtenha suas chaves)
GEMINI_API_KEY=sua_chave_gemini_aqui
WHATSAPP_ACCESS_TOKEN=seu_token_whatsapp_aqui  
WHATSAPP_PHONE_NUMBER_ID=seu_phone_id_aqui
WHATSAPP_VERIFY_TOKEN=meu_token_verificacao_123

# Log
LOG_LEVEL=INFO
```

### 4. Execute a aplicação

```bash
# Execute diretamente
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# OU use o Makefile
make dev
```

### 5. Configure ngrok

Em outro terminal:
```bash
# Instale ngrok se não tiver
# https://ngrok.com/download

# Execute
ngrok http 8000

# Copie a URL HTTPS (ex: https://abc123.ngrok-free.app)
```

### 6. URLs para o Meta for Developers

**Webhook URL:**
```
https://SEU-SUBDOMINIO.ngrok-free.app/webhook/whatsapp
```

**Verify Token:**
```
meu_token_verificacao_123
```
(ou o valor que você colocou em `WHATSAPP_VERIFY_TOKEN`)

## Opção 2: Corrigir Docker (se preferir)

### Reiniciar Docker Desktop

1. **Feche completamente o Docker Desktop**
2. **Reinicie como administrador**
3. **Aguarde inicializar completamente**
4. **Teste novamente:**

```bash
docker version
docker-compose up -d --build
```

### Se ainda não funcionar:

```bash
# Reinstale Docker Desktop
# https://www.docker.com/products/docker-desktop/

# Ou use Docker alternativo (Podman)
# https://podman.io/getting-started/installation
```

## 🧪 Teste se está funcionando

```bash
# 1. Teste health
curl http://localhost:8000/health

# 2. Teste webhook verification
curl "http://localhost:8000/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=meu_token_verificacao_123&hub.challenge=test123"
# Deve retornar: test123

# 3. Veja documentação
# Abra: http://localhost:8000/docs
```

## 📱 Configuração no Meta for Developers

1. **Acesse**: https://developers.facebook.com
2. **Vá para**: Seu App → WhatsApp → Configuration → Webhooks
3. **Configure**:
   - **Callback URL**: `https://SEU-NGROK.ngrok-free.app/webhook/whatsapp`
   - **Verify Token**: `meu_token_verificacao_123`
   - **Webhook fields**: ☑️ `messages`
4. **Clique**: "Verify and Save"

## 🔧 Troubleshooting

### Erro "Module not found"
```bash
# Instale dependências
pip install -r requirements.txt

# Ou instale individualmente
pip install fastapi uvicorn pydantic motor httpx python-dotenv google-generativeai langgraph bcrypt
```

### Erro MongoDB
```bash
# Se usando MongoDB local, verifique se está rodando
mongod --version

# Se usando Atlas, verifique a connection string
```

### Erro Gemini API
```bash
# Verifique sua chave API
# https://makersuite.google.com/app/apikey
```

### Erro WhatsApp
```bash
# Verifique tokens no Meta for Developers
# https://developers.facebook.com/apps/
```

## ✅ Pronto!

Quando tudo estiver funcionando:
1. Envie uma mensagem para seu número WhatsApp Business
2. O ClinicAI deve responder automaticamente
3. Veja os logs no terminal

---

**💡 Dica**: Para desenvolvimento, a Opção 1 (sem Docker) é mais rápida e fácil de debugar!
