"""
Comando para configurar la tarea periódica de scraping en Celery Beat.
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json


class Command(BaseCommand):
    help = "Configura la tarea periódica de scraping programado en Celery Beat"

    def handle(self, *args, **options):
        # Crear o obtener un intervalo de 1 minuto
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.MINUTES,
        )

        # Crear o actualizar la tarea periódica
        task, created = PeriodicTask.objects.get_or_create(
            name="Check and Run Scheduled Scraping",
            defaults={
                "interval": schedule,
                "task": "matching.tasks_stealth.check_and_run_scheduled_scraping",
                "enabled": True,
            },
        )

        if not created:
            task.interval = schedule
            task.task = "matching.tasks_stealth.check_and_run_scheduled_scraping"
            task.enabled = True
            task.save()
            self.stdout.write(
                self.style.SUCCESS("✅ Tarea periódica actualizada exitosamente")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("✅ Tarea periódica creada exitosamente")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n📋 Detalles de la tarea:"
                f"\n   Nombre: {task.name}"
                f"\n   Tarea: {task.task}"
                f"\n   Intervalo: Cada {schedule.every} {schedule.period}"
                f'\n   Estado: {"Activada" if task.enabled else "Desactivada"}'
                f"\n\n🎯 La tarea verificará cada minuto si debe ejecutar el scraping programado."
            )
        )
