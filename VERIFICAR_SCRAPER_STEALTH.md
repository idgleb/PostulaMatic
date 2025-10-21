# ✅ Cómo Verificar que el Scraper Stealth Funciona

## 🎯 Métodos de Verificación

### **Método 1: Script de Verificación Automática (Recomendado)**

Este script verifica TODO automáticamente:

```bash
# Linux/Mac
bash scripts/verify_stealth_status.sh

# Windows PowerShell
.\scripts\verify_stealth_status.ps1
```

**Verifica:**
- ✅ Contenedores corriendo (worker, web, redis)
- ✅ Chrome instalado
- ✅ Dependencias Python (undetected-chromedriver, selenium)
- ✅ Archivos del scraper presentes
- ✅ Ofertas en base de datos
- ✅ Logs de scraping
- ✅ Tareas Celery registradas

---

### **Método 2: Verificación Manual Paso a Paso**

#### **1️⃣ Verificar que Docker esté corriendo**

```bash
docker ps
```

**Debes ver:**
```
CONTAINER ID   IMAGE                    STATUS
xxxxx          postulamatic-worker      Up
xxxxx          postulamatic-web         Up
xxxxx          redis                    Up
```

---

#### **2️⃣ Verificar Chrome en el contenedor**

```bash
docker exec postulamatic-worker-1 google-chrome --version
```

**Respuesta esperada:**
```
Google Chrome 131.x.x.x
```

❌ **Si dice "command not found":**
```bash
docker-compose build worker
docker-compose up -d worker
```

---

#### **3️⃣ Verificar dependencias Python**

```bash
docker exec postulamatic-worker-1 python -c "import undetected_chromedriver; print('✅ OK')"
docker exec postulamatic-worker-1 python -c "import selenium; print('✅ OK')"
```

**Respuesta esperada:** `✅ OK` en ambos casos

---

#### **4️⃣ Probar el scraper**

```bash
# Forma 1: Script automatizado
bash scripts/test_stealth_docker.sh

# Forma 2: Comando directo
docker exec -it postulamatic-worker-1 python manage.py test_stealth_scraper --user-id=2 --headless
```

**Resultado esperado:**
```
Iniciando navegador...
Navegador iniciado correctamente
Realizando login...
Login exitoso
Scrapeando ofertas...
Scraping completado: 9 ofertas encontradas

--- Oferta 1 ---
Título: EDITOR semi sr.
Email: rrhh@basquetpass.tv
...
```

---

#### **5️⃣ Verificar ofertas en base de datos**

```bash
docker exec -it postulamatic-worker-1 python manage.py shell
```

```python
from matching.models import JobPosting

# Contar ofertas del scraper stealth
count = JobPosting.objects.filter(source='dvcarreras_stealth').count()
print(f"✅ Ofertas encontradas: {count}")

# Ver última oferta
if count > 0:
    latest = JobPosting.objects.filter(source='dvcarreras_stealth').latest('created_at')
    print(f"\n📋 Última oferta:")
    print(f"   Título: {latest.title}")
    print(f"   Empresa: {latest.company}")
    print(f"   Fecha: {latest.created_at}")
```

---

#### **6️⃣ Verificar logs de scraping**

```bash
# Ver logs del contenedor
docker logs postulamatic-worker-1 --tail 50 | grep DVCarrerasStealth

# Ver logs en base de datos
docker exec -it postulamatic-worker-1 python manage.py shell
```

```python
from matching.models import ScrapingLog

# Ver últimos 5 logs
logs = ScrapingLog.objects.filter(task_id='stealth_scraper').order_by('-timestamp')[:5]
for log in logs:
    print(f"{log.timestamp} - {log.log_type}: {log.message}")
```

---

#### **7️⃣ Verificar sesiones guardadas**

```bash
# Ver sesiones guardadas
docker exec postulamatic-worker-1 ls -lh media/sessions/

# Ver contenido de una sesión
docker exec postulamatic-worker-1 cat media/sessions/user_2_stealth_session.json
```

**Debe mostrar:**
```json
{
  "cookies": [...],
  "timestamp": "2025-10-19T...",
  "user_agent": "Mozilla/5.0..."
}
```

---

#### **8️⃣ Ejecutar desde Celery**

```bash
docker exec -it postulamatic-worker-1 python manage.py shell
```

```python
from matching.tasks_stealth import scrape_dvcarreras_jobs_stealth

# Ejecutar tarea
result = scrape_dvcarreras_jobs_stealth.delay(2)  # user_id=2

# Ver resultado (espera hasta que termine)
print(result.get())
```

**Resultado esperado:**
```python
{
    'success': True,
    'new_jobs': 9,
    'saved_jobs': 9,
    'total_found': 9,
    'user_id': 2
}
```

---

## 📊 **Dashboard de Verificación**

### **Ver estadísticas completas**

```bash
docker exec -it postulamatic-worker-1 python manage.py shell
```

