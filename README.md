# ClinicAI - Assistente Virtual para Triagem Médica

## 🚀 Início Rápido

```bash
cd clinicai
cp env.example .env
# Configure suas credenciais no .env
pip install -r requirements.txt
python main.py
```

## 📖 Sobre

ClinicAI é um assistente virtual inteligente que realiza triagem médica via WhatsApp, coletando informações estruturadas dos pacientes através de conversa natural com Gemini AI.

## 📁 Estrutura do Projeto

```
clinicai/               # Aplicação principal
├── main.py            # Arquivo principal da aplicação
├── requirements.txt   # Dependências Python
├── env.example       # Exemplo de configuração
├── README.md         # Documentação detalhada
├── health_check.py   # Verificação de configuração
├── docker-compose.yml # Orquestração Docker
└── Dockerfile        # Imagem Docker
```

## 🔧 Configuração

1. **Configure o ambiente**:
   ```bash
   cd clinicai
   cp env.example .env
   ```

2. **Edite o `.env`** com suas credenciais:
   - MongoDB Atlas URI
   - Chave da API do Gemini
   - Tokens do WhatsApp Business API

3. **Instale dependências**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verifique configuração**:
   ```bash
   python health_check.py
   ```

5. **Execute a aplicação**:
   ```bash
   python main.py
   ```

## 📚 Documentação Completa

Consulte `clinicai/README.md` para documentação detalhada incluindo:
- Configuração completa das APIs
- Estrutura da conversa
- Endpoints da API
- Deployment em produção
- Monitoramento e logs

## 🤖 Funcionalidades

- ✅ Conversa natural via WhatsApp
- ✅ Coleta estruturada de 6 categorias médicas
- ✅ Detecção automática de emergências
- ✅ Persistência em MongoDB Atlas
- ✅ API REST para consultas
- ✅ Timeout automático de sessão
- ✅ Segurança e privacidade

## 🏥 Como Funciona

1. **Paciente** envia mensagem via WhatsApp
2. **ClinicAI** responde e inicia triagem
3. **Gemini AI** conduz conversa natural
4. **Sistema** coleta informações estruturadas
5. **Dados** são salvos no MongoDB
6. **Profissional** consulta via API

---

**ClinicAI** - Transformando triagem médica com IA 🏥✨