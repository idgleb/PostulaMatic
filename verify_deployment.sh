#!/bin/bash

# Script de verificación post-despliegue para PostulaMatic

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🔍 Verificando despliegue de PostulaMatic..."

# 1. Verificar contenedores
print_status "Verificando contenedores Docker..."
docker-compose ps

# 2. Verificar servicios web
print_status "Verificando servicio web..."
if curl -f -s http://localhost:8000/ > /dev/null; then
    print_success "Servicio web respondiendo correctamente"
else
    print_error "Servicio web no responde"
    exit 1
fi

# 3. Verificar base de datos
print_status "Verificando conexión a base de datos..."
if docker-compose exec -T postulamatic_web python manage.py check --database default; then
    print_success "Conexión a base de datos OK"
else
    print_error "Error de conexión a base de datos"
    exit 1
fi

# 4. Verificar migraciones
print_status "Verificando migraciones..."
if docker-compose exec -T postulamatic_web python manage.py showmigrations --plan | grep -q "\[X\]"; then
    print_success "Migraciones aplicadas correctamente"
else
    print_warning "No hay migraciones aplicadas o hay problemas"
fi

# 5. Verificar Redis
print_status "Verificando Redis..."
if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
    print_success "Redis funcionando"
else
    print_error "Redis no responde"
    exit 1
fi

# 6. Verificar Celery Worker
print_status "Verificando Celery Worker..."
if docker-compose exec -T worker celery -A postulamatic inspect ping 2>/dev/null | grep -q "pong"; then
    print_success "Celery Worker funcionando"
else
    print_warning "Celery Worker puede no estar funcionando correctamente"
fi

# 7. Verificar Playwright
print_status "Verificando Playwright..."
if docker-compose exec -T postulamatic_web python -c "from playwright.sync_api import sync_playwright; print('OK')" 2>/dev/null; then
    print_success "Playwright instalado"
else
    print_warning "Playwright puede necesitar instalación de navegadores"
fi

# 8. Verificar encriptación
print_status "Verificando sistema de encriptación..."
if docker-compose exec -T postulamatic_web python -c "from matching.utils.encryption import EncryptionManager; em = EncryptionManager(); print('Encriptación OK')" 2>/dev/null; then
    print_success "Sistema de encriptación funcionando"
else
    print_error "Error en sistema de encriptación"
    exit 1
fi

# 9. Verificar archivos estáticos
print_status "Verificando archivos estáticos..."
if [ -d "staticfiles" ] && [ "$(ls -A staticfiles)" ]; then
    print_success "Archivos estáticos recopilados"
else
    print_warning "Archivos estáticos no encontrados o vacíos"
fi

# 10. Verificar logs recientes
print_status "Verificando logs recientes..."
echo "--- Logs de los últimos 10 minutos ---"
docker-compose logs --since=10m postulamatic_web | tail -20

print_success "🎉 Verificación completada!"
print_status "Para monitorear en tiempo real: docker-compose logs -f"
