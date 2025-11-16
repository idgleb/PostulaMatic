#!/bin/bash
# Script para verificar scraping activo en el servidor remoto

SSH_KEY="${1:-~/.ssh/postulamatic_win_ed25519}"
SSH_USER="${2:-deploy}"
SSH_HOST="${3:-178.156.188.95}"

echo "🔍 Conectando al servidor para verificar scraping activo..."
echo "📡 Servidor: ${SSH_USER}@${SSH_HOST}"
echo ""

ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" << 'EOF'
cd /home/deploy/postulamatic || cd ~/postulamatic || exit 1

echo "📋 Verificando estado del scraping..."
echo ""

# Verificar lock y estado de la tarea
docker exec postulamatic-postulamatic_web-1 python manage.py check_active_scraping

echo ""
echo "📋 Si hay un lock huérfano, puedes liberarlo con:"
echo "docker exec postulamatic-postulamatic_web-1 python manage.py check_scraping_lock --force-release"
EOF

echo ""
echo "✅ Verificación completada"

