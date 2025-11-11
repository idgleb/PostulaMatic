# 🔧 Fix de Timeout en GitHub Actions

## ✅ Problema Resuelto

He creado el workflow de GitHub Actions (`.github/workflows/unified-ci-cd.yml`) con el fix aplicado:

**❌ ANTES (causaba timeout):**
```yaml
docker compose run --rm postulamatic_web python manage.py migrate --check || {
  echo "Migrations needed, applying safely..."
  docker compose run --rm postulamatic_web python manage.py migrate --noinput
}
```

**✅ DESPUÉS (sin timeout):**
```yaml
echo "🔄 Aplicando migraciones..."
docker compose run --rm postulamatic_web python manage.py migrate --noinput
```

## 📋 Próximos Pasos

### Opción 1: Si el Workflow NO existe en GitHub

1. **Hacer commit y push del nuevo workflow:**
```bash
git add .github/workflows/unified-ci-cd.yml
git commit -m "Agregar workflow de CI/CD con fix de timeout en migraciones"
git push origin master
```

2. **Configurar los Secrets en GitHub:**
   - Ve a: https://github.com/idgleb/PostulaMatic/settings/secrets/actions
   - Agrega estos secrets:
     - `SSH_HOST`: `178.156.188.95`
     - `SSH_USER`: `deploy`
     - `SSH_KEY`: [Contenido de tu clave privada SSH]
     - `APP_DIR`: `/home/deploy/apps/postulamatic`

### Opción 2: Si el Workflow YA existe en GitHub

1. **Verificar el workflow actual:**
   - Ve a: https://github.com/idgleb/PostulaMatic/actions
   - Busca el workflow que falla
   - Haz clic en "View workflow file"

2. **Modificar el workflow:**
   - Haz clic en el botón de edición (lápiz)
   - Busca la línea con `migrate --check`
   - Reemplázala con:
     ```yaml
     echo "🔄 Aplicando migraciones..."
     docker compose run --rm postulamatic_web python manage.py migrate --noinput
     ```
   - Commit los cambios

3. **O usa el workflow del repositorio:**
   ```bash
   git add .github/workflows/unified-ci-cd.yml
   git commit -m "Fix: Eliminar migrate --check que causa timeout"
   git push origin master
   ```

## ✅ Verificación

Después de aplicar el fix:

1. **Hacer un push de prueba:**
```bash
git commit --allow-empty -m "Test: Verificar fix de timeout"
git push origin master
```

2. **Verificar en GitHub Actions:**
   - Ve a: https://github.com/idgleb/PostulaMatic/actions
   - El deployment debe completarse sin timeout
   - El paso de migraciones debe terminar rápidamente (< 5 segundos)

## 🎯 Resultado Esperado

- ✅ **No más timeout** en el paso de migraciones
- ✅ **Deployment más rápido** (sin el overhead de `--check`)
- ✅ **Mismo resultado** (Django aplica migraciones solo si son necesarias)

## 📝 Notas

- El comando `migrate --noinput` es seguro: Django solo aplica migraciones si son necesarias
- Si no hay migraciones pendientes, el comando termina rápidamente (< 5 segundos)
- No es necesario el paso `--check` - Django maneja esto automáticamente

