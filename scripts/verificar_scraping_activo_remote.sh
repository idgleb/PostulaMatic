#!/bin/bash
# Script para verificar si hay realmente un scraping en curso en el servidor remoto

SSH_HOST="${SSH_HOST:-tu-servidor}"
SSH_USER="${SSH_USER:-usuario}"
SSH_KEY="${SSH_KEY:-~/.ssh/id_rsa}"

echo "🔍 Verificando estado del scraping en el servidor remoto..."
echo ""

ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" << 'EOF'
cd /ruta/a/postulamatic || cd ~/postulamatic || exit 1

echo "📋 1. Verificando lock en Redis/Cache:"
echo "=========================================="
docker exec postulamatic-postulamatic_web-1 python manage.py shell << 'PYTHON_EOF'
from django.core.cache import cache
from celery.result import AsyncResult
from matching.services.scraping_lock import scraping_lock

# Verificar lock
lock_task_id = scraping_lock.get_lock_task_id()
if lock_task_id:
    print(f"✅ Lock encontrado: task_id={lock_task_id}")
    
    # Verificar estado de la tarea
    try:
        task_result = AsyncResult(lock_task_id)
        task_status = task_result.status
        is_ready = task_result.ready()
        
        print(f"📊 Estado de la tarea: {task_status}")
        print(f"📊 ¿Tarea lista?: {is_ready}")
        
        if is_ready:
            if task_result.successful():
                print("✅ Tarea completada exitosamente")
            elif task_result.failed():
                print(f"❌ Tarea falló: {task_result.result}")
            else:
                print(f"⚠️ Tarea en estado desconocido: {task_status}")
        else:
            print("🔄 Tarea aún en ejecución")
            
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
                        print(f"✅ Tarea encontrada en worker: {worker}")
                        break
                if task_in_workers:
                    break
        
        if not task_in_workers and not is_ready:
            print("⚠️ ADVERTENCIA: Tarea no está en workers activos pero tampoco está lista")
            print("   Esto podría indicar un lock huérfano")
    except Exception as e:
        print(f"❌ Error verificando tarea: {e}")
else:
    print("ℹ️ No hay lock activo")
PYTHON_EOF

echo ""
echo "📋 2. Verificando tareas activas de Celery:"
echo "=========================================="
docker exec postulamatic-postulamatic_web-1 python manage.py shell << 'PYTHON_EOF'
from celery import current_app

inspect = current_app.control.inspect()
active_tasks = inspect.active()

if active_tasks:
    print("✅ Tareas activas encontradas:")
    for worker, tasks in active_tasks.items():
        print(f"\n📦 Worker: {worker}")
        for task in tasks:
            print(f"  - Task ID: {task.get('id')}")
            print(f"    Name: {task.get('name')}")
            print(f"    Args: {task.get('args')}")
            print(f"    State: {task.get('state', 'N/A')}")
else:
    print("ℹ️ No hay tareas activas en Celery")
PYTHON_EOF

echo ""
echo "📋 3. Verificando información del lock:"
echo "=========================================="
docker exec postulamatic-postulamatic_web-1 python manage.py shell << 'PYTHON_EOF'
from matching.services.scraping_lock import scraping_lock

active_info = scraping_lock.get_active_scraping()
if active_info:
    print("✅ Información del scraping activo:")
    print(f"  - Task ID: {active_info.get('task_id')}")
    print(f"  - User ID: {active_info.get('user_id')}")
    print(f"  - Started at: {active_info.get('started_at')}")
    print(f"  - Is locked: {scraping_lock.is_locked()}")
else:
    print("ℹ️ No hay información de scraping activo")
    print(f"  - Is locked: {scraping_lock.is_locked()}")
PYTHON_EOF
EOF

echo ""
echo "✅ Verificación completada"

