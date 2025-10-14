# 🚀 Guía Rápida - Sistema de Envío Automático de Emails

## ⚡ Inicio Rápido

### 1. Verificar que el Sistema Esté Funcionando

```bash
# Verificar contenedores
docker compose ps

# Verificar logs del worker
docker compose logs worker --tail 10

# Verificar que las tareas estén registradas
docker compose exec postulamatic_web celery -A postulamatic inspect registered
```

### 2. Crear Datos de Prueba

```bash
# Crear usuario, CV y puestos de prueba
docker compose exec postulamatic_web python manage.py create_test_data
```

### 3. Probar el Sistema

```bash
# Prueba básica de envío individual
docker compose exec postulamatic_web python manage.py test_email_system --test-type=single

# Prueba de envío masivo
docker compose exec postulamatic_web python manage.py test_email_system --test-type=bulk

# Prueba de matching automático
docker compose exec postulamatic_web python manage.py test_email_system --test-type=auto-matching
```

### 4. Acceder al Dashboard

```
URL: http://localhost:8000/matching/email-monitoring/
```

## 🔧 Configuración Rápida

### Variables de Entorno Esenciales

```bash
# .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
AI_PROVIDER=openai

# Celery (ya configurado)
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

### Configuración SMTP (Opcional para Pruebas)

```bash
# Para pruebas locales, usar consola backend
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

## 📋 Comandos Útiles

### Gestión de Workers

```bash
# Reiniciar worker
docker compose restart worker

# Ver estado de workers
docker compose exec postulamatic_web celery -A postulamatic inspect active

# Ver estadísticas
docker compose exec postulamatic_web celery -A postulamatic inspect stats
```

### Gestión de Base de Datos

```bash
# Aplicar migraciones
docker compose exec postulamatic_web python manage.py migrate

# Crear superusuario
docker compose exec postulamatic_web python manage.py createsuperuser
```

### Logs y Debugging

```bash
# Logs del worker en tiempo real
docker compose logs -f worker

# Logs de la aplicación web
docker compose logs -f postulamatic_web

# Logs de Redis
docker compose logs -f redis
```

## 🧪 Testing Rápido

### 1. Test de Conectividad IA

```bash
# Verificar configuración de IA
docker compose exec postulamatic_web python manage.py shell
```

```python
# En el shell de Django
from matching.services.ai_service import ai_email_service
print("OpenAI configurado:", ai_email_service.is_provider_configured('openai'))
print("Anthropic configurado:", ai_email_service.is_provider_configured('anthropic'))
```

### 2. Test de Tareas Celery

```bash
# Ejecutar tarea simple
docker compose exec postulamatic_web python manage.py shell
```

```python
# En el shell de Django
from matching.tasks_email import send_personalized_email_task
result = send_personalized_email_task.delay(1, 8, 16, 'base', 'openai')
print("Task ID:", result.id)
```

### 3. Test de APIs

```bash
# Test de API de CVs
curl -H "Authorization: Bearer <token>" http://localhost:8000/matching/api/user-cvs/

# Test de API de puestos
curl -H "Authorization: Bearer <token>" http://localhost:8000/matching/api/job-postings/
```

## 🚨 Troubleshooting Común

### Error: "Task not found"

```bash
# Solución: Reiniciar worker
docker compose restart worker

# Verificar que las tareas estén registradas
docker compose exec postulamatic_web celery -A postulamatic inspect registered | grep email
```

### Error: "Connection refused" (SMTP)

```bash
# Esto es normal sin configuración SMTP
# Para pruebas, usar backend de consola:
echo "EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend" >> .env
docker compose restart postulamatic_web
```

### Error: "No module named 'allauth'"

```bash
# Solución: Reconstruir contenedores
docker compose down
docker compose up -d --build
```

### Error: "EmailSentLog does not exist"

```bash
# Solución: Aplicar migraciones
docker compose exec postulamatic_web python manage.py makemigrations
docker compose exec postulamatic_web python manage.py migrate
```

## 📊 Monitoreo Rápido

### Dashboard Web
```
URL: http://localhost:8000/matching/email-monitoring/

Funcionalidades:
- Estadísticas en tiempo real
- Configuración de usuario
- Historial de emails
- Acciones de envío
```

### APIs de Monitoreo
```bash
# Estado de tarea específica
GET /matching/task-status/{task_id}/

# Estadísticas de emails
GET /matching/api/email-statistics/

# Logs de emails con filtros
GET /matching/api/email-logs/?status=sent&page=1
```

## 🔄 Flujo de Desarrollo

### 1. Hacer Cambios en el Código
```bash
# Editar archivos
vim matching/tasks_email.py
vim matching/views_email_monitoring.py
```

### 2. Reiniciar Servicios
```bash
# Reiniciar worker para cambios en tareas
docker compose restart worker

# Reiniciar web para cambios en vistas
docker compose restart postulamatic_web
```

### 3. Probar Cambios
```bash
# Ejecutar tests
docker compose exec postulamatic_web python manage.py test_email_system

# Verificar logs
docker compose logs worker --tail 20
```

## 📈 Métricas de Rendimiento

### Tiempo Promedio de Envío
- **Envío individual**: ~2-5 segundos
- **Envío masivo (10 emails)**: ~30-60 segundos
- **Matching automático**: ~10-30 segundos

### Límites Recomendados
- **Límite diario**: 50-100 emails
- **Batch size**: 5-10 emails
- **Delay entre batches**: 300-600 segundos
- **Pausas individuales**: 30-120 segundos

## 🎯 Próximos Pasos

### Para Producción
1. **Configurar SMTP real**
2. **Configurar credenciales de IA**
3. **Configurar monitoreo avanzado**
4. **Configurar alertas**
5. **Optimizar rate limiting**

### Para Desarrollo
1. **Agregar más templates de email**
2. **Implementar personalización avanzada de CV**
3. **Agregar métricas adicionales**
4. **Implementar notificaciones en tiempo real**

---

## 📞 Soporte Rápido

### Comandos de Diagnóstico
```bash
# Estado general del sistema
docker compose ps
docker compose exec postulamatic_web python manage.py check

# Estado de Celery
docker compose exec postulamatic_web celery -A postulamatic inspect active
docker compose exec postulamatic_web celery -A postulamatic inspect stats

# Logs de errores
docker compose logs worker | grep ERROR
docker compose logs postulamatic_web | grep ERROR
```

### URLs Importantes
- **Dashboard**: http://localhost:8000/matching/email-monitoring/
- **Admin**: http://localhost:8000/admin/
- **API Docs**: http://localhost:8000/matching/api/

### Archivos de Configuración Clave
- `matching/tasks_email.py` - Tareas principales
- `matching/views_email_monitoring.py` - Vistas del dashboard
- `matching/models.py` - Modelos de base de datos
- `postulamatic/settings.py` - Configuración Django
- `docker-compose.yml` - Configuración de contenedores

---

**⚡ Esta guía te permite comenzar a usar el sistema de envío automático de emails en menos de 5 minutos!**
