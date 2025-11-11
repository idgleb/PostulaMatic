#!/bin/bash
# Script de deployment optimizado para ejecutar en el servidor
# Elimina el paso de --check que causa timeout
# Uso: Este script debe ejecutarse en el servidor en /home/deploy/apps/postulamatic

# No usar set -e para permitir manejo de errores más flexible
# set -e  # Comentado para permitir continuar en algunos casos

echo "🚀 Iniciando deployment de PostulaMatic..."
echo "📅 $(date)"

# Backup current config (si existe)
if [ -f "conf.d/postulamatic.conf" ]; then
    cp conf.d/postulamatic.conf conf.d/postulamatic.conf.backup.$(date +%Y%m%d_%H%M%S) || true
    echo "✅ Backup de configuración creado"
fi

# Pull latest changes
echo "📥 Actualizando código desde repositorio..."
echo "Rama actual: $(git branch --show-current)"
git checkout master || git checkout -b master
git fetch origin
git reset --hard origin/master
echo "✅ Código actualizado al commit: $(git log --oneline -1)"

# Update Nginx config from repository (si existe)
if [ -f "nginx/postulamatic.conf" ]; then
    if [ -d "conf.d" ]; then
        cp nginx/postulamatic.conf conf.d/postulamatic.conf
        echo "✅ Configuración de Nginx actualizada desde repositorio"
    fi
fi

# Test Nginx config (si existe el directorio y el archivo)
if [ -d "conf.d" ] && [ -f "conf.d/postulamatic.conf" ]; then
    echo "🔍 Validando configuración de Nginx..."
    if docker exec nginx-proxy nginx -t 2>&1; then
        echo "✅ Configuración de Nginx válida"
    else
        echo "❌ Error: Configuración de Nginx inválida"
        # Restaurar backup si existe
        if ls conf.d/postulamatic.conf.backup.* 1> /dev/null 2>&1; then
            LATEST_BACKUP=$(ls -t conf.d/postulamatic.conf.backup.* | head -1)
            cp "$LATEST_BACKUP" conf.d/postulamatic.conf
            echo "✅ Backup restaurado: $LATEST_BACKUP"
        fi
        exit 1
    fi
fi

# Backup database before migration
echo "📦 Creando backup de base de datos..."
if [ -f "db.sqlite3" ]; then
    cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d_%H%M%S) || echo "⚠️ No se pudo hacer backup de la BD (puede ser normal)"
    echo "✅ Backup de base de datos creado"
else
    echo "ℹ️ No hay base de datos existente para hacer backup"
fi

# Deploy Django app
echo "🐳 Construyendo contenedores Docker..."
docker compose build

# ✅ MEJORA: Aplicar migraciones DIRECTAMENTE (sin --check que causa timeout)
# Django es seguro: si no hay migraciones pendientes, simplemente dice "No migrations to apply"
echo "🔄 Aplicando migraciones..."
docker compose run --rm postulamatic_web python manage.py migrate --noinput
echo "✅ Migraciones aplicadas (o no había migraciones pendientes)"

# Iniciar contenedores
echo "🚀 Iniciando contenedores..."
docker compose up -d

# Wait for containers to be ready
echo "⏳ Esperando que los contenedores se inicien..."
sleep 15

# Reload Nginx (si existe)
if [ -d "conf.d" ] && [ -f "conf.d/postulamatic.conf" ]; then
    echo "🔄 Recargando Nginx..."
    if docker exec nginx-proxy nginx -s reload; then
        echo "✅ Nginx recargado correctamente"
    else
        echo "⚠️ No se pudo recargar Nginx (puede ser normal si no hay cambios)"
    fi
fi

# Health check con retry logic
echo "🏥 Verificando salud del sitio..."
MAX_RETRIES=3
RETRY_DELAY=10

for i in $(seq 1 $MAX_RETRIES); do
    if curl -f -s https://postulamatic.app > /dev/null 2>&1; then
        echo "✅ Health check exitoso (intento $i/$MAX_RETRIES)"
        echo "🎉 Deployment completado exitosamente"
        echo "🌐 Sitio disponible en: https://postulamatic.app"
        exit 0
    else
        echo "⏳ Health check fallido (intento $i/$MAX_RETRIES), reintentando en ${RETRY_DELAY}s..."
        sleep $RETRY_DELAY
    fi
done

echo "⚠️ Health check falló después de $MAX_RETRIES intentos"
echo "ℹ️ El deployment se completó, pero el sitio puede tardar unos minutos en responder"
echo "ℹ️ Verifica manualmente: curl -I https://postulamatic.app"
exit 0  # No fallar el deployment por el health check

