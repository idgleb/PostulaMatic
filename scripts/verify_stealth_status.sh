#!/bin/bash
# Script para verificar el estado del scraper stealth en Docker

echo "🔍 Verificando estado del Scraper Stealth..."
echo ""

# 1. Verificar contenedores
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  VERIFICANDO CONTENEDORES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker ps | grep -q "postulamatic-worker-1"; then
    echo "✅ Worker: Corriendo"
else
    echo "❌ Worker: No está corriendo"
    echo "   Ejecuta: docker-compose up -d"
    exit 1
fi

if docker ps | grep -q "postulamatic-postulamatic_web-1"; then
    echo "✅ Web: Corriendo"
else
    echo "⚠️  Web: No está corriendo"
fi

if docker ps | grep -q "postulamatic-redis-1"; then
    echo "✅ Redis: Corriendo"
else
    echo "❌ Redis: No está corriendo"
    exit 1
fi

echo ""

# 2. Verificar Chrome
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  VERIFICANDO CHROME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CHROME_VERSION=$(docker exec postulamatic-worker-1 google-chrome --version 2>/dev/null || echo "No instalado")
if [[ "$CHROME_VERSION" != "No instalado" ]]; then
    echo "✅ Chrome instalado: $CHROME_VERSION"
else
    echo "❌ Chrome no instalado"
    echo "   Reconstruye: docker-compose build worker"
    exit 1
fi

# Verificar ChromeDriver
CHROMEDRIVER_VERSION=$(docker exec postulamatic-worker-1 chromedriver --version 2>/dev/null || echo "N/A")
if [[ "$CHROMEDRIVER_VERSION" != "N/A" ]]; then
    echo "✅ ChromeDriver: $CHROMEDRIVER_VERSION"
else
    echo "ℹ️  ChromeDriver: Se instalará automáticamente"
fi

echo ""

# 3. Verificar dependencias Python
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  VERIFICANDO DEPENDENCIAS PYTHON"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Verificar undetected-chromedriver
UC_VERSION=$(docker exec postulamatic-worker-1 python -c "import undetected_chromedriver; print(undetected_chromedriver.__version__)" 2>/dev/null || echo "No instalado")
if [[ "$UC_VERSION" != "No instalado" ]]; then
    echo "✅ undetected-chromedriver: $UC_VERSION"
else
    echo "❌ undetected-chromedriver no instalado"
    echo "   Ejecuta: docker exec postulamatic-worker-1 pip install undetected-chromedriver"
    exit 1
fi

# Verificar selenium
SELENIUM_VERSION=$(docker exec postulamatic-worker-1 python -c "import selenium; print(selenium.__version__)" 2>/dev/null || echo "No instalado")
if [[ "$SELENIUM_VERSION" != "No instalado" ]]; then
    echo "✅ selenium: $SELENIUM_VERSION"
else
    echo "❌ selenium no instalado"
    exit 1
fi

echo ""

# 4. Verificar archivos del scraper
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  VERIFICANDO ARCHIVOS DEL SCRAPER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker exec postulamatic-worker-1 test -f matching/clients/dvcarreras_stealth.py; then
    echo "✅ Cliente stealth: Presente"
else
    echo "❌ Cliente stealth: No encontrado"
    exit 1
fi

if docker exec postulamatic-worker-1 test -f matching/tasks_stealth.py; then
    echo "✅ Tareas Celery: Presentes"
else
    echo "❌ Tareas Celery: No encontradas"
    exit 1
fi

if docker exec postulamatic-worker-1 test -f matching/management/commands/test_stealth_scraper.py; then
    echo "✅ Comando de prueba: Presente"
else
    echo "⚠️  Comando de prueba: No encontrado (opcional)"
fi

echo ""

