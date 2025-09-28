# ClinicAI Makefile

.PHONY: help install dev test lint format clean build up down logs restart health

# Default target
help:
	@echo "ClinicAI - AI Medical Triage Agent"
	@echo ""
	@echo "Available commands:"
	@echo "  install    Install dependencies"
	@echo "  dev        Run development server"
	@echo "  test       Run tests"
	@echo "  lint       Run linting"
	@echo "  format     Format code"
	@echo "  clean      Clean temporary files"
	@echo "  build      Build Docker image"
	@echo "  up         Start services with Docker Compose"
	@echo "  down       Stop services"
	@echo "  logs       Show service logs"
	@echo "  restart    Restart services"
	@echo "  health     Check service health"

# Development commands
install:
	@echo "Installing dependencies..."
	pip install -e ".[test,dev]"

dev:
	@echo "Starting development server..."
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	@echo "Running tests..."
	pytest tests/ -v --tb=short

lint:
	@echo "Running linting..."
	flake8 app/ tests/
	mypy app/

format:
	@echo "Formatting code..."
	black app/ tests/
	isort app/ tests/

clean:
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

# Docker commands
build:
	@echo "Building Docker image..."
	docker build -t clinicai:latest .

up:
	@echo "Starting services..."
	docker-compose up -d

down:
	@echo "Stopping services..."
	docker-compose down

logs:
	@echo "Showing logs..."
	docker-compose logs -f

restart:
	@echo "Restarting services..."
	docker-compose restart

health:
	@echo "Checking service health..."
	@curl -f http://localhost:8000/health || echo "Service not healthy"
	@docker-compose ps

# Database commands
db-shell:
	@echo "Opening MongoDB shell..."
	docker-compose exec mongo mongosh clinicai

db-backup:
	@echo "Creating database backup..."
	docker-compose exec mongo mongodump --db clinicai --out /data/backup/$(shell date +%Y%m%d_%H%M%S)

db-restore:
	@echo "Restoring database from backup..."
	@echo "Usage: make db-restore BACKUP_DIR=<backup_directory>"
	docker-compose exec mongo mongorestore --db clinicai /data/backup/$(BACKUP_DIR)

# Testing and validation
test-unit:
	@echo "Running unit tests..."
	pytest tests/ -v -m "not integration"

test-integration:
	@echo "Running integration tests..."
	pytest tests/ -v -m "integration"

test-coverage:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=app --cov-report=html --cov-report=term

# Production commands
prod-build:
	@echo "Building production image..."
	docker build -f Dockerfile.prod -t clinicai:prod .

prod-up:
	@echo "Starting production services..."
	docker-compose -f docker-compose.prod.yml up -d

prod-logs:
	@echo "Showing production logs..."
	docker-compose -f docker-compose.prod.yml logs -f

# Security checks
security-check:
	@echo "Running security checks..."
	safety check
	bandit -r app/

# Setup commands
setup-env:
	@echo "Setting up environment..."
	cp env.example .env
	@echo "Please edit .env file with your configuration"

setup-hooks:
	@echo "Setting up git hooks..."
	pre-commit install

# Deployment helpers
deploy-check:
	@echo "Checking deployment readiness..."
	@echo "Testing environment variables..."
	python -c "from app.config import settings; print('✓ Config loaded successfully')"
	@echo "Testing database connection..."
	docker-compose exec app python -c "from app.db import db; import asyncio; asyncio.run(db.connect()); print('✓ Database connection successful')"
	
ngrok-tunnel:
	@echo "Starting ngrok tunnel..."
	@echo "Make sure ngrok is installed and configured"
	ngrok http 8000

# Monitoring
monitor:
	@echo "Monitoring services..."
	watch -n 5 'docker-compose ps && echo "" && curl -s http://localhost:8000/health | jq .'

stats:
	@echo "Service statistics..."
	docker stats clinicai-app clinicai-mongo --no-stream

