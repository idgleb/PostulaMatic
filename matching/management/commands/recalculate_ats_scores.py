"""
Comando de Django para recalcular todos los scores de matching usando el algoritmo ATS unificado.

Este comando:
1. Obtiene todos los MatchScore existentes
2. Recalcula el score usando el nuevo algoritmo ATS
3. Actualiza el campo 'details' con el breakdown ATS
4. Guarda los cambios en la base de datos

Uso:
    python manage.py recalculate_ats_scores [--dry-run] [--user-id USER_ID]
"""

import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from matching.models import JobPosting, MatchScore, UserCV
from matching.services.matching import matching_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Recalcula todos los scores de matching usando el algoritmo ATS unificado"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula la ejecución sin guardar cambios en la base de datos",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            help="Recalcular solo para un usuario específico",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Número de scores a procesar por lote (default: 100)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        user_id = options.get("user_id")
        batch_size = options["batch_size"]

        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(
            self.style.SUCCESS("🔄 RECALCULANDO SCORES CON ALGORITMO ATS UNIFICADO")
        )
        self.stdout.write(self.style.SUCCESS("=" * 80))

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  MODO DRY-RUN: No se guardarán cambios en la base de datos"
                )
            )

        # Filtrar por usuario si se especifica
        queryset = MatchScore.objects.select_related("user", "cv", "job_posting")
        if user_id:
            queryset = queryset.filter(user_id=user_id)
            self.stdout.write(
                self.style.WARNING(f"📌 Filtrando por usuario ID: {user_id}")
            )

        total_scores = queryset.count()
        self.stdout.write(
            self.style.SUCCESS(f"📊 Total de scores a recalcular: {total_scores}")
        )

        if total_scores == 0:
            self.stdout.write(self.style.WARNING("⚠️  No hay scores para recalcular"))
            return

        # Estadísticas
        processed = 0
        updated = 0
        errors = 0
        skipped = 0

        # Procesar en lotes
        for i in range(0, total_scores, batch_size):
            batch = queryset[i : i + batch_size]
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n📦 Procesando lote {i // batch_size + 1} "
                    f"({i + 1}-{min(i + batch_size, total_scores)} de {total_scores})"
                )
            )

            for match_score in batch:
                processed += 1

                try:
                    # Verificar que el CV tenga texto parseado
                    if not match_score.cv.parsed_text:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⏭️  Score {match_score.id}: CV sin texto parseado, omitiendo"
                            )
                        )
                        skipped += 1
                        continue

                    # Recalcular usando el servicio de matching
                    old_score = match_score.score
                    match_result = matching_service.calculate_cv_job_match(
                        match_score.cv, match_score.job_posting
                    )

                    new_score = int(match_result.score)
                    diff = new_score - old_score

                    # Actualizar el score
                    if not dry_run:
                        match_score.score = new_score
                        match_score.details = match_result.details
                        match_score.save()

                    updated += 1

                    # Mostrar progreso
                    if diff != 0:
                        diff_str = f"{diff:+d}"
                        color = self.style.SUCCESS if diff > 0 else self.style.ERROR
                        self.stdout.write(
                            color(
                                f"  ✅ Score {match_score.id}: "
                                f"{old_score}% → {new_score}% ({diff_str}%)"
                            )
                        )
                    else:
                        self.stdout.write(
                            f"  ✅ Score {match_score.id}: {new_score}% (sin cambios)"
                        )

                except Exception as e:
                    errors += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ❌ Error en Score {match_score.id}: {str(e)}"
                        )
                    )
                    logger.error(
                        f"Error recalculando score {match_score.id}: {e}",
                        exc_info=True,
                    )

        # Resumen final
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 80))
        self.stdout.write(self.style.SUCCESS("📊 RESUMEN DE RECALCULACIÓN"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(f"Total procesados: {processed}")
        self.stdout.write(self.style.SUCCESS(f"✅ Actualizados: {updated}"))
        self.stdout.write(self.style.WARNING(f"⏭️  Omitidos: {skipped}"))
        self.stdout.write(self.style.ERROR(f"❌ Errores: {errors}"))

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  MODO DRY-RUN: No se guardaron cambios en la base de datos"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "\n✅ Recalculación completada y guardada en la base de datos"
                )
            )
