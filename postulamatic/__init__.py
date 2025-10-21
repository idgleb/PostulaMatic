import os

# Asegurar el settings module por defecto
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "postulamatic.settings")

# Importar desde core (es donde realmente está definida la app de Celery)
from core.celery import app as celery_app  # noqa: F401

__all__ = ("celery_app",)
