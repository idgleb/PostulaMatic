#!/bin/bash
# Script para aplicar el fix directamente en el servidor
# Busca y reemplaza migrate --check en TODOS los archivos encontrados

SSH_KEY="${HOME}/.ssh/postulamatic_win_ed25519"
SERVER="deploy@178.156.188.95"
APP_DIR="/home/deploy/apps/postulamatic"

echo "🚀 Aplicando fix de timeout en el servidor..."
echo ""

ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
cd /home/deploy/apps/postulamatic

echo "🔍 Buscando archivos con 'migrate --check'..."
FILES=$(grep -r "migrate --check" . 2>/dev/null | grep -v ".git" | grep -v ".backup" | cut -d: -f1 | sort -u || echo "")

if [ -z "$FILES" ]; then
    echo "ℹ️ No se encontró 'migrate --check' en archivos locales"
    echo ""
    echo "💡 El problema puede estar en:"
    echo "   1. GitHub Actions (revisa .github/workflows/*.yml en el repo)"
    echo "   2. Un script ejecutado desde otro lugar"
    echo "   3. Un hook de git"
    echo ""
    echo "📋 Buscando en otros lugares..."
    
    # Buscar en hooks de git
    if [ -d ".git/hooks" ]; then
        HOOK_FILES=$(grep -r "migrate --check" .git/hooks 2>/dev/null | cut -d: -f1 | sort -u || echo "")
        if [ -n "$HOOK_FILES" ]; then
            echo "⚠️ Encontrado en hooks de git:"
            echo "$HOOK_FILES"
            FILES="$HOOK_FILES"
        fi
    fi
    
    # Buscar en /home/deploy/bin/ si existe
    if [ -d "/home/deploy/bin" ]; then
        BIN_FILES=$(grep -r "migrate --check" /home/deploy/bin 2>/dev/null | cut -d: -f1 | sort -u || echo "")
        if [ -n "$BIN_FILES" ]; then
            echo "⚠️ Encontrado en /home/deploy/bin:"
            echo "$BIN_FILES"
            FILES="$FILES $BIN_FILES"
        fi
    fi
fi

if [ -z "$FILES" ]; then
    echo "❌ No se encontró 'migrate --check' en ningún lugar"
    echo ""
    echo "📋 Verificación manual:"
    echo "   1. Revisa GitHub Actions: https://github.com/idgleb/PostulaMatic/actions"
    echo "   2. Revisa los logs del último deployment"
    echo "   3. Ejecuta manualmente: grep -r 'migrate --check' /home/deploy/"
    exit 1
fi

echo "📝 Archivos encontrados:"
echo "$FILES" | while read file; do
    echo "   - $file"
done
echo ""

# Aplicar fix en cada archivo
for file in $FILES; do
    if [ ! -f "$file" ]; then
        echo "⚠️ Archivo no existe: $file"
        continue
    fi
    
    echo "🔧 Modificando: $file"
    
    # Crear backup
    backup_file="${file}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$file" "$backup_file" 2>/dev/null || {
        echo "   ⚠️ No se pudo crear backup (puede ser un archivo protegido)"
    }
    
    # Usar Python para reemplazar (más confiable)
    python3 << PYTHON_SCRIPT
import re
import sys
import os

file_path = '$file'

try:
    # Leer archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Patrón 1: Bloque completo con || y {}
    # Ejemplo: migrate --check || { echo "..."; migrate --noinput; }
    pattern1 = r'docker compose run --rm postulamatic_web python manage\.py migrate --check\s*\|\|\s*\{[^}]*migrate --noinput[^}]*\}'
    replacement1 = 'echo "🔄 Aplicando migraciones..."\ndocker compose run --rm postulamatic_web python manage.py migrate --noinput'
    content = re.sub(pattern1, replacement1, content, flags=re.DOTALL | re.MULTILINE)
    
    # Patrón 2: Línea simple con migrate --check
    if 'migrate --check' in content:
        lines = content.split('\n')
        new_lines = []
        i = 0
        in_block = False
        brace_count = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Detectar inicio de bloque con migrate --check
            if 'migrate --check' in line and '||' in line:
                # Saltar esta línea
                i += 1
                # Buscar el inicio del bloque {}
                if i < len(lines) and '{' in lines[i]:
                    in_block = True
                    brace_count = lines[i].count('{') - lines[i].count('}')
                    i += 1
                    # Saltar líneas hasta el cierre del bloque
                    while i < len(lines) and (in_block or brace_count > 0):
                        if '{' in lines[i]:
                            brace_count += lines[i].count('{')
                        if '}' in lines[i]:
                            brace_count -= lines[i].count('}')
                            if brace_count <= 0:
                                in_block = False
                        # Si encontramos migrate --noinput dentro del bloque, usarlo como reemplazo
                        if 'migrate --noinput' in lines[i] and in_block:
                            new_lines.append('echo "🔄 Aplicando migraciones..."')
                            new_lines.append('docker compose run --rm postulamatic_web python manage.py migrate --noinput')
                        i += 1
                    continue
                else:
                    # No hay bloque, solo reemplazar la línea
                    new_lines.append('echo "🔄 Aplicando migraciones..."')
                    new_lines.append('docker compose run --rm postulamatic_web python manage.py migrate --noinput')
                    i += 1
                    continue
            elif 'migrate --check' in line:
                # Línea simple con migrate --check (sin ||)
                new_lines.append('echo "🔄 Aplicando migraciones..."')
                new_lines.append('docker compose run --rm postulamatic_web python manage.py migrate --noinput')
                i += 1
                continue
            
            # Eliminar líneas relacionadas innecesarias
            if 'Migrations needed' in line or ('echo' in line and 'migrate' in line.lower() and i > 0 and 'migrate --check' in '\n'.join(lines[max(0,i-5):i])):
                i += 1
                continue
            
            new_lines.append(line)
            i += 1
        
        content = '\n'.join(new_lines)
    
    # Si el contenido cambió, guardar
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"   ✅ Modificado correctamente")
        
        # Verificar que ya no tiene migrate --check
        if 'migrate --check' not in content:
            print(f"   ✅ Verificado: ya no contiene 'migrate --check'")
        else:
            print(f"   ⚠️ Aún contiene 'migrate --check' - revisar manualmente")
    else:
        print(f"   ⚠️ No se pudo modificar automáticamente")
        print(f"   💡 Editar manualmente: nano $file")
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)
PYTHON_SCRIPT
done

echo ""
echo "✅ Fix aplicado"
echo ""
echo "📋 Verificación final:"
REMAINING=$(grep -r "migrate --check" . 2>/dev/null | grep -v ".git" | grep -v ".backup" | wc -l || echo "0")
if [ "$REMAINING" -eq 0 ]; then
    echo "✅ No se encontró 'migrate --check' en archivos"
else
    echo "⚠️ Aún hay $REMAINING instancias de 'migrate --check'"
    echo "📝 Archivos que necesitan revisión manual:"
    grep -r "migrate --check" . 2>/dev/null | grep -v ".git" | grep -v ".backup" | cut -d: -f1 | sort -u
fi

EOF

echo ""
echo "✅ Proceso completado"
echo ""
echo "📋 Próximos pasos:"
echo "   1. Verificar que el próximo deployment no tenga timeout"
echo "   2. Si el problema persiste, revisa GitHub Actions"

