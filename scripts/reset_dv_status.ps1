# Script de emergencia para resetear el estado DV

Write-Host "🔧 Reseteando estado DV..." -ForegroundColor Cyan
Write-Host ""

# Obtener user_id
$userId = Read-Host "Ingresa el ID de usuario (por defecto: 2)"
if ([string]::IsNullOrWhiteSpace($userId)) {
    $userId = "2"
}

Write-Host "📝 Reseteando estado para usuario $userId..." -ForegroundColor Yellow

# Reset del estado
$command = @"
from matching.models import UserProfile;
try:
    p = UserProfile.objects.get(user_id=$userId);
    print(f'Estado actual: {p.dv_connection_status}');
    p.dv_connection_status = 'not_verified';
    p.save();
    print('✅ Estado reseteado a: not_verified');
except UserProfile.DoesNotExist:
    print('❌ Error: Usuario no encontrado');
"@

docker exec postulamatic-postulamatic_web-1 python manage.py shell -c $command

Write-Host ""
Write-Host "✅ Proceso completado" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Ahora:" -ForegroundColor Cyan
Write-Host "   1. Refresca la página de perfil (F5)" -ForegroundColor White
Write-Host "   2. El bucle infinito debería haber terminado" -ForegroundColor White
Write-Host "   3. El estado debería mostrar 'NO VERIFICADO'" -ForegroundColor White
Write-Host ""

