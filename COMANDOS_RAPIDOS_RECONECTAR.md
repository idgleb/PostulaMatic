# ⚡ Comandos Rápidos para Reconectar Después del Rescale

## 🚀 Solución Rápida (Copia y Pega)

### En Windows PowerShell:

```powershell
# 1. Conectarse al servidor
ssh -i C:\Users\idgle\.ssh\postulamatic_win_ed25519 deploy@178.156.188.95

# 2. Una vez conectado, ejecutar estos comandos:
cd /home/deploy/apps/postulamatic
sudo systemctl start docker
docker compose down
docker compose up -d
sleep 15
docker compose ps
curl -I http://localhost:8000
```

### O en una sola línea (desde tu máquina):

```powershell
ssh -i C:\Users\idgle\.ssh\postulamatic_win_ed25519 deploy@178.156.188.95 "cd /home/deploy/apps/postulamatic && sudo systemctl start docker && docker compose down && docker compose up -d && sleep 15 && docker compose ps && curl -I http://localhost:8000"
```

## 📋 Explicación de los Comandos

1. **`sudo systemctl start docker`** - Asegura que Docker esté corriendo
2. **`docker compose down`** - Detiene todos los contenedores
3. **`docker compose up -d`** - Inicia todos los contenedores en background
4. **`sleep 15`** - Espera a que los contenedores se inicien
5. **`docker compose ps`** - Muestra el estado de los contenedores
6. **`curl -I http://localhost:8000`** - Verifica que Django responda

## ✅ Verificación Final

Después de ejecutar los comandos, verifica:

```bash
# Ver que todo está corriendo
docker compose ps

# Ver logs por si hay errores
docker compose logs postulamatic_web --tail=20

# Verificar que el sitio funciona
curl -I https://postulamatic.app
```

## 🚨 Si Aún No Funciona

### Verificar Nginx:

```bash
# Ver si Nginx está corriendo
docker ps | grep nginx

# Si no está, puede que necesites iniciarlo manualmente
# (depende de tu configuración)
```

### Ver Logs de Errores:

```bash
# Ver todos los logs
docker compose logs

# Ver solo errores
docker compose logs | grep -i error
```

