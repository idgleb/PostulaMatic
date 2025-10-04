#!/bin/bash

# Script para backup automático de configuración de Nginx
# Se ejecuta antes de cada despliegue

BACKUP_DIR="/home/deploy/nginx-backups"
CONFIG_FILE="/home/deploy/conf.d/postulamatic.conf"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/postulamatic.conf.$TIMESTAMP"

# Crear directorio de backups si no existe
mkdir -p "$BACKUP_DIR"

# Backup de la configuración actual
cp "$CONFIG_FILE" "$BACKUP_FILE"

# Mantener solo los últimos 10 backups
ls -t "$BACKUP_DIR"/postulamatic.conf.* | tail -n +11 | xargs -r rm

echo "✅ Backup creado: $BACKUP_FILE"
echo "📊 Backups disponibles:"
ls -la "$BACKUP_DIR"/postulamatic.conf.* | tail -5
