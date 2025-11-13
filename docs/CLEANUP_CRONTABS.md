# 🧹 Limpieza de Crontabs No Utilizados

Este documento explica cómo limpiar los crontabs no utilizados en PostulaMatic.

## 📋 Problema

Cuando se cambia la hora del scraping programado múltiples veces, se crean nuevos `CrontabSchedule` pero los anteriores no se eliminan, acumulándose en la base de datos.

## ✅ Solución Implementada

1. **Comando de limpieza**: `cleanup_unused_crontabs` para eliminar crontabs huérfanos
2. **Limpieza automática**: El código ahora elimina automáticamente el crontab anterior cuando se cambia la hora

## 🚀 Ejecutar Limpieza en el Servidor

### Opción 1: Ejecutar directamente en el servidor

```bash
# Conectarse al servidor
ssh deploy@178.156.188.95

# Ir al directorio de la aplicación
cd /home/deploy/apps/postulamatic

# Ver qué se eliminaría (modo dry-run)
docker compose exec postulamatic_web python manage.py cleanup_unused_crontabs --dry-run

# Eliminar realmente los crontabs no utilizados
docker compose exec postulamatic_web python manage.py cleanup_unused_crontabs
```

### Opción 2: Usar el script proporcionado

```bash
# En el servidor
cd /home/deploy/apps/postulamatic
chmod +x scripts/cleanup_crontabs.sh
./scripts/cleanup_crontabs.sh
```

### Opción 3: Desde tu máquina local (si tienes acceso SSH)

```bash
# Ver qué se eliminaría
ssh deploy@178.156.188.95 "cd /home/deploy/apps/postulamatic && docker compose exec postulamatic_web python manage.py cleanup_unused_crontabs --dry-run"

# Eliminar realmente
ssh deploy@178.156.188.95 "cd /home/deploy/apps/postulamatic && docker compose exec postulamatic_web python manage.py cleanup_unused_crontabs"
```

## 📊 Qué hace el comando

1. **Identifica crontabs no utilizados**: Busca todos los `CrontabSchedule` que no tienen `PeriodicTask` asociadas
2. **Muestra estadísticas**: Total de crontabs, cuántos están en uso, cuántos no utilizados
3. **Elimina solo los no utilizados**: Solo elimina crontabs que no tienen tareas asociadas

## 🔄 Prevención Futura

El código ahora:
- Guarda el crontab anterior antes de cambiarlo
- Elimina automáticamente el crontab anterior si no tiene otras tareas asociadas
- Reutiliza crontabs existentes cuando es posible

## ⚠️ Notas Importantes

- El comando es **seguro**: Solo elimina crontabs que no tienen tareas asociadas
- Usa `--dry-run` primero para ver qué se eliminaría
- Los crontabs en uso **nunca** se eliminan
- La limpieza automática solo funciona para cambios futuros

## 📝 Ejemplo de Salida

```
🔍 Buscando crontabs no utilizados...

📊 Estadísticas:
   Total de crontabs: 20
   Crontabs en uso: 3
   Crontabs no utilizados: 17

   ✅ Eliminado: * * * * * (m/h/dM/MY/d) America/Argentina/Buenos_Aires - Every minute
   ✅ Eliminado: */5 * * * * (m/h/dM/MY/d) America/Argentina/Buenos_Aires - Every 5 minutes
   ...

✅ Limpieza completada: 17 de 17 crontabs eliminados
```

