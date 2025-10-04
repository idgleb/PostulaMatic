#!/bin/bash

# Script para validar configuración de Nginx antes de recargar

CONFIG_FILE="/home/deploy/conf.d/postulamatic.conf"
NGINX_CONTAINER="nginx-proxy"

echo "🔍 Validando configuración de Nginx..."

# Verificar que el archivo existe
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "❌ Error: Archivo de configuración no encontrado: $CONFIG_FILE"
    exit 1
fi

# Verificar sintaxis básica
if ! grep -q "server_name postulamatic.app" "$CONFIG_FILE"; then
    echo "❌ Error: server_name no encontrado en configuración"
    exit 1
fi

if ! grep -q "proxy_pass http://postulamatic-postulamatic_web-1:8000" "$CONFIG_FILE"; then
    echo "❌ Error: proxy_pass incorrecto en configuración"
    exit 1
fi

# Verificar que el contenedor Nginx existe
if ! docker ps | grep -q "$NGINX_CONTAINER"; then
    echo "❌ Error: Contenedor Nginx no está ejecutándose"
    exit 1
fi

# Validar configuración con nginx -t
if docker exec "$NGINX_CONTAINER" nginx -t; then
    echo "✅ Configuración de Nginx válida"
    exit 0
else
    echo "❌ Error: Configuración de Nginx inválida"
    exit 1
fi
