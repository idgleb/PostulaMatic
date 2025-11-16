#!/bin/bash
# Script para verificar logs específicos de Django relacionados con scraper_status_view

echo "🔍 Verificando logs de Django para scraper_status_view..."
echo ""

# Verificar si el contenedor está corriendo
if ! docker ps | grep -q postulamatic-postulamatic_web-1; then
    echo "❌ El contenedor postulamatic_web no está corriendo"
    exit 1
fi

# Buscar errores relacionados con scraper_status_view
echo "📋 Buscando errores en scraper_status_view:"
echo "=========================================="
docker logs postulamatic-postulamatic_web-1 --tail 500 2>&1 | \
    grep -A 10 -B 5 "scraper_status_view\|6ec19dc5-be36-4efd-a42c-f7c36721bf3c" | \
    tail -50

echo ""
echo "📋 Últimos errores de Python/Django:"
echo "=========================================="
docker logs postulamatic-postulamatic_web-1 --tail 200 2>&1 | \
    grep -i "error\|exception\|traceback" | \
    tail -20

echo ""
echo "📋 Verificando si hay problemas de importación:"
echo "=========================================="
docker logs postulamatic-postulamatic_web-1 --tail 100 2>&1 | \
    grep -i "import\|module\|cannot import" | \
    tail -10

