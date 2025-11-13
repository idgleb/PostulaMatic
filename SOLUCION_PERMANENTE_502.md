# 🔧 Solución Permanente para Error 502 Bad Gateway

## 🎯 Problema

El error `502 Bad Gateway` aparece cuando los contenedores Docker se reinician y Nginx mantiene la IP antigua en caché, impidiendo la conexión con Django.

## ✅ Solución Implementada

Se implementaron **dos soluciones complementarias**:

### 1. Resolver Dinámico en Nginx

Se configuró Nginx para usar el resolver DNS dinámico de Docker (`127.0.0.11`), que re-resuelve automáticamente las IPs cuando cambian.

**Cambios en `nginx/postulamatic.conf`:**
- Agregado `resolver 127.0.0.11 valid=10s;` al inicio del bloque `server`
- Cambiado `proxy_pass` para usar una variable con resolución dinámica

### 2. Script de Monitoreo Automático

Se creó un script que monitorea la conexión cada minuto y reinicia Nginx automáticamente si detecta problemas.

**Scripts creados:**
- `scripts/nginx_auto_reload.sh` - Monitorea y reinicia Nginx si es necesario
- `scripts/setup_nginx_monitor.sh` - Configura el cron job automático

## 📋 Pasos para Aplicar en el Servidor

### Paso 1: Actualizar Configuración de Nginx

```bash
# Conectarse al servidor
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95

# Copiar nueva configuración
cd /home/deploy/apps/postulamatic
git pull origin master

# Copiar configuración a la ubicación de Nginx
cp nginx/postulamatic.conf /home/deploy/conf.d/postulamatic.conf

# Validar configuración
docker exec nginx-proxy nginx -t

# Si es válida, recargar Nginx
docker exec nginx-proxy nginx -s reload
```

### Paso 2: Configurar Monitoreo Automático

```bash
# Hacer scripts ejecutables
chmod +x /home/deploy/apps/postulamatic/scripts/nginx_auto_reload.sh
chmod +x /home/deploy/apps/postulamatic/scripts/setup_nginx_monitor.sh

# Ejecutar script de configuración
/home/deploy/apps/postulamatic/scripts/setup_nginx_monitor.sh
```

### Paso 3: Verificar que Funciona

```bash
# Ver logs del monitoreo
tail -f /home/deploy/nginx_auto_reload.log

# Verificar que el cron job está activo
crontab -l | grep nginx_auto_reload
```

## 🔍 Cómo Funciona

### Resolver Dinámico

El resolver DNS de Docker (`127.0.0.11`) re-resuelve automáticamente los nombres de contenedores cada 10 segundos. Esto significa que cuando Django cambia de IP, Nginx la detecta automáticamente sin necesidad de reiniciarse.

### Monitoreo Automático

El script `nginx_auto_reload.sh` se ejecuta cada minuto y:
1. Verifica que Nginx esté corriendo
2. Verifica que Django esté corriendo
3. Intenta conectar desde Nginx a Django
4. Si falla, reinicia Nginx automáticamente
5. Registra todo en `/home/deploy/nginx_auto_reload.log`

## 📊 Verificación

Después de aplicar los cambios:

```bash
# Verificar que Nginx puede conectarse a Django
docker exec nginx-proxy curl -I http://postulamatic-postulamatic_web-1:8000

# Verificar que el sitio responde
curl -I https://postulamatic.app

# Ver logs del monitoreo
tail -20 /home/deploy/nginx_auto_reload.log
```

## 🛠️ Mantenimiento

### Ver Logs del Monitoreo

```bash
tail -f /home/deploy/nginx_auto_reload.log
```

### Desactivar Monitoreo (si es necesario)

```bash
crontab -e
# Eliminar la línea que contiene: nginx_auto_reload.sh
```

### Reiniciar Manualmente (si es necesario)

```bash
docker restart nginx-proxy
```

## ✅ Resultado Esperado

Con esta solución:
- ✅ Nginx re-resuelve automáticamente las IPs cuando cambian
- ✅ El monitoreo detecta y corrige problemas automáticamente
- ✅ No más errores 502 Bad Gateway después de reinicios
- ✅ El sitio se mantiene accesible automáticamente

## 📝 Notas

- El resolver dinámico es la solución principal y debería prevenir la mayoría de los problemas
- El script de monitoreo es una capa adicional de seguridad
- Los logs se guardan en `/home/deploy/nginx_auto_reload.log` para diagnóstico

