#!/bin/bash
# Script para verificar logs del servidor y diagnosticar errores 500

echo "🔍 Verificando logs del servidor para diagnosticar error 500..."
echo ""

# Verificar logs de Django del contenedor
echo "📋 Últimos 50 logs de Django (postulamatic_web):"
echo "=========================================="
docker logs postulamatic-postulamatic_web-1 --tail 50 2>&1 | grep -i "error\|exception\|traceback\|scraper_status" || echo "No se encontraron errores recientes"

echo ""
echo "📋 Logs relacionados con scraper_status_view:"
echo "=========================================="
docker logs postulamatic-postulamatic_web-1 --tail 100 2>&1 | grep -i "scraper_status\|task_id.*6ec19dc5" || echo "No se encontraron logs relacionados"

echo ""
echo "📋 Errores 500 recientes:"
echo "=========================================="
docker logs postulamatic-postulamatic_web-1 --tail 200 2>&1 | grep -i "500\|internal server error" || echo "No se encontraron errores 500 explícitos"

echo ""
echo "📋 Estado del contenedor:"
echo "=========================================="
docker ps | grep postulamatic_web || echo "Contenedor no encontrado"

echo ""
echo "✅ Verificación completada"

