# Cómo Verificar Logs del Servidor para Diagnosticar Error 500

## Método 1: Verificar logs directamente en el servidor

Conéctate al servidor y ejecuta:

```bash
# Ver últimos logs de Django
docker logs postulamatic-postulamatic_web-1 --tail 100

# Buscar errores relacionados con scraper_status_view
docker logs postulamatic-postulamatic_web-1 --tail 500 | grep -i "scraper_status\|6ec19dc5"

# Ver errores 500 recientes
docker logs postulamatic-postulamatic_web-1 --tail 200 | grep -i "500\|internal server error"

# Ver traceback completo de errores
docker logs postulamatic-postulamatic_web-1 --tail 500 | grep -A 20 "Traceback"
```

## Método 2: Usar el script proporcionado

```bash
# En el servidor
bash scripts/check_server_logs.sh
# o
bash scripts/check_django_logs.sh
```

## Método 3: Verificar logs en tiempo real

```bash
# Seguir logs en tiempo real
docker logs -f postulamatic-postulamatic_web-1
```

## Qué buscar

1. **Errores de importación**: `ImportError`, `ModuleNotFoundError`
2. **Errores de atributo**: `AttributeError`, `'NoneType' object has no attribute`
3. **Errores de base de datos**: `OperationalError`, `DatabaseError`
4. **Errores de Celery**: `celery.exceptions`, `AsyncResult`
5. **Traceback completo**: Buscar líneas que empiecen con `Traceback`

## Información útil

- **Task ID problemático**: `6ec19dc5-be36-4efd-a42c-f7c36721bf3c`
- **Endpoint**: `/matching/scraper-status/6ec19dc5-be36-4efd-a42c-f7c36721bf3c/`
- **Función**: `scraper_status_view` en `matching/views.py` línea 1441

