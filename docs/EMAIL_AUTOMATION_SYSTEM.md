# 📧 Sistema de Envío Automático de Emails - PostulaMatic

## 📋 Resumen

El Sistema de Envío Automático de Emails de PostulaMatic permite a los usuarios enviar emails personalizados de forma masiva a puestos de trabajo, utilizando inteligencia artificial para generar contenido único y relevante para cada aplicación.

## 🏗️ Arquitectura del Sistema

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────┐
│                    DASHBOARD WEB                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Monitoreo     │  │   Configuración │  │ Estadísticas │ │
│  │   de Emails     │  │   de Usuario    │  │   y Logs     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    CELERY WORKERS                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Envío Individual│  │  Envío Masivo   │  │Matching Auto │ │
│  │                 │  │                 │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  SERVICIOS DE IA                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Generación de  │  │ Personalización │  │ Análisis de  │ │
│  │     Emails      │  │      de CV      │  │  Requisitos  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    BASE DE DATOS                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   EmailSentLog  │  │   UserProfile   │  │   JobPosting │ │
│  │                 │  │                 │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Configuración del Sistema

### 1. Variables de Entorno

```bash
# Configuración de Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Configuración de IA
OPENAI_API_KEY=tu_api_key_openai
ANTHROPIC_API_KEY=tu_api_key_anthropic
AI_PROVIDER=openai  # o anthropic

# Configuración de Email
DEFAULT_FROM_EMAIL=idgleb646807@gmail.com
```

### 2. Servicios de Docker

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  worker:
    build: .
    command: celery -A postulamatic worker --loglevel=info
    depends_on:
      - redis
  
  beat:
    build: .
    command: celery -A postulamatic beat --loglevel=info
    depends_on:
      - redis
