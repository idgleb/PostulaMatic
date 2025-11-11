# 🔧 Solución Rápida: Eliminar Timeout en Migraciones

## 🎯 Problema

El script de deployment tiene un timeout en este comando:
```bash
docker compose run --rm postulamatic_web python manage.py migrate --check
```

## ✅ Solución Rápida

### **Opción 1: Modificar Script Directamente en el Servidor (RECOMENDADA)**

1. **Conectarse al servidor:**
```bash
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95
cd /home/deploy/apps/postulamatic
```

2. **Buscar el script que tiene `migrate --check`:**
```bash
grep -r "migrate --check" .
```

3. **Modificar el script encontrado:**
```bash
# Si es un archivo .sh
nano [nombre_del_script].sh

# O si está en línea en algún lugar, buscar y reemplazar
```

4. **Cambiar esta línea:**
```bash
# ❌ ELIMINAR ESTA LÍNEA (causa timeout):
docker compose run --rm postulamatic_web python manage.py migrate --check || {
  echo "Migrations needed, applying safely..."
  docker compose run --rm postulamatic_web python manage.py migrate --noinput
}
```

5. **Por esta línea (más rápida y segura):**
```bash
# ✅ USAR ESTA LÍNEA (sin timeout):
echo "🔄 Aplicando migraciones..."
docker compose run --rm postulamatic_web python manage.py migrate --noinput
```

### **Opción 2: Usar Script Mejorado**

1. **Copiar el script mejorado al servidor:**
```bash
# Desde tu máquina local
scp -i ~/.ssh/postulamatic_win_ed25519 scripts/server_deploy.sh deploy@178.156.188.95:/home/deploy/apps/postulamatic/server_deploy.sh
```

2. **Conectarse al servidor y hacerlo ejecutable:**
```bash
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95
cd /home/deploy/apps/postulamatic
chmod +x server_deploy.sh
```

3. **Probar el script:**
```bash
./server_deploy.sh
```

4. **Si funciona, reemplazar el script actual:**
```bash
# Hacer backup del script actual
if [ -f "deploy.sh" ]; then
    mv deploy.sh deploy.sh.old.$(date +%Y%m%d_%H%M%S)
fi

# Usar el nuevo script
mv server_deploy.sh deploy.sh
```

### **Opción 3: Si se Ejecuta desde GitHub Actions**

1. **Ir a GitHub Actions:**
   - https://github.com/idgleb/PostulaMatic/actions
   - Buscar el workflow que falla

2. **Ver el workflow (si está en el repo):**
   - Buscar `.github/workflows/*.yml`
   - O ver la configuración en GitHub

3. **Modificar el paso de migraciones:**
```yaml
# ❌ ELIMINAR:
- name: Check migrations
  run: |
    docker compose run --rm postulamatic_web python manage.py migrate --check || {
      docker compose run --rm postulamatic_web python manage.py migrate --noinput
    }

# ✅ REEMPLAZAR CON:
- name: Apply migrations
  run: docker compose run --rm postulamatic_web python manage.py migrate --noinput
```

## 🔍 Buscar Script en el Servidor

Si no sabes dónde está el script, ejecuta esto en el servidor:

```bash
# Buscar en todos los archivos .sh
find . -name "*.sh" -exec grep -l "migrate --check" {} \;

# Buscar en todos los archivos
grep -r "migrate --check" .

# Buscar en scripts comunes
ls -la *.sh
ls -la scripts/*.sh 2>/dev/null
```

## ✅ Verificación

Después de hacer el cambio, verificar que funciona:

```bash
# Probar el comando de migraciones directamente
docker compose run --rm postulamatic_web python manage.py migrate --noinput

# Debe terminar rápidamente (< 5 segundos) con mensaje:
# "Operations to perform: ... No migrations to apply."
# O aplicar migraciones si hay pendientes
```

## 📝 Notas Importantes

- ✅ **Es seguro eliminar `--check`**: Django solo aplica migraciones si son necesarias
- ✅ **Más rápido**: Termina en < 5 segundos si no hay migraciones
- ✅ **Sin timeout**: No hay límite de tiempo que cause problemas
- ✅ **Mismo resultado**: El comportamiento final es el mismo

## 🚀 Comando Rápido para Aplicar el Fix

Si tienes acceso SSH al servidor, ejecuta esto:

```bash
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 << 'EOF'
cd /home/deploy/apps/postulamatic

# Buscar y reemplazar migrate --check en todos los scripts
find . -name "*.sh" -type f -exec sed -i.bak 's/migrate --check.*migrate --noinput/docker compose run --rm postulamatic_web python manage.py migrate --noinput/g' {} \;

# O si prefieres hacerlo manualmente:
# 1. Encontrar el script: grep -r "migrate --check" .
# 2. Editar el script: nano [script].sh
# 3. Eliminar la línea con --check
# 4. Dejar solo: docker compose run --rm postulamatic_web python manage.py migrate --noinput
EOF
```

## 🎯 Resultado Esperado

Después de aplicar el fix:
- ✅ No más timeouts en migraciones
- ✅ Deployment más rápido
- ✅ Mismo nivel de seguridad
- ✅ Migraciones aplicadas correctamente

