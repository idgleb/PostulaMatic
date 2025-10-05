# 🚀 Guía de Despliegue - PostulaMatic

## ⚡ **Resumen Rápido - Estado Actual**

### **✅ Deployment Automático FUNCIONANDO**
- **Push a GitHub** → Deploy automático al servidor
- **Workflow**: `.github/workflows/unified-ci-cd.yml`
- **Tests automáticos** antes del deploy
- **Health check** después del deploy

### **🔧 Configuración Actual del Servidor**
- **Ubicación**: `/home/deploy/apps/postulamatic`
- **Repositorio**: Clonado desde GitHub
- **Variables**: `.env` configurado
- **Docker**: Compose funcionando
- **Nginx**: Configuración versionada

### **📋 Para hacer cambios:**
```bash
git add .
git commit -m "Descripción del cambio"
git push origin master
# ¡Deploy automático!
```

---

## 📋 Resumen de Mejoras Implementadas

Para evitar problemas como el error `502 Bad Gateway` que experimentamos, hemos implementado las siguientes mejoras:

### ✅ **Configuración de Nginx Versionada**
- **Archivo:** `nginx/postulamatic.conf`
- **Beneficio:** La configuración está en el repositorio, versionada y probada
- **Uso:** Se copia automáticamente durante el despliegue

### ✅ **Scripts de Despliegue Automatizados**
- **`scripts/deploy.sh`** - Despliegue completo con validaciones
- **`scripts/nginx-validate.sh`** - Validación de configuración Nginx
- **`scripts/health-check.sh`** - Verificación de salud del sitio
- **`scripts/nginx-backup.sh`** - Backup automático de configuraciones

### ✅ **Makefile para Comandos Simplificados**
- **`make deploy`** - Despliegue completo
- **`make deploy-dry-run`** - Simulación sin cambios reales
- **`make health-check`** - Verificar sitio en producción
- **`make nginx-validate`** - Validar configuración Nginx

---

## 🔄 **Proceso de Despliegue Mejorado**

### **1. Despliegue Automático (ACTUAL - RECOMENDADO)**
```bash
# El despliegue ahora es completamente automático via GitHub Actions
git add .
git commit -m "Descripción del cambio"
git push origin master

# GitHub Actions ejecutará automáticamente:
# 1. Tests (Django, Black, isort, Ruff)
# 2. Si tests pasan → Deploy automático al servidor
# 3. Health check final
```

### **2. Configuración de Deployment Automático**
El workflow está configurado en `.github/workflows/unified-ci-cd.yml` y requiere estos secrets en GitHub:

**Secrets requeridos en GitHub Settings → Secrets and variables → Actions:**
- `SSH_HOST`: `178.156.188.95`
- `SSH_USER`: `deploy`
- `SSH_KEY`: [Contenido de la clave privada SSH]
- `APP_DIR`: `/home/deploy/apps/postulamatic`

**Clave SSH privada para copiar:**
```
⚠️ IMPORTANTE: La clave SSH privada debe obtenerse del archivo local:
~/.ssh/postulamatic_win_ed25519

NUNCA incluir claves privadas en documentación pública.
```

### **3. Despliegue Manual (Solo en emergencias)**
```bash
# Solo usar si GitHub Actions falla
make deploy

# O script directo
./scripts/deploy.sh
```

### **2. Validaciones Automáticas**
El proceso de despliegue ahora incluye:
- ✅ Backup automático de configuración actual
- ✅ Validación de sintaxis de Nginx
- ✅ Rollback automático si falla la validación
- ✅ Health check del sitio después del despliegue
- ✅ Verificación de headers de seguridad

### **3. Comandos de Verificación**
```bash
# Verificar salud del sitio
make health-check

# Validar configuración de Nginx
make nginx-validate

# Recargar Nginx manualmente
make nginx-reload

# Crear backup de configuración
make nginx-backup
```

---

## 🚀 **Flujo de Deployment Automático Actual**

### **Configuración del Servidor (Ya completada)**
```bash
# El servidor está configurado con:
# - Repositorio git clonado en: /home/deploy/apps/postulamatic
# - Archivo .env con variables de entorno
# - Docker Compose configurado
# - Nginx configurado
```

### **Flujo de Deployment**
1. **Push a GitHub** → Trigger automático del workflow
2. **Tests automáticos** → Django tests, Black, isort, Ruff
3. **Si tests pasan** → SSH al servidor
4. **Backup configuración** → Backup automático de Nginx
5. **Git pull** → Actualizar código en servidor
6. **Update Nginx** → Copiar configuración desde repo
7. **Validate Nginx** → `nginx -t` para validar
8. **Build Docker** → Reconstruir contenedores
9. **Migrate DB** → Ejecutar migraciones
10. **Start containers** → Levantar servicios
11. **Reload Nginx** → Aplicar nueva configuración
12. **Health check** → Verificar que el sitio responde

### **Monitoreo del Deployment**
- **GitHub Actions**: https://github.com/idgleb/PostulaMatic/actions
- **Logs del servidor**: SSH al servidor y ver logs de Docker
- **Health check**: https://postulamatic.app