```

## 📊 Modelos de Base de Datos

### EmailSentLog

```python
class EmailSentLog(models.Model):
    """Log de emails enviados para auditoría y estadísticas."""
    
    STATUS_CHOICES = [
        ('sent', 'Enviado'),
        ('failed', 'Fallido'),
        ('queued', 'En Cola'),
        ('retry', 'Reintento'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cv = models.ForeignKey(UserCV, on_delete=models.CASCADE)
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE)
    
    # Contenido del email
    email_subject = models.CharField(max_length=500)
    email_body = models.TextField()
    
    # Detalles del envío
    sent_to = models.EmailField()
    message_id = models.CharField(max_length=500, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    error_message = models.TextField(blank=True, null=True)
    
    # Metadatos
    task_id = models.CharField(max_length=255, blank=True, null=True)
    email_template = models.CharField(max_length=50, default='base')
    ai_provider = models.CharField(max_length=50, default='openai')
    
    # Timestamps
    sent_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

## 🚀 Tareas de Celery

### 1. Envío Individual de Emails

```python
@shared_task(bind=True, max_retries=3)
def send_personalized_email_task(
    self, 
    user_id: int, 
    cv_id: int, 
    job_id: int, 
    email_template: str = 'base',
    ai_provider: str = 'openai'
) -> Dict:
    """
    Envía un email personalizado a un puesto específico.
    
    Características:
    - Verificación de límites diarios
    - Generación de email con IA
    - Personalización de CV adjunto
    - Pausas aleatorias entre envíos
    - Reintentos automáticos
    - Logging completo
    """
```

### 2. Envío Masivo de Emails

```python
@shared_task(bind=True, max_retries=2)
def send_bulk_emails_task(
    self, 
    user_id: int, 
    job_ids: List[int], 
    email_template: str = 'base',
    ai_provider: str = 'openai',
    batch_size: int = 5,
    delay_between_batches: int = 300
) -> Dict:
    """
    Envía emails masivos a múltiples puestos.
    
    Características:
    - Procesamiento en batches
    - Delays configurables entre batches
    - Manejo de errores por lote
    - Monitoreo de progreso
    """
```

### 3. Matching Automático

```python
@shared_task
def process_matching_and_send_emails_task(
    user_id: int,
    min_match_score: int = 70,
    email_template: str = 'base',
    ai_provider: str = 'openai'
) -> Dict:
    """
    Procesa matching automático y envía emails.
    
    Características:
    - Filtrado por score de coincidencia
    - Envío automático a matches altos
    - Integración con sistema de matching
    """
```

## 🎛️ Dashboard de Monitoreo

### URL de Acceso
```
http://localhost:8000/matching/email-monitoring/
```

### Funcionalidades del Dashboard

#### 1. Estadísticas Generales
- **Total de emails enviados**: Contador total histórico
- **Emails hoy**: Contador del día actual
- **Esta semana**: Contador de los últimos 7 días
- **Tasa de éxito**: Porcentaje de emails enviados exitosamente

#### 2. Configuración del Usuario
- **Límite diario**: Número máximo de emails por día
- **Umbral de match**: Score mínimo para envío automático
- **Estado**: Activo/Inactivo del sistema automático
- **Pausas**: Rango de pausas entre envíos (min-max segundos)

#### 3. Emails Recientes
- Lista de los últimos 10 emails enviados
- Estado visual (enviado/fallido/reintento)
- Información del puesto y timestamp

#### 4. Acciones Disponibles

##### Envío de Prueba
```javascript
// Modal para envío individual
{
  cv_id: "Seleccionar CV del usuario",
  job_id: "Seleccionar puesto de trabajo",
  email_template: "base|formal|creative|technical",
  ai_provider: "openai|anthropic"
}
```

##### Envío Masivo
```javascript
// Modal para envío masivo
{
  job_ids: "Múltiples puestos seleccionados",
  email_template: "Template a usar",
  ai_provider: "Proveedor de IA",
  batch_size: "Tamaño del lote (1-20)",
  delay_between_batches: "Delay entre lotes (60-3600s)"
}
```

##### Matching Automático
```javascript
// Modal para matching automático
{
  min_match_score: "Score mínimo (0-100)",
  email_template: "Template a usar",
  ai_provider: "Proveedor de IA"
}
```

## 📡 APIs REST

### 1. Obtener CVs del Usuario
```http
GET /matching/api/user-cvs/
Authorization: Required

Response:
{
  "success": true,
  "cvs": [
    {
      "id": 8,
      "created_at": "14/10/2025 21:29",
      "skills_count": 20,
      "is_processed": true,
      "file_name": "cv_juan_perez.txt"
    }
  ]
}
```

### 2. Obtener Puestos de Trabajo
```http
GET /matching/api/job-postings/
Authorization: Required

Response:
{
  "success": true,
  "jobs": [
    {
      "id": 16,
      "title": "Desarrollador Backend Python",
      "email": "hr@techcompany.com",
      "created_at": "14/10/2025",
      "description_preview": "Buscamos un desarrollador Python senior..."
    }
  ]
}
```

### 3. Obtener Logs de Emails
```http
GET /matching/api/email-logs/?status=sent&page=1&per_page=20
Authorization: Required

Response:
{
  "success": true,
  "logs": [
    {
      "id": 1,
      "job_title": "Desarrollador Backend Python",
      "job_email": "hr@techcompany.com",
      "email_subject": "Aplicación para Desarrollador Backend Python",
      "status": "sent",
      "status_display": "Enviado",
      "sent_at": "14/10/2025 21:30",
      "email_template": "base",
      "ai_provider": "openai"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_count": 1,
    "total_pages": 1
  }
}
```

### 4. Obtener Estadísticas
```http
GET /matching/api/email-statistics/
Authorization: Required

Response:
{
  "success": true,
  "statistics": {
    "total_emails": 5,
    "successful_emails": 4,
    "failed_emails": 1,
    "success_rate": 80.0,
    "daily_stats": [
      {
        "date": "2025-10-14",
        "sent": 3,
        "failed": 0,
        "total": 3
      }
    ],
    "template_stats": [
      {
        "template": "base",
        "count": 3
      }
    ],
    "ai_provider_stats": [
      {
        "provider": "openai",
        "count": 5
      }
    ]
  }
}
```

## 🛠️ Comandos de Gestión

### 1. Crear Datos de Prueba
```bash
# Crear usuario, CV y puestos de prueba
docker compose exec postulamatic_web python manage.py create_test_data

# Para usuario específico
docker compose exec postulamatic_web python manage.py create_test_data --user-id 1
```

### 2. Probar Sistema de Emails
```bash
# Prueba de envío individual
docker compose exec postulamatic_web python manage.py test_email_system --test-type=single

# Prueba de envío masivo
docker compose exec postulamatic_web python manage.py test_email_system --test-type=bulk

# Prueba de matching automático
docker compose exec postulamatic_web python manage.py test_email_system --test-type=auto-matching

# Con parámetros personalizados
docker compose exec postulamatic_web python manage.py test_email_system \
  --test-type=single \
  --email-template=formal \
  --ai-provider=anthropic \
  --user-id=1
```

## 🔒 Seguridad y Rate Limiting

### Límites de Envío
- **Límite diario por usuario**: Configurable (default: 50)
- **Pausas entre envíos**: 30-120 segundos (aleatorias)
- **Delays entre batches**: 60-3600 segundos
- **Reintentos automáticos**: Máximo 3 intentos

### Verificación de Límites
```python
def check_daily_email_limit(user: User) -> Dict:
    """
    Verifica límites de envío diario.
    
    Returns:
        {
            'can_send': bool,
            'sent_today': int,
            'daily_limit': int,
            'remaining': int,
            'retry_after': datetime
        }
    """
```

## 📈 Monitoreo y Logs

### Logs Estructurados
```python
# Ejemplo de log de envío exitoso
{
    "timestamp": "2025-10-14T21:30:00Z",
    "level": "INFO",
    "message": "Email enviado exitosamente",
    "user_id": 1,
    "cv_id": 8,
    "job_id": 16,
    "email_id": "msg_123456",
    "task_id": "abc123-def456"
}
```

### Estados de Tareas
- **PENDING**: En cola de procesamiento
- **STARTED**: En ejecución
- **SUCCESS**: Completada exitosamente
- **FAILURE**: Falló con error
- **RETRY**: Reintentando

### Limpieza Automática
```python
@shared_task
def cleanup_old_email_logs_task(days_to_keep: int = 30):
    """
    Limpia logs de emails antiguos.
    
    Ejecuta automáticamente para mantener la base de datos optimizada.
    """
```

## 🎨 Templates de Email

### Tipos de Templates Disponibles

1. **Base**: Template estándar profesional
2. **Formal**: Estilo corporativo formal
3. **Creative**: Enfoque creativo e innovador
4. **Technical**: Enfocado en aspectos técnicos

### Personalización Automática
- **Asunto**: Generado basado en el puesto
- **Saludo**: Personalizado con nombre del usuario
- **Cuerpo**: Adaptado al perfil y experiencia
- **Cierre**: Profesional y específico

## 🚨 Manejo de Errores

### Tipos de Errores
1. **Errores de IA**: API no disponible, límites excedidos
2. **Errores SMTP**: Servidor no disponible, credenciales incorrectas
3. **Errores de datos**: CV no encontrado, puesto inexistente
4. **Errores de límites**: Límite diario excedido

### Estrategia de Reintentos
```python
# Backoff exponencial
countdown = 60 * (2 ** retry_count)  # 60s, 120s, 240s

# Solo reintentar errores temporales
if error_type in ['network', 'timeout', 'rate_limit']:
    retry_task()
else:
    mark_as_failed()
```

## 📊 Métricas y Analytics

### Métricas Disponibles
- **Tasa de éxito**: % de emails enviados exitosamente
- **Tiempo promedio**: Duración media de envío
- **Distribución por template**: Uso de cada tipo de template
- **Distribución por proveedor IA**: Uso de OpenAI vs Anthropic
- **Patrones temporales**: Envíos por día/hora

### Dashboard de Estadísticas
```
URL: /matching/email-statistics/

Características:
- Gráficos de tendencias diarias
- Distribución por templates
- Estadísticas por proveedor de IA
- Top puestos por envíos
```

## 🔧 Configuración Avanzada

### Configuración de Usuario
```python
class UserProfile(models.Model):
    # Límites de envío
    daily_limit = models.IntegerField(default=50)
    match_threshold = models.IntegerField(default=70)
    
    # Pausas configurables
    min_pause_seconds = models.IntegerField(default=30)
    max_pause_seconds = models.IntegerField(default=120)
    
    # Control de automatización
    is_active = models.BooleanField(default=False)
```

### Configuración de Celery
```python
# postulamatic/settings.py
CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/1"
CELERY_TIMEZONE = "America/Argentina/Buenos_Aires"

# Configuración de tareas periódicas
CELERY_BEAT_SCHEDULE = {
    'cleanup-email-logs': {
        'task': 'matching.tasks_email.cleanup_old_email_logs_task',
        'schedule': crontab(hour=2, minute=0),  # Diariamente a las 2 AM
    },
}
```

## 🚀 Despliegue y Producción

### Checklist de Producción

- [ ] Configurar Redis para alta disponibilidad
- [ ] Configurar múltiples workers de Celery
- [ ] Configurar monitoreo de workers (Supervisor/systemd)
- [ ] Configurar logs centralizados
- [ ] Configurar alertas de fallos
- [ ] Configurar backup de base de datos
- [ ] Configurar rate limiting a nivel de servidor
- [ ] Configurar SSL/TLS para emails
- [ ] Configurar autenticación SMTP

### Monitoreo Recomendado
```bash
# Verificar estado de workers
docker compose exec postulamatic_web celery -A postulamatic inspect active

# Verificar colas
docker compose exec postulamatic_web celery -A postulamatic inspect stats

# Monitorear logs en tiempo real
docker compose logs -f worker
```

## 📚 Referencias y Recursos

### Documentación Técnica
- [Celery Documentation](https://docs.celeryproject.org/)
- [Django Email Backends](https://docs.djangoproject.com/en/stable/topics/email/)
- [Redis Documentation](https://redis.io/documentation)

### Archivos de Configuración
- `matching/tasks_email.py` - Tareas principales
- `matching/views_email_monitoring.py` - Vistas del dashboard
- `matching/models.py` - Modelos de base de datos
- `templates/matching/email_monitoring_dashboard.html` - Interface web

### Comandos Útiles
```bash
# Reiniciar workers
docker compose restart worker

# Ver logs de workers
docker compose logs worker --tail 50

# Ejecutar migraciones
docker compose exec postulamatic_web python manage.py migrate

# Crear superusuario
docker compose exec postulamatic_web python manage.py createsuperuser
```

---

## 📞 Soporte

Para soporte técnico o reportar problemas:

1. **Revisar logs**: `docker compose logs worker`
2. **Verificar estado**: Dashboard de monitoreo
3. **Probar sistema**: Comando `test_email_system`
4. **Documentar error**: Incluir logs y configuración

---

**Versión**: 1.0  
**Última actualización**: 14 de Octubre, 2025  
**Autor**: Sistema PostulaMatic
