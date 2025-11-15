"""
Comando Django para verificar y limpiar locks de scraping huérfanos.
"""

import logging

from celery.result import AsyncResult
from django.core.cache import cache
from django.core.management.base import BaseCommand

from matching.services.scraping_lock import (
    SCRAPING_INFO_KEY,
    SCRAPING_LOCK_KEY,
    scraping_lock,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Verifica el estado del lock de scraping y limpia locks huérfanos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-release",
            action="store_true",
            help="Libera el lock forzosamente si la tarea de Celery no está activa",
        )

    def handle(self, *args, **options):
        self.stdout.write("🔍 Verificando estado del lock de scraping...\n")

        # Verificar si hay un lock activo
        task_id = cache.get(SCRAPING_LOCK_KEY)
        info = cache.get(SCRAPING_INFO_KEY)

        if not task_id:
            self.stdout.write(self.style.SUCCESS("✅ No hay lock de scraping activo"))
            return

        self.stdout.write(f"🔒 Lock encontrado: task_id={task_id}")
        if info:
            self.stdout.write(f"   - Usuario: {info.get('user_id')}")
            self.stdout.write(f"   - Origen: {info.get('source')}")
            self.stdout.write(f"   - Iniciado: {info.get('started_at')}")

        # Verificar estado de la tarea en Celery
        self.stdout.write("\n🔍 Verificando estado de la tarea en Celery...")
        try:
            task_result = AsyncResult(task_id)
            celery_state = task_result.state
            self.stdout.write(f"   - Estado Celery: {celery_state}")

            # Estados que indican que la tarea ya terminó
            finished_states = ["SUCCESS", "FAILURE", "REVOKED", "REJECTED"]

            if celery_state in finished_states:
                self.stdout.write(
                    self.style.WARNING(
                        f"\n⚠️ La tarea de Celery ya terminó ({celery_state}) pero el lock sigue activo"
                    )
                )
                self.stdout.write("   Esto indica un lock huérfano que debe limpiarse.")

                if options["force_release"]:
                    self.stdout.write("\n🧹 Liberando lock forzosamente...")
                    if scraping_lock.force_release_lock():
                        self.stdout.write(
                            self.style.SUCCESS("✅ Lock liberado exitosamente")
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR("❌ Error al liberar el lock")
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "\n💡 Ejecuta con --force-release para limpiar el lock"
                        )
                    )
            elif celery_state == "PENDING":
                self.stdout.write(
                    self.style.WARNING(
                        "\n⚠️ La tarea está en estado PENDING (puede que nunca se ejecutó)"
                    )
                )
                if options["force_release"]:
                    self.stdout.write("\n🧹 Liberando lock forzosamente...")
                    if scraping_lock.force_release_lock():
                        self.stdout.write(
                            self.style.SUCCESS("✅ Lock liberado exitosamente")
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "\n💡 Ejecuta con --force-release para limpiar el lock"
                        )
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✅ La tarea está activa ({celery_state}), el lock es válido"
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\n❌ Error al verificar tarea de Celery: {e}")
            )
            if options["force_release"]:
                self.stdout.write("\n🧹 Liberando lock forzosamente...")
                if scraping_lock.force_release_lock():
                    self.stdout.write(
                        self.style.SUCCESS("✅ Lock liberado exitosamente")
                    )
