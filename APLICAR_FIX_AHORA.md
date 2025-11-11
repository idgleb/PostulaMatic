# 🚀 Aplicar Fix de Timeout - Comando Directo

## ✅ Comando para Ejecutar AHORA

Copia y pega este comando en tu terminal:

```bash
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 << 'EOF'
cd /home/deploy/apps/postulamatic

echo "🔍 Buscando 'migrate --check'..."
FILES=$(grep -r "migrate --check" . 2>/dev/null | cut -d: -f1 | sort -u || echo "")

if [ -z "$FILES" ]; then
    echo "ℹ️ No se encontró 'migrate --check' en archivos"
    echo "💡 Puede estar en GitHub Actions o ejecutándose inline"
    echo ""
    echo "📋 Buscar manualmente:"
    echo "   grep -r 'migrate --check' ."
else
    echo "📝 Archivos encontrados:"
    echo "$FILES"
    echo ""
    
    for file in $FILES; do
        echo "🔧 Modificando: $file"
        cp "$file" "${file}.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Reemplazar usando Python (más confiable)
        python3 << PYTHON
import re

with open('$file', 'r') as f:
    content = f.read()

# Reemplazar el bloque completo
pattern = r'docker compose run --rm postulamatic_web python manage\.py migrate --check\s*\|\|\s*\{[^}]*echo[^}]*migrate --noinput[^}]*\}'
replacement = 'echo "🔄 Aplicando migraciones..."\ndocker compose run --rm postulamatic_web python manage.py migrate --noinput'

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Si no se reemplazó, buscar y eliminar líneas individuales
if new_content == content:
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if 'migrate --check' in line:
            # Saltar esta línea y las siguientes relacionadas
            i += 1
            while i < len(lines) and ('migrate --noinput' not in lines[i] or '}' not in lines[i]):
                if 'migrate --noinput' in lines[i]:
                    new_lines.append('echo "🔄 Aplicando migraciones..."')
                    new_lines.append('docker compose run --rm postulamatic_web python manage.py migrate --noinput')
                i += 1
            if i < len(lines) and '}' in lines[i]:
                i += 1
            continue
        new_lines.append(line)
        i += 1
    new_content = '\n'.join(new_lines)

with open('$file', 'w') as f:
    f.write(new_content)
PYTHON
        
        echo "   ✅ Modificado: $file"
    done
    
    echo ""
    echo "✅ Fix aplicado"
    echo "📋 Verificación:"
    grep -r "migrate --check" . 2>/dev/null || echo "✅ No se encontró 'migrate --check'"
fi

echo ""
echo "🎯 Próximo paso: Probar el deployment"
EOF
```

## 🔍 Si el Script está en GitHub Actions

Si el comando anterior no encuentra archivos, el script probablemente está en GitHub Actions:

1. **Ir a:** https://github.com/idgleb/PostulaMatic/actions
2. **Buscar el workflow que falla**
3. **Ver la configuración del workflow**
4. **Modificar manualmente** el paso de migraciones

## 📝 Método Manual (Si los anteriores no funcionan)

1. **Conectarse al servidor:**
```bash
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95
cd /home/deploy/apps/postulamatic
```

2. **Buscar el script:**
```bash
grep -r "migrate --check" .
```

3. **Editar el archivo encontrado:**
```bash
nano [nombre_del_archivo]
```

4. **Eliminar estas líneas:**
```bash
docker compose run --rm postulamatic_web python manage.py migrate --check || {
  echo "Migrations needed, applying safely..."
  docker compose run --rm postulamatic_web python manage.py migrate --noinput
}
```

5. **Reemplazar por:**
```bash
echo "🔄 Aplicando migraciones..."
docker compose run --rm postulamatic_web python manage.py migrate --noinput
```

6. **Guardar** (Ctrl+X, Y, Enter)

## ✅ Verificación

Después de aplicar el fix:

```bash
# Verificar que no hay más migrate --check
grep -r "migrate --check" .

# Probar el comando de migraciones
docker compose run --rm postulamatic_web python manage.py migrate --noinput

# Debe terminar rápidamente (< 5 segundos)
```

