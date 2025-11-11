#!/bin/bash
# Script simple para reemplazar migrate --check en el servidor

echo "🔍 Buscando 'migrate --check' en el servidor..."

# Buscar en todos los archivos
FILES=$(grep -r "migrate --check" . 2>/dev/null | cut -d: -f1 | sort -u || echo "")

if [ -z "$FILES" ]; then
    echo "ℹ️ No se encontró 'migrate --check' en ningún archivo"
    echo "💡 El script puede estar ejecutándose inline o en GitHub Actions"
    exit 0
fi

echo "📝 Archivos encontrados:"
echo "$FILES"
echo ""

for file in $FILES; do
    echo "🔧 Modificando: $file"
    
    # Backup
    cp "$file" "${file}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Reemplazar usando sed (método simple)
    # Eliminar líneas con migrate --check y el bloque relacionado
    sed -i.bak2 '/migrate --check/,/migrate --noinput/{
        /migrate --check/d
        /Migrations needed/d
        /migrate --noinput/{
            s/.*/echo "🔄 Aplicando migraciones..."\
docker compose run --rm postulamatic_web python manage.py migrate --noinput/
        }
    }' "$file" 2>/dev/null || {
        # Método alternativo: reemplazo directo
        sed -i.bak3 's/.*migrate --check.*/echo "🔄 Aplicando migraciones..."\ndocker compose run --rm postulamatic_web python manage.py migrate --noinput/' "$file"
    }
    
    echo "   ✅ Modificado"
done

echo ""
echo "✅ Fix aplicado"
echo "📋 Verificar: grep -r 'migrate --check' ."

