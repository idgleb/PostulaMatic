# 🚀 Scraper Stealth en Docker - Guía Completa

## 📋 Resumen

El **Scraper Stealth** usa `undetected-chromedriver` para bypasear Cloudflare Turnstile y scrapear ofertas de DV Carreras de manera automatizada en contenedores Docker.

## 🎯 Características

✅ **Anti-detección avanzada** con `undetected-chromedriver`  
✅ **Bypaseo automático** de Cloudflare Turnstile  
✅ **Comportamiento humano simulado** (delays, movimientos, etc.)  
✅ **Gestión de sesiones** para reutilización de cookies  
✅ **Logging completo** con persistencia en base de datos  
✅ **Integración con Celery** para automatización  

---

## 🐳 Configuración en Docker

### 1. **Archivos actualizados**

Los siguientes archivos ya están configurados para ejecutar el scraper stealth en Docker:

#### `requirements.txt`
```txt
undetected-chromedriver
selenium
```

#### `Dockerfile`
- Instala Google Chrome y todas las dependencias necesarias
- Configura el entorno para ejecutar navegadores headless

---

## 📦 Despliegue

### 1. **Reconstruir contenedores**

Después de actualizar el `Dockerfile` y `requirements.txt`:

```bash
# Detener contenedores actuales
docker-compose down

# Reconstruir las imágenes
docker-compose build

# Iniciar contenedores
docker-compose up -d
```

### 2. **Verificar que Chrome esté instalado**

```bash
# Entrar al contenedor worker
docker exec -it postulamatic-worker-1 bash

# Verificar instalación de Chrome
google-chrome --version

# Salir del contenedor
exit
```

---

## 🎮 Uso del Scraper Stealth

### **Opción 1: Ejecutar desde Django Admin**

1. Ir al Admin de Django: `http://postulamatic.app/admin/`
2. Buscar el modelo **User Profile**
3. Seleccionar un usuario con credenciales DV configuradas
4. En la sección de acciones, seleccionar **"Scrapear con Stealth"**

### **Opción 2: Ejecutar desde Celery (Recomendado)**

```bash
# Entrar al contenedor worker
docker exec -it postulamatic-worker-1 bash

# Ejecutar scraping para un usuario específico
python manage.py shell
>>> from matching.tasks_stealth import scrape_dvcarreras_jobs_stealth
>>> result = scrape_dvcarreras_jobs_stealth.delay(user_id=2)
>>> result.get()
```

### **Opción 3: Ejecutar comando Django**

```bash
# Entrar al contenedor worker
docker exec -it postulamatic-worker-1 bash

# Ejecutar comando de prueba
python manage.py test_stealth_scraper --user-id=2 --headless
```

### **Opción 4: Programar tarea periódica**

Agregar tarea periódica en `matching/celery.py`:

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    'scrape-stealth-daily': {
        'task': 'matching.tasks_stealth.scrape_dvcarreras_jobs_stealth',
        'schedule': crontab(hour=8, minute=0),  # Cada día a las 8:00 AM
        'args': (2,),  # user_id
    },
}
```

---

## 🔧 Configuración avanzada

### **Variables de entorno**

Agregar en `.env`:

```env
# Scraper Stealth
STEALTH_HEADLESS=true
STEALTH_MAX_RETRIES=3
STEALTH_TIMEOUT=60
STEALTH_USER_AGENTS="Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."
```

### **Logs y debugging**

Los logs del scraper stealth se guardan en:

1. **Base de datos**: Tabla `ScrapingLog`
2. **Archivos**: `media/debug/scraper_html/`
3. **Logs de Docker**:

```bash
# Ver logs del worker
docker logs postulamatic-worker-1 --tail 100 -f

# Filtrar logs del scraper stealth
docker logs postulamatic-worker-1 2>&1 | grep "DVCarrerasStealth"
```

---

## 📊 Monitoreo

### **Ver ofertas scrapeadas**

```bash
docker exec -it postulamatic-worker-1 python manage.py shell
>>> from matching.models import JobPosting
>>> JobPosting.objects.filter(source='dvcarreras_stealth').count()
>>> JobPosting.objects.filter(source='dvcarreras_stealth').latest('created_at')
```

### **Ver logs de scraping**

```bash
docker exec -it postulamatic-worker-1 python manage.py shell
>>> from matching.models import ScrapingLog
>>> logs = ScrapingLog.objects.filter(task_id='stealth_scraper').order_by('-timestamp')[:10]
>>> for log in logs:
>>>     print(f"{log.timestamp} - {log.log_type}: {log.message}")
```

---

## 🛠️ Troubleshooting

### **Error: Chrome no encontrado**

```bash
# Reconstruir imagen con Chrome
docker-compose build worker
docker-compose up -d worker
```

### **Error: Timeout durante scraping**

Aumentar timeout en `matching/clients/dvcarreras_stealth.py`:

```python
WebDriverWait(self.driver, 30)  # Aumentar de 10 a 30 segundos
```

### **Error: Cloudflare Turnstile no se resuelve**

El scraper stealth generalmente resuelve Turnstile automáticamente. Si persiste:

1. Verificar User-Agent
2. Aumentar delays entre acciones
3. Rotar proxies (próxima implementación)

### **Error: Sesión expirada**

Las sesiones expiran después de 24 horas. Para limpiar:

```bash
# Eliminar sesiones antiguas
rm -rf media/sessions/user_*_stealth_session.json
```

---

## 🔐 Seguridad

### **Permisos necesarios**

El contenedor worker necesita:
- Acceso a `/dev/shm` para Chrome
- Permisos para escribir en `media/sessions/`
- Permisos para escribir en `media/debug/`

### **Credenciales**

Las credenciales DV están:
- ✅ **Encriptadas en base de datos**
- ✅ **No loggeadas**
- ✅ **Solo accesibles por el usuario propietario**

---

## 📈 Performance

### **Recursos recomendados**

Para ejecutar el scraper stealth en producción:

- **CPU**: 2 cores mínimo
- **RAM**: 2GB mínimo (4GB recomendado)
- **Disco**: 1GB para Chrome + dependencias

### **Optimizaciones**

1. **Headless mode**: Reduce uso de CPU/RAM
2. **Disable images**: Acelera carga de páginas
3. **Sesiones reutilizables**: Evita logins repetidos
4. **Rate limiting**: Previene bans

---

## 🔄 Integración con sistema existente

### **Flujo completo**

1. **Usuario configura credenciales DV** en perfil
2. **Celery ejecuta tarea periódica** `scrape_dvcarreras_jobs_stealth`
3. **Scraper stealth**:
   - Inicia Chrome con anti-detección
   - Hace login (o carga sesión guardada)
   - Scrapea ofertas del tablero
   - Guarda ofertas en base de datos
4. **Sistema de matching**:
   - Calcula match % contra CV del usuario
   - Si supera umbral, genera email personalizado
   - Envía email desde cuenta SMTP del usuario
5. **Dashboard** muestra estadísticas y ofertas

---

## 📚 Referencias

- [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
- [Selenium WebDriver](https://www.selenium.dev/documentation/)
- [Cloudflare Turnstile](https://developers.cloudflare.com/turnstile/)
- [Docker Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)

---

## 🎯 Próximas mejoras

- [ ] Rotación de proxies
- [ ] Captcha solving avanzado
- [ ] Scraping de múltiples páginas
- [ ] Notificaciones en tiempo real
- [ ] Dashboard de monitoreo
- [ ] Rate limiting inteligente
- [ ] Retry con backoff exponencial

---

**Autor**: PostulaMatic Team  
**Última actualización**: Octubre 2025  
**Versión**: 1.0.0

