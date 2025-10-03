#!/bin/bash

# Script de despliegue para PostulaMatic
# Ejecutar en el servidor de producción

set -e  # Salir si hay algún error

echo "🚀 Iniciando despliegue de PostulaMatic..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
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

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.yml" ]; then
    print_error "No se encontró docker-compose.yml. Asegúrate de estar en el directorio del proyecto."
    exit 1
fi

# 1. Backup de la base de datos
print_status "Haciendo backup de la base de datos..."
if command -v pg_dump &> /dev/null; then
    # Si tienes PostgreSQL instalado localmente
    pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
    print_success "Backup de base de datos completado"
else
    print_warning "pg_dump no encontrado. Considera hacer backup manual de la base de datos."
fi

# 2. Detener contenedores
print_status "Deteniendo contenedores..."
docker-compose down

# 3. Actualizar código desde GitHub
print_status "Actualizando código desde GitHub..."
git pull origin master

# 4. Reconstruir contenedores
print_status "Reconstruyendo contenedores con dependencias actualizadas..."
docker-compose build --no-cache

# 5. Iniciar contenedores
print_status "Iniciando contenedores..."
docker-compose up -d

# 6. Esperar a que los servicios estén listos
print_status "Esperando a que los servicios estén listos..."
sleep 10

# 7. Aplicar migraciones
print_status "Aplicando migraciones de base de datos..."
docker-compose exec -T postulamatic_web python manage.py migrate

# 8. Recopilar archivos estáticos
print_status "Recopilando archivos estáticos..."
docker-compose exec -T postulamatic_web python manage.py collectstatic --noinput

# 9. Verificar servicios
print_status "Verificando servicios..."

# Verificar que la web esté respondiendo
if curl -f http://localhost:8000/ > /dev/null 2>&1; then
    print_success "Servicio web funcionando correctamente"
else
    print_error "El servicio web no está respondiendo"
    exit 1
fi

# Verificar Redis
if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
    print_success "Redis funcionando correctamente"
else
    print_error "Redis no está respondiendo"
    exit 1
fi

# Verificar Celery Worker
if docker-compose ps worker | grep -q "Up"; then
    print_success "Celery Worker funcionando"
else
    print_error "Celery Worker no está funcionando"
    exit 1
fi

# Verificar Celery Beat
if docker-compose ps beat | grep -q "Up"; then
    print_success "Celery Beat funcionando"
else
    print_error "Celery Beat no está funcionando"
    exit 1
fi

# 10. Verificar Playwright
print_status "Verificando instalación de Playwright..."
docker-compose exec -T postulamatic_web python -c "from playwright.sync_api import sync_playwright; print('Playwright instalado correctamente')" 2>/dev/null && print_success "Playwright funcionando" || print_warning "Playwright puede necesitar instalación de navegadores"

# 11. Limpiar imágenes Docker no utilizadas
print_status "Limpiando imágenes Docker no utilizadas..."
docker image prune -f

print_success "🎉 Despliegue completado exitosamente!"
print_status "Puedes verificar la aplicación en: http://localhost:8000"
print_status "Para ver los logs: docker-compose logs -f"

# Mostrar estado de los contenedores
echo ""
print_status "Estado de los contenedores:"
docker-compose ps
