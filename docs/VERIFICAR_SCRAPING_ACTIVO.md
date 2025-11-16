# Cómo Verificar si Hay Scraping Realmente en Curso

## Método 1: Usar el comando de Django (Recomendado)

El método más simple es usar el comando de gestión de Django:

```bash
# En el servidor, dentro del contenedor
docker exec postulamatic-postulamatic_web-1 python manage.py check_active_scraping
```

Este comando verificará:
- ✅ Si hay un lock activo en Redis/Cache
- ✅ El estado real de la tarea de Celery
- ✅ Si la tarea está en workers activos
- ✅ Si el lock está huérfano (tarea terminada pero lock no liberado)

## Método 2: Usar el script bash

```bash
# En el servidor
bash scripts/verificar_scraping_activo.sh
```

## Método 3: Verificar manualmente con Python

```bash
docker exec postulamatic-postulamatic_web-1 python manage.py shell
```

Luego ejecuta:

```python
from django.core.cache import cache
from celery.result import AsyncResult
from matching.services.scraping_lock import scraping_lock

# Verificar lock
lock_task_id = scraping_lock.get_lock_task_id()
print(f"Lock task ID: {lock_task_id}")

if lock_task_id:
    # Verificar estado de la tarea
    task_result = AsyncResult(lock_task_id)
    print(f"Estado: {task_result.status}")
    print(f"¿Lista?: {task_result.ready()}")
    
    if task_result.ready():
        if task_result.successful():
            print("✅ Tarea completada")
        elif task_result.failed():
            print(f"❌ Tarea falló: {task_result.result}")
    
    # Verificar si está en workers activos
    from celery import current_app
    inspect = current_app.control.inspect()
    active_tasks = inspect.active()
    
    task_in_workers = False
    if active_tasks:
        for worker, tasks in active_tasks.items():
            for task in tasks:
                if task.get("id") == lock_task_id:
                    task_in_workers = True
                    print(f"✅ En worker: {worker}")
                    break
            if task_in_workers:
                break
    
    if not task_in_workers and not task_result.ready():
        print("⚠️ ADVERTENCIA: Lock huérfano detectado")
```

## Interpretación de Resultados

### Caso 1: Scraping Realmente en Curso
```
✅ Lock encontrado: task_id=6ec19dc5-be36-4efd-a42c-f7c36721bf3c
📊 Estado de la tarea: STARTED
📊 ¿Tarea lista?: False
🔄 Tarea aún en ejecución
✅ Tarea encontrada en worker: celery@worker1
```
**Acción**: Esperar a que termine o cancelar si es necesario.

### Caso 2: Lock Huérfano (Tarea Terminada pero Lock No Liberado)
```
✅ Lock encontrado: task_id=6ec19dc5-be36-4efd-a42c-f7c36721bf3c
📊 Estado de la tarea: SUCCESS
📊 ¿Tarea lista?: True
✅ Tarea completada exitosamente
⚠️ ADVERTENCIA: Tarea no está en workers activos pero tampoco está lista
   Esto podría indicar un lock huérfano
```
**Acción**: Liberar el lock manualmente usando:
```bash
docker exec postulamatic-postulamatic_web-1 python manage.py check_scraping_lock --force-release
```

### Caso 3: No Hay Scraping en Curso
```
ℹ️ No hay lock activo
ℹ️ No hay tareas activas en Celery
ℹ️ No hay información de scraping activo
  - Is locked: False
```
**Acción**: Puedes iniciar un nuevo scraping.

## Limpiar Lock Huérfano

Si detectas un lock huérfano, puedes liberarlo con:

```bash
# Opción 1: Usar el comando de gestión
docker exec postulamatic-postulamatic_web-1 python manage.py check_scraping_lock --force-release

# Opción 2: Usar Python shell
docker exec postulamatic-postulamatic_web-1 python manage.py shell
```

Luego:
```python
from matching.services.scraping_lock import scraping_lock
scraping_lock.force_release_lock()
print("✅ Lock liberado")
```

## Verificar Tareas Activas de Celery

Para ver todas las tareas activas en Celery:

```bash
docker exec postulamatic-postulamatic_web-1 python manage.py shell
```

```python
from celery import current_app
inspect = current_app.control.inspect()
active_tasks = inspect.active()

if active_tasks:
    for worker, tasks in active_tasks.items():
        print(f"Worker: {worker}")
        for task in tasks:
            print(f"  - Task ID: {task.get('id')}")
            print(f"    Name: {task.get('name')}")
            print(f"    State: {task.get('state', 'N/A')}")
```

## Troubleshooting

### El frontend muestra "Scraping en curso" pero no hay tarea activa

1. Verifica el lock: `python manage.py check_active_scraping`
2. Si el lock está huérfano, libéralo: `python manage.py check_scraping_lock --force-release`
3. Recarga la página del frontend

### El scraping terminó pero el lock no se liberó

Esto debería limpiarse automáticamente, pero si persiste:
1. Verifica el estado: `python manage.py check_active_scraping`
2. Si la tarea está en estado `SUCCESS` o `FAILURE`, libéralo manualmente
3. El sistema debería limpiar locks huérfanos automáticamente en el próximo intento

