# 🚀 Scraper Stealth - Guía Rápida

## ✅ ¿Qué se implementó?

Se creó un **scraper stealth** usando `undetected-chromedriver` que:
- ✅ Bypasea Cloudflare Turnstile automáticamente
- ✅ Simula comportamiento humano
- ✅ Scrapea ofertas de DV Carreras
- ✅ Funciona en contenedores Docker
- ✅ Se integra con Celery para automatización

---

## 🐳 Ejecutar en Docker

### **Paso 1: Reconstruir contenedores**

```bash
# Detener contenedores
docker-compose down

# Reconstruir con Chrome instalado
docker-compose build

# Iniciar contenedores
docker-compose up -d
```

### **Paso 2: Probar el scraper**

#### **Opción A: Script automatizado (Recomendado)**

```bash
# Linux/Mac
bash scripts/test_stealth_docker.sh

# Windows PowerShell
.\scripts\test_stealth_docker.ps1
```

#### **Opción B: Comando manual**

```bash
# Entrar al contenedor worker
docker exec -it postulamatic-worker-1 bash

# Ejecutar el comando de prueba
python manage.py test_stealth_scraper --user-id=2 --headless

# Salir
exit
```

---

## 📋 Ejecutar desde Celery

### **Opción 1: Tarea manual**

```bash
docker exec -it postulamatic-worker-1 python manage.py shell
```

```python
from matching.tasks_stealth import scrape_dvcarreras_jobs_stealth

# Ejecutar scraping para usuario ID 2
result = scrape_dvcarreras_jobs_stealth.delay(2)

# Ver resultado
print(result.get())
# Output: {'success': True, 'new_jobs': 9, 'saved_jobs': 9, 'total_found': 9, 'user_id': 2}
```

### **Opción 2: Tarea programada**

Agregar en `core/celery.py` o `postulamatic/celery.py`:

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    # Scrapear ofertas todos los días a las 8:00 AM
    'scrape-stealth-daily': {
        'task': 'matching.tasks_stealth.scrape_dvcarreras_jobs_stealth',
        'schedule': crontab(hour=8, minute=0),
        'args': (2,),  # user_id
    },
}
```

Luego reiniciar el beat:

```bash
docker-compose restart beat
```

---

## 🔍 Verificar resultados

### **Ver ofertas scrapeadas**

```bash
docker exec -it postulamatic-worker-1 python manage.py shell
```

```python
from matching.models import JobPosting

# Contar ofertas del scraper stealth
count = JobPosting.objects.filter(source='dvcarreras_stealth').count()
print(f"Ofertas encontradas: {count}")

# Ver última oferta
latest = JobPosting.objects.filter(source='dvcarreras_stealth').latest('created_at')
print(f"Título: {latest.title}")
print(f"Empresa: {latest.company}")
print(f"Fecha: {latest.created_at}")
```

### **Ver logs de scraping**

```bash
# Logs del contenedor
docker logs postulamatic-worker-1 --tail 100 | grep DVCarrerasStealth

# Logs en base de datos
docker exec -it postulamatic-worker-1 python manage.py shell
```

```python
from matching.models import ScrapingLog

# Ver últimos 10 logs
logs = ScrapingLog.objects.filter(task_id='stealth_scraper').order_by('-timestamp')[:10]
for log in logs:
    print(f"{log.timestamp} - {log.log_type}: {log.message}")
```

---

## 🎯 Archivos importantes

### **Cliente Stealth**
- `matching/clients/dvcarreras_stealth.py` - Scraper con undetected-chromedriver

### **Tareas Celery**
- `matching/tasks_stealth.py` - Tareas asíncronas para automatización

### **Comandos Django**
- `matching/management/commands/test_stealth_scraper.py` - Comando de prueba

### **Docker**
- `Dockerfile` - Imagen con Chrome instalado
- `requirements.txt` - Dependencias (undetected-chromedriver, selenium)

### **Documentación**
- `docs/STEALTH_SCRAPER_DOCKER.md` - Guía completa
- `SOLUCION_CLOUDFLARE_TURNSTILE.md` - Documentación del problema

---

## 🛠️ Troubleshooting

### **Error: Chrome not found**

```bash
# Verificar instalación
docker exec postulamatic-worker-1 google-chrome --version

# Si no está instalado, reconstruir
docker-compose build worker
docker-compose up -d worker
```

### **Error: Cloudflare Turnstile persiste**

El scraper stealth generalmente resuelve Turnstile automáticamente. Si persiste:

1. Verificar que esté usando `headless=True`
2. Revisar logs: `docker logs postulamatic-worker-1 --tail 50`
3. Verificar sesiones guardadas: `ls -la media/sessions/`

### **Error: ModuleNotFoundError**

```bash
# Reinstalar dependencias
docker exec postulamatic-worker-1 pip install -r requirements.txt
```

---

## 📊 Estadísticas de prueba

En la última prueba exitosa:

- ✅ **Login exitoso** sin intervención manual
- ✅ **9 ofertas encontradas** y guardadas
- ✅ **Emails extraídos** correctamente
- ✅ **Sesión guardada** para reutilización
- ⏱️ **Tiempo total**: ~30-45 segundos

---

## 🔐 Seguridad

- ✅ Credenciales **encriptadas** en base de datos
- ✅ **No se loggean** credenciales sensibles
- ✅ Sesiones **expiran** después de 24 horas
- ✅ User-Agent **aleatorio** para evitar detección

---

## 🎉 Próximos pasos

1. **Configurar tarea periódica** en Celery Beat
2. **Agregar rotación de proxies** (opcional)
3. **Integrar con sistema de matching** para envío automático
4. **Configurar notificaciones** cuando encuentre nuevas ofertas
5. **Agregar dashboard** de monitoreo

---

## 📚 Referencias

- Documentación completa: `docs/STEALTH_SCRAPER_DOCKER.md`
- Problema original: `SOLUCION_CLOUDFLARE_TURNSTILE.md`
- GitHub: [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver)

---

**¿Preguntas?** Revisa la documentación completa en `docs/STEALTH_SCRAPER_DOCKER.md`

