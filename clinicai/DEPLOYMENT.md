# Guia de Deploy - ClinicAI

Este documento fornece instruções detalhadas para deploy do ClinicAI em diferentes ambientes.

## 🚀 Deploy Local (Desenvolvimento)

### Pré-requisitos
- Python 3.11+
- Docker & Docker Compose
- ngrok
- Chaves API (Gemini, WhatsApp)

### Passos

1. **Clone e configure**:
```bash
git clone <repository-url>
cd clinicai
cp env.example .env
```

2. **Configure variáveis (.env)**:
```bash
# Obrigatórias
GEMINI_API_KEY=your_gemini_key
WHATSAPP_ACCESS_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
WHATSAPP_VERIFY_TOKEN=your_verify_token
PHONE_HASH_SALT=secure_random_string

# Opcionais (valores padrão funcionam)
PORT=8000
MONGODB_URI=mongodb://root:rootpassword@mongo:27017/clinicai?authSource=admin
LOG_LEVEL=INFO
```

3. **Execute**:
```bash
make up          # Sobe MongoDB + App
make logs        # Vê logs
ngrok http 8000  # Em outro terminal
```

4. **Configure webhook no Meta**:
- URL: `https://your-ngrok.ngrok-free.app/webhook/whatsapp`
- Token: valor do `WHATSAPP_VERIFY_TOKEN`

## 🌐 Deploy em Produção

### Opção 1: VPS/Cloud Server

#### Pré-requisitos
- Servidor Linux (Ubuntu 20.04+)
- Docker & Docker Compose
- Domínio com HTTPS
- Firewall configurado

#### Configuração

1. **Preparar servidor**:
```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

2. **Deploy da aplicação**:
```bash
# Clone no servidor
git clone <repository-url> /opt/clinicai
cd /opt/clinicai

# Configure variáveis de produção
cp env.example .env
nano .env  # Configure com valores reais

# Execute
docker-compose -f docker-compose.prod.yml up -d
```

3. **Configure proxy reverso (Nginx)**:
```nginx
server {
    listen 80;
    server_name clinicai.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

4. **Configure HTTPS (Let's Encrypt)**:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d clinicai.yourdomain.com
```

### Opção 2: Docker Swarm

#### docker-compose.prod.yml
```yaml
version: '3.8'

services:
  app:
    image: clinicai:latest
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
    environment:
      - MONGODB_URI=${MONGODB_URI}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    networks:
      - clinicai-net

  mongo:
    image: mongo:7.0
    deploy:
      replicas: 1
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
    volumes:
      - mongo_data:/data/db
    networks:
      - clinicai-net

volumes:
  mongo_data:

networks:
  clinicai-net:
    driver: overlay
```

#### Deploy
```bash
docker stack deploy -c docker-compose.prod.yml clinicai
```

### Opção 3: Kubernetes

#### Deployment YAML
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: clinicai-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: clinicai
  template:
    metadata:
      labels:
        app: clinicai
    spec:
      containers:
      - name: clinicai
        image: clinicai:latest
        ports:
        - containerPort: 8000
        env:
        - name: MONGODB_URI
          valueFrom:
            secretKeyRef:
              name: clinicai-secrets
              key: mongodb-uri
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: clinicai-secrets
              key: gemini-api-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: clinicai-service
spec:
  selector:
    app: clinicai
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## 🔧 Configurações de Produção

### Variáveis de Ambiente

```bash
# Obrigatórias
GEMINI_API_KEY=your_production_key
WHATSAPP_ACCESS_TOKEN=your_production_token
WHATSAPP_PHONE_NUMBER_ID=your_production_phone_id
WHATSAPP_VERIFY_TOKEN=strong_verify_token
PHONE_HASH_SALT=very_secure_random_salt

# Recomendadas para produção
LOG_LEVEL=WARNING
MONGODB_URI=mongodb://user:pass@mongo-cluster/clinicai?replicaSet=rs0
BASE_URL=https://clinicai.yourdomain.com

# Opcionais
PORT=8000
```

### Segurança

1. **Firewall**:
```bash
# Permitir apenas portas necessárias
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

2. **MongoDB**:
```bash
# Criar usuário específico
mongo
use clinicai
db.createUser({
  user: "clinicai_user",
  pwd: "secure_password",
  roles: [{ role: "readWrite", db: "clinicai" }]
})
```

3. **Backup automatizado**:
```bash
#!/bin/bash
# /etc/cron.d/clinicai-backup
0 2 * * * root docker exec clinicai-mongo mongodump --db clinicai --out /backup/$(date +\%Y\%m\%d)
```

### Monitoramento

#### Health Checks
```bash
# Script de monitoramento
#!/bin/bash
HEALTH_URL="https://clinicai.yourdomain.com/health"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $STATUS != "200" ]; then
    echo "ClinicAI is down! Status: $STATUS"
    # Enviar alerta
fi
```

#### Logs
```bash
# Configurar rotação de logs
cat > /etc/logrotate.d/clinicai << EOF
/opt/clinicai/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    create 644 root root
}
EOF
```

### Performance

#### Nginx Caching
```nginx
location /static/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

location /health {
    access_log off;
    return 200 "healthy\n";
}
```

#### Database Tuning
```javascript
// MongoDB indexes para performance
db.messages.createIndex({ "phone_hash": 1, "timestamp": -1 })
db.triages.createIndex({ "phone_hash": 1, "status": 1 })
db.triages.createIndex({ "emergency_flag": 1, "created_at": -1 })
```

## 🚨 Troubleshooting

### Problemas Comuns

1. **Webhook não funciona**:
```bash
# Verificar conectividade
curl -X POST https://your-domain.com/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{"test": "webhook"}'

# Verificar logs
docker-compose logs -f app | grep webhook
```

2. **MongoDB lento**:
```bash
# Verificar indexes
docker exec clinicai-mongo mongo clinicai --eval "db.messages.getIndexes()"

# Monitorar performance
docker exec clinicai-mongo mongostat --host localhost
```

3. **Memory issues**:
```bash
# Verificar uso de memória
docker stats clinicai-app

# Ajustar limites
docker-compose up -d --scale app=2
```

### Logs Úteis

```bash
# Logs da aplicação
docker-compose logs -f app

# Logs com filtro
docker-compose logs app | grep ERROR

# Logs do MongoDB
docker-compose logs mongo

# Logs do sistema
journalctl -u docker -f
```

## 📊 Métricas e Alertas

### Prometheus + Grafana

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### Alertas básicos

```bash
# Script de alerta
#!/bin/bash
HEALTH=$(curl -s http://localhost:8000/health | jq -r '.status')
if [ "$HEALTH" != "ok" ]; then
    curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
         -d chat_id=$CHAT_ID \
         -d text="🚨 ClinicAI está com problemas!"
fi
```

## 🔄 Backup e Restore

### Backup
```bash
# Backup do MongoDB
docker exec clinicai-mongo mongodump --db clinicai --out /backup

# Backup dos logs
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/

# Upload para S3 (opcional)
aws s3 cp backup/ s3://clinicai-backups/ --recursive
```

### Restore
```bash
# Restore do MongoDB
docker exec clinicai-mongo mongorestore --db clinicai /backup/clinicai/

# Verificar integridade
docker exec clinicai-mongo mongo clinicai --eval "db.triages.count()"
```

---

**⚠️ Importante**: Sempre teste o deploy em ambiente de staging antes de produção!

