#!/bin/bash
# Script para buscar y corregir migrate --check en el servidor
# Este script se conecta al servidor y busca/modifica el script problemático

SSH_KEY="${HOME}/.ssh/postulamatic_win_ed25519"
SERVER="deploy@178.156.188.95"
APP_DIR="/home/deploy/apps/postulamatic"

echo "🔍 Buscando scripts con 'migrate --check' en el servidor..."
echo ""

# Buscar en el servidor
ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
cd /home/deploy/apps/postulamatic

echo "📋 Buscando 'migrate --check' en todos los archivos..."
echo ""

# Buscar en archivos .sh
SH_FILES=$(find . -name "*.sh" -type f 2>/dev/null | head -20)
if [ -n "$SH_FILES" ]; then
    echo "📝 Archivos .sh encontrados:"
    echo "$SH_FILES" | while read file; do
        if grep -q "migrate --check" "$file" 2>/dev/null; then
            echo "   ⚠️ $file (contiene 'migrate --check')"
        fi
    done
    echo ""
fi

# Buscar en todos los archivos
ALL_MATCHES=$(grep -r "migrate --check" . 2>/dev/null | grep -v ".git" | head -10)
if [ -n "$ALL_MATCHES" ]; then
    echo "🔴 Archivos con 'migrate --check':"
    echo "$ALL_MATCHES"
    echo ""
else
    echo "✅ No se encontró 'migrate --check' en archivos locales"
    echo ""
    echo "💡 El script puede estar en:"
    echo "   1. GitHub Actions (workflow .yml en el repositorio)"
    echo "   2. Un script que se ejecuta desde otro lugar"
    echo "   3. Un hook de git (pre-push, post-receive, etc.)"
    echo "   4. Un cron job"
    echo ""
    echo "📋 Para buscar más:"
    echo "   - Scripts en /home/deploy/bin/"
    echo "   - Hooks de git: find .git/hooks -type f 2>/dev/null"
    echo "   - Cron jobs: crontab -l"
    echo "   - Servicios systemd: systemctl list-units | grep postulamatic"
fi

# Buscar scripts comunes de deployment
echo ""
echo "📋 Scripts de deployment comunes:"
for script in deploy.sh server_deploy.sh deploy.sh update.sh; do
    if [ -f "$script" ]; then
        echo "   📄 $script (existe)"
        if grep -q "migrate" "$script" 2>/dev/null; then
            echo "      → Contiene 'migrate'"
            grep "migrate" "$script" | head -3
        fi
    fi
done

EOF

echo ""
echo "✅ Búsqueda completada"
echo ""
echo "📋 Próximos pasos:"
echo "   1. Si se encontró un archivo con 'migrate --check', ejecuta el fix:"
echo "      bash scripts/aplicar_fix_directo.sh"
echo ""
echo "   2. Si no se encontró, el problema puede estar en GitHub Actions"
echo "      Revisa: https://github.com/idgleb/PostulaMatic/actions"

