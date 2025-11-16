# Instrucciones para Verificar Logs del Error 500

## Comandos para ejecutar en el servidor

### 1. Ver logs recientes de Django
```bash
docker logs postulamatic-postulamatic_web-1 --tail 100
```

### 2. Buscar errores relacionados con scraper_status_view
```bash
docker logs postulamatic-postulamatic_web-1 --tail 500 | grep -i "scraper_status\|6ec19dc5-be36-4efd-a42c-f7c36721bf3c"
```

### 3. Ver traceback completo de errores
```bash
docker logs postulamatic-postulamatic_web-1 --tail 500 | grep -A 30 "Traceback"
```

### 4. Ver errores 500 específicos
```bash
docker logs postulamatic-postulamatic_web-1 --tail 500 | grep -B 5 -A 20 "500\|Internal Server Error"
```

### 5. Ver logs en tiempo real (útil para debugging)
```bash
docker logs -f postulamatic-postulamatic_web-1
```

## Qué buscar en los logs

1. **Errores de importación**: `ImportError`, `ModuleNotFoundError`
2. **Errores de atributo**: `AttributeError`, `'NoneType' object has no attribute`
3. **Errores de base de datos**: `OperationalError`, `DatabaseError`
4. **Errores de Celery**: `celery.exceptions`, problemas con `AsyncResult`
5. **Traceback completo**: Buscar líneas que empiecen con `Traceback`

## Información útil

- **Task ID problemático**: `6ec19dc5-be36-4efd-a42c-f7c36721bf3c`
- **Endpoint**: `/matching/scraper-status/6ec19dc5-be36-4efd-a42c-f7c36721bf3c/`
- **Función**: `scraper_status_view` en `matching/views.py` línea 1441
- **Último commit**: `b04df1a` - "Format: Corregir orden de imports en matching/views.py"

## Posibles causas del error 500

1. **Código no actualizado en el servidor**: El deployment puede estar en curso
2. **Error de importación**: Algún módulo no se puede importar
3. **Error de base de datos**: Problema con las consultas a la BD
4. **Error de Celery**: Problema con `AsyncResult` o conexión a Celery
5. **Error en decoradores**: Problema con `@login_required` o `@user_passes_test`

## Solución temporal

Si el error persiste, el código debería retornar 200 con información de error en lugar de 500. Si sigue devolviendo 500, significa que el código en el servidor no se ha actualizado todavía.

