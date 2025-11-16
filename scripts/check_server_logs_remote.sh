#!/bin/bash
# Script para verificar logs del servidor remoto

SSH_HOST="${SSH_HOST:-tu-servidor}"
SSH_USER="${SSH_USER:-usuario}"
SSH_KEY="${SSH_KEY:-~/.ssh/id_rsa}"

echo "🔍 Verificando logs del servidor remoto..."
echo ""

ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" << 'EOF'
cd /ruta/a/postulamatic || cd ~/postulamatic || exit 1

echo "📋 Últimos 50 logs de Django:"
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
EOF

echo ""
echo "✅ Verificación completada"

