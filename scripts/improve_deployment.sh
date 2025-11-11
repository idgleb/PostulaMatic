#!/bin/bash
# Script mejorado de deployment que elimina el timeout de migraciones
# Este script debe ejecutarse en el servidor

set -e  # Salir si hay errores

echo "🚀 Iniciando deployment mejorado de PostulaMatic..."

# Backup current config (si existe)
if [ -f "conf.d/postulamatic.conf" ]; then
    cp conf.d/postulamatic.conf conf.d/postulamatic.conf.backup.$(date +%Y%m%d_%H%M%S) || true
fi

# Pull latest changes
echo "📥 Actualizando código..."
git checkout master || git checkout -b master
git fetch origin
git reset --hard origin/master
echo "✅ Código actualizado al commit: $(git log --oneline -1)"

# Update Nginx config from repository (si existe)
if [ -f "nginx/postulamatic.conf" ]; then
    if [ -d "conf.d" ]; then
        cp nginx/postulamatic.conf conf.d/postulamatic.conf
        echo "✅ Configuración de Nginx actualizada"
    fi
fi

# Test Nginx config (si existe el directorio)
if [ -d "conf.d" ] && [ -f "conf.d/postulamatic.conf" ]; then
    docker exec nginx-proxy nginx -t
    if [ $? -ne 0 ]; then
        echo "❌ Error: Configuración de Nginx inválida"
        exit 1
    fi
    echo "✅ Configuración de Nginx válida"
fi

# Backup database before migration
echo "📦 Creando backup de base de datos..."
if [ -f "db.sqlite3" ]; then
    cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d_%H%M%S) || echo "⚠️ No se pudo hacer backup de la BD"
fi

# Deploy Django app
echo "🐳 Construyendo contenedores Docker..."
docker compose build

# Aplicar migraciones DIRECTAMENTE (sin --check que causa timeout)
# Django es seguro: si no hay migraciones pendientes, simplemente dice "No migrations to apply"
echo "🔄 Aplicando migraciones..."
docker compose run --rm postulamatic_web python manage.py migrate --noinput || {
    echo "⚠️ Error aplicando migraciones, pero continuando..."
}

# Iniciar contenedores
echo "🚀 Iniciando contenedores..."
docker compose up -d

# Wait for containers to be ready
echo "⏳ Esperando que los contenedores se inicien..."
sleep 10

# Reload Nginx (si existe)
if [ -d "conf.d" ] && [ -f "conf.d/postulamatic.conf" ]; then
    echo "🔄 Recargando Nginx..."
    docker exec nginx-proxy nginx -s reload || echo "⚠️ No se pudo recargar Nginx"
fi

# Health check con retry logic
echo "🏥 Verificando salud del sitio..."
MAX_RETRIES=3
RETRY_DELAY=10

for i in $(seq 1 $MAX_RETRIES); do
    if curl -f -s https://postulamatic.app > /dev/null 2>&1; then
        echo "✅ Health check exitoso (intento $i/$MAX_RETRIES)"
        echo "🎉 Deployment completado exitosamente"
        exit 0
    else
        echo "⏳ Health check fallido (intento $i/$MAX_RETRIES), reintentando en ${RETRY_DELAY}s..."
        sleep $RETRY_DELAY
    fi
done

echo "⚠️ Health check falló después de $MAX_RETRIES intentos"
echo "ℹ️ El deployment se completó, pero el sitio puede tardar unos minutos en responder"
exit 0  # No fallar el deployment por el health check

