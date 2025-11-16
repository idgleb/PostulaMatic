#!/bin/bash
# Script para configurar mantenimiento automático del servidor

echo "⚙️ Configurando mantenimiento automático..."
echo ""

# Crear directorio de logs si no existe
sudo mkdir -p /var/log
sudo touch /var/log/disk_monitor.log
sudo chmod 644 /var/log/disk_monitor.log

# Copiar scripts a /usr/local/bin
echo "📋 Copiando scripts de mantenimiento..."
sudo cp scripts/monitor_disk_space.sh /usr/local/bin/
sudo cp scripts/cleanup_docker.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/monitor_disk_space.sh
sudo chmod +x /usr/local/bin/cleanup_docker.sh

# Configurar cron jobs
echo "⏰ Configurando cron jobs..."

# Crear archivo temporal con los cron jobs
CRON_FILE=$(mktemp)

# Mantener crontab existente
crontab -l > "$CRON_FILE" 2>/dev/null || true

# Agregar nuevos cron jobs si no existen
if ! grep -q "monitor_disk_space.sh" "$CRON_FILE"; then
    echo "" >> "$CRON_FILE"
    echo "# Monitoreo de espacio en disco cada hora" >> "$CRON_FILE"
    echo "0 * * * * /usr/local/bin/monitor_disk_space.sh" >> "$CRON_FILE"
fi

if ! grep -q "cleanup_docker.sh" "$CRON_FILE"; then
    echo "" >> "$CRON_FILE"
    echo "# Limpieza semanal de Docker (domingos a las 3 AM)" >> "$CRON_FILE"
    echo "0 3 * * 0 /usr/local/bin/cleanup_docker.sh" >> "$CRON_FILE"
fi

# Instalar nuevo crontab
crontab "$CRON_FILE"
rm "$CRON_FILE"

echo ""
echo "✅ Mantenimiento automático configurado:"
echo ""
echo "  🔍 Monitoreo de disco: Cada hora"
echo "      - Si uso > 90%: Limpieza agresiva automática"
echo "      - Si uso > 80%: Limpieza moderada automática"
echo ""
echo "  🧹 Limpieza de Docker: Domingos 3:00 AM"
echo "      - Elimina contenedores detenidos"
echo "      - Elimina imágenes no usadas"
echo "      - Elimina volúmenes no usados"
echo "      - Elimina build cache"
echo ""
echo "  📝 Logs guardados en: /var/log/disk_monitor.log"
echo ""
echo "Para ver los cron jobs configurados:"
echo "  crontab -l"
echo ""
echo "Para ver el log de monitoreo:"
echo "  tail -f /var/log/disk_monitor.log"
echo ""
echo "✅ Configuración completada"

