# Comandos SSH para el Servidor

## Información de Conexión

- **Servidor**: `178.156.188.95`
- **Usuario deploy**: `deploy`
- **Usuario root**: `root`
- **Claves SSH**:
  - `~/.ssh/postulamatic_win_ed25519` (recomendada)
  - `~/.ssh/jetinnohetzner_ed25519`
  - `~/.ssh/jetinnohetzner_ed25519` (root)

## Comandos de Conexión

### Conectar como deploy (recomendado)
```bash
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95
```

### Conectar como root
```bash
ssh -i ~/.ssh/jetinnohetzner_ed25519 root@178.156.188.95
```

## Scripts Disponibles

### 1. Verificar Scraping Activo

**Linux/Mac:**
```bash
bash scripts/verificar_scraping_remoto.sh
```

**Windows (PowerShell):**
```powershell
.\scripts\verificar_scraping_remoto.ps1
```

**Con parámetros personalizados:**
```bash
bash scripts/verificar_scraping_remoto.sh ~/.ssh/postulamatic_win_ed25519 deploy 178.156.188.95
```

### 2. Liberar Lock Huérfano

**Linux/Mac:**
```bash
bash scripts/liberar_lock_remoto.sh
```

**Windows (PowerShell):**
```powershell
.\scripts\liberar_lock_remoto.ps1
```

## Comandos Manuales (una vez conectado)

### Verificar scraping activo
```bash
cd /home/deploy/postulamatic
docker exec postulamatic-postulamatic_web-1 python manage.py check_active_scraping
```

### Liberar lock huérfano
```bash
cd /home/deploy/postulamatic
docker exec postulamatic-postulamatic_web-1 python manage.py check_scraping_lock --force-release
```

### Ver logs de Django
```bash
docker logs postulamatic-postulamatic_web-1 --tail 100
```

### Ver logs relacionados con scraping
```bash
docker logs postulamatic-postulamatic_web-1 --tail 500 | grep -i "scraping\|scrape_dvcarreras"
```

### Reiniciar contenedores
```bash
cd /home/deploy/postulamatic
docker-compose restart
```

### Ver estado de contenedores
```bash
docker ps
```

### Ver logs en tiempo real
```bash
docker logs -f postulamatic-postulamatic_web-1
```

## Troubleshooting

### Error de conexión SSH
- Verifica que la clave SSH tenga permisos correctos: `chmod 600 ~/.ssh/postulamatic_win_ed25519`
- Verifica que la clave esté en la ruta correcta
- Prueba con otra clave SSH si la primera no funciona

### Error "Permission denied"
- Asegúrate de usar el usuario correcto (`deploy` o `root`)
- Verifica que la clave SSH esté autorizada en el servidor

### No se encuentra el contenedor
- Verifica que los contenedores estén corriendo: `docker ps`
- Verifica el nombre exacto del contenedor: `docker ps | grep postulamatic`

