# 🚀 Guía de Despliegue - PostulaMatic

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

### **1. Despliegue Manual (Recomendado)**
```bash
# Opción 1: Usar Makefile (más fácil)
make deploy

# Opción 2: Script directo
./scripts/deploy.sh

# Opción 3: Simulación primero (recomendado)
make deploy-dry-run
make deploy
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

---

## 🎯 **Próximos Pasos Recomendados**

1. **Implementar GitHub Actions** para despliegue automático
2. **Configurar monitoreo 24/7** con alertas
3. **Crear dashboard de métricas** del sitio
4. **Implementar tests de integración** antes del despliegue
5. **Configurar CDN** para mejorar performance

---

*Última actualización: Octubre 2025*
