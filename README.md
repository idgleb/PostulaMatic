# README — Arquitectura actual del servidor

## Estado
Servidor en producción con HTTPS para postulamatic.app y jetinno.store. Renovación automática de certificados activa.

---

## 1) Acceso al servidor
- **Host (IPv4):** 178.156.188.95
- **Host (IPv6):** 2a01:4ff:f0:fc33::1
- **Usuario SSH:** deploy (sin sudo por defecto; usar sudo cuando aplique)
- **Autenticación:** clave pública (ejemplo: ~/.ssh/postulamatic_win_ed25519.pub añadida a /home/deploy/.ssh/authorized_keys)
- **Ruta de la app:** /home/deploy/apps/postulamatic

⚠️ Nunca commitear claves ni SECRET_KEY. Variables sensibles van en ~/apps/postulamatic/.env.

---

## 2) Dominios y DNS
- **postulamatic.app** → A/AAAA apuntan al servidor (ver arriba)
- **www.postulamatic.app** → CNAME/A/AAAA al mismo destino
- **jetinno.store** y **www.jetinno.store** → igual

Comprobación rápida desde el server:
```
getent hosts postulamatic.app
getent hosts www.postulamatic.app
```

---

## 3) Contenedores Docker & redes
### Red lógica
- Red externa: `web` (bridge). Nginx reverse proxy y servicios web se conectan aquí.

### Servicios principales
#### A) Nginx Reverse Proxy (fuera de compose)
- **Nombre contenedor:** nginx-proxy
- **Imagen:** nginx:alpine
- **Puertos publicados:** 80:80 y 443:443
- **Red:** web
- **Montajes:**
  - ~/conf.d → /etc/nginx/conf.d (vhosts estáticos)
  - ~/certbot → /var/www/certbot (webroot de ACME)
  - ~/letsencrypt_host/letsencrypt → /etc/letsencrypt (certificados)
- **Comandos útiles:**
  - `docker ps --format "table {{.Names}}\t{{.Ports}}"`
  - `docker logs --tail=100 nginx-proxy`
  - `docker exec -it nginx-proxy nginx -t && docker exec -it nginx-proxy nginx -s reload`

#### B) PostulaMatic (Django + Gunicorn)
- **Ruta del proyecto:** ~/apps/postulamatic
- **Compose:** docker-compose.yml
- **Servicio:** postulamatic_web
- **Construcción:** `docker compose build`
- **Migraciones:** `docker compose run --rm postulamatic_web python manage.py migrate`
- **Arranque:** `docker compose up -d`
- **Exposición:** no publica puertos; escucha en 8000/tcp dentro de la red web
- **Nombre del contenedor:** postulamatic-postulamatic_web-1
- **Dockerfile:**
  - Base python:3.12-slim
  - requirements.txt → pip install
  - CMD gunicorn en 0.0.0.0:8000
  - collectstatic corre en build

#### C) Jetinno (PHP/Nginx)
- **Contenedor:** jetinno-web-1 (red jetinno_default)
- **Proxy upstream:** proxy_pass http://jetinno-web-1:80;

---

## 4) Nginx (vhosts)
- **Ruta en host:** ~/conf.d/*.conf
- **postulamatic.conf:**
  - HTTP (80): deja abierto /.well-known/acme-challenge/ al webroot /var/www/certbot. El resto redirige a HTTPS.
  - HTTPS (443):
    - ssl_certificate /etc/letsencrypt/live/postulamatic.app/fullchain.pem
    - ssl_certificate_key /etc/letsencrypt/live/postulamatic.app/privkey.pem
    - add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    - proxy_pass http://postulamatic_web:8000;
    - http2 on;
- **default.conf (Jetinno):** estructura equivalente, upstream a jetinno-web-1:80, certs propios, http2 on.
- **Validación & reload:**
  - `docker exec -it nginx-proxy nginx -t && docker exec -it nginx-proxy nginx -s reload`

---

## 5) HTTPS & Certificados (Let’s Encrypt)
- **Ubicación (host):** ~/letsencrypt_host/letsencrypt
- **Webroot ACME:** ~/certbot/.well-known/acme-challenge/
- **Prueba rápida:**
  ```sh
  echo ok > ~/certbot/.well-known/acme-challenge/test
  curl -I http://postulamatic.app/.well-known/acme-challenge/test
  ```
- **Emisión/renovación:** vía webroot
- **Dry-run renovación:**
  ```sh
  $HOME/bin/renew_postulamatic.sh --dry-run --no-random-sleep-on-renew -v
  ```
- **Script renovación:** ~/bin/renew_postulamatic.sh
- **Cron:**
  - `17 3 * * * $HOME/bin/renew_postulamatic.sh >> $HOME/renew_postulamatic.log 2>&1`
- **Logs:**
  - `tail -n 200 ~/renew_postulamatic.log`
- **Verificar vigencia cert:**
  ```sh
  docker exec nginx-proxy cat /etc/letsencrypt/live/postulamatic.app/fullchain.pem > /tmp/fullchain_postu.pem
  openssl x509 -in /tmp/fullchain_postu.pem -noout -issuer -subject -dates
  ```

---

## 6) Despliegue de la app (PostulaMatic)
- Subir cambios al server (git pull o scp)
- Reconstruir y migrar:
  ```sh
  cd ~/apps/postulamatic
  docker compose build
  docker compose run --rm postulamatic_web python manage.py migrate
  docker compose up -d
  ```
- Reload Nginx si modificaste vhosts:
  ```sh
  docker exec -it nginx-proxy nginx -t && docker exec -it nginx-proxy nginx -s reload
  ```

---

## 7) Comprobaciones rápidas
- **Salud de contenedores:**
  - `docker ps --format "table {{.Names}}\t{{.Networks}}\t{{.Status}}\t{{.Ports}}"`
- **PostulaMatic responde por HTTPS:**
  - `curl -I https://postulamatic.app | sed -n '1,5p'`
- **HSTS activo:**
  - `curl -sI https://postulamatic.app | sed -n '1p;/Strict-Transport-Security/p'`
- **Webroot ACME (HTTP):**
  - `echo ok > ~/certbot/.well-known/acme-challenge/test`
  - `curl -I http://postulamatic.app/.well-known/acme-challenge/test`

---

## 8) Rutas importantes (host)
- Proyecto Django: /home/deploy/apps/postulamatic
- Compose: /home/deploy/apps/postulamatic/docker-compose.yml
- Nginx vhosts: /home/deploy/conf.d/*.conf
- Certs LE: /home/deploy/letsencrypt_host/letsencrypt
- Webroot ACME: /home/deploy/certbot/.well-known/acme-challenge
- Script renovación: /home/deploy/bin/renew_postulamatic.sh
- Cron log: /home/deploy/renew_postulamatic.log

---

## 9) Política de cambios / seguridad
- No guardar secretos en git. Usar ~/apps/postulamatic/.env.
- Validar y recargar Nginx tras cambios en conf.
- Mantener /.well-known/acme-challenge/ sin redirección a HTTPS en los bloques de HTTP:80 de todos los vhosts.

