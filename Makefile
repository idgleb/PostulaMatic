# Makefile para PostulaMatic
# Simplifica comandos de desarrollo y despliegue

.PHONY: help build up down logs shell migrate deploy deploy-dry-run health-check nginx-validate nginx-reload

# Variables
SSH_KEY := $(HOME)/.ssh/postulamatic_win_ed25519
SERVER := deploy@178.156.188.95

help: ## Mostrar ayuda
	@echo "Comandos disponibles:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Construir contenedores Docker
	docker compose build

up: ## Levantar servicios
	docker compose up -d

down: ## Bajar servicios
	docker compose down

logs: ## Ver logs de los servicios
	docker compose logs -f

shell: ## Abrir shell en el contenedor web
	docker compose exec postulamatic_web bash

migrate: ## Ejecutar migraciones
	docker compose run --rm postulamatic_web python manage.py migrate

deploy: ## Desplegar a producción
	@echo "🚀 Desplegando a producción..."
	@chmod +x scripts/deploy.sh
	@./scripts/deploy.sh

deploy-dry-run: ## Simular despliegue (sin cambios reales)
	@echo "🔍 Simulando despliegue..."
	@chmod +x scripts/deploy.sh
	@./scripts/deploy.sh --dry-run

health-check: ## Verificar salud del sitio en producción
	@echo "🏥 Verificando salud del sitio..."
	@chmod +x scripts/health-check.sh
	@ssh -i $(SSH_KEY) -o BatchMode=yes $(SERVER) 'cd /home/deploy/apps/postulamatic && bash -s' < scripts/health-check.sh

nginx-validate: ## Validar configuración de Nginx en producción
	@echo "🔍 Validando configuración de Nginx..."
	@chmod +x scripts/nginx-validate.sh
	@ssh -i $(SSH_KEY) -o BatchMode=yes $(SERVER) 'bash -s' < scripts/nginx-validate.sh

nginx-reload: ## Recargar Nginx en producción
	@echo "🔄 Recargando Nginx..."
	@ssh -i $(SSH_KEY) -o BatchMode=yes $(SERVER) 'docker exec nginx-proxy nginx -s reload'

nginx-backup: ## Crear backup de configuración de Nginx
	@echo "📦 Creando backup de Nginx..."
	@chmod +x scripts/nginx-backup.sh
	@ssh -i $(SSH_KEY) -o BatchMode=yes $(SERVER) 'bash -s' < scripts/nginx-backup.sh

setup-dev: ## Configurar entorno de desarrollo
	@echo "⚙️ Configurando entorno de desarrollo..."
	@pip install -r requirements.txt
	@python manage.py migrate
	@python manage.py collectstatic --noinput
	@echo "✅ Entorno de desarrollo configurado"

test: ## Ejecutar tests
	python manage.py test

lint: ## Ejecutar linting
	black .
	ruff check .
	isort .

format: ## Formatear código
	black .
	isort .
