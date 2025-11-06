import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "postulamatic.settings")

app = Celery("postulamatic")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Especificar paquetes donde buscar tareas
app.autodiscover_tasks(['matching'], related_name='tasks')
app.autodiscover_tasks(['matching'], related_name='tasks_dv')
app.autodiscover_tasks(['matching'], related_name='tasks_email')
app.autodiscover_tasks(['matching'], related_name='tasks_stealth')
app.autodiscover_tasks(['matching'], related_name='tasks_bulk_email')
app.autodiscover_tasks(['matching'], related_name='tasks_auto_send')

# Configuración de tareas periódicas
app.conf.beat_schedule = {
    # Procesar CVs pendientes cada 5 minutos
    "process-pending-cvs": {
        "task": "matching.tasks.process_pending_cvs",
        "schedule": crontab(minute="*/5"),  # Cada 5 minutos
    },
    # Limpiar ofertas antiguas diariamente a las 2 AM
    "cleanup-old-jobs": {
        "task": "matching.tasks.cleanup_old_jobs",
        "schedule": crontab(hour=2, minute=0),  # Diariamente a las 2 AM
    },
    # Verificar y enviar emails automáticos cada 5 minutos (TEMPORAL PARA PRUEBAS)
    "check-auto-send-emails": {
        "task": "matching.tasks_auto_send.check_and_send_auto_emails",
        "schedule": crontab(minute="*/5"),  # Cada 5 minutos (TEMPORAL)
    },
}

app.conf.timezone = "America/Argentina/Buenos_Aires"
