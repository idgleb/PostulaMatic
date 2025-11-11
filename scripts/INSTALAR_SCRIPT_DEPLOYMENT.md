# 📋 Instrucciones para Instalar Script de Deployment Mejorado

## 🎯 Objetivo

Reemplazar el script de deployment en el servidor que usa `migrate --check` (causa timeout) por uno optimizado que aplica migraciones directamente.

## 📍 Ubicación del Script en el Servidor

El script actual probablemente está en:
- `/home/deploy/apps/postulamatic/` (directorio del proyecto)
- O ejecutado directamente por GitHub Actions
- O en algún cron job

## 🚀 Opción 1: Copiar Script Mejorado al Servidor

### Paso 1: Copiar el script al servidor

```bash
# Desde tu máquina local
scp -i ~/.ssh/postulamatic_win_ed25519 scripts/server_deploy.sh deploy@178.156.188.95:/home/deploy/apps/postulamatic/server_deploy.sh
```

### Paso 2: Hacer el script ejecutable

```bash
# Conectarse al servidor
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95

# Ir al directorio del proyecto
cd /home/deploy/apps/postulamatic

# Hacer el script ejecutable
chmod +x server_deploy.sh
```

### Paso 3: Probar el script

```bash
# Ejecutar el script manualmente para probarlo
./server_deploy.sh
```

### Paso 4: Reemplazar el script actual (si existe)

Si hay un script de deployment existente, hacer backup y reemplazarlo:

```bash
# Backup del script actual (si existe)
if [ -f "deploy.sh" ]; then
    mv deploy.sh deploy.sh.old.$(date +%Y%m%d_%H%M%S)
fi

# Usar el nuevo script
mv server_deploy.sh deploy.sh
chmod +x deploy.sh
```

## 🔧 Opción 2: Modificar Script Existente en el Servidor

Si el script está en el servidor, conectarse y modificarlo:

```bash
# Conectarse al servidor
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95
cd /home/deploy/apps/postulamatic

# Buscar el script que tiene migrate --check
grep -r "migrate --check" .

# Editar el script (reemplazar con nano o vi)
nano [nombre_del_script].sh
```

**Cambiar esta línea:**
```bash
# ❌ ANTES (causa timeout)
docker compose run --rm postulamatic_web python manage.py migrate --check || {
  echo "Migrations needed, applying safely..."
  docker compose run --rm postulamatic_web python manage.py migrate --noinput
}
```

**Por esta:**
```bash
# ✅ DESPUÉS (sin timeout)
echo "🔄 Aplicando migraciones..."
docker compose run --rm postulamatic_web python manage.py migrate --noinput
```

## 🔄 Opción 3: Si se Ejecuta desde GitHub Actions

Si el script se ejecuta desde GitHub Actions, necesitas:

1. **Encontrar el workflow de GitHub Actions:**
   - Ir a: https://github.com/idgleb/PostulaMatic/actions
   - Buscar el workflow que hace el deployment
   - Ver el archivo `.github/workflows/*.yml`

2. **Modificar el workflow:**
   - Buscar la línea que tiene `migrate --check`
   - Reemplazarla con `migrate --noinput`

3. **Ejemplo de cambio en workflow:**
```yaml
# ❌ ANTES
- name: Check migrations
  run: docker compose run --rm postulamatic_web python manage.py migrate --check

# ✅ DESPUÉS
- name: Apply migrations
  run: docker compose run --rm postulamatic_web python manage.py migrate --noinput
```

## ✅ Verificación

Después de hacer los cambios, verificar que funciona:

```bash
# Conectarse al servidor
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95
cd /home/deploy/apps/postulamatic

# Ejecutar el script de deployment
./deploy.sh  # o el nombre del script que uses

# Verificar que NO aparece el timeout
# El comando de migraciones debe terminar rápidamente (< 5 segundos)
```

## 🎯 Resultado Esperado

Después de los cambios, el deployment debería:

- ✅ **NO tener timeout** en migraciones
- ✅ **Aplicar migraciones rápidamente** (< 5 segundos si no hay cambios)
- ✅ **Completar el deployment exitosamente**
- ✅ **Health check funcionando**

## 📝 Notas

- El script `server_deploy.sh` ya está optimizado y listo para usar
- No es necesario el paso `--check` - Django maneja esto automáticamente
- Si no hay migraciones pendientes, el comando termina en < 1 segundo
- Si hay migraciones, Django las aplica automáticamente

