#!/bin/bash

# Script para configurar el monitoreo automático de Nginx
# Este script configura un cron job que verifica la conexión cada minuto

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_SCRIPT="$SCRIPT_DIR/nginx_auto_reload.sh"
CRON_JOB="* * * * * $MONITOR_SCRIPT >> /home/deploy/nginx_auto_reload.log 2>&1"

echo "🔧 Configurando monitoreo automático de Nginx..."

# Hacer el script ejecutable
chmod +x "$MONITOR_SCRIPT"

# Verificar si el cron job ya existe
if crontab -l 2>/dev/null | grep -q "nginx_auto_reload.sh"; then
    echo "⚠️  El cron job ya existe, omitiendo..."
else
    # Agregar el cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Cron job agregado: Verificación cada minuto"
fi

echo "✅ Monitoreo configurado correctamente"
echo "📋 Para ver los logs: tail -f /home/deploy/nginx_auto_reload.log"
echo "📋 Para desactivar: crontab -e (y eliminar la línea con nginx_auto_reload.sh)"

