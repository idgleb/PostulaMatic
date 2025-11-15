#!/bin/bash
# Script para verificar y limpiar locks de scraping en el servidor

SSH_KEY="$HOME/.ssh/jetinnohetzner_ed25519"
SERVER_USER="deploy"
SERVER_HOST="178.156.188.95"
APP_DIR="/home/deploy/apps/postulamatic"

# Verificar si se pasó el flag --force-release
FORCE_RELEASE=false
if [ "$1" == "--force-release" ]; then
    FORCE_RELEASE=true
    echo "⚠️ Modo FORCE RELEASE activado - se limpiará el lock si está huérfano"
    echo ""
fi

echo "🔍 Verificando estado del lock de scraping en el servidor..."
echo ""

# Verificar si la clave existe
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ Clave SSH no encontrada: $SSH_KEY"
    exit 1
fi

# Ejecutar comando de verificación
if [ "$FORCE_RELEASE" = true ]; then
    echo "Ejecutando verificación con limpieza automática..."
    ssh -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=10 "$SERVER_USER@$SERVER_HOST" \
        "cd $APP_DIR && docker compose exec -T postulamatic_web python manage.py check_scraping_lock --force-release" 2>&1
else
    echo "Ejecutando verificación (sin limpiar)..."
    ssh -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=10 "$SERVER_USER@$SERVER_HOST" \
        "cd $APP_DIR && docker compose exec -T postulamatic_web python manage.py check_scraping_lock" 2>&1
    
    echo ""
    echo "💡 Para limpiar un lock huérfano, ejecuta:"
    echo "   bash scripts/check_scraping_lock_remote.sh --force-release"
fi

echo ""
echo "✅ Verificación completada"

