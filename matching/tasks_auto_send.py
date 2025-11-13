"""
Tarea Celery para envío automático diario de emails a nuevos matches.
"""

import logging

from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone

from .models import EmailSentLog, MatchScore, UserCV, UserProfile
from .tasks_bulk_email import send_bulk_emails_task

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def check_and_send_auto_emails(self):
    """
    Tarea programada que verifica usuarios con envío automático activado
    y envía emails a nuevos matches.

    Se ejecuta periódicamente (cada hora) y verifica:
    1. Usuarios con auto_send_enabled=True
    2. Hora actual coincide con auto_send_time del usuario
    3. No se ha ejecutado hoy (auto_send_last_run)
    """
    logger.info("🔄 Verificando usuarios con envío automático activado...")

    # Obtener hora actual en la zona horaria de Buenos Aires
    import pytz

    buenos_aires_tz = pytz.timezone("America/Argentina/Buenos_Aires")
    now = timezone.now()
    now_local = now.astimezone(buenos_aires_tz)
    current_time = now_local.time()
    current_date = now_local.date()

    # Obtener usuarios con envío automático activado
    users_with_auto_send = UserProfile.objects.filter(
        auto_send_enabled=True
    ).select_related("user")

    if not users_with_auto_send.exists():
        logger.info("⚪ No hay usuarios con envío automático activado")
        return {
            "success": True,
            "message": "No hay usuarios con envío automático",
            "users_processed": 0,
        }

    logger.info(
        f"👥 Encontrados {users_with_auto_send.count()} usuarios con envío automático"
    )

    users_processed = 0
    emails_sent = 0

    for profile in users_with_auto_send:
        user = profile.user

        # ============================================================
        # 🔄 VERIFICAR SI LA HORA PROGRAMADA CAMBIÓ
        # ============================================================
        # Si el usuario cambió la hora programada, permitir ejecución inmediata
        schedule_changed = False
        if profile.auto_send_last_run:
            # Obtener la hora a la que se ejecutó la última vez
            last_run_local = profile.auto_send_last_run.astimezone(buenos_aires_tz)
            last_run_time = last_run_local.time()

            # Comparar con la hora actualmente programada (con tolerancia de ±1 minuto)
            time_diff_minutes = abs(
                (profile.auto_send_time.hour * 60 + profile.auto_send_time.minute)
                - (last_run_time.hour * 60 + last_run_time.minute)
            )

            if time_diff_minutes > 1:  # Si la diferencia es mayor a 1 minuto
                schedule_changed = True
                logger.info(
                    f"🔄 Usuario {user.username}: Hora programada cambió: "
                    f"Anterior={last_run_time.strftime('%H:%M')}, "
                    f"Nueva={profile.auto_send_time.strftime('%H:%M')} - "
                    f"Permitiendo ejecución inmediata"
                )

        # Verificar si ya se ejecutó hoy (prevenir ejecuciones duplicadas)
        # PERO: Si la hora programada cambió, permitir ejecución
        if profile.auto_send_last_run and not schedule_changed:
            last_run_date = profile.auto_send_last_run.date()
            if last_run_date == current_date:
                logger.info(
                    f"⏭️ Usuario {user.username}: Ya se ejecutó hoy ({profile.auto_send_last_run})"
                )
                continue

        # Verificar si la hora actual está cerca de la hora configurada (±30 minutos)
        target_time = profile.auto_send_time
        time_diff = abs(
            (current_time.hour * 60 + current_time.minute)
            - (target_time.hour * 60 + target_time.minute)
        )

        if time_diff > 30:  # Más de 30 minutos de diferencia
            logger.info(
                f"⏰ Usuario {user.username}: Hora no coincide "
                f"(actual: {current_time.strftime('%H:%M')}, "
                f"configurada: {target_time.strftime('%H:%M')})"
            )
            continue

        logger.info(f"✅ Usuario {user.username}: Iniciando envío automático...")

        # Buscar nuevos matches (no enviados)
        new_matches = find_new_matches(user, profile)

        if not new_matches:
            logger.info(f"📭 Usuario {user.username}: No hay nuevos matches")
            # Actualizar last_run aunque no haya matches (guardar hora local)
            profile.auto_send_last_run = now_local
            profile.save(update_fields=["auto_send_last_run"])
            continue

        logger.info(
            f"📬 Usuario {user.username}: {len(new_matches)} nuevos matches encontrados"
        )

        # Obtener CV más reciente del usuario
        user_cv = UserCV.objects.filter(user=user).order_by("-created_at").first()

        if not user_cv:
            logger.warning(f"⚠️ Usuario {user.username}: No tiene CV, saltando...")
            continue

        # Enviar emails masivos usando la tarea existente
        job_ids = [match.job_posting.id for match in new_matches]

        try:
            # Llamar a la tarea de envío masivo
            result = send_bulk_emails_task.delay(
                user_id=user.id,
                job_ids=job_ids,
                cv_id=user_cv.id,
                email_template="base",
                ai_provider="openai",
                batch_size=5,
                delay_between_batches=300,
            )

            logger.info(
                f"📤 Usuario {user.username}: Envío masivo iniciado "
                f"(Task ID: {result.id}, {len(job_ids)} puestos)"
            )

            # Actualizar última ejecución (guardar hora local)
            profile.auto_send_last_run = now_local
            profile.save(update_fields=["auto_send_last_run"])

            users_processed += 1
            emails_sent += len(job_ids)

        except Exception as e:
            logger.error(f"❌ Error enviando emails para {user.username}: {e}")
            continue

    logger.info(
        f"✅ Envío automático completado: "
        f"{users_processed} usuarios procesados, "
        f"{emails_sent} emails programados"
    )

    return {
        "success": True,
        "users_processed": users_processed,
        "emails_sent": emails_sent,
        "timestamp": now.isoformat(),
    }


