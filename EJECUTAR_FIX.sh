#!/bin/bash
# Script para ejecutar el fix directamente en el servidor
# Uso: bash EJECUTAR_FIX.sh

SSH_KEY="${HOME}/.ssh/postulamatic_win_ed25519"
SERVER="deploy@178.156.188.95"

echo "🚀 Aplicando fix de timeout en el servidor..."
echo ""

# Ejecutar comando en el servidor para buscar y reemplazar
ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
cd /home/deploy/apps/postulamatic

echo "🔍 Buscando 'migrate --check'..."
FILES=$(grep -r "migrate --check" . 2>/dev/null | cut -d: -f1 | sort -u || echo "")

if [ -z "$FILES" ]; then
    echo "ℹ️ No se encontró 'migrate --check' en archivos locales"
    echo "💡 El script puede estar en:"
    echo "   - GitHub Actions (workflow .yml)"
    echo "   - Ejecutándose inline en algún script"
    echo "   - En un cron job"
    echo ""
    echo "📋 Para buscar manualmente en todos los lugares:"
    echo "   grep -r 'migrate --check' ."
    echo "   cat ~/.bashrc | grep migrate"
    echo "   crontab -l | grep migrate"
    exit 0
fi

echo "📝 Archivos encontrados:"
echo "$FILES"
echo ""

for file in $FILES; do
    echo "🔧 Modificando: $file"
    
    # Backup
    backup="${file}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$file" "$backup"
    echo "   📦 Backup: $backup"
    
    # Leer el archivo y reemplazar
    python3 << PYTHON_SCRIPT
import re
import sys

file_path = '$file'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Patrón 1: Bloque completo con ||
    pattern1 = r'docker compose run --rm postulamatic_web python manage\.py migrate --check\s*\|\|\s*\{[^}]*migrate --noinput[^}]*\}'
    replacement = 'echo "🔄 Aplicando migraciones..."\ndocker compose run --rm postulamatic_web python manage.py migrate --noinput'
    content = re.sub(pattern1, replacement, content, flags=re.DOTALL)
    
    # Patrón 2: Línea simple con migrate --check
    if 'migrate --check' in content:
        lines = content.split('\n')
        new_lines = []
        skip_until_close = False
        
        for i, line in enumerate(lines):
            if 'migrate --check' in line:
                # Encontrar el bloque completo
                if '||' in line and '{' in line:
                    skip_until_close = True
                    # Agregar la línea de reemplazo
                    new_lines.append('echo "🔄 Aplicando migraciones..."')
                    new_lines.append('docker compose run --rm postulamatic_web python manage.py migrate --noinput')
                    continue
                elif '||' in line:
                    # Buscar el cierre del bloque
                    j = i + 1
                    while j < len(lines) and ('}' not in lines[j] or lines[j].strip() != '}'):
                        j += 1
                    # Saltar todo el bloque
                    i = j
                    # Agregar la línea de reemplazo
                    new_lines.append('echo "🔄 Aplicando migraciones..."')
                    new_lines.append('docker compose run --rm postulamatic_web python manage.py migrate --noinput')
                    continue
                else:
                    # Línea simple, reemplazar
                    new_lines.append('echo "🔄 Aplicando migraciones..."')
                    new_lines.append('docker compose run --rm postulamatic_web python manage.py migrate --noinput')
                    continue
            
            if skip_until_close:
                if '}' in line and line.strip() == '}':
                    skip_until_close = False
                continue
            
            # Eliminar líneas relacionadas
            if 'Migrations needed' in line or ('migrate --noinput' in line and i > 0 and 'migrate --check' in '\n'.join(lines[max(0,i-3):i])):
                continue
            
            new_lines.append(line)
        
        content = '\n'.join(new_lines)
    
    # Si cambió, guardar
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"   ✅ Modificado correctamente")
    else:
        print(f"   ⚠️ No se pudo modificar automáticamente")
        print(f"   💡 Editar manualmente: nano $file")
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)
PYTHON_SCRIPT
done

echo ""
echo "✅ Proceso completado"
echo ""
echo "📋 Verificación:"
if grep -r "migrate --check" . 2>/dev/null | grep -v ".backup."; then
    echo "⚠️ Aún hay archivos con 'migrate --check'"
    echo "📝 Archivos que necesitan edición manual:"
    grep -r "migrate --check" . 2>/dev/null | grep -v ".backup." | cut -d: -f1 | sort -u
else
    echo "✅ No se encontró 'migrate --check' en archivos"
fi

EOF

echo ""
echo "✅ Fix aplicado en el servidor"
echo ""
echo "📋 Próximos pasos:"
echo "1. Verificar que el próximo deployment no tenga timeout"
echo "2. O probar manualmente:"
echo "   ssh -i $SSH_KEY $SERVER 'cd /home/deploy/apps/postulamatic && docker compose run --rm postulamatic_web python manage.py migrate --noinput'"

