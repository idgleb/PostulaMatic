#!/bin/bash
# Script para diagnosticar y solucionar error 502 Bad Gateway

SSH_KEY="${HOME}/.ssh/postulamatic_win_ed25519"
SERVER="deploy@178.156.188.95"

echo "🔍 Diagnosticando error 502 Bad Gateway..."
echo ""

ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
cd /home/deploy/apps/postulamatic

echo "📊 Estado de contenedores Docker:"
echo "=================================="
docker compose ps
echo ""

echo "🌐 Verificando que Django responda:"
echo "==================================="
if curl -f -s http://localhost:8000 > /dev/null 2>&1; then
    echo "✅ Django responde en localhost:8000"
    curl -I http://localhost:8000 2>&1 | head -5
else
    echo "❌ Django NO responde en localhost:8000"
    echo ""
    echo "📋 Logs de Django:"
    docker compose logs postulamatic_web --tail=30
fi
echo ""

echo "🔍 Verificando Nginx:"
echo "===================="
if docker ps | grep -q nginx-proxy; then
    echo "✅ Nginx está corriendo"
    docker exec nginx-proxy curl -I http://postulamatic_web:8000 2>&1 | head -5 || echo "❌ Nginx no puede conectarse a Django"
else
    echo "❌ Nginx NO está corriendo"
    echo "Iniciando Nginx..."
    docker start nginx-proxy 2>/dev/null || echo "⚠️ No se pudo iniciar Nginx"
fi
echo ""

echo "🔗 Verificando red Docker:"
echo "=========================="
docker network inspect web 2>/dev/null | grep -A 5 "postulamatic" || echo "⚠️ Verificar red 'web'"
echo ""

echo "📋 Logs de Nginx:"
echo "================="
docker logs nginx-proxy --tail=20 2>&1 | grep -i error || echo "✅ No hay errores recientes en Nginx"
echo ""

echo "🔧 Solución rápida:"
echo "=================="
echo "1. Reiniciar contenedores Django:"
echo "   cd /home/deploy/apps/postulamatic"
echo "   docker compose restart postulamatic_web"
echo ""
echo "2. Verificar logs:"
echo "   docker compose logs postulamatic_web --tail=50"
echo ""
echo "3. Reiniciar Nginx:"
echo "   docker restart nginx-proxy"

EOF

echo ""
echo "✅ Diagnóstico completado"

