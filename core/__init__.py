import os

# Asegurar el settings module por defecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'postulamatic.settings')

from .celery import app as celery_app  # noqa: F401

__all__ = ('celery_app',)

