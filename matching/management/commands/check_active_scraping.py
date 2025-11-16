"""
Management command para verificar si hay realmente un scraping en curso.
"""

from celery.result import AsyncResult
from django.core.management.base import BaseCommand

from matching.services.scraping_lock import scraping_lock


class Command(BaseCommand):
    help = "Verifica si hay realmente un scraping en curso"

    def handle(self, *args, **options):
        self.stdout.write("🔍 Verificando estado del scraping...")
        self.stdout.write("")

        # Verificar lock
        lock_task_id = scraping_lock.get_lock_task_id()
        if lock_task_id:
            self.stdout.write(
                self.style.SUCCESS(f"✅ Lock encontrado: task_id={lock_task_id}")
            )

            # Verificar estado de la tarea
            try:
                task_result = AsyncResult(lock_task_id)
                task_status = task_result.status
                is_ready = task_result.ready()

                self.stdout.write(f"📊 Estado de la tarea: {task_status}")
                self.stdout.write(f"📊 ¿Tarea lista?: {is_ready}")

                if is_ready:
                    if task_result.successful():
                        self.stdout.write(
                            self.style.SUCCESS("✅ Tarea completada exitosamente")
                        )
                    elif task_result.failed():
                        self.stdout.write(
                            self.style.ERROR(f"❌ Tarea falló: {task_result.result}")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"⚠️ Tarea en estado desconocido: {task_status}"
                            )
                        )
                else:
                    self.stdout.write(self.style.WARNING("🔄 Tarea aún en ejecución"))

                # Verificar si está en workers activos
                from celery import current_app

                inspect = current_app.control.inspect()
                active_tasks = inspect.active()

                task_in_workers = False
                if active_tasks:
                    for worker, tasks in active_tasks.items():
                        for task in tasks:
                            if task.get("id") == lock_task_id:
                                task_in_workers = True
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"✅ Tarea encontrada en worker: {worker}"
                                    )
                                )
                                break
                        if task_in_workers:
                            break

                if not task_in_workers and not is_ready:
                    self.stdout.write(
                        self.style.WARNING(
                            "⚠️ ADVERTENCIA: Tarea no está en workers activos pero tampoco está lista"
                        )
                    )
                    self.stdout.write("   Esto podría indicar un lock huérfano")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error verificando tarea: {e}"))
        else:
            self.stdout.write(self.style.SUCCESS("ℹ️ No hay lock activo"))

        # Verificar tareas activas de Celery
        self.stdout.write("")
        self.stdout.write("📋 Verificando tareas activas de Celery:")
        self.stdout.write("=" * 50)

        try:
            from celery import current_app

            inspect = current_app.control.inspect()
            active_tasks = inspect.active()

            if active_tasks:
                self.stdout.write(self.style.SUCCESS("✅ Tareas activas encontradas:"))
                for worker, tasks in active_tasks.items():
                    self.stdout.write(f"\n📦 Worker: {worker}")
                    for task in tasks:
                        self.stdout.write(f"  - Task ID: {task.get('id')}")
                        self.stdout.write(f"    Name: {task.get('name')}")
                        self.stdout.write(f"    Args: {task.get('args')}")
                        self.stdout.write(f"    State: {task.get('state', 'N/A')}")
            else:
                self.stdout.write("ℹ️ No hay tareas activas en Celery")
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error verificando tareas activas: {e}")
            )

        # Verificar información del lock
        self.stdout.write("")
        self.stdout.write("📋 Verificando información del lock:")
        self.stdout.write("=" * 50)

        active_info = scraping_lock.get_active_scraping()
        if active_info:
            self.stdout.write(self.style.SUCCESS("✅ Información del scraping activo:"))
            self.stdout.write(f"  - Task ID: {active_info.get('task_id')}")
            self.stdout.write(f"  - User ID: {active_info.get('user_id')}")
            self.stdout.write(f"  - Started at: {active_info.get('started_at')}")
            self.stdout.write(f"  - Is locked: {scraping_lock.is_locked()}")
        else:
            self.stdout.write("ℹ️ No hay información de scraping activo")
            self.stdout.write(f"  - Is locked: {scraping_lock.is_locked()}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("✅ Verificación completada"))
