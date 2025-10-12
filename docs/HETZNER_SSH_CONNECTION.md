# Conexión SSH a Servidor Hetzner - PostulaMatic

## 📋 Información del Servidor

### Datos de Conexión
- **Host (IPv4):** `178.156.188.95`
- **Host (IPv6):** `2a01:4ff:f0:fc33::1`
- **Usuario SSH:** `deploy` (NO usar `root`)
- **Puerto SSH:** `22` (por defecto)
- **Clave SSH:** `~/.ssh/postulamatic_win_ed25519`

### Comandos de Conexión

#### Conexión Interactiva
```bash
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95
```

#### Ejecutar Comando Específico (sin conexión interactiva)
```bash
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "comando_aqui"
```

#### Ejemplos de Comandos Útiles
```bash
# Ver archivos en /media
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "ls -la /home/deploy/apps/postulamatic/media/"

# Ver estado de contenedores Docker
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "docker ps"

# Ver logs de la aplicación
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "docker logs postulamatic-postulamatic_web-1"

# Reiniciar la aplicación
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "cd /home/deploy/apps/postulamatic && docker compose restart"
```

## 🗂️ Rutas Importantes en el Servidor

### Aplicación PostulaMatic
- **Proyecto:** `/home/deploy/apps/postulamatic`
- **Media files:** `/home/deploy/apps/postulamatic/media/`
- **Base de datos:** `/home/deploy/apps/postulamatic/db.sqlite3`
- **Logs:** `/home/deploy/apps/postulamatic/logs/`

### Configuración Nginx
- **VHosts:** `/home/deploy/conf.d/`
- **Certificados:** `/home/deploy/letsencrypt_host/letsencrypt/`
- **Webroot ACME:** `/home/deploy/certbot/`

### Docker
- **Compose file:** `/home/deploy/apps/postulamatic/docker-compose.yml`
- **Contenedor principal:** `postulamatic-postulamatic_web-1`
- **Red:** `postulamatic_default`

## 🔧 Comandos de Mantenimiento

### Gestión de Archivos Media
```bash
# Ver tamaño de archivos media
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "du -sh /home/deploy/apps/postulamatic/media/"

# Eliminar archivos media específicos
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "rm -rf /home/deploy/apps/postulamatic/media/cvs/2025/10/12/"

# Eliminar TODOS los archivos media (¡CUIDADO!)
# NOTA: Los archivos pueden tener permisos de root, usar contenedor temporal:
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "cd /home/deploy/apps/postulamatic && docker run --rm -v /home/deploy/apps/postulamatic:/app --user root ubuntu:latest bash -c 'chmod -R 777 /app/media && rm -rf /app/media/cvs/*'"

# Verificar que los archivos fueron eliminados
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "find /home/deploy/apps/postulamatic/media/ -type f | wc -l"
```

### Gestión de Docker
```bash
# Ver estado de contenedores
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

# Reiniciar aplicación
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "cd /home/deploy/apps/postulamatic && docker compose up -d"

# Ver logs en tiempo real
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "docker logs -f postulamatic-postulamatic_web-1"

# Reconstruir aplicación
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "cd /home/deploy/apps/postulamatic && docker compose build && docker compose up -d"
```

### Base de Datos
```bash
# Hacer backup de la base de datos
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "cp /home/deploy/apps/postulamatic/db.sqlite3 /home/deploy/apps/postulamatic/db_backup_$(date +%Y%m%d_%H%M%S).sqlite3"

# Aplicar migraciones
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95 "cd /home/deploy/apps/postulamatic && docker compose run --rm postulamatic_web python manage.py migrate"
```

## ⚠️ Notas de Seguridad

1. **NUNCA** usar `root` como usuario SSH
2. **SIEMPRE** usar la clave `postulamatic_win_ed25519`
3. **CUIDADO** con comandos `rm -rf` - pueden eliminar datos irreversibles
4. **BACKUP** antes de operaciones críticas
5. **VERIFICAR** rutas antes de ejecutar comandos destructivos

## 🚨 Solución de Problemas

### Error: "Permission denied (publickey)"
- Verificar que la clave existe: `ls -la ~/.ssh/postulamatic_win_ed25519`
- Verificar permisos: `chmod 600 ~/.ssh/postulamatic_win_ed25519`

### Error: "Connection timed out"
- Verificar conectividad: `ping 178.156.188.95`
- Verificar que el servidor esté activo

### Error: "Host key verification failed"
- Eliminar clave del host: `ssh-keygen -R 178.156.188.95`
- Reconectar y aceptar la nueva clave

## 📞 Contacto y Soporte

- **Servidor:** Hetzner Cloud
- **Proyecto:** PostulaMatic
- **Dominio:** postulamatic.app
- **Documentación:** Ver `README.md` para detalles completos del sistema
