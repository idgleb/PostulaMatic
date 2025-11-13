#!/bin/bash

# Script para reiniciar Nginx automáticamente cuando Django se reinicia
# Este script monitorea el estado de la conexión y reinicia Nginx si es necesario

NGINX_CONTAINER="nginx-proxy"
DJANGO_CONTAINER="postulamatic-postulamatic_web-1"
LOG_FILE="/home/deploy/nginx_auto_reload.log"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Verificar que Nginx está corriendo
if ! docker ps | grep -q "$NGINX_CONTAINER"; then
    log_message "❌ Nginx no está corriendo, iniciando..."
    docker start "$NGINX_CONTAINER" || exit 1
    log_message "✅ Nginx iniciado"
    exit 0
fi

# Verificar que Django está corriendo
if ! docker ps | grep -q "$DJANGO_CONTAINER"; then
    log_message "⚠️  Django no está corriendo, esperando..."
    exit 0
fi

# Intentar conectar desde Nginx a Django
if docker exec "$NGINX_CONTAINER" curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://$DJANGO_CONTAINER:8000" | grep -qE "^(200|400|301|302)"; then
    log_message "✅ Conexión OK: Nginx puede conectarse a Django"
    exit 0
else
    log_message "⚠️  Conexión fallida: Reiniciando Nginx para re-resolver DNS..."
    docker restart "$NGINX_CONTAINER"
    sleep 3
    
    # Verificar nuevamente
    if docker exec "$NGINX_CONTAINER" curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://$DJANGO_CONTAINER:8000" | grep -qE "^(200|400|301|302)"; then
        log_message "✅ Conexión restaurada después del reinicio"
        exit 0
    else
        log_message "❌ Error: Conexión aún falla después del reinicio"
        exit 1
    fi
fi