def find_new_matches(user: User, profile: UserProfile):
    """
    Encuentra matches nuevos (no enviados previamente) que superen el umbral.

    Args:
        user: Usuario
        profile: Perfil del usuario con configuración

    Returns:
        QuerySet de MatchScore con nuevos matches
    """
    # Obtener todos los matches del usuario que superen el umbral
    matches_above_threshold = MatchScore.objects.filter(
        user=user, score__gte=profile.match_threshold
    ).select_related("job_posting")

    # Filtrar solo los que NO tienen email enviado
    new_matches = []

    for match in matches_above_threshold:
        # Verificar si ya se envió email para este puesto
        email_exists = EmailSentLog.objects.filter(
            user=user, job_posting=match.job_posting
        ).exists()

        if not email_exists:
            new_matches.append(match)

    logger.info(
        f"🔍 Usuario {user.username}: "
        f"{matches_above_threshold.count()} matches sobre umbral, "
        f"{len(new_matches)} sin email enviado"
    )

    return new_matches


@shared_task(bind=True)
def send_auto_emails_for_user(self, user_id: int):
    """
    Envía emails automáticamente para un usuario específico.
    Útil para testing o ejecución manual.

    Args:
        user_id: ID del usuario
    """
    logger.info(f"📧 Iniciando envío automático manual para usuario {user_id}")

    try:
        user = User.objects.get(id=user_id)
        profile = UserProfile.objects.get(user=user)

        if not profile.auto_send_enabled:
            logger.warning(f"⚠️ Usuario {user.username}: Envío automático desactivado")
            return {"success": False, "error": "Envío automático desactivado"}

        # Buscar nuevos matches
        new_matches = find_new_matches(user, profile)

        if not new_matches:
            logger.info(f"📭 Usuario {user.username}: No hay nuevos matches")
            return {
                "success": True,
                "message": "No hay nuevos matches",
                "matches_found": 0,
            }

        # Obtener CV más reciente
        user_cv = UserCV.objects.filter(user=user).order_by("-created_at").first()

        if not user_cv:
            logger.error(f"❌ Usuario {user.username}: No tiene CV")
            return {"success": False, "error": "Usuario no tiene CV"}

        # Enviar emails
        job_ids = [match.job_posting.id for match in new_matches]

        result = send_bulk_emails_task.delay(
            user_id=user.id,
            job_ids=job_ids,
            cv_id=user_cv.id,
            email_template="base",
            ai_provider="openai",
            batch_size=5,
            delay_between_batches=300,
        )

        # Actualizar última ejecución
        profile.auto_send_last_run = timezone.now()
        profile.save(update_fields=["auto_send_last_run"])

        logger.info(
            f"✅ Usuario {user.username}: Envío iniciado "
            f"(Task ID: {result.id}, {len(job_ids)} puestos)"
        )

        return {
            "success": True,
            "task_id": result.id,
            "matches_found": len(new_matches),
            "emails_sent": len(job_ids),
        }

    except User.DoesNotExist:
        logger.error(f"❌ Usuario {user_id} no encontrado")
        return {"success": False, "error": "Usuario no encontrado"}
    except UserProfile.DoesNotExist:
        logger.error(f"❌ Usuario {user_id} no tiene perfil")
        return {"success": False, "error": "Usuario no tiene perfil"}
    except Exception as e:
        logger.error(f"❌ Error en envío automático para usuario {user_id}: {e}")
        return {"success": False, "error": str(e)}
