# Guía de Prevención: Problemas de Disco Lleno y Redis

Esta guía explica cómo evitar los problemas de disco lleno y bloqueo de Redis que ocurrieron el 2025-11-16.

## 📋 Resumen de Soluciones Implementadas

### 1. Límites de Logs en Docker (✅ Ya implementado)

**Archivo**: `docker-compose.yml`

Todos los servicios ahora tienen límites de logs:
- **Web/Worker/Beat**: Max 10MB por archivo, 3 archivos (30MB máx por servicio)
- **Redis/FlareSolverr**: Max 5MB por archivo, 2 archivos (10MB máx por servicio)

**Configuración de Redis mejorada**:
```yaml
command: redis-server --save 60 1 --loglevel warning --maxmemory 256mb --maxmemory-policy allkeys-lru
```
- `--save 60 1`: Guarda snapshot cada 60s si hay al menos 1 cambio
- `--loglevel warning`: Solo logs importantes
- `--maxmemory 256mb`: Límite de memoria
- `--maxmemory-policy allkeys-lru`: Elimina claves viejas cuando se llena

**Para aplicar los cambios**:
```bash
cd /home/deploy/postulamatic
git pull
docker-compose down
docker-compose up -d
```

### 2. Scripts de Mantenimiento Automático

#### a) Monitor de Disco (`monitor_disk_space.sh`)
- **Ejecución**: Cada hora (vía cron)
- **Función**: Verifica uso de disco
- **Acción si uso > 80%**: Limpieza moderada (contenedores/imágenes/volúmenes no usados)
- **Acción si uso > 90%**: Limpieza agresiva (todo Docker + logs antiguos)
- **Log**: `/var/log/disk_monitor.log`

#### b) Limpieza de Docker (`cleanup_docker.sh`)
- **Ejecución**: Semanal (domingos 3:00 AM)
- **Función**: Limpieza preventiva de Docker
- **Limpia**:
  - Contenedores detenidos
  - Imágenes no usadas
  - Volúmenes no usados
  - Build cache

### 3. Instalación del Sistema de Mantenimiento

#### En el servidor:

```bash
# 1. Conectar al servidor
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95

# 2. Ir al directorio del proyecto
cd /home/deploy/postulamatic

# 3. Actualizar código
git pull

# 4. Instalar scripts de mantenimiento
bash scripts/setup_automatic_maintenance.sh

# 5. Verificar cron jobs instalados
crontab -l
```

**Deberías ver**:
```
# Monitoreo de espacio en disco cada hora
0 * * * * /usr/local/bin/monitor_disk_space.sh

# Limpieza semanal de Docker (domingos a las 3 AM)
0 3 * * 0 /usr/local/bin/cleanup_docker.sh
```

## 🔍 Monitoreo y Verificación

### Verificar Espacio en Disco
```bash
df -h /
```
**Objetivo**: Mantener uso < 80%

### Ver Logs de Monitoreo
```bash
tail -f /var/log/disk_monitor.log
```

### Ver Estadísticas de Docker
```bash
docker system df
```

### Limpieza Manual (si es necesario)
```bash
# Limpieza moderada
bash /usr/local/bin/cleanup_docker.sh

# Limpieza agresiva (cuidado!)
docker system prune -a -f --volumes
```

## 🚨 Alertas y Umbrales

### Umbrales Configurados

| Uso de Disco | Estado | Acción Automática |
|--------------|--------|-------------------|
| < 80% | ✅ Normal | Ninguna |
| 80-90% | ⚠️ Advertencia | Limpieza moderada |
| > 90% | 🚨 Crítico | Limpieza agresiva |

### Verificación de Redis

```bash
# Verificar que Redis funciona
docker exec postulamatic-redis-1 redis-cli PING
# Debe responder: PONG

# Ver info de Redis
docker exec postulamatic-redis-1 redis-cli INFO memory
```

## 📊 Mantenimiento Preventivo Manual

### Cada Semana (opcional, ya es automático)
```bash
bash /usr/local/bin/cleanup_docker.sh
```

### Cada Mes
```bash
# Ver qué está usando más espacio
du -sh /var/lib/docker/* | sort -h

# Ver imágenes antiguas
docker images | grep -v $(docker ps -a | awk '{print $2}')
```

### Verificar Locks de Scraping
```bash
docker exec postulamatic-postulamatic_web-1 python manage.py check_scraping_lock
```

## 🔧 Troubleshooting

### Problema: Redis dice "MISCONF ... unable to persist to disk"

**Solución temporal**:
```bash
docker exec postulamatic-redis-1 redis-cli CONFIG SET stop-writes-on-bgsave-error no
```

**Solución permanente**:
1. Liberar espacio en disco (ver arriba)
2. Reiniciar Redis: `docker restart postulamatic-redis-1`

### Problema: Lock de scraping atascado

```bash
# Verificar lock
docker exec postulamatic-postulamatic_web-1 python manage.py check_scraping_lock

# Liberar si está atascado
docker exec postulamatic-postulamatic_web-1 python manage.py check_scraping_lock --force-release
```

### Problema: Disco sigue llenándose

**Buscar archivos grandes**:
```bash
# Top 20 archivos más grandes
find /home /var -type f -size +100M 2>/dev/null | xargs du -h | sort -h | tail -20

# Ver qué directorio usa más espacio
du -sh /* | sort -h | tail -10
```

## 📈 Mejoras Futuras (Opcional)

### Monitoreo Avanzado con Prometheus

```yaml
# docker-compose.yml (agregar)
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

### Alertas por Email

Configurar alertas cuando:
- Disco > 85%
- Redis tiene errores
- Locks no se liberan en > 10 minutos

### Backup Automático

```bash
# Cron job para backup diario
0 2 * * * docker exec postulamatic-db-1 pg_dump -U postgres > /backups/db-$(date +\%Y\%m\%d).sql
```

## ✅ Checklist de Configuración

- [ ] `docker-compose.yml` actualizado con límites de logs
- [ ] Scripts de mantenimiento instalados (`setup_automatic_maintenance.sh`)
- [ ] Cron jobs configurados (verificar con `crontab -l`)
- [ ] Verificar espacio en disco < 80%
- [ ] Redis funcionando correctamente
- [ ] No hay locks atascados
- [ ] Logs de monitoreo activos (`tail -f /var/log/disk_monitor.log`)

## 📞 Contacto y Soporte

Si los problemas persisten:
1. Verificar logs: `/var/log/disk_monitor.log`
2. Revisar estado de Docker: `docker system df`
3. Verificar Redis: `docker logs postulamatic-redis-1 --tail 50`
4. Consultar documentación de incidente: `docs/INCIDENTE_DISCO_LLENO_2025-11-16.md`

