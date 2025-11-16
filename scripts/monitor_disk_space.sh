#!/bin/bash
# Script para monitorear espacio en disco y limpiar automáticamente si es necesario

# Configuración
DISK_THRESHOLD=80          # Umbral de uso de disco (%)
CRITICAL_THRESHOLD=90      # Umbral crítico (%)
LOG_FILE="/var/log/disk_monitor.log"

# Obtener uso actual del disco
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')

# Función de logging
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_message "📊 Verificando espacio en disco: ${DISK_USAGE}% usado"

# Si el uso es mayor al umbral crítico (90%), limpiar agresivamente
if [ "$DISK_USAGE" -gt "$CRITICAL_THRESHOLD" ]; then
    log_message "🚨 CRÍTICO: Disco al ${DISK_USAGE}% - Limpiando agresivamente..."
    
    # Limpieza completa de Docker
    log_message "🧹 Ejecutando limpieza completa de Docker..."
    docker system prune -a -f --volumes 2>&1 | tee -a "$LOG_FILE"
    
    # Limpiar logs antiguos de aplicación (mayores a 7 días)
    log_message "🧹 Limpiando logs antiguos..."
    find /var/log -name "*.log" -type f -mtime +7 -delete 2>/dev/null
    
    # Recalcular uso
    NEW_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    FREED=$((DISK_USAGE - NEW_USAGE))
    log_message "✅ Limpieza completada. Liberado: ${FREED}% | Nuevo uso: ${NEW_USAGE}%"
    
elif [ "$DISK_USAGE" -gt "$DISK_THRESHOLD" ]; then
    log_message "⚠️ ADVERTENCIA: Disco al ${DISK_USAGE}% - Limpiando moderadamente..."
    
    # Limpieza moderada de Docker (solo lo no usado)
    log_message "🧹 Limpiando recursos no usados de Docker..."
    docker container prune -f 2>&1 | tee -a "$LOG_FILE"
    docker image prune -f 2>&1 | tee -a "$LOG_FILE"
    docker volume prune -f 2>&1 | tee -a "$LOG_FILE"
    docker builder prune -f 2>&1 | tee -a "$LOG_FILE"
    
    # Recalcular uso
    NEW_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    FREED=$((DISK_USAGE - NEW_USAGE))
    log_message "✅ Limpieza completada. Liberado: ${FREED}% | Nuevo uso: ${NEW_USAGE}%"
    
else
    log_message "✅ Espacio en disco OK (${DISK_USAGE}%)"
fi

# Mostrar estadísticas de Docker
log_message "📦 Estadísticas de Docker:"
docker system df 2>&1 | tee -a "$LOG_FILE"

