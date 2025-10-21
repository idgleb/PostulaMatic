#!/bin/bash
# Script de emergencia para resetear el estado DV

echo "🔧 Reseteando estado DV..."
echo ""

# Obtener user_id
read -p "Ingresa el ID de usuario (por defecto: 2): " user_id
user_id=${user_id:-2}

echo "📝 Reseteando estado para usuario $user_id..."

# Reset del estado
docker exec postulamatic-postulamatic_web-1 python manage.py shell -c "
from matching.models import UserProfile
try:
    p = UserProfile.objects.get(user_id=$user_id)
    print(f'Estado actual: {p.dv_connection_status}')
    p.dv_connection_status = 'not_verified'
    p.save()
    print('✅ Estado reseteado a: not_verified')
except UserProfile.DoesNotExist:
    print('❌ Error: Usuario no encontrado')
"

echo ""
echo "✅ Proceso completado"
echo ""
echo "📋 Ahora:"
echo "   1. Refresca la página de perfil (F5)"
echo "   2. El bucle infinito debería haber terminado"
echo "   3. El estado debería mostrar 'NO VERIFICADO'"
echo ""

