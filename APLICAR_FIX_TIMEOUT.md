# 🚀 Aplicar Fix de Timeout en Servidor - Guía Rápida

## 📋 Resumen

El script de deployment en el servidor usa `migrate --check` que causa timeout. Necesitamos eliminar ese paso.

## ✅ Solución en 3 Pasos

### Paso 1: Conectarse al Servidor

```bash
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95
cd /home/deploy/apps/postulamatic
```

### Paso 2: Buscar el Script con `migrate --check`

```bash
# Buscar en todos los archivos
grep -r "migrate --check" .

# Si encuentra archivos .sh, listarlos
find . -name "*.sh" -exec grep -l "migrate --check" {} \;
```

### Paso 3: Modificar el Script

**Opción A: Si el script está en un archivo .sh**

```bash
# Editar el archivo encontrado (ejemplo: deploy.sh)
nano deploy.sh

# Buscar esta línea:
docker compose run --rm postulamatic_web python manage.py migrate --check || {
  echo "Migrations needed, applying safely..."
  docker compose run --rm postulamatic_web python manage.py migrate --noinput
}

# Reemplazar por:
echo "🔄 Aplicando migraciones..."
docker compose run --rm postulamatic_web python manage.py migrate --noinput

# Guardar (Ctrl+X, Y, Enter)
```

**Opción B: Usar el Script Mejorado del Repositorio**

```bash
# El script mejorado ya está en el repositorio
# Solo necesitas actualizar el código
git pull origin master

# El script server_deploy.sh ya está disponible
# Puedes usarlo directamente o reemplazar el actual
chmod +x scripts/server_deploy.sh
./scripts/server_deploy.sh
```

## 🔍 Si el Script está en GitHub Actions

Si el script se ejecuta desde GitHub Actions:

1. **Ir a:** https://github.com/idgleb/PostulaMatic/actions
2. **Buscar el workflow que falla**
3. **Ver el archivo del workflow** (si está en el repo: `.github/workflows/*.yml`)
4. **Modificar el paso de migraciones:**

```yaml
# Cambiar de:
- name: Check migrations
  run: docker compose run --rm postulamatic_web python manage.py migrate --check

# A:
- name: Apply migrations
  run: docker compose run --rm postulamatic_web python manage.py migrate --noinput
```

## ✅ Verificación

Después de hacer el cambio, verificar:

```bash
# Probar el comando directamente
docker compose run --rm postulamatic_web python manage.py migrate --noinput

# Debe terminar rápidamente (< 5 segundos) con:
# "Operations to perform: ... No migrations to apply."
```

## 🎯 Comando Rápido (Todo en Uno)

Si quieres aplicar el fix automáticamente:

```bash
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 << 'EOF'
cd /home/deploy/apps/postulamatic

# Actualizar código del repositorio (incluye el script mejorado)
git pull origin master

# Buscar scripts con migrate --check
echo "🔍 Buscando scripts con migrate --check..."
find . -name "*.sh" -exec grep -l "migrate --check" {} \; | while read script; do
    echo "📝 Encontrado: $script"
    echo "📦 Haciendo backup..."
    cp "$script" "${script}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "🔧 Modificando..."
    sed -i 's/migrate --check.*migrate --noinput/docker compose run --rm postulamatic_web python manage.py migrate --noinput/g' "$script"
    echo "✅ Modificado: $script"
done

echo "✅ Fix aplicado. Prueba ejecutando el script de deployment."
EOF
```

## 📝 Notas

- ✅ **Es seguro**: Django solo aplica migraciones si son necesarias
- ✅ **Más rápido**: Termina en < 5 segundos
- ✅ **Sin timeout**: No hay límite de tiempo
- ✅ **Mismo resultado**: Comportamiento final idéntico

## 🆘 Si No Funciona

Si después de aplicar el fix sigue habiendo timeout:

1. **Verificar que el cambio se aplicó:**
```bash
grep -r "migrate --check" .
# No debe encontrar nada
```

2. **Verificar que el script se está ejecutando:**
```bash
# Ver qué script se ejecuta en el deployment
ps aux | grep deploy
```

3. **Ver logs del deployment:**
```bash
# Ver logs de Docker
docker compose logs postulamatic_web | tail -50
```