# 5. Verificar directorios
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  VERIFICANDO DIRECTORIOS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker exec postulamatic-worker-1 test -d media/sessions; then
    SESSION_COUNT=$(docker exec postulamatic-worker-1 ls -1 media/sessions/*.json 2>/dev/null | wc -l || echo "0")
    echo "✅ Directorio de sesiones: Presente ($SESSION_COUNT sesiones)"
else
    echo "⚠️  Directorio de sesiones: No existe (se creará automáticamente)"
fi

if docker exec postulamatic-worker-1 test -d media/debug/scraper_html; then
    DEBUG_COUNT=$(docker exec postulamatic-worker-1 ls -1 media/debug/scraper_html/*.html 2>/dev/null | wc -l || echo "0")
    echo "✅ Directorio de debug: Presente ($DEBUG_COUNT archivos)"
else
    echo "⚠️  Directorio de debug: No existe (se creará automáticamente)"
fi

echo ""

# 6. Verificar base de datos
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣  VERIFICANDO BASE DE DATOS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Verificar ofertas scrapeadas
JOBS_COUNT=$(docker exec postulamatic-worker-1 python manage.py shell -c "from matching.models import JobPosting; print(JobPosting.objects.filter(source='dvcarreras_stealth').count())" 2>/dev/null || echo "Error")
if [[ "$JOBS_COUNT" =~ ^[0-9]+$ ]]; then
    if [ "$JOBS_COUNT" -gt 0 ]; then
        echo "✅ Ofertas scrapeadas: $JOBS_COUNT encontradas"
        
        # Obtener fecha de última oferta
        LAST_JOB=$(docker exec postulamatic-worker-1 python manage.py shell -c "from matching.models import JobPosting; from django.utils import timezone; j = JobPosting.objects.filter(source='dvcarreras_stealth').order_by('-created_at').first(); print(j.created_at.strftime('%Y-%m-%d %H:%M:%S') if j else 'N/A')" 2>/dev/null || echo "N/A")
        echo "   Última oferta: $LAST_JOB"
    else
        echo "ℹ️  Ofertas scrapeadas: Ninguna (ejecuta el scraper)"
    fi
else
    echo "⚠️  No se pudo verificar la base de datos"
fi

# Verificar logs de scraping
LOGS_COUNT=$(docker exec postulamatic-worker-1 python manage.py shell -c "from matching.models import ScrapingLog; print(ScrapingLog.objects.filter(task_id='stealth_scraper').count())" 2>/dev/null || echo "Error")
if [[ "$LOGS_COUNT" =~ ^[0-9]+$ ]]; then
    if [ "$LOGS_COUNT" -gt 0 ]; then
        echo "✅ Logs de scraping: $LOGS_COUNT registros"
        
        # Obtener último log
        LAST_LOG=$(docker exec postulamatic-worker-1 python manage.py shell -c "from matching.models import ScrapingLog; l = ScrapingLog.objects.filter(task_id='stealth_scraper').order_by('-timestamp').first(); print(f'{l.log_type}: {l.message[:50]}...' if l else 'N/A')" 2>/dev/null || echo "N/A")
        echo "   Último log: $LAST_LOG"
    else
        echo "ℹ️  Logs de scraping: Ninguno (el scraper no se ha ejecutado)"
    fi
fi

echo ""

# 7. Verificar tareas Celery
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7️⃣  VERIFICANDO TAREAS CELERY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Verificar que Celery esté corriendo
CELERY_WORKERS=$(docker exec postulamatic-worker-1 celery -A postulamatic inspect active 2>/dev/null | grep -c "active" || echo "0")
if [ "$CELERY_WORKERS" -gt 0 ]; then
    echo "✅ Celery: Activo"
else
    echo "⚠️  Celery: No se pudo verificar (puede estar corriendo)"
fi

# Verificar tareas registradas
TASK_REGISTERED=$(docker exec postulamatic-worker-1 celery -A postulamatic inspect registered 2>/dev/null | grep -c "scrape_dvcarreras_jobs_stealth" || echo "0")
if [ "$TASK_REGISTERED" -gt 0 ]; then
    echo "✅ Tarea registrada: scrape_dvcarreras_jobs_stealth"
else
    echo "⚠️  Tarea no registrada o Celery no responde"
fi

echo ""

# Resumen final
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RESUMEN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Sistema listo para ejecutar el scraper stealth"
echo ""
echo "🚀 Para probar el scraper:"
echo "   bash scripts/test_stealth_docker.sh"
echo ""
echo "📋 Para ejecutar manualmente:"
echo "   docker exec -it postulamatic-worker-1 python manage.py test_stealth_scraper --user-id=2 --headless"
echo ""
echo "📊 Para ver logs en tiempo real:"
echo "   docker logs postulamatic-worker-1 -f | grep DVCarrerasStealth"
echo ""

