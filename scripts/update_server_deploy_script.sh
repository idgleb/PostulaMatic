#!/bin/bash
# Script para actualizar el script de deployment en el servidor
# Elimina el paso de migrate --check que causa timeout

set -e

SSH_KEY="${HOME}/.ssh/postulamatic_win_ed25519"
SERVER="deploy@178.156.188.95"
APP_DIR="/home/deploy/apps/postulamatic"

echo "🚀 Actualizando script de deployment en el servidor..."
echo ""

# Verificar que existe la clave SSH
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ Error: No se encuentra la clave SSH en $SSH_KEY"
    exit 1
fi

# Copiar el script mejorado al servidor
echo "📤 Copiando script mejorado al servidor..."
scp -i "$SSH_KEY" scripts/server_deploy.sh "$SERVER:$APP_DIR/server_deploy.sh"

# Hacer el script ejecutable y crear backup del actual
echo "🔧 Configurando script en el servidor..."
ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
cd /home/deploy/apps/postulamatic

# Hacer el script ejecutable
chmod +x server_deploy.sh

# Buscar scripts de deployment existentes y hacer backup
echo "🔍 Buscando scripts de deployment existentes..."

# Si existe deploy.sh, hacer backup
if [ -f "deploy.sh" ]; then
    echo "📦 Haciendo backup de deploy.sh existente..."
    cp deploy.sh deploy.sh.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Backup creado"
fi

# Buscar otros scripts que puedan tener migrate --check
for script in *.sh; do
    if [ -f "$script" ] && grep -q "migrate --check" "$script" 2>/dev/null; then
        echo "⚠️ Encontrado script con migrate --check: $script"
        echo "📦 Haciendo backup..."
        cp "$script" "${script}.backup.$(date +%Y%m%d_%H%M%S)"
    fi
done

echo "✅ Scripts configurados correctamente"
EOF

echo ""
echo "✅ Script actualizado en el servidor"
echo ""
echo "📋 Próximos pasos:"
echo "1. Conectarse al servidor: ssh -i $SSH_KEY $SERVER"
echo "2. Ir al directorio: cd $APP_DIR"
echo "3. Probar el script: ./server_deploy.sh"
echo ""
echo "💡 Si el script funciona correctamente, puedes reemplazar el script actual:"
echo "   mv server_deploy.sh deploy.sh"
echo ""

