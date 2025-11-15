#!/bin/bash
# Script para verificar directamente el estado del lock de scraping en el servidor

SSH_KEY="$HOME/.ssh/jetinnohetzner_ed25519"
SERVER_USER="deploy"
SERVER_HOST="178.156.188.95"
APP_DIR="/home/deploy/apps/postulamatic"

echo "🔍 Verificando estado del lock de scraping directamente..."
echo ""

# Verificar si la clave existe
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ Clave SSH no encontrada: $SSH_KEY"
    exit 1
fi

# Ejecutar verificación directa usando Python inline
ssh -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=10 "$SERVER_USER@$SERVER_HOST" << 'EOF'
cd /home/deploy/apps/postulamatic

echo "📦 Verificando lock en Redis/cache..."
docker compose exec -T postulamatic_web python << 'PYTHON_SCRIPT'
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'postulamatic.settings')
django.setup()

from django.core.cache import cache
from celery.result import AsyncResult

# Claves de cache
SCRAPING_LOCK_KEY = "global_scraping_lock"
SCRAPING_INFO_KEY = "global_scraping_info"

# Verificar lock
task_id = cache.get(SCRAPING_LOCK_KEY)
info = cache.get(SCRAPING_INFO_KEY)

if not task_id:
    print("✅ No hay lock de scraping activo")
    print("   El sistema está libre para iniciar un nuevo scraping")
else:
    print(f"🔒 Lock encontrado: task_id={task_id}")
    if info:
        print(f"   - Usuario: {info.get('user_id')}")
        print(f"   - Origen: {info.get('source')}")
        print(f"   - Iniciado: {info.get('started_at')}")
    
    # Verificar estado de Celery
    print("\n🔍 Verificando estado de la tarea en Celery...")
    try:
        task_result = AsyncResult(task_id)
        celery_state = task_result.state
        print(f"   - Estado Celery: {celery_state}")
        
        # Estados que indican que la tarea ya terminó
        finished_states = ["SUCCESS", "FAILURE", "REVOKED", "REJECTED"]
        
        if celery_state in finished_states:
            print(f"\n⚠️ PROBLEMA DETECTADO:")
            print(f"   La tarea de Celery ya terminó ({celery_state}) pero el lock sigue activo")
            print(f"   Esto es un LOCK HUÉRFANO que debe limpiarse")
            print(f"\n💡 Para limpiar, ejecuta:")
            print(f"   bash scripts/check_scraping_lock_direct.sh --force-release")
        elif celery_state == "PENDING":
            print(f"\n⚠️ La tarea está en estado PENDING")
            print(f"   Puede que nunca se ejecutó o ya expiró")
            print(f"\n💡 Para limpiar, ejecuta:")
            print(f"   bash scripts/check_scraping_lock_direct.sh --force-release")
        else:
            print(f"\n✅ La tarea está activa ({celery_state}), el lock es válido")
    except Exception as e:
        print(f"\n❌ Error al verificar tarea de Celery: {e}")
        print(f"   El lock puede estar huérfano")
        print(f"\n💡 Para limpiar, ejecuta:")
        print(f"   bash scripts/check_scraping_lock_direct.sh --force-release")

PYTHON_SCRIPT

EOF

# Si se pasó --force-release, limpiar el lock
if [ "$1" == "--force-release" ]; then
    echo ""
    echo "🧹 Limpiando lock forzosamente..."
    ssh -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=10 "$SERVER_USER@$SERVER_HOST" << 'EOF'
cd /home/deploy/apps/postulamatic

docker compose exec -T postulamatic_web python << 'PYTHON_SCRIPT'
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'postulamatic.settings')
django.setup()

from django.core.cache import cache

# Claves de cache
SCRAPING_LOCK_KEY = "global_scraping_lock"
SCRAPING_INFO_KEY = "global_scraping_info"

# Liberar lock forzosamente
cache.delete(SCRAPING_LOCK_KEY)
cache.delete(SCRAPING_INFO_KEY)

print("✅ Lock liberado forzosamente")
print("   El sistema ahora está libre para iniciar un nuevo scraping")

PYTHON_SCRIPT

EOF
fi

echo ""
echo "✅ Verificación completada"

