# ClinicAI - Assistente Virtual para Triagem Médica

## 📖 Visão Geral

ClinicAI é um assistente virtual inteligente para triagem médica via WhatsApp. O sistema coleta informações estruturadas dos pacientes através de conversa natural, detecta emergências e organiza dados para facilitar o atendimento médico.

## ✨ Funcionalidades

- 🤖 **Conversa Natural**: Interação via WhatsApp usando Gemini AI
- 📋 **Coleta Estruturada**: 6 categorias de informações médicas
- 🚨 **Detecção de Emergências**: Identificação automática de casos urgentes
- 💾 **Persistência**: Dados salvos em MongoDB Atlas
- 🔒 **Segurança**: Hash de telefones e sanitização de dados
- ⏰ **Timeout**: Reset automático após 30 minutos de inatividade
- 📊 **API REST**: Endpoints para consulta de triagens

## 🏗️ Arquitetura

```
WhatsApp ←→ FastAPI ←→ Gemini AI ←→ MongoDB Atlas
```

### Tecnologias Utilizadas

- **Python 3.11+**
- **FastAPI** - API REST e webhooks
- **Google Gemini 2.5 Flash Lite** - Processamento de linguagem natural
- **MongoDB Atlas** - Banco de dados na nuvem
- **Motor** - Driver MongoDB assíncrono
- **Pydantic** - Validação de dados
- **Uvicorn** - Servidor ASGI

## 🚀 Instalação e Configuração

### 1. Pré-requisitos

- Python 3.11 ou superior
- Conta no MongoDB Atlas
- Token de acesso do WhatsApp Business API
- Chave da API do Google Gemini
- ngrok (para desenvolvimento local)

### 2. Configuração do Ambiente

```bash
# Clone o repositório
git clone <repository-url>
cd med-triage-chat/clinicai

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp env.example .env
```

### 3. Configuração das Variáveis de Ambiente

Edite o arquivo `.env` com suas credenciais:

```bash
# Servidor
PORT=8080

# MongoDB Atlas
MONGODB_URI=mongodb+srv://usuario:senha@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB=clinicai_db

# Segurança
PHONE_HASH_SALT=sua_salt_aleatoria_aqui

# Google Gemini AI
GEMINI_API_KEY=sua_chave_gemini_aqui

# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=seu_token_whatsapp
WHATSAPP_PHONE_NUMBER_ID=seu_phone_number_id
WHATSAPP_VERIFY_TOKEN=seu_verify_token

# URL Base (para webhooks)
BASE_URL=https://seu-dominio.com
```

### 4. Configuração do MongoDB Atlas

1. Acesse [MongoDB Atlas](https://cloud.mongodb.com/)
2. Crie uma conta gratuita
3. Crie um novo cluster
4. Configure acesso de rede (0.0.0.0/0 para desenvolvimento)
5. Crie um usuário de banco de dados
6. Obtenha a string de conexão

### 5. Configuração do WhatsApp Business API

1. Acesse [Meta for Developers](https://developers.facebook.com/)
2. Crie um app WhatsApp Business
3. Configure webhook URL: `https://seu-dominio.com/webhook/whatsapp`
4. Configure Verify Token no `.env`
5. Obtenha Access Token e Phone Number ID

### 6. Configuração do Google Gemini

1. Acesse [Google AI Studio](https://aistudio.google.com/)
2. Crie uma API key
3. Configure no `.env`

## 🏃‍♂️ Execução

### Desenvolvimento Local

```bash
# Instalar ngrok (se necessário)
# Windows: winget install ngrok

# Executar a aplicação
python main.py

# Em outro terminal, expor via ngrok
ngrok http 8080
```

### Produção com Docker

```bash
# Build da imagem
docker build -t clinicai .

# Executar container
docker run -d \
  --name clinicai \
  --env-file .env \
  -p 8080:8080 \
  clinicai
```

### Produção com Docker Compose

```bash
# Iniciar todos os serviços
docker-compose up -d

# Parar os serviços
docker-compose down
```

## 📡 API Endpoints

### Webhook WhatsApp
- `GET /webhook/whatsapp` - Verificação do webhook
- `POST /webhook/whatsapp` - Receber mensagens

### Consultas
- `GET /health` - Status da aplicação
- `GET /triages/{phone_hash}` - Consultar triagens de um usuário

### Exemplo de Uso da API

```bash
# Verificar status
curl https://seu-dominio.com/health

# Consultar triagens
curl https://seu-dominio.com/triages/abc123...
```

## 💬 Fluxo de Conversa

### 1. Início
```
🏥 Olá! Sou seu assistente virtual e vou ajudar a organizar suas informações para agilizar seu atendimento.

⚠️ Importante: Sou um assistente virtual e não substituo uma avaliação médica profissional.
```

### 2. Coleta de Informações
O sistema coleta automaticamente:
1. **Queixa Principal** - Motivo do contato
2. **Sintomas Detalhados** - Descrição completa
3. **Duração e Frequência** - Tempo e recorrência
4. **Intensidade** - Escala de dor/desconforto
5. **Histórico de Saúde** - Condições relevantes
6. **Medidas Tomadas** - Tratamentos já tentados

### 3. Detecção de Emergências
Palavras-chave que ativam alerta de emergência:
- Dor no peito
- Dificuldade para respirar
- Desmaio
- Sangramento intenso
- E outras situações críticas

### 4. Finalização
Resumo das informações coletadas e orientações.

## 🔒 Segurança e Privacidade

- **Hash de Telefones**: Números são convertidos em hash SHA-256
- **Sanitização**: Dados são limpos antes do armazenamento
- **Timeout**: Sessões expiram automaticamente
- **Validação**: Todos os dados são validados com Pydantic
- **Logs**: Sistema de logging estruturado

## 🛠️ Desenvolvimento

### Estrutura do Projeto

```
clinicai/
├── main.py              # Aplicação principal
├── requirements.txt     # Dependências Python
├── env.example         # Exemplo de configuração
├── docker-compose.yml  # Orquestração Docker
├── Dockerfile         # Imagem Docker
├── Makefile          # Comandos automatizados
└── pyproject.toml    # Configuração do projeto
```

### Comandos Make

```bash
# Desenvolvimento
make dev

# Testes
make test

# Docker
make up      # Subir containers
make down    # Parar containers
```

## 📊 Monitoramento

A aplicação gera logs estruturados que incluem:
- Mensagens recebidas/enviadas
- Processamento do Gemini
- Operações no banco de dados
- Detecção de emergências
- Erros e exceções

## 🚨 Emergências

O sistema detecta automaticamente situações de emergência baseado em palavras-chave e orienta o usuário a:
- Procurar atendimento imediato no pronto-socorro
- Ligar para 192 (SAMU)

## 📈 Escalabilidade

- **Assíncrono**: Toda a aplicação é assíncrona
- **MongoDB**: Banco de dados escalável na nuvem
- **Stateless**: Aplicação sem estado persistente
- **Docker**: Fácil deployment e scaling

## 🆘 Suporte

Para problemas ou dúvidas:
1. Verifique os logs da aplicação
2. Confirme as configurações no `.env`
3. Teste conectividade com MongoDB e APIs externas

## 📄 Licença

Este projeto é de uso interno e proprietário.

---

**ClinicAI - Transformando triagem médica com inteligência artificial** 🏥✨