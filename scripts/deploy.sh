#!/bin/bash

# Script de despliegue seguro para PostulaMatic
# Uso: ./scripts/deploy.sh [--dry-run]

set -e  # Salir si hay errores

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 MODO DRY-RUN: No se aplicarán cambios reales"
fi

echo "🚀 Iniciando despliegue de PostulaMatic..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Función para ejecutar comandos con verificación
run_ssh() {
    local cmd="$1"
    local description="$2"
    
    echo "📋 $description"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "   [DRY-RUN] ssh deploy@178.156.188.95 '$cmd'"
        return 0
    fi
    
    if ssh -i ~/.ssh/postulamatic_win_ed25519 -o BatchMode=yes deploy@178.156.188.95 "$cmd"; then
        log_info "$description completado"
        return 0
    else
        log_error "$description falló"
        return 1
    fi
}

# 1. Backup de configuración actual
echo "📦 Creando backup de configuración actual..."
run_ssh "cp /home/deploy/conf.d/postulamatic.conf /home/deploy/conf.d/postulamatic.conf.backup.\$(date +%Y%m%d_%H%M%S)" "Backup de configuración"

# 2. Actualizar código
echo "📥 Actualizando código desde repositorio..."
run_ssh "cd /home/deploy/apps/postulamatic && git pull origin main" "Git pull"

# 3. Actualizar configuración de Nginx desde repo
echo "⚙️ Actualizando configuración de Nginx..."
if [[ "$DRY_RUN" == "true" ]]; then
    echo "   [DRY-RUN] Copiando nginx/postulamatic.conf a servidor"
else
    scp -i ~/.ssh/postulamatic_win_ed25519 nginx/postulamatic.conf deploy@178.156.188.95:/home/deploy/conf.d/postulamatic.conf
    log_info "Configuración de Nginx copiada"
fi

# 4. Validar configuración de Nginx
echo "🔍 Validando configuración de Nginx..."
if run_ssh "docker exec nginx-proxy nginx -t" "Validación de Nginx"; then
    log_info "Configuración de Nginx es válida"
    
    # 5. Recargar Nginx
    echo "🔄 Recargando Nginx..."
    run_ssh "docker exec nginx-proxy nginx -s reload" "Recarga de Nginx"
else
    log_error "Configuración de Nginx inválida, restaurando backup"
    run_ssh "cp /home/deploy/conf.d/postulamatic.conf.backup.\$(date +%Y%m%d_%H%M%S) /home/deploy/conf.d/postulamatic.conf" "Restauración de backup"
    exit 1
fi

# 6. Desplegar aplicación Django
echo "🐳 Desplegando aplicación Django..."
run_ssh "cd /home/deploy/apps/postulamatic && docker compose build" "Build de Docker"
run_ssh "cd /home/deploy/apps/postulamatic && docker compose run --rm postulamatic_web python manage.py migrate" "Migraciones"
run_ssh "cd /home/deploy/apps/postulamatic && docker compose up -d" "Start de contenedores"

# 7. Health check
echo "🏥 Verificando salud del sitio..."
sleep 10
if run_ssh "curl -f -s https://postulamatic.app > /dev/null" "Health check"; then
    log_info "Despliegue exitoso - sitio respondiendo correctamente"
    echo ""
    echo "🎉 ¡Despliegue completado exitosamente!"
    echo "🌐 Sitio disponible en: https://postulamatic.app"
else
    log_error "Despliegue falló - sitio no responde"
    exit 1
fi
