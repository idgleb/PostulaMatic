# 🔧 Solución: ERR_CONNECTION_REFUSED después del Rescale

## 🔍 Problema

Después del rescale del servidor, el sitio muestra:
```
ERR_CONNECTION_REFUSED
La página postulamatic.app ha rechazado la conexión.
```

## ✅ Solución: Reiniciar Servicios

Después de un rescale, el servidor se reinicia y los servicios Docker pueden no iniciarse automáticamente.

### Pasos para Solucionar:

#### 1. Conectarse al Servidor

```bash
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95
```

**En Windows PowerShell, la ruta puede ser:**
```powershell
ssh -i C:\Users\idgle\.ssh\postulamatic_win_ed25519 deploy@178.156.188.95
```

#### 2. Verificar Estado de Docker

```bash
# Verificar que Docker esté corriendo
sudo systemctl status docker

# Si no está corriendo, iniciarlo
sudo systemctl start docker
```

#### 3. Verificar Contenedores

```bash
# Ver qué contenedores están corriendo
docker ps

# Ver todos los contenedores (incluyendo detenidos)
docker ps -a
```

#### 4. Reiniciar Servicios de PostulaMatic

```bash
cd /home/deploy/apps/postulamatic

# Iniciar todos los servicios
docker compose up -d

# Verificar que se iniciaron correctamente
docker compose ps
```

#### 5. Verificar Nginx

```bash
# Verificar que Nginx esté corriendo
docker ps | grep nginx-proxy

# Si no está corriendo, iniciarlo
# (Nginx puede estar en un contenedor separado)
docker start nginx-proxy 2>/dev/null || echo "Nginx puede estar en otro lugar"
```

#### 6. Verificar Logs

```bash
# Ver logs de Django
cd /home/deploy/apps/postulamatic
docker compose logs postulamatic_web --tail=50

# Ver si hay errores
docker compose logs postulamatic_web | grep -i error
```

#### 7. Verificar Conectividad

```bash
# Verificar que Django responde localmente
curl -I http://localhost:8000

# Verificar que Nginx puede conectarse a Django
docker exec nginx-proxy curl -I http://postulamatic_web:8000
```

## 🔧 Comandos Rápidos (Todo en Uno)

Ejecuta estos comandos uno por uno en el servidor:

```bash
# 1. Conectarse
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95

# 2. Iniciar Docker si no está corriendo
sudo systemctl start docker
sleep 3

# 3. Ir a la aplicación
cd /home/deploy/apps/postulamatic

# 4. Reiniciar servicios
docker compose down
docker compose up -d

# 5. Esperar a que se inicien
sleep 15

# 6. Verificar estado
docker compose ps

# 7. Verificar logs
docker compose logs postulamatic_web --tail=20

# 8. Verificar que Django responde
curl -I http://localhost:8000
```

## 🚨 Si Aún No Funciona

### Verificar Nginx

```bash
# Ver si Nginx está corriendo
docker ps | grep nginx

# Si no está, puede que necesites iniciarlo manualmente
# (depende de cómo esté configurado en tu servidor)
```

### Verificar Red Docker

```bash
# Ver redes Docker
docker network ls

# Verificar que los contenedores estén en la red correcta
docker network inspect web
```

### Verificar Puertos

```bash
# Ver qué puertos están escuchando
sudo netstat -tlnp | grep -E ':(80|443|8000)'
# O
sudo ss -tlnp | grep -E ':(80|443|8000)'
```

### Reiniciar Todo

```bash
# Detener todo
cd /home/deploy/apps/postulamatic
docker compose down

# Reiniciar Docker (si es necesario)
sudo systemctl restart docker

# Iniciar servicios
docker compose up -d

# Esperar
sleep 20

# Verificar
docker compose ps
curl -I http://localhost:8000
```

## 📋 Checklist de Verificación

- [ ] Docker está corriendo (`sudo systemctl status docker`)
- [ ] Contenedores están corriendo (`docker compose ps`)
- [ ] Django responde en localhost:8000 (`curl -I http://localhost:8000`)
- [ ] Nginx está corriendo (`docker ps | grep nginx`)
- [ ] Nginx puede conectarse a Django
- [ ] Los puertos 80 y 443 están abiertos
- [ ] No hay errores en los logs (`docker compose logs`)

## ✅ Resultado Esperado

Después de ejecutar estos comandos:
- ✅ El sitio debería estar accesible en https://postulamatic.app
- ✅ Todos los servicios deberían estar corriendo
- ✅ No debería haber errores en los logs

## 💡 Nota

Después de un rescale, es normal que los servicios no se inicien automáticamente. Siempre hay que reiniciarlos manualmente.

