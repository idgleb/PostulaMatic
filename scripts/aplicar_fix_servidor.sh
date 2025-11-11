#!/bin/bash
# Script para aplicar el fix de timeout en el servidor
# Este script se ejecuta desde tu máquina local

SSH_KEY="${HOME}/.ssh/postulamatic_win_ed25519"
SERVER="deploy@178.156.188.95"
APP_DIR="/home/deploy/apps/postulamatic"

echo "🚀 Aplicando fix de timeout en el servidor..."
echo ""

# Verificar que existe la clave SSH
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ Error: No se encuentra la clave SSH en $SSH_KEY"
    echo "💡 Usa una de estas claves:"
    echo "   - ~/.ssh/jetinnohetzner_ed25519"
    echo "   - ~/.ssh/postulamatic_win_ed25519"
    exit 1
fi

# Copiar el script de fix al servidor
echo "📤 Copiando script de fix al servidor..."
scp -i "$SSH_KEY" scripts/fix_migrate_check.sh "$SERVER:$APP_DIR/fix_migrate_check.sh"

# Ejecutar el script en el servidor
echo "🔧 Ejecutando fix en el servidor..."
ssh -i "$SSH_KEY" "$SERVER" << 'ENDSSH'
cd /home/deploy/apps/postulamatic

# Hacer el script ejecutable
chmod +x fix_migrate_check.sh

# Ejecutar el script
./fix_migrate_check.sh

# Verificar el resultado
echo ""
echo "📋 Verificando que el fix se aplicó..."
if grep -r "migrate --check" . --include="*.sh" 2>/dev/null | grep -v "fix_migrate_check.sh" | grep -v ".backup."; then
    echo "⚠️ Aún hay archivos con 'migrate --check'"
    echo "📝 Archivos que necesitan edición manual:"
    grep -r "migrate --check" . --include="*.sh" 2>/dev/null | grep -v "fix_migrate_check.sh" | grep -v ".backup." | cut -d: -f1 | sort -u
else
    echo "✅ No se encontraron más instancias de 'migrate --check' en scripts .sh"
fi

ENDSSH

echo ""
echo "✅ Fix aplicado en el servidor"
echo ""
echo "📋 Próximos pasos:"
echo "1. Verificar que el deployment funciona:"
echo "   ssh -i $SSH_KEY $SERVER 'cd $APP_DIR && ./server_deploy.sh'"
echo ""
echo "2. O probar el próximo deployment automático"
echo ""