```python
from matching.models import JobPosting, ScrapingLog, UserProfile
from django.contrib.auth.models import User

# Estadísticas generales
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("📊 ESTADÍSTICAS DEL SCRAPER STEALTH")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

# Ofertas
total_jobs = JobPosting.objects.filter(source='dvcarreras_stealth').count()
print(f"\n✅ Total ofertas: {total_jobs}")

if total_jobs > 0:
    latest = JobPosting.objects.filter(source='dvcarreras_stealth').latest('created_at')
    print(f"   Última: {latest.title[:50]}...")
    print(f"   Fecha: {latest.created_at}")

# Logs
total_logs = ScrapingLog.objects.filter(task_id='stealth_scraper').count()
print(f"\n📝 Total logs: {total_logs}")

if total_logs > 0:
    success_logs = ScrapingLog.objects.filter(
        task_id='stealth_scraper', 
        log_type='success'
    ).count()
    error_logs = ScrapingLog.objects.filter(
        task_id='stealth_scraper', 
        log_type='error'
    ).count()
    print(f"   ✅ Success: {success_logs}")
    print(f"   ❌ Errors: {error_logs}")

# Usuarios con credenciales DV
users_with_dv = UserProfile.objects.exclude(dv_username='').exclude(dv_username__isnull=True).count()
print(f"\n👥 Usuarios con credenciales DV: {users_with_dv}")

print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
```

---

## 🔍 **Logs en Tiempo Real**

### **Ver logs del worker en tiempo real:**

```bash
docker logs postulamatic-worker-1 -f
```

### **Filtrar solo logs del scraper stealth:**

```bash
# Linux/Mac
docker logs postulamatic-worker-1 -f 2>&1 | grep --color=always "DVCarrerasStealth"

# Windows PowerShell
docker logs postulamatic-worker-1 -f | Select-String "DVCarrerasStealth"
```

### **Ver logs de Celery:**

```bash
docker logs postulamatic-worker-1 -f 2>&1 | grep --color=always "scrape_dvcarreras_jobs_stealth"
```

---

## 🚨 **Troubleshooting**

### **Problema: "Chrome not found"**

```bash
# Verificar Chrome
docker exec postulamatic-worker-1 google-chrome --version

# Si falla, reconstruir imagen
docker-compose down
docker-compose build worker
docker-compose up -d
```

---

### **Problema: "ModuleNotFoundError: undetected_chromedriver"**

```bash
# Instalar dependencias
docker exec postulamatic-worker-1 pip install -r requirements.txt

# O específicamente
docker exec postulamatic-worker-1 pip install undetected-chromedriver selenium
```

---

### **Problema: "Cloudflare Turnstile persiste"**

```bash
# Ver logs detallados
docker logs postulamatic-worker-1 --tail 100

# Ver HTML guardado
docker exec postulamatic-worker-1 ls -lh media/debug/scraper_html/

# Ver último HTML
docker exec postulamatic-worker-1 cat media/debug/scraper_html/turnstile_challenge_*.html | tail -100
```

---

### **Problema: "Login fallido"**

```bash
# Verificar credenciales del usuario
docker exec -it postulamatic-worker-1 python manage.py shell
```

```python
from matching.models import UserProfile

profile = UserProfile.objects.get(user_id=2)
print(f"Username: {profile.dv_username}")
print(f"Has password: {'Yes' if profile.dv_password else 'No'}")

# Probar credenciales
print(f"Username decrypted: {profile.get_dv_username()}")
print(f"Password decrypted: {'***' if profile.get_dv_password() else 'None'}")
```

---

### **Problema: "Ofertas no se guardan"**

```bash
# Ver permisos del directorio media
docker exec postulamatic-worker-1 ls -la media/

# Ver logs de errores
docker exec -it postulamatic-worker-1 python manage.py shell
```

```python
from matching.models import ScrapingLog

# Ver errores
errors = ScrapingLog.objects.filter(
    task_id='stealth_scraper',
    log_type='error'
).order_by('-timestamp')[:5]

for error in errors:
    print(f"{error.timestamp}: {error.message}")
```

---

## ✅ **Checklist Rápido**

Marca cada item cuando lo verifiques:

- [ ] Contenedores corriendo (`docker ps`)
- [ ] Chrome instalado (`google-chrome --version`)
- [ ] Dependencias Python instaladas
- [ ] Archivos del scraper presentes
- [ ] Usuario con credenciales DV configuradas
- [ ] Scraper ejecutado exitosamente
- [ ] Ofertas guardadas en base de datos (>0)
- [ ] Logs de scraping presentes
- [ ] Sesiones guardadas en `media/sessions/`

---

## 🎯 **Comando Todo-en-Uno**

Para verificar todo de una vez:

```bash
# Linux/Mac
bash scripts/verify_stealth_status.sh && bash scripts/test_stealth_docker.sh

# Windows PowerShell
.\scripts\verify_stealth_status.ps1; .\scripts\test_stealth_docker.ps1
```

---

## 📞 **Soporte**

Si después de verificar todo aún no funciona:

1. **Revisa logs completos:**
   ```bash
   docker logs postulamatic-worker-1 --tail 200 > scraper_logs.txt
   ```

2. **Verifica la documentación:**
   - `docs/STEALTH_SCRAPER_DOCKER.md` - Guía completa
   - `STEALTH_SCRAPER_QUICKSTART.md` - Guía rápida

3. **Reconstruye todo desde cero:**
   ```bash
   docker-compose down -v
   docker-compose build --no-cache
   docker-compose up -d
   ```

---

**¡Listo!** Con estas verificaciones puedes confirmar que el scraper stealth está funcionando correctamente en Docker. 🚀

