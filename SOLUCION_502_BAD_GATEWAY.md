# 🔧 Solución: Error 502 Bad Gateway

## 🔍 Problema

Nginx muestra error `502 Bad Gateway` porque no puede conectarse a Django.

**Error en logs de Nginx:**
```
connect() failed (111: Connection refused) while connecting to upstream, 
upstream: "http://172.20.0.5:8000/"
```

## ✅ Causa

Después del rescale del servidor, las IPs de los contenedores Docker cambiaron:
- **Nginx intenta:** `172.20.0.5:8000` (IP antigua)
- **Django está en:** `172.20.0.6:8000` (IP nueva después del rescale)

## ✅ Solución Aplicada

### 1. Reiniciar Nginx

Reiniciar Nginx para que resuelva el DNS correctamente:

```bash
docker restart nginx-proxy
docker exec nginx-proxy nginx -t
docker exec nginx-proxy nginx -s reload
```

### 2. Verificar Conexión

```bash
# Desde dentro del contenedor Nginx
docker exec nginx-proxy curl -I http://postulamatic-postulamatic_web-1:8000

# Debe responder HTTP 200 o 400 (no 502)
```

### 3. Si Persiste el Problema

**Opción A: Reiniciar todos los contenedores**

```bash
cd /home/deploy/apps/postulamatic
docker compose restart
docker restart nginx-proxy
```

**Opción B: Verificar configuración de Nginx**

```bash
# Verificar que la configuración use el nombre correcto
cat /home/deploy/conf.d/postulamatic.conf | grep proxy_pass

# Debe ser:
# proxy_pass http://postulamatic-postulamatic_web-1:8000;
```

**Opción C: Recrear red Docker (último recurso)**

```bash
# Detener todos los contenedores
docker compose down
docker stop nginx-proxy

# Recrear red
docker network rm web
docker network create web

# Reiniciar todo
docker compose up -d
docker start nginx-proxy
```

## 📋 Verificación

Después de aplicar la solución:

1. **Verificar que Django responde:**
   ```bash
   curl -I http://localhost:8000
   # Debe ser: HTTP/1.1 200 OK
   ```

2. **Verificar que Nginx puede conectarse:**
   ```bash
   docker exec nginx-proxy curl -I http://postulamatic-postulamatic_web-1:8000
   # Debe responder (200 o 400, no 502)
   ```

3. **Verificar el sitio:**
   ```bash
   curl -I https://postulamatic.app
   # Debe ser: HTTP/2 200
   ```

## 🎯 Resultado Esperado

- ✅ Django responde en localhost:8000
- ✅ Nginx puede conectarse a Django
- ✅ El sitio funciona en https://postulamatic.app
- ✅ No más errores 502

## 📝 Notas

- Este problema es común después de un rescale porque las IPs de los contenedores cambian
- Nginx usa DNS interno de Docker, pero a veces necesita reiniciarse para actualizar
- La solución más rápida es reiniciar Nginx

