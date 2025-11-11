#!/bin/bash
# Script para buscar y reemplazar migrate --check en el servidor
# Este script se ejecuta en el servidor

set -e

echo "🔍 Buscando scripts con 'migrate --check'..."

# Buscar en todos los archivos .sh
FOUND_FILES=$(find . -name "*.sh" -type f -exec grep -l "migrate --check" {} \; 2>/dev/null || true)

if [ -z "$FOUND_FILES" ]; then
    echo "ℹ️ No se encontraron archivos .sh con 'migrate --check'"
    echo "🔍 Buscando en todos los archivos..."
    FOUND_FILES=$(grep -r "migrate --check" . --include="*.sh" 2>/dev/null | cut -d: -f1 | sort -u || true)
fi

if [ -z "$FOUND_FILES" ]; then
    echo "⚠️ No se encontró 'migrate --check' en ningún archivo .sh"
    echo "💡 El script puede estar en GitHub Actions o ejecutándose inline"
    echo ""
    echo "📋 Para verificar, ejecuta manualmente:"
    echo "   grep -r 'migrate --check' ."
    exit 0
fi

echo "✅ Archivos encontrados:"
echo "$FOUND_FILES"
echo ""

# Procesar cada archivo
for file in $FOUND_FILES; do
    echo "📝 Procesando: $file"
    
    # Crear backup
    backup_file="${file}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$file" "$backup_file"
    echo "   📦 Backup creado: $backup_file"
    
    # Reemplazar el patrón problemático
    # Buscar líneas que contengan "migrate --check" y el bloque completo
    if grep -q "migrate --check" "$file"; then
        # Crear archivo temporal con el reemplazo
        temp_file=$(mktemp)
        
        # Usar sed para reemplazar el bloque completo
        # Patrón 1: migrate --check || { ... migrate --noinput }
        sed -e '/migrate --check/,/migrate --noinput/s/.*migrate --check.*/echo "🔄 Aplicando migraciones...\ndocker compose run --rm postulamatic_web python manage.py migrate --noinput/' \
            -e '/migrate --check/d' \
            -e '/Migrations needed/d' \
            -e '/migrate --noinput/d' \
            "$file" > "$temp_file" 2>/dev/null || {
            # Si sed falla, usar un método más simple
            echo "   ⚠️ Usando método alternativo de reemplazo..."
            python3 << PYTHON_SCRIPT
import re
import sys

with open('$file', 'r') as f:
    content = f.read()

# Patrón para encontrar el bloque completo
pattern = r'docker compose run --rm postulamatic_web python manage\.py migrate --check.*?migrate --noinput.*?\n'
replacement = 'echo "🔄 Aplicando migraciones..."\ndocker compose run --rm postulamatic_web python manage.py migrate --noinput\n'

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Si no se reemplazó, buscar líneas individuales
if new_content == content:
    # Reemplazar línea por línea
    lines = content.split('\n')
    new_lines = []
    skip_next = False
    for i, line in enumerate(lines):
        if 'migrate --check' in line:
            skip_next = True
            continue
        if skip_next and ('migrate --noinput' in line or 'Migrations needed' in line):
            if 'migrate --noinput' in line:
                new_lines.append('echo "🔄 Aplicando migraciones..."')
                new_lines.append('docker compose run --rm postulamatic_web python manage.py migrate --noinput')
            skip_next = False
            continue
        new_lines.append(line)
    new_content = '\n'.join(new_lines)

with open('$temp_file', 'w') as f:
    f.write(new_content)
PYTHON_SCRIPT
        }
        
        # Verificar que el reemplazo funcionó
        if ! grep -q "migrate --check" "$temp_file" 2>/dev/null; then
            mv "$temp_file" "$file"
            echo "   ✅ Archivo modificado correctamente"
        else
            echo "   ⚠️ El reemplazo automático no funcionó completamente"
            echo "   💡 Edita el archivo manualmente: nano $file"
            rm "$temp_file"
        fi
    fi
done

echo ""
echo "✅ Proceso completado"
echo ""
echo "📋 Verificación:"
echo "   grep -r 'migrate --check' ."
echo ""
echo "💡 Si aún aparece 'migrate --check', edita los archivos manualmente"

