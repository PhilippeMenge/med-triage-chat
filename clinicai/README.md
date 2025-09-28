# ClinicAI - Agente de Triagem Médica com IA

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0+-green.svg)](https://mongodb.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)

Agente de IA para triagem médica automatizada via WhatsApp, desenvolvido com LangGraph, Gemini 1.5 Flash e FastAPI.

## 🎯 Objetivo

O ClinicAI é um assistente virtual que:

- 📱 Recebe mensagens via WhatsApp Cloud API (webhook)
- 🤖 Responde usando Gemini 1.5 Flash com persona acolhedora
- 📋 Conduz slot-filling para coletar dados estruturados de triagem
- 🚨 Detecta emergências e orienta busca por atendimento urgente
- 💾 Persiste contexto completo no MongoDB
- 🔗 Expõe APIs REST com documentação OpenAPI/Swagger
- 🌐 Roda localmente com uvicorn + ngrok

## ⚠️ Disclaimers Importantes

**ATENÇÃO**: Este é um assistente de triagem, **NÃO um sistema médico**:

- ❌ **NÃO fornece diagnósticos**
- ❌ **NÃO recomenda tratamentos ou medicações**
- ❌ **NÃO substitui avaliação médica profissional**
- ✅ **Apenas coleta informações para agilizar atendimento humano**
- 🚨 **Detecta emergências e orienta busca por atendimento urgente**

## 🏗️ Arquitetura

```mermaid
graph TD
    A[WhatsApp] --> B[Webhook FastAPI]
    B --> C[LangGraph Agent]
    C --> D[Emergency Check]
    D -->|Emergência| E[Resposta de Emergência]
    D -->|Normal| F[Extract Slots - Gemini]
    F --> G[Update Database]
    G --> H[Next Prompt - Gemini]
    H --> I[Send WhatsApp]
    I --> J[MongoDB]
```

### Componentes Principais

- **FastAPI**: Endpoints REST + webhook WhatsApp
- **LangGraph**: Orquestração do fluxo do agente
- **Gemini 1.5 Flash**: Processamento de linguagem natural
- **MongoDB**: Persistência de mensagens e triagens
- **Docker**: Containerização e deploy

## 🚀 Quick Start

### Pré-requisitos

- Python 3.11+
- Docker & Docker Compose
- Conta no Google AI Studio (Gemini API)
- Conta no Meta for Developers (WhatsApp Cloud API)
- ngrok (para desenvolvimento local)

### 1. Clone e Configure

```bash
git clone <repository-url>
cd clinicai

# Copie o arquivo de exemplo de configuração
cp env.example .env
```

### 2. Configure Variáveis de Ambiente

Edite o arquivo `.env`:

```bash
# Server
PORT=8000
BASE_URL=http://localhost:8000

# Database
MONGODB_URI=mongodb://root:rootpassword@mongo:27017/clinicai?authSource=admin
MONGODB_DB=clinicai

# Security
PHONE_HASH_SALT=your-secure-random-salt-here

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here

# WhatsApp Cloud API
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token

# Logging
LOG_LEVEL=INFO
```

### 3. Execute com Docker

```bash
# Suba os serviços
make up

# Ou manualmente:
docker-compose up -d

# Verifique os logs
make logs
```

### 4. Configure ngrok para Webhook

```bash
# Em outro terminal
ngrok http 8000

# Copie a URL pública (ex: https://abc123.ngrok-free.app)
```

### 5. Configure WhatsApp Webhook

No painel do Meta for Developers:

1. Acesse seu App WhatsApp Business
2. Configure Webhooks:
   - **URL**: `https://abc123.ngrok-free.app/webhook/whatsapp`
   - **Token de Verificação**: valor do `WHATSAPP_VERIFY_TOKEN`
   - **Eventos**: `messages`

### 6. Teste a Aplicação

```bash
# Verifique se está funcionando
curl http://localhost:8000/health

# Veja a documentação
open http://localhost:8000/docs
```

## 🧪 Testes

```bash
# Instalar dependências de desenvolvimento
make install

# Executar todos os testes
make test

# Testes com cobertura
make test-coverage

# Testes específicos
pytest tests/test_emergency.py -v
```

## 📊 Monitoramento

### Health Check

```bash
curl http://localhost:8000/health
```

### Logs da Aplicação

```bash
# Logs em tempo real
make logs

# Logs específicos
docker-compose logs -f app
```

### Métricas Básicas

```bash
# Status dos containers
make health

# Estatísticas de uso
make stats
```

## 🔧 Desenvolvimento

### Ambiente Local

```bash
# Instalar dependências
pip install -e ".[dev,test]"

# Executar em modo desenvolvimento
make dev

# Formatar código
make format

# Executar linting
make lint
```

### Estrutura do Projeto

```
clinicai/
├── app/                    # Código principal
│   ├── main.py            # FastAPI app
│   ├── config.py          # Configurações
│   ├── schemas.py         # Modelos Pydantic
│   ├── db.py              # MongoDB
│   ├── whatsapp.py        # WhatsApp Cloud API
│   ├── llm.py             # Gemini LLM
│   ├── graph/             # LangGraph agent
│   │   ├── state.py       # Estado do agente
│   │   ├── nodes.py       # Nós do workflow
│   │   ├── prompts.py     # Templates e persona
│   │   └── workflow.py    # Definição do grafo
│   └── utils/             # Utilitários
│       ├── security.py    # Hash e sanitização
│       ├── emergency.py   # Detecção de emergência
│       └── logging.py     # Logging estruturado
├── tests/                 # Testes unitários
├── docker-compose.yml     # Orquestração local
├── Dockerfile            # Container da app
├── Makefile              # Comandos úteis
└── README.md             # Esta documentação
```

## 📋 Workflow de Triagem

### 1. Slots Coletados

O agente coleta as seguintes informações:

1. **Queixa Principal**: Motivo do contato
2. **Sintomas**: Descrição detalhada
3. **Duração**: Há quanto tempo
4. **Frequência**: Com que frequência ocorre
5. **Intensidade**: Escala 0-10
6. **Histórico**: Condições médicas relevantes
7. **Medidas Tomadas**: O que já foi tentado

### 2. Detecção de Emergência

**Palavras-chave monitoradas**:
- Dor no peito
- Falta de ar / dificuldade para respirar
- Desmaio / perda de consciência
- Sangramento intenso / hemorragia
- Convulsão
- Fraqueza súbita
- Confusão súbita
- Vômito com sangue
- Febre muito alta (>39°C)

**Resposta de emergência**:
```
🚨 Entendi. Seus sintomas podem indicar uma situação de emergência.
Por favor, procure o pronto-socorro mais próximo ou ligue 192 imediatamente.
```

### 3. Persona do Agente

- **Tom**: Acolhedor, empático, calmo e profissional
- **Linguagem**: Simples, clara, sem jargões médicos
- **Comportamento**: Uma pergunta por vez, explica o motivo das perguntas
- **Limitações**: Sempre deixa claro que não substitui avaliação médica

## 🔒 Segurança e Privacidade

### Proteção de Dados

- **Hash de telefones**: SHA-256 com salt para anonimização
- **Sanitização de logs**: Remove informações sensíveis automaticamente
- **Validação rigorosa**: Todas as entradas são validadas com Pydantic

### Guardrails Médicos

- **Detecção de conteúdo médico**: Bloqueia tentativas de diagnóstico/tratamento
- **Sanitização de saída**: LLM outputs são filtrados para remover conteúdo inapropriado
- **Rate limiting**: Prevenção de spam (implementar se necessário)

## 📊 Banco de Dados

### Coleções MongoDB

#### messages
```javascript
{
  "_id": "ObjectId",
  "phone": "5551999999999",
  "phone_hash": "sha256_hash",
  "direction": "in|out",
  "message_id": "whatsapp_msg_id",
  "text": "conteúdo da mensagem",
  "timestamp": "ISODate",
  "meta": { /* payload original */ },
  "triage_state_snapshot": { /* estado da triagem */ }
}
```

#### triages
```javascript
{
  "_id": "ObjectId",
  "phone_hash": "sha256_hash",
  "status": "open|closed|emergency",
  "slots": {
    "chief_complaint": "string|null",
    "symptoms": "string|null",
    "duration": "string|null",
    "frequency": "string|null",
    "intensity": "0-10|null",
    "history": "string|null",
    "measures_taken": "string|null"
  },
  "emergency_flag": false,
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "last_message_at": "ISODate"
}
```

## 🌐 API Endpoints

### Core Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/health` | Health check |
| `GET` | `/webhook/whatsapp` | Verificação do webhook |
| `POST` | `/webhook/whatsapp` | Recebimento de mensagens |
| `GET` | `/triages/{phone_hash}` | Status da triagem |
| `GET` | `/docs` | Documentação Swagger |

### Exemplo de Uso

```bash
# Health check
curl http://localhost:8000/health

# Status de triagem
curl http://localhost:8000/triages/abc123...

# Documentação interativa
open http://localhost:8000/docs
```

## 🚨 Troubleshooting

### Problemas Comuns

#### 1. Erro de conexão com MongoDB
```bash
# Verifique se o MongoDB está rodando
docker-compose ps mongo

# Reinicie o serviço
docker-compose restart mongo
```

#### 2. Webhook não recebe mensagens
```bash
# Verifique se ngrok está ativo
curl https://your-ngrok-url.ngrok-free.app/health

# Verifique logs do webhook
make logs | grep webhook
```

#### 3. Gemini API não responde
```bash
# Verifique a chave da API
python -c "from app.config import settings; print('Key:', settings.gemini_api_key[:10]+'...')"

# Teste a conexão
curl "https://generativelanguage.googleapis.com/v1/models?key=YOUR_API_KEY"
```

### Logs Úteis

```bash
# Logs da aplicação
docker-compose logs -f app

# Logs do MongoDB
docker-compose logs -f mongo

# Logs com filtro
docker-compose logs app | grep ERROR
```

## 🤝 Contribuição

### Padrões de Código

- **Python**: PEP 8, type hints obrigatórios
- **Commits**: Conventional Commits
- **Testes**: Cobertura mínima de 80%
- **Documentação**: Docstrings em todas as funções

### Processo de Desenvolvimento

1. Fork o repositório
2. Crie uma branch feature (`git checkout -b feature/nova-funcionalidade`)
3. Implemente com testes
4. Execute `make lint` e `make test`
5. Commit e push
6. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a MIT License - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 📞 Suporte

Para suporte e dúvidas:

- **Issues**: Abra uma issue no GitHub
- **Email**: dev@clinicai.com
- **Documentação**: `/docs` endpoint da aplicação

---

**Desenvolvido com ❤️ para melhorar o atendimento médico através da tecnologia**