---

## 🛡️ **Prevención de Problemas**

### **Problema Anterior: Configuración Corrupta**
- **Causa:** Escape incorrecto de variables en PowerShell
- **Solución:** Configuración versionada en repositorio

### **Problema Anterior: Sin Validación**
- **Causa:** No se validaba la configuración antes de aplicar
- **Solución:** Validación automática con `nginx -t`

### **Problema Anterior: Sin Rollback**
- **Causa:** No había backup de configuración anterior
- **Solución:** Backup automático y rollback en caso de fallo

---

## 📁 **Estructura de Archivos**

```
postulamatic/
├── nginx/
│   └── postulamatic.conf          # Configuración versionada
├── scripts/
│   ├── deploy.sh                  # Despliegue completo
│   ├── nginx-validate.sh          # Validación Nginx
│   ├── health-check.sh            # Health check
│   └── nginx-backup.sh            # Backup automático
├── Makefile                       # Comandos simplificados
└── DEPLOYMENT.md                  # Esta documentación
```

---

## 🚨 **Respuesta a Incidentes**

### **Si GitHub Actions falla:**

1. **Verificar secrets en GitHub:**
   - Ir a: https://github.com/idgleb/PostulaMatic/settings/secrets/actions
   - Verificar que todos los secrets estén configurados correctamente

2. **Ver logs de GitHub Actions:**
   - Ir a: https://github.com/idgleb/PostulaMatic/actions
   - Click en el workflow fallido para ver logs detallados

3. **Deployment manual de emergencia:**
   ```bash
   # Si GitHub Actions falla, hacer deployment manual
   make deploy
   ```

### **Si el sitio no responde después del despliegue:**

1. **Verificar estado del sitio:**
   ```bash
   make health-check
   ```

2. **Validar configuración de Nginx:**
   ```bash
   make nginx-validate
   ```

3. **Recargar Nginx si es necesario:**
   ```bash
   make nginx-reload
   ```

4. **Ver logs del servidor:**
   ```bash
   ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "docker logs nginx-proxy --tail 50"
   ```

### **Si el repositorio en el servidor se corrompe:**

```bash
# Reconectar el repositorio en el servidor
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "
  cd /home/deploy/apps
  rm -rf postulamatic
  git clone https://github.com/idgleb/PostulaMatic.git postulamatic
  cd postulamatic
  cp ../postulamatic_backup_/.env .env
"
```

### **Rollback de emergencia:**
```bash
# Restaurar configuración anterior
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "
  cd /home/deploy/nginx-backups
  ls -t postulamatic.conf.* | head -1 | xargs -I {} cp {} /home/deploy/conf.d/postulamatic.conf
  docker exec nginx-proxy nginx -t && docker exec nginx-proxy nginx -s reload
"
```

---

## 📊 **Monitoreo Continuo**

### **Verificación Diaria (Opcional)**
```bash
# Agregar a crontab del servidor para verificación automática
0 9 * * * /home/deploy/apps/postulamatic/scripts/health-check.sh >> /home/deploy/health-check.log 2>&1
```

### **Alertas por Email (Futuro)**
- Configurar alertas cuando el health check falle
- Notificaciones por Slack/Discord
- Dashboard de monitoreo

---

## 🔧 **Configuración del Servidor**

### **Variables de Entorno Requeridas**
```bash
# En ~/.ssh/config o como variables de entorno
SSH_KEY=~/.ssh/postulamatic_win_ed25519
SERVER=deploy@178.156.188.95
```

### **Permisos SSH**
```bash
# Verificar que la clave SSH funciona
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "echo 'SSH OK'"
```

---

## 📝 **Notas Importantes**

1. **Siempre hacer `make deploy-dry-run` primero** para simular el despliegue
2. **La configuración de Nginx está ahora versionada** en el repositorio
3. **Los backups se mantienen automáticamente** (últimos 10)
4. **El proceso incluye validaciones** en cada paso
5. **Hay rollback automático** si algo falla

## ⚠️ **CRÍTICO: Mantener Deployment Automático**

### **🚨 NUNCA hacer estos cambios sin actualizar la documentación:**

1. **Cambios en `.github/workflows/unified-ci-cd.yml`:**
   - ✅ SIEMPRE probar localmente antes de push
   - ✅ Verificar que los secrets estén configurados
   - ✅ Validar sintaxis YAML antes de commit

2. **Cambios en estructura del servidor:**
   - ✅ SIEMPRE actualizar `APP_DIR` en secrets si cambia la ruta
   - ✅ Verificar permisos SSH después de cambios
   - ✅ Documentar cualquier cambio en variables de entorno

3. **Cambios en Docker/Docker Compose:**
   - ✅ SIEMPRE probar `docker compose up` localmente
   - ✅ Verificar que todos los servicios se levanten correctamente
   - ✅ Actualizar `docker-compose.yml` si se agregan servicios

4. **Cambios en Nginx:**
   - ✅ SIEMPRE validar con `nginx -t` antes de push
   - ✅ Mantener `nginx/postulamatic.conf` actualizado
   - ✅ Probar configuración en ambiente de desarrollo

