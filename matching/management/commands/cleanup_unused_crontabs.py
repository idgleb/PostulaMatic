"""
Comando para limpiar crontabs no utilizados en django-celery-beat.
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask


class Command(BaseCommand):
    help = "Elimina crontabs que no tienen tareas periódicas asociadas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostrar qué se eliminaría sin eliminar realmente",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write(self.style.SUCCESS("🔍 Buscando crontabs no utilizados..."))

        # Obtener todos los crontabs
        all_crontabs = CrontabSchedule.objects.all()
        total_crontabs = all_crontabs.count()

        # Obtener todos los crontabs que están siendo usados por tareas periódicas
        used_crontab_ids = set(
            PeriodicTask.objects.exclude(crontab=None)
            .values_list("crontab_id", flat=True)
            .distinct()
        )

        # Encontrar crontabs no utilizados
        unused_crontabs = [
            crontab for crontab in all_crontabs if crontab.id not in used_crontab_ids
        ]

        unused_count = len(unused_crontabs)

        self.stdout.write(f"\n📊 Estadísticas:")
        self.stdout.write(f"   Total de crontabs: {total_crontabs}")
        self.stdout.write(f"   Crontabs en uso: {len(used_crontab_ids)}")
        self.stdout.write(f"   Crontabs no utilizados: {unused_count}")

        if unused_count == 0:
            self.stdout.write(
                self.style.SUCCESS("\n✅ No hay crontabs no utilizados para limpiar")
            )
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n🔍 MODO DRY-RUN: Se eliminarían {unused_count} crontabs:"
                )
            )
            for crontab in unused_crontabs:
                self.stdout.write(
                    f"   - {crontab} (ID: {crontab.id}) - {crontab.human_readable}"
                )
            self.stdout.write(
                self.style.WARNING("\n💡 Ejecuta sin --dry-run para eliminar realmente")
            )
            return

        # Eliminar crontabs no utilizados
        deleted_count = 0
        for crontab in unused_crontabs:
            crontab_str = f"{crontab} - {crontab.human_readable}"
            try:
                crontab.delete()
                deleted_count += 1
                self.stdout.write(f"   ✅ Eliminado: {crontab_str}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"   ❌ Error al eliminar {crontab_str}: {e}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Limpieza completada: {deleted_count} de {unused_count} crontabs eliminados"
            )
        )
