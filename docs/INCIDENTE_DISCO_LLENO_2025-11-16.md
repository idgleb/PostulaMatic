# Incidente: Disco Lleno y Redis Bloqueado (2025-11-16)

## Resumen

El servidor experimentó un problema crítico donde el disco se llenó al 100%, causando que Redis bloqueara todas las escrituras y, como consecuencia, que los locks de scraping no se pudieran liberar automáticamente.

## Cronología

1. **00:38 UTC** - Scraping manual iniciado
2. **00:38 UTC** - Scraping falla inmediatamente (Redis no puede escribir)
3. **00:40 UTC** - Lock queda atascado (no se puede liberar porque Redis no permite escrituras)
4. **01:00 UTC** - Diagnóstico realizado:
   - Disco al 100% de uso (38GB usados de 38GB)
   - Solo 2MB libres
   - Redis bloqueado: `MISCONF Redis is configured to save RDB snapshots, but it's currently unable to persist to disk`

## Causa Raíz

1. **Acumulación de imágenes Docker no usadas**: 29.77GB (90% recuperable)
2. **Build cache de Docker**: 2.26GB
3. **Total de espacio recuperable**: ~29GB

## Soluciones Aplicadas

### 1. Desbloqueo temporal de Redis
```bash
docker exec postulamatic-redis-1 redis-cli CONFIG SET stop-writes-on-bgsave-error no
```
Esto permite que Redis acepte escrituras temporalmente mientras se libera espacio.

### 2. Limpieza de Docker
```bash
docker system prune -a -f --volumes
```
**Resultado**: Liberados 29.09GB

### 3. Verificación de espacio
```bash
df -h /
# Antes: 38G   36G  2.0M 100% /
# Después: 38G   12G   25G  32% /
```

### 4. Reinicio de Redis
```bash
docker restart postulamatic-redis-1
```

### 5. Liberación manual del lock
```bash
docker exec postulamatic-postulamatic_web-1 python manage.py check_scraping_lock --force-release
```

## Estado Final

- ✅ Disco: 32% de uso (25GB libres)
- ✅ Redis: Funcionando correctamente
- ✅ Lock: Liberado exitosamente
- ✅ Sistema: Completamente operacional

## Prevención Futura

### 1. Monitoreo de Disco

Crear script de monitoreo:

```bash
#!/bin/bash
# scripts/monitor_disk_space.sh

THRESHOLD=80
USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')

if [ "$USAGE" -gt "$THRESHOLD" ]; then
    echo "⚠️ ADVERTENCIA: Disco al ${USAGE}%"
    echo "Ejecutando limpieza automática..."
    docker system prune -f
fi
```

### 2. Limpieza Automática Semanal

Agregar a crontab:
```bash
# Limpiar imágenes no usadas cada semana
0 3 * * 0 docker system prune -f
```

### 3. Límites de Logs de Docker

Actualizar `docker-compose.yml`:
```yaml
services:
  postulamatic_web:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 4. Alertas de Monitoreo

Configurar alertas cuando:
- Disco > 80%
- Redis tiene errores de escritura
- Locks no se liberan en > 10 minutos

## Lecciones Aprendidas

1. **El disco lleno causa fallas en cascada**:
   - Redis no puede escribir → Locks no se liberan → Frontend queda atascado

2. **Docker acumula mucho espacio sin limpieza**:
   - 29GB de imágenes no usadas
   - Limpieza manual necesaria periódicamente

3. **Necesidad de monitoreo proactivo**:
   - Sin monitoreo, el problema no se detecta hasta que es crítico

4. **Importancia de liberar locks en finally**:
   - Aunque teníamos el código, Redis bloqueado impidió que funcionara
   - El código mejorado (commit cc3cb8d) ahora tiene logging detallado para detectar estos casos

## Comandos Útiles

```bash
# Verificar espacio en disco
df -h /

# Ver qué está usando espacio en Docker
docker system df

# Limpiar Docker (cuidado: elimina todo lo no usado)
docker system prune -a -f --volumes

# Verificar estado de Redis
docker exec postulamatic-redis-1 redis-cli PING

# Ver logs de Redis
docker logs postulamatic-redis-1 --tail 50

# Verificar lock de scraping
docker exec postulamatic-postulamatic_web-1 python manage.py check_scraping_lock

# Liberar lock forzosamente
docker exec postulamatic-postulamatic_web-1 python manage.py check_scraping_lock --force-release
```

## Estado del Código

- ✅ Commit cc3cb8d: Reforzado logging de liberación de lock en finally
- ✅ El código ahora detecta cuando el lock no se puede liberar
- ✅ Logs detallados para diagnosticar problemas futuros

## Próximos Pasos

1. [ ] Implementar monitoreo automático de disco
2. [ ] Configurar limpieza automática semanal
3. [ ] Agregar límites de logs en docker-compose
4. [ ] Configurar alertas de monitoreo (opcional: Prometheus/Grafana)
5. [ ] Documentar proceso de recuperación ante disco lleno

