#!/bin/bash
# Script para probar el scraper stealth en Docker

set -e

echo "🚀 Probando Scraper Stealth en Docker..."
echo ""

# Verificar que los contenedores estén corriendo
if ! docker ps | grep -q postulamatic-worker-1; then
    echo "❌ Error: El contenedor worker no está corriendo"
    echo "   Ejecuta: docker-compose up -d"
    exit 1
fi

echo "✅ Contenedor worker está corriendo"
echo ""

# Verificar que Chrome esté instalado
echo "🔍 Verificando instalación de Chrome..."
CHROME_VERSION=$(docker exec postulamatic-worker-1 google-chrome --version 2>/dev/null || echo "No instalado")
echo "   Chrome: $CHROME_VERSION"
echo ""

if [[ "$CHROME_VERSION" == "No instalado" ]]; then
    echo "❌ Chrome no está instalado en el contenedor"
    echo "   Reconstruye la imagen: docker-compose build worker"
    exit 1
fi

# Pedir ID de usuario
read -p "Ingresa el ID del usuario (default: 2): " USER_ID
USER_ID=${USER_ID:-2}

echo ""
echo "📋 Ejecutando scraper stealth para usuario $USER_ID..."
echo "   (Esto puede tardar 30-60 segundos)"
echo ""

# Ejecutar el comando de prueba
docker exec -it postulamatic-worker-1 python manage.py test_stealth_scraper --user-id=$USER_ID --headless

echo ""
echo "✅ Prueba completada!"
echo ""
echo "📊 Para ver las ofertas scrapeadas:"
echo "   docker exec -it postulamatic-worker-1 python manage.py shell"
echo "   >>> from matching.models import JobPosting"
echo "   >>> JobPosting.objects.filter(source='dvcarreras_stealth').count()"
echo ""
echo "📝 Para ver los logs:"
echo "   docker logs postulamatic-worker-1 --tail 50 | grep DVCarrerasStealth"
echo ""

