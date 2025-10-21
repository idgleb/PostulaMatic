# Script para verificar el estado del scraper stealth en Docker (Windows)

Write-Host "🔍 Verificando estado del Scraper Stealth..." -ForegroundColor Cyan
Write-Host ""

# 1. Verificar contenedores
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "1️⃣  VERIFICANDO CONTENEDORES" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$workerRunning = docker ps | Select-String "postulamatic-worker-1"
if ($workerRunning) {
    Write-Host "✅ Worker: Corriendo" -ForegroundColor Green
} else {
    Write-Host "❌ Worker: No está corriendo" -ForegroundColor Red
    Write-Host "   Ejecuta: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}

$webRunning = docker ps | Select-String "postulamatic-postulamatic_web-1"
if ($webRunning) {
    Write-Host "✅ Web: Corriendo" -ForegroundColor Green
} else {
    Write-Host "⚠️  Web: No está corriendo" -ForegroundColor Yellow
}

$redisRunning = docker ps | Select-String "postulamatic-redis-1"
if ($redisRunning) {
    Write-Host "✅ Redis: Corriendo" -ForegroundColor Green
} else {
    Write-Host "❌ Redis: No está corriendo" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 2. Verificar Chrome
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "2️⃣  VERIFICANDO CHROME" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

try {
    $chromeVersion = docker exec postulamatic-worker-1 google-chrome --version 2>&1
    if ($chromeVersion -match "Google Chrome") {
        Write-Host "✅ Chrome instalado: $chromeVersion" -ForegroundColor Green
    } else {
        throw "Chrome no encontrado"
    }
} catch {
    Write-Host "❌ Chrome no instalado" -ForegroundColor Red
    Write-Host "   Reconstruye: docker-compose build worker" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# 3. Verificar dependencias Python
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "3️⃣  VERIFICANDO DEPENDENCIAS PYTHON" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

try {
    $ucVersion = docker exec postulamatic-worker-1 python -c "import undetected_chromedriver; print(undetected_chromedriver.__version__)" 2>&1
    if ($ucVersion -match "^\d+\.\d+") {
        Write-Host "✅ undetected-chromedriver: $ucVersion" -ForegroundColor Green
    } else {
        throw "No instalado"
    }
} catch {
    Write-Host "❌ undetected-chromedriver no instalado" -ForegroundColor Red
    Write-Host "   Ejecuta: docker exec postulamatic-worker-1 pip install undetected-chromedriver" -ForegroundColor Yellow
    exit 1
}

try {
    $seleniumVersion = docker exec postulamatic-worker-1 python -c "import selenium; print(selenium.__version__)" 2>&1
    if ($seleniumVersion -match "^\d+\.\d+") {
        Write-Host "✅ selenium: $seleniumVersion" -ForegroundColor Green
    } else {
        throw "No instalado"
    }
} catch {
    Write-Host "❌ selenium no instalado" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 4. Verificar archivos del scraper
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "4️⃣  VERIFICANDO ARCHIVOS DEL SCRAPER" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$clientExists = docker exec postulamatic-worker-1 test -f matching/clients/dvcarreras_stealth.py 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Cliente stealth: Presente" -ForegroundColor Green
} else {
    Write-Host "❌ Cliente stealth: No encontrado" -ForegroundColor Red
    exit 1
}

$tasksExist = docker exec postulamatic-worker-1 test -f matching/tasks_stealth.py 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Tareas Celery: Presentes" -ForegroundColor Green
} else {
    Write-Host "❌ Tareas Celery: No encontradas" -ForegroundColor Red
    exit 1
}

$commandExists = docker exec postulamatic-worker-1 test -f matching/management/commands/test_stealth_scraper.py 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Comando de prueba: Presente" -ForegroundColor Green
} else {
    Write-Host "⚠️  Comando de prueba: No encontrado (opcional)" -ForegroundColor Yellow
}

Write-Host ""

# 5. Verificar base de datos
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "5️⃣  VERIFICANDO BASE DE DATOS" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

try {
    $jobsCount = docker exec postulamatic-worker-1 python manage.py shell -c "from matching.models import JobPosting; print(JobPosting.objects.filter(source='dvcarreras_stealth').count())" 2>&1
    if ($jobsCount -match "^\d+$") {
        if ([int]$jobsCount -gt 0) {
            Write-Host "✅ Ofertas scrapeadas: $jobsCount encontradas" -ForegroundColor Green
            
            # Obtener fecha de última oferta
            $lastJob = docker exec postulamatic-worker-1 python manage.py shell -c "from matching.models import JobPosting; from django.utils import timezone; j = JobPosting.objects.filter(source='dvcarreras_stealth').order_by('-created_at').first(); print(j.created_at.strftime('%Y-%m-%d %H:%M:%S') if j else 'N/A')" 2>&1
            Write-Host "   Última oferta: $lastJob" -ForegroundColor White
        } else {
            Write-Host "ℹ️  Ofertas scrapeadas: Ninguna (ejecuta el scraper)" -ForegroundColor Cyan
        }
    } else {
        Write-Host "⚠️  No se pudo verificar la base de datos" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Error verificando base de datos" -ForegroundColor Yellow
}

# Verificar logs de scraping
try {
    $logsCount = docker exec postulamatic-worker-1 python manage.py shell -c "from matching.models import ScrapingLog; print(ScrapingLog.objects.filter(task_id='stealth_scraper').count())" 2>&1
    if ($logsCount -match "^\d+$") {
        if ([int]$logsCount -gt 0) {
            Write-Host "✅ Logs de scraping: $logsCount registros" -ForegroundColor Green
        } else {
            Write-Host "ℹ️  Logs de scraping: Ninguno (el scraper no se ha ejecutado)" -ForegroundColor Cyan
        }
    }
} catch {
    Write-Host "⚠️  Error verificando logs" -ForegroundColor Yellow
}

Write-Host ""

# Resumen final
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "📊 RESUMEN" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ Sistema listo para ejecutar el scraper stealth" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 Para probar el scraper:" -ForegroundColor Cyan
Write-Host "   .\scripts\test_stealth_docker.ps1" -ForegroundColor White
Write-Host ""
Write-Host "📋 Para ejecutar manualmente:" -ForegroundColor Cyan
Write-Host "   docker exec -it postulamatic-worker-1 python manage.py test_stealth_scraper --user-id=2 --headless" -ForegroundColor White
Write-Host ""
Write-Host "📊 Para ver logs en tiempo real:" -ForegroundColor Cyan
Write-Host "   docker logs postulamatic-worker-1 -f | Select-String DVCarrerasStealth" -ForegroundColor White
Write-Host ""

