# Script para probar el scraper stealth en Docker (Windows)

Write-Host "🚀 Probando Scraper Stealth en Docker..." -ForegroundColor Green
Write-Host ""

# Verificar que los contenedores estén corriendo
$workerRunning = docker ps | Select-String "postulamatic-worker-1"
if (-not $workerRunning) {
    Write-Host "❌ Error: El contenedor worker no está corriendo" -ForegroundColor Red
    Write-Host "   Ejecuta: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Contenedor worker está corriendo" -ForegroundColor Green
Write-Host ""

# Verificar que Chrome esté instalado
Write-Host "🔍 Verificando instalación de Chrome..." -ForegroundColor Cyan
try {
    $chromeVersion = docker exec postulamatic-worker-1 google-chrome --version 2>&1
    Write-Host "   Chrome: $chromeVersion" -ForegroundColor White
} catch {
    Write-Host "❌ Chrome no está instalado en el contenedor" -ForegroundColor Red
    Write-Host "   Reconstruye la imagen: docker-compose build worker" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Pedir ID de usuario
$userId = Read-Host "Ingresa el ID del usuario (default: 2)"
if ([string]::IsNullOrWhiteSpace($userId)) {
    $userId = "2"
}

Write-Host ""
Write-Host "📋 Ejecutando scraper stealth para usuario $userId..." -ForegroundColor Cyan
Write-Host "   (Esto puede tardar 30-60 segundos)" -ForegroundColor Gray
Write-Host ""

# Ejecutar el comando de prueba
docker exec -it postulamatic-worker-1 python manage.py test_stealth_scraper --user-id=$userId --headless

Write-Host ""
Write-Host "✅ Prueba completada!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Para ver las ofertas scrapeadas:" -ForegroundColor Cyan
Write-Host "   docker exec -it postulamatic-worker-1 python manage.py shell" -ForegroundColor White
Write-Host "   >>> from matching.models import JobPosting" -ForegroundColor White
Write-Host "   >>> JobPosting.objects.filter(source='dvcarreras_stealth').count()" -ForegroundColor White
Write-Host ""
Write-Host "📝 Para ver los logs:" -ForegroundColor Cyan
Write-Host "   docker logs postulamatic-worker-1 --tail 50 | Select-String DVCarrerasStealth" -ForegroundColor White
Write-Host ""