### **🔧 Checklist antes de cada push:**

```bash
# 1. Verificar que el código funciona localmente
docker compose up
# Probar funcionalidades principales

# 2. Verificar sintaxis de archivos críticos
nginx -t  # Si hay cambios en Nginx
python manage.py check  # Django
black --check .  # Formato
isort --check-only .  # Imports

# 3. Verificar que GitHub Actions tiene los secrets
# Ir a: https://github.com/idgleb/PostulaMatic/settings/secrets/actions
# Verificar: SSH_HOST, SSH_USER, SSH_KEY, APP_DIR

# 4. Hacer commit y push
git add .
git commit -m "Descripción clara del cambio"
git push origin master

# 5. Monitorear GitHub Actions
# Ir a: https://github.com/idgleb/PostulaMatic/actions
# Esperar que pase todos los tests y deployment
```

### **🚫 Errores comunes que rompen el deployment:**

1. **YAML mal formado** en workflows
2. **Secrets faltantes** en GitHub Actions
3. **Permisos SSH incorrectos**
4. **Variables de entorno faltantes** en `.env`
5. **Docker Compose mal configurado**
6. **Nginx config inválida**

### **🔍 Diagnóstico rápido si el deployment falla:**

```bash
# 1. Verificar que GitHub Actions se está ejecutando
# Ir a: https://github.com/idgleb/PostulaMatic/actions
# Si no hay workflows ejecutándose, el problema está en el trigger

# 2. Verificar secrets de GitHub Actions
# Ir a: https://github.com/idgleb/PostulaMatic/settings/secrets/actions
# Verificar que existan: SSH_HOST, SSH_USER, SSH_KEY, APP_DIR

# 3. Verificar conectividad SSH desde GitHub Actions
# En los logs del workflow, buscar errores de conexión SSH

# 4. Verificar que el servidor está accesible
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "echo 'Servidor accesible'"

# 5. Verificar que el repositorio en el servidor está actualizado
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "
  cd /home/deploy/apps/postulamatic
  git status
  git log --oneline -3
"

# 6. Verificar estado de Docker en el servidor
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "
  cd /home/deploy/apps/postulamatic
  docker compose ps
"
```

### **🛠️ Soluciones comunes:**

#### **Problema: "Workflow not triggered"**
```bash
# Verificar que el push fue a la rama master
git branch  # Debe estar en master
git push origin master  # Asegurar que es master
```

#### **Problema: "SSH connection failed"**
```bash
# Regenerar clave SSH si es necesario
ssh-keygen -t ed25519 -f ~/.ssh/postulamatic_win_ed25519_new
# Actualizar secret SSH_KEY en GitHub con la nueva clave
# Agregar la nueva clave pública al servidor
ssh-copy-id -i ~/.ssh/postulamatic_win_ed25519_new.pub deploy@178.156.188.95
```

#### **Problema: "Docker build failed"**
```bash
# Verificar que docker-compose.yml es válido
docker compose config
# Probar localmente
docker compose up --build
```

#### **Problema: "Nginx config invalid"**
```bash
# Validar configuración Nginx
nginx -t
# Verificar sintaxis del archivo
nginx/postulamatic.conf
```

### **📅 Mantenimiento Preventivo (Mensual):**

```bash
# 1. Verificar que todos los secrets siguen siendo válidos
# Ir a: https://github.com/idgleb/PostulaMatic/settings/secrets/actions
# Verificar que SSH_KEY sigue funcionando:
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "echo 'SSH OK'"

# 2. Verificar que el servidor tiene espacio suficiente
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "df -h"

# 3. Limpiar imágenes Docker viejas (opcional)
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "
  cd /home/deploy/apps/postulamatic
  docker system prune -f
"

# 4. Verificar logs de GitHub Actions para errores recurrentes
# Ir a: https://github.com/idgleb/PostulaMatic/actions
# Revisar workflows fallidos de los últimos 30 días

# 5. Actualizar documentación si hay cambios en el proceso
# Actualizar este archivo DEPLOYMENT.md si cambia algo
```

### **🔄 Proceso de actualización de secrets:**

Si necesitas cambiar algún secret de GitHub Actions:

1. **Ir a**: https://github.com/idgleb/PostulaMatic/settings/secrets/actions
2. **Actualizar el secret** con el nuevo valor
3. **Hacer un push de prueba** para verificar que funciona:
   ```bash
   echo "# Test secret update" >> README.md
   git add README.md
   git commit -m "Test: Verify secrets update"
   git push origin master
   ```
4. **Monitorear GitHub Actions** para confirmar que funciona

---

## 🎯 **Próximos Pasos Recomendados**

1. ✅ **GitHub Actions implementado** - Deployment automático funcionando
2. **Configurar monitoreo 24/7** con alertas
3. **Crear dashboard de métricas** del sitio
4. **Implementar tests de integración** más completos
5. **Configurar CDN** para mejorar performance
6. **Backup automático de base de datos** en el workflow
7. **Notificaciones por Slack/Email** cuando falla el deployment

---

*Última actualización: Octubre 2025 - Documentación actualizada para prevenir fallos del deployment automático*
