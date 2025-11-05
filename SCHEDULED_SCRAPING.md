# 🕒 Scraping Automático Programado

## Descripción

Sistema de scraping automático que permite programar la ejecución del scraper de DV Carreras a una hora específica cada día.

## Características

- ✅ **Programación flexible**: Configura la hora exacta de ejecución (formato 24h)
- ✅ **Activación/Desactivación**: Switch para activar o desactivar sin perder la configuración
- ✅ **Rotación automática**: Usa credenciales de diferentes usuarios verificados
- ✅ **Cálculo de matches**: Calcula automáticamente matches para todos los usuarios con CVs
- ✅ **Prevención de duplicados**: Solo se ejecuta una vez por día
- ✅ **Registro de ejecuciones**: Muestra la última vez que se ejecutó

## Configuración

### 1. Acceso a la configuración

Solo los **administradores** pueden acceder a la configuración del scraping programado en:

```
http://localhost:8000/matching/probar-scraper/
```

Desplázate hasta la sección "Scraping Automático Programado".

### 2. Configurar el scraping

1. **Activar el switch**: Marca el checkbox "Activado"
2. **Establecer la hora**: Selecciona la hora deseada (formato 24h)
3. **Guardar**: Haz clic en "Guardar Configuración"

### 3. Verificar que está funcionando

- La configuración se guarda en la base de datos
- Celery Beat verifica cada minuto si debe ejecutar el scraping
- Cuando llega la hora configurada, se ejecuta automáticamente
- La "Última ejecución" se actualiza después de cada ejecución

## Arquitectura Técnica

### Componentes

1. **Modelo `ScheduledScraping`** (`matching/models.py`):
   - Almacena la configuración (hora, estado activado/desactivado, última ejecución)

2. **Tarea Celery `check_and_run_scheduled_scraping`** (`matching/tasks_stealth.py`):
   - Se ejecuta cada minuto
   - Verifica si la hora actual coincide con la hora programada
   - Previene ejecuciones duplicadas el mismo día
   - Lanza el scraping global si corresponde

3. **Tarea Periódica de Celery Beat**:
   - Configurada automáticamente con el comando `setup_scheduled_scraping`
   - Intervalo: Cada 1 minuto

4. **API REST** (`/matching/api/scheduled-scraping/`):
   - GET: Obtiene la configuración actual
   - POST: Guarda la nueva configuración

### Flujo de Ejecución

```
┌─────────────────────────────────────────────────────────┐
│  Celery Beat (cada minuto)                              │
│    ↓                                                     │
│  check_and_run_scheduled_scraping()                     │
│    ↓                                                     │
│  ¿Es la hora programada?                                │
│    ├─ No  → Termina                                     │
│    └─ Sí  → ¿Ya se ejecutó hoy?                        │
│              ├─ Sí → Termina                            │
│              └─ No  → Ejecuta scraping                  │
│                       ↓                                  │
│                  scrape_dvcarreras_jobs_stealth()       │
│                       ↓                                  │
│                  Rotación de credenciales               │
│                       ↓                                  │
│                  Extrae ofertas                         │
│                       ↓                                  │
│                  Calcula matches para todos             │
│                       ↓                                  │
│                  Actualiza last_run                     │
└─────────────────────────────────────────────────────────┘
```

## Comandos Útiles

### Configurar la tarea periódica (ya ejecutado)

```bash
docker-compose exec postulamatic_web python manage.py setup_scheduled_scraping
```

### Ver logs de Celery Beat

```bash
docker-compose logs -f beat
```

### Ver logs del Worker

```bash
docker-compose logs -f worker
```

### Reiniciar servicios

```bash
docker-compose restart beat worker postulamatic_web
```

## Troubleshooting

### El scraping no se ejecuta automáticamente

1. **Verificar que Celery Beat está corriendo**:
   ```bash
   docker-compose ps beat
   ```

2. **Verificar que la tarea periódica está configurada**:
   ```bash
   docker-compose exec postulamatic_web python manage.py shell
   >>> from django_celery_beat.models import PeriodicTask
   >>> PeriodicTask.objects.filter(name='Check and Run Scheduled Scraping').first()
   ```

3. **Verificar la configuración**:
   ```bash
   docker-compose exec postulamatic_web python manage.py shell
   >>> from matching.models import ScheduledScraping
   >>> config = ScheduledScraping.objects.first()
   >>> print(f"Enabled: {config.is_enabled}, Time: {config.scheduled_time}")
   ```

4. **Ver logs en tiempo real**:
   ```bash
   docker-compose logs -f beat worker
   ```

### El scraping se ejecuta pero falla

- Verificar que hay usuarios con credenciales **verificadas**
- Ver los logs del scraping en la página de "Probar Scraper"
- Verificar que los usuarios tienen CVs procesados para el cálculo de matches

## Notas Importantes

- ⚠️ Solo se ejecuta **una vez por día** a la hora configurada
- ⚠️ Requiere al menos **un usuario con credenciales verificadas**
- ⚠️ La hora se interpreta en la **zona horaria del servidor** (configurada en `settings.py`)
- ⚠️ Si el servidor está apagado a la hora programada, el scraping **no se ejecutará** hasta el día siguiente

## Ejemplo de Uso

**Escenario**: Quieres que el scraper se ejecute todos los días a las 9:00 AM

1. Ve a `http://localhost:8000/matching/probar-scraper/`
2. Activa el switch "Activado"
3. Establece la hora: `09:00`
4. Haz clic en "Guardar Configuración"
5. ✅ A partir de mañana a las 9:00 AM, el scraper se ejecutará automáticamente

## Zona Horaria

La hora configurada se interpreta según la zona horaria del servidor. Para verificar o cambiar la zona horaria:

```python
# core/settings.py
TIME_ZONE = 'America/Argentina/Buenos_Aires'  # Ajustar según necesidad
USE_TZ = True
```

