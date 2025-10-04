"""
Tareas de Celery para scraping y procesamiento de ofertas.
"""

import logging

# Importar sync_to_async para usar ORM en contexto async
from asgiref.sync import sync_to_async
from celery import shared_task

from .clients.dvcarreras import DVCarrerasClient
# Importar tareas avanzadas
from .clients.dvcarreras_advanced import DVCarrerasAdvancedClient
from .models import JobPosting, MatchScore, ScrapingLog, UserCV, UserProfile
from .services.matching import matching_service

logger = logging.getLogger(__name__)


# Funciones async wrapper para operaciones del ORM
def create_or_update_job(external_id, defaults):
    return JobPosting.objects.update_or_create(
        external_id=external_id, defaults=defaults
    )


async_create_or_update_job = sync_to_async(create_or_update_job)
async_get_user_profile = sync_to_async(
    lambda user_id: UserProfile.objects.get(user_id=user_id)
)
async_calculate_matches = sync_to_async(matching_service.calculate_user_job_matches)
async_save_match_score = sync_to_async(matching_service.save_match_score)


def save_scraping_log(user_id, task_id, message, log_type="info"):
    """Guarda un log de scraping en la base de datos."""
    from django.contrib.auth.models import User

    user = User.objects.get(id=user_id)
    ScrapingLog.objects.create(
        user=user, task_id=task_id, message=message, log_type=log_type
    )


async_save_scraping_log = sync_to_async(save_scraping_log)


@shared_task(bind=True)
def recalculate_matches_for_user(self, user_id: int):
    """
    Recalcula todos los matches para un usuario cuando cambia el umbral.
    Maneja cancelaciones y actualiza progreso.

    Args:
        user_id: ID del usuario

    Returns:
        Dict con estadísticas del recálculo
    """
    try:
        logger.info(f"Iniciando recálculo de matches para usuario {user_id}")

        # Actualizar progreso inicial
        self.update_state(
            state="PROGRESS",
            meta={
                "current_step": "Iniciando recálculo",
                "progress_info": "Obteniendo perfil del usuario",
                "progress_percentage": 10,
            },
        )

        # Verificar si la tarea fue cancelada
        # Nota: Celery no tiene is_aborted(), verificamos el estado de la tarea
        if self.request.called_directly:
            # Si se llama directamente, no hay cancelación
            pass

        # Obtener perfil del usuario
        user_profile = UserProfile.objects.get(user_id=user_id)

        # Obtener todas las ofertas de trabajo
        all_jobs = JobPosting.objects.all()
        total_jobs = all_jobs.count()

        # Actualizar progreso
        self.update_state(
            state="PROGRESS",
            meta={
                "current_step": "Preparando recálculo",
                "progress_info": f"Encontradas {total_jobs} ofertas para procesar",
                "progress_percentage": 20,
            },
        )

        # Eliminar matches existentes del usuario
        old_matches_count = MatchScore.objects.filter(user_id=user_id).count()
        MatchScore.objects.filter(user_id=user_id).delete()

        logger.info(
            f"Eliminados {old_matches_count} matches antiguos para usuario {user_id}"
        )

        # Actualizar progreso
        self.update_state(
            state="PROGRESS",
            meta={
                "current_step": "Recalculando matches",
                "progress_info": f"Eliminados {old_matches_count} matches antiguos",
                "progress_percentage": 30,
            },
        )

        # Recalcular matches para todas las ofertas
        new_matches_count = 0
        processed_jobs = 0

        for job in all_jobs:
            # Verificar si la tarea fue cancelada
            # Nota: Simplificamos la verificación de cancelación
            pass

            try:
                # Calcular matches con el nuevo umbral
                matches = matching_service.calculate_user_job_matches(user_profile, job)

                for cv, match_result in matches:
                    # Solo guardar si supera el nuevo umbral
                    if match_result.score >= user_profile.match_threshold:
                        matching_service.save_match_score(
                            user_profile.user, cv, job, match_result
                        )
                        new_matches_count += 1

                processed_jobs += 1

                # Actualizar progreso cada 5 ofertas procesadas
                if processed_jobs % 5 == 0:
                    progress = 30 + (processed_jobs / total_jobs) * 60
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "current_step": "Recalculando matches",
                            "progress_info": f"Procesadas {processed_jobs}/{total_jobs} ofertas",
                            "progress_percentage": int(progress),
                        },
                    )

            except Exception as e:
                logger.error(f"Error recalculando matches para job {job.id}: {e}")
                continue

        # Actualizar progreso final
        self.update_state(
            state="PROGRESS",
            meta={
                "current_step": "Finalizando recálculo",
                "progress_info": f"Creados {new_matches_count} nuevos matches",
                "progress_percentage": 95,
            },
        )

        result = {
            "success": True,
            "user_id": user_id,
            "old_matches_count": old_matches_count,
            "new_matches_count": new_matches_count,
            "threshold": user_profile.match_threshold,
            "processed_jobs": processed_jobs,
            "total_jobs": total_jobs,
        }

        logger.info(f"Recálculo completado para usuario {user_id}: {result}")

        # Estado final
        self.update_state(
            state="SUCCESS",
            meta={
                "current_step": "Recálculo completado",
                "progress_info": f"Recálculo exitoso: {new_matches_count} matches",
                "progress_percentage": 100,
            },
        )

        return result

    except UserProfile.DoesNotExist:
        logger.error(f"Usuario {user_id} no tiene perfil configurado")
        return {"error": "Usuario sin perfil"}
    except Exception as e:
        logger.error(f"Error en recálculo para usuario {user_id}: {e}")
        return {"error": str(e)}


@shared_task(bind=True, max_retries=3)
def scrape_dvcarreras_jobs(self, user_id: int):
    """
    Tarea para scrapear ofertas de INTRANET DAVINCI para un usuario específico.

    Args:
        user_id: ID del usuario que tiene las credenciales

    Returns:
        Dict con estadísticas del scraping
    """
    try:
        logger.info(f"Iniciando scraping de INTRANET DAVINCI para usuario {user_id}")

        # Obtener perfil del usuario
        try:
            user_profile = UserProfile.objects.get(user_id=user_id)
        except UserProfile.DoesNotExist:
            logger.error(f"Usuario {user_id} no tiene perfil configurado")
            return {"error": "Usuario sin perfil configurado"}

        # Verificar credenciales
        if not user_profile.dv_username or not user_profile.dv_password:
            logger.error(
                f"Usuario {user_id} no tiene credenciales de INTRANET DAVINCI configuradas"
            )
            return {"error": "Credenciales de INTRANET DAVINCI no configuradas"}

        # Realizar scraping
        with DVCarrerasClient(
            username=user_profile.get_dv_username(),
            password=user_profile.get_dv_password(),
            rate_limit_delay=(2.0, 5.0),  # Delay más conservador para producción
        ) as client:

            # Login
            if not client.login():
                logger.error(f"Login fallido para usuario {user_id}")
                raise Exception("Login fallido en INTRANET DAVINCI")

            # Scrapear ofertas
            job_postings_data = client.scrape_job_board(max_pages=3)

            logger.info(
                f"Encontradas {len(job_postings_data)} ofertas para usuario {user_id}"
            )

            # Procesar y guardar ofertas
            saved_jobs = 0
            new_jobs = 0

            for job_data in job_postings_data:
                try:
                    # Crear o actualizar JobPosting
                    job_posting, created = JobPosting.objects.update_or_create(
                        external_id=job_data.external_id,
                        defaults={
                            "title": job_data.title,
                            "description": job_data.description,
                            "email": getattr(job_data, "email", ""),
                            "raw_html": getattr(job_data, "raw_html", ""),
                        },
                    )

                    saved_jobs += 1
                    if created:
                        new_jobs += 1
                        logger.info(
                            f"Nueva oferta guardada: {job_posting.title} - Email: {job_posting.email}"
                        )

                    # Calcular matches con CVs del usuario
                    matches = matching_service.calculate_user_job_matches(
                        user_profile, job_posting
                    )

                    for cv, match_result in matches:
                        # Solo guardar si supera el umbral
                        if match_result.score >= user_profile.match_threshold:
                            matching_service.save_match_score(
                                user_profile.user, cv, job_posting, match_result
                            )
                            logger.info(
                                f"Match encontrado: {match_result.score}% para {job_posting.title}"
                            )

                except Exception as e:
                    logger.error(f"Error procesando oferta {job_data.external_id}: {e}")
                    continue

        result = {
            "success": True,
            "user_id": user_id,
            "total_jobs": len(job_postings_data),
            "saved_jobs": saved_jobs,
            "new_jobs": new_jobs,
            "matches_found": MatchScore.objects.filter(user=user_profile).count(),
        }

        logger.info(f"Scraping completado para usuario {user_id}: {result}")
        return result

    except Exception as e:
        logger.error(f"Error en scraping para usuario {user_id}: {e}")

        # Reintentar si no es el último intento
        if self.request.retries < self.max_retries:
            logger.info(
                f"Reintentando scraping para usuario {user_id} (intento {self.request.retries + 1})"
            )
            raise self.retry(countdown=60 * (self.request.retries + 1))

        return {"error": str(e)}


@shared_task
def process_new_job_postings():
    """
    Tarea periódica para procesar nuevas ofertas de trabajo.
    Calcula matches para todos los usuarios activos.
    """
    try:
        logger.info("Iniciando procesamiento de nuevas ofertas")

        # Obtener usuarios activos con credenciales configuradas
        active_users = (
            UserProfile.objects.filter(
                is_active=True, dv_username__isnull=False, dv_password__isnull=False
            )
            .exclude(dv_username="")
            .exclude(dv_password="")
        )

        logger.info(f"Procesando para {active_users.count()} usuarios activos")

        results = []
        for user_profile in active_users:
            try:
                # Ejecutar scraping para cada usuario
                result = scrape_dvcarreras_jobs.delay(user_profile.user.id)
                results.append({"user_id": user_profile.user.id, "task_id": result.id})
            except Exception as e:
                logger.error(
                    f"Error iniciando scraping para usuario {user_profile.user.id}: {e}"
                )
                results.append({"user_id": user_profile.user.id, "error": str(e)})

        return {"success": True, "processed_users": len(results), "results": results}

    except Exception as e:
        logger.error(f"Error en procesamiento de ofertas: {e}")
        return {"error": str(e)}


@shared_task
def calculate_matches_for_job(job_id: int):
    """
    Calcula matches para una oferta específica con todos los usuarios activos.

    Args:
        job_id: ID de la oferta de trabajo

    Returns:
        Dict con estadísticas de matches
    """
    try:
        logger.info(f"Calculando matches para oferta {job_id}")

        job_posting = JobPosting.objects.get(id=job_id)

        # Obtener usuarios activos con CVs
        active_users = (
            UserProfile.objects.filter(
                is_active=True, user__cvs__parsed_text__isnull=False
            )
            .exclude(user__cvs__parsed_text="")
            .distinct()
        )

        matches_calculated = 0
        high_matches = 0

        for user_profile in active_users:
            try:
                # Calcular matches
                matches = matching_service.calculate_user_job_matches(
                    user_profile, job_posting
                )

                for cv, match_result in matches:
                    # Guardar si supera umbral
                    if match_result.score >= user_profile.match_threshold:
                        matching_service.save_match_score(
                            user_profile.user, cv, job_posting, match_result
                        )
                        matches_calculated += 1

                        if match_result.score >= 80:  # Matches muy altos
                            high_matches += 1

            except Exception as e:
                logger.error(
                    f"Error calculando matches para usuario {user_profile.user.id}: {e}"
                )
                continue

        result = {
            "success": True,
            "job_id": job_id,
            "matches_calculated": matches_calculated,
            "high_matches": high_matches,
            "users_processed": active_users.count(),
        }

        logger.info(f"Matches calculados para oferta {job_id}: {result}")
        return result

    except JobPosting.DoesNotExist:
        logger.error(f"Oferta {job_id} no encontrada")
        return {"error": "Oferta no encontrada"}
    except Exception as e:
        logger.error(f"Error calculando matches para oferta {job_id}: {e}")
        return {"error": str(e)}


@shared_task
def cleanup_old_jobs():
    """
    Limpia ofertas de trabajo antiguas y matches obsoletos.
    """
    try:
        from datetime import datetime, timedelta

        logger.info("Iniciando limpieza de ofertas antiguas")

        # Obtener fecha límite (30 días atrás)
        cutoff_date = datetime.now() - timedelta(days=30)

        # Eliminar ofertas antiguas sin matches recientes
        old_jobs = JobPosting.objects.filter(
            posted_at__lt=cutoff_date, matchscores__isnull=True
        )

        deleted_count = old_jobs.count()
        old_jobs.delete()

        # Eliminar matches de ofertas que ya no existen
        orphan_matches = MatchScore.objects.filter(job_posting__isnull=True)
        orphan_count = orphan_matches.count()
        orphan_matches.delete()

        result = {
            "success": True,
            "deleted_jobs": deleted_count,
            "deleted_orphan_matches": orphan_count,
        }

        logger.info(f"Limpieza completada: {result}")
        return result

    except Exception as e:
        logger.error(f"Error en limpieza: {e}")
        return {"error": str(e)}


@shared_task(bind=True, max_retries=3)
def process_cv_file(self, cv_id: int):
    """
    Procesa un CV específico: extrae texto y detecta habilidades.

    Args:
        cv_id: ID del CV a procesar

    Returns:
        Dict con resultado del procesamiento
    """
    try:
        from .services.cv_parser import cv_parser
        from .services.skills_extractor import skills_extractor

        logger.info(f"Procesando CV ID {cv_id}")

        # Obtener el CV
        try:
            cv = UserCV.objects.get(id=cv_id)
        except UserCV.DoesNotExist:
            logger.error(f"CV {cv_id} no encontrado")
            return {"error": "CV no encontrado"}

        # Verificar si ya está procesado
        if cv.is_processed:
            logger.info(f"CV {cv_id} ya está procesado")
            return {
                "success": True,
                "cv_id": cv_id,
                "already_processed": True,
                "skills_count": cv.skills_count,
            }

        # Procesar el CV
        try:
            # Extraer texto del archivo
            parse_result = cv_parser.parse_cv(cv.original_file.path)
            parsed_text = parse_result["text"]

            # Detectar habilidades
            skills_data = skills_extractor.extract_skills(parsed_text)

            # Guardar resultados
            cv.parsed_text = parsed_text
            cv.skills = skills_data
            cv.save()

            logger.info(
                f"CV {cv_id} procesado exitosamente: {cv.skills_count} skills detectadas"
            )

            return {
                "success": True,
                "cv_id": cv_id,
                "skills_count": cv.skills_count,
                "skills_list": cv.skills_list,
                "word_count": parse_result.get("word_count", 0),
            }

        except Exception as e:
            logger.error(f"Error procesando CV {cv_id}: {e}")
            # Reintentar si es posible
            if self.request.retries < self.max_retries:
                logger.info(
                    f"Reintentando procesamiento de CV {cv_id} (intento {self.request.retries + 1})"
                )
                raise self.retry(countdown=60 * (self.request.retries + 1))
            return {"error": f"Error procesando CV: {str(e)}"}

    except Exception as e:
        logger.error(f"Error en procesamiento de CV {cv_id}: {e}")
        return {"error": str(e)}


@shared_task
def process_pending_cvs():
    """
    Procesa todos los CVs que están pendientes de procesamiento.
    Se ejecuta periódicamente para procesar CVs que no se procesaron automáticamente.
    """
    try:
        logger.info("Iniciando procesamiento de CVs pendientes")

        # Obtener CVs pendientes (sin parsed_text)
        pending_cvs = UserCV.objects.filter(parsed_text="")

        if not pending_cvs.exists():
            logger.info("No hay CVs pendientes de procesamiento")
            return {
                "success": True,
                "processed_count": 0,
                "message": "No hay CVs pendientes",
            }

        processed_count = 0
        errors = []

        for cv in pending_cvs:
            try:
                # Enviar tarea individual para cada CV
                task_result = process_cv_file.delay(cv.id)
                processed_count += 1
                logger.info(
                    f"Tarea de procesamiento enviada para CV {cv.id}: {task_result.id}"
                )

            except Exception as e:
                error_msg = f"Error enviando tarea para CV {cv.id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        result = {
            "success": True,
            "processed_count": processed_count,
            "errors": errors,
            "total_pending": pending_cvs.count(),
        }

        logger.info(f"Procesamiento de CVs pendientes completado: {result}")
        return result

    except Exception as e:
        logger.error(f"Error en procesamiento de CVs pendientes: {e}")
        return {"error": str(e)}


@shared_task(bind=True, max_retries=3)
def scrape_dvcarreras_jobs_advanced(self, user_id: int):
    """
    Tarea AVANZADA para scrapear ofertas de INTRANET DAVINCI con técnicas anti-detección.

    Args:
        user_id: ID del usuario que tiene las credenciales

    Returns:
        Dict con estadísticas del scraping
    """
    try:
        logger.info(
            f"Iniciando scraping AVANZADO de INTRANET DAVINCI para usuario {user_id}"
        )

        # Obtener perfil del usuario
        try:
            user_profile = UserProfile.objects.get(user_id=user_id)
        except UserProfile.DoesNotExist:
            logger.error(f"Usuario {user_id} no tiene perfil configurado")
            raise Exception("Usuario sin perfil configurado")

        # Verificar credenciales
        if not user_profile.dv_username or not user_profile.dv_password:
            logger.error(
                f"Usuario {user_id} no tiene credenciales de INTRANET DAVINCI configuradas"
            )
            raise Exception("Credenciales de INTRANET DAVINCI no configuradas")

        # Realizar scraping con cliente avanzado
        with DVCarrerasAdvancedClient(
            username=user_profile.get_dv_username(),
            password=user_profile.get_dv_password(),
            use_proxies=False,  # Cambiar a True si tienes proxies configurados
        ) as client:

            # Login con técnicas avanzadas
            if not client.login():
                logger.error(f"Login AVANZADO fallido para usuario {user_id}")
                raise Exception("Login fallido en INTRANET DAVINCI (método avanzado)")

            # Scrapear ofertas
            job_postings_data = client.scrape_job_board(max_pages=3)

            logger.info(
                f"Encontradas {len(job_postings_data)} ofertas para usuario {user_id}"
            )

            # Procesar y guardar ofertas
            saved_jobs = 0
            new_jobs = 0
            matches_found = 0

            for job_data in job_postings_data:
                try:
                    # Crear o actualizar JobPosting
                    job_posting, created = JobPosting.objects.update_or_create(
                        external_id=job_data.external_id,
                        defaults={
                            "title": job_data.title,
                            "description": job_data.description,
                            "email": getattr(job_data, "email", ""),
                            "raw_html": getattr(job_data, "raw_html", ""),
                        },
                    )

                    saved_jobs += 1
                    if created:
                        new_jobs += 1
                        logger.info(
                            f"Nueva oferta guardada: {job_posting.title} - Email: {job_posting.email}"
                        )

                    # Calcular matches con CVs del usuario
                    matches = matching_service.calculate_user_job_matches(
                        user_profile, job_posting
                    )

                    for cv, match_result in matches:
                        # Solo guardar si supera el umbral
                        if match_result.score >= user_profile.match_threshold:
                            matching_service.save_match_score(
                                user_profile.user, cv, job_posting, match_result
                            )
                            matches_found += 1
                            logger.info(
                                f"Match encontrado: {match_result.score}% para {job_posting.title}"
                            )

                except Exception as e:
                    logger.error(f"Error procesando oferta {job_data.external_id}: {e}")
                    continue

        result = {
            "success": True,
            "user_id": user_id,
            "total_jobs": len(job_postings_data),
            "saved_jobs": saved_jobs,
            "new_jobs": new_jobs,
            "matches_found": matches_found,
            "method": "advanced",
            "message": "Scraping avanzado completado exitosamente",
        }

        logger.info(f"Scraping AVANZADO completado para usuario {user_id}: {result}")
        return result

    except Exception as e:
        logger.error(f"Error en scraping AVANZADO para usuario {user_id}: {e}")

        # Reintentar si no es el último intento
        if self.request.retries < self.max_retries:
            logger.info(
                f"Reintentando scraping AVANZADO para usuario {user_id} (intento {self.request.retries + 1})"
            )
            raise self.retry(countdown=60 * (self.request.retries + 1))

        raise


@shared_task(bind=True, max_retries=3)
def scrape_dvcarreras_jobs_playwright(self, user_id: int):
    """
    Tarea con Playwright para scrapear ofertas de INTRANET DAVINCI usando navegador real.

    Args:
        user_id: ID del usuario que tiene las credenciales

    Returns:
        Dict con estadísticas del scraping
    """
    try:
        logger.info(f"Iniciando scraping con PLAYWRIGHT para usuario {user_id}")

        # Actualizar estado: Iniciando
        logger.info("Enviando actualización de estado: Iniciando scraping")
        self.update_state(
            state="STARTED",
            meta={
                "current_step": "Iniciando scraping con Playwright",
                "progress_info": "Preparando navegador y credenciales",
                "progress_percentage": 10,
            },
        )

        # Guardar log en la base de datos
        import asyncio

        asyncio.run(
            async_save_scraping_log(
                user_id, self.request.id, "Worker iniciando proceso de scraping", "info"
            )
        )

        # Función async para usar Playwright
        async def run_playwright_scraping():
            import asyncio

            from .clients.dvcarreras_playwright_simple import \
                DVCarrerasPlaywrightSimple

            # Actualizar estado: Iniciando navegador
            logger.info("Enviando actualización de estado: Iniciando navegador")
            self.update_state(
                state="STARTED",
                meta={
                    "current_step": "Iniciando navegador",
                    "progress_info": "Abriendo navegador Playwright",
                    "progress_percentage": 20,
                },
            )
            await asyncio.sleep(1)  # Pausa para que el frontend capture el estado

            # Guardar log en la base de datos
            await async_save_scraping_log(
                user_id, self.request.id, "Iniciando navegador Playwright", "info"
            )

            # Obtener perfil del usuario usando función async
            try:
                user_profile = await async_get_user_profile(user_id)
            except UserProfile.DoesNotExist:
                logger.error(f"Usuario {user_id} no tiene perfil configurado")
                raise Exception("Usuario sin perfil configurado")

            # Verificar credenciales
            if not user_profile.dv_username or not user_profile.dv_password:
                logger.error(
                    f"Usuario {user_id} no tiene credenciales de INTRANET DAVINCI configuradas"
                )
                raise Exception("Credenciales de INTRANET DAVINCI no configuradas")

            # Actualizar estado: Iniciando sesión
            logger.info("Enviando actualización de estado: Iniciando sesión")
            self.update_state(
                state="STARTED",
                meta={
                    "current_step": "Iniciando sesión",
                    "progress_info": "Autenticándose en INTRANET DAVINCI",
                    "progress_percentage": 30,
                },
            )
            await asyncio.sleep(1)  # Pausa para que el frontend capture el estado

            # Guardar log en la base de datos
            await async_save_scraping_log(
                user_id, self.request.id, "Iniciando sesión", "info"
            )
            await async_save_scraping_log(
                user_id, self.request.id, "Autenticándose en INTRANET DAVINCI", "info"
            )
            await async_save_scraping_log(
                user_id,
                self.request.id,
                "🔐 Verificando credenciales de INTRANET DAVINCI",
                "info",
            )

            # Crear callback para logging
            async def log_callback(message: str, log_type: str = "info"):
                await async_save_scraping_log(
                    user_id, self.request.id, message, log_type
                )

            async with DVCarrerasPlaywrightSimple(
                username=user_profile.get_dv_username(),
                password=user_profile.get_dv_password(),
                log_callback=log_callback,
            ) as client:

                # Intentar login - un solo intento como en el perfil
                login_success = await client.login()
                if not login_success:
                    logger.error(
                        f"Login con PLAYWRIGHT fallido para usuario {user_id} - credenciales incorrectas"
                    )
                    await async_save_scraping_log(
                        user_id,
                        self.request.id,
                        "🛑 Scraping detenido por credenciales incorrectas",
                        "error",
                    )
                    # No reintentar - fallar inmediatamente
                    return {
                        "success": False,
                        "user_id": user_id,
                        "error": "Credenciales incorrectas",
                        "message": "Login fallido en INTRANET DAVINCI - verifica usuario y contraseña",
                    }

                # Actualizar estado: Navegando al portal
                logger.info("Enviando actualización de estado: Navegando al portal")
                self.update_state(
                    state="STARTED",
                    meta={
                        "current_step": "Navegando al portal",
                        "progress_info": "Accediendo a la bolsa de trabajo",
                        "progress_percentage": 40,
                    },
                )
                await asyncio.sleep(1)  # Pausa para que el frontend capture el estado

                # Guardar log en la base de datos
                await async_save_scraping_log(
                    user_id, self.request.id, "Navegando al portal", "info"
                )
                await async_save_scraping_log(
                    user_id, self.request.id, "Accediendo a la bolsa de trabajo", "info"
                )

                # Actualizar estado: Extrayendo ofertas
                logger.info("Enviando actualización de estado: Extrayendo ofertas")
                self.update_state(
                    state="STARTED",
                    meta={
                        "current_step": "Extrayendo ofertas",
                        "progress_info": "Scrapeando ofertas de trabajo",
                        "progress_percentage": 50,
                    },
                )
                await asyncio.sleep(1)  # Pausa para que el frontend capture el estado

                # Guardar log en la base de datos
                await async_save_scraping_log(
                    user_id, self.request.id, "Extrayendo ofertas", "info"
                )
                await async_save_scraping_log(
                    user_id, self.request.id, "Scrapeando ofertas de trabajo", "info"
                )

                job_postings_data = await client.scrape_job_board(max_pages=3)

                logger.info(
                    f"Encontradas {len(job_postings_data)} ofertas para usuario {user_id}"
                )

                # Guardar log con cantidad de ofertas encontradas
                await async_save_scraping_log(
                    user_id,
                    self.request.id,
                    f"Ofertas encontradas: {len(job_postings_data)}",
                    "info",
                )

                # Log de únicas vs duplicadas dentro del lote
                try:
                    unique_external_ids = {jp.external_id for jp in job_postings_data}
                    uniques_count = len(unique_external_ids)
                    duplicates_in_batch = len(job_postings_data) - uniques_count
                    await async_save_scraping_log(
                        user_id,
                        self.request.id,
                        f"Únicas en lote: {uniques_count} (duplicadas en lote: {duplicates_in_batch})",
                        "info",
                    )
                except Exception as _e:
                    logger.warning(
                        f"No se pudo calcular únicas/duplicadas en lote: {_e}"
                    )

                # Actualizar estado: Procesando datos
                logger.info("Enviando actualización de estado: Procesando datos")
                self.update_state(
                    state="STARTED",
                    meta={
                        "current_step": "Procesando datos",
                        "progress_info": "Analizando ofertas encontradas",
                        "progress_percentage": 60,
                    },
                )
                await asyncio.sleep(1)  # Pausa para que el frontend capture el estado

                # Guardar log en la base de datos
                await async_save_scraping_log(
                    user_id, self.request.id, "Procesando datos", "info"
                )
                await async_save_scraping_log(
                    user_id, self.request.id, "Analizando ofertas encontradas", "info"
                )

                # Procesar y guardar ofertas
                saved_jobs = 0  # Solo ofertas realmente guardadas (nuevas)
                new_jobs = 0
                matches_found = 0

                for job_data in job_postings_data:
                    try:
                        logger.info(
                            f"Verificando duplicado para: {job_data.title} - Email: {job_data.email}"
                        )

                        # Crear nueva oferta (la verificación de duplicados se hace en el modelo)
                        job_posting, created = await async_create_or_update_job(
                            external_id=job_data.external_id,
                            defaults={
                                "title": job_data.title,
                                "description": job_data.description,
                                "email": job_data.email,
                                "raw_html": job_data.raw_html,
                            },
                        )

                        if created:
                            saved_jobs += (
                                1  # Solo contar las que realmente se guardaron
                            )
                            new_jobs += 1
                            logger.info(
                                f"Nueva oferta guardada: {job_posting.title} - Email: {job_posting.email}"
                            )
                        else:
                            logger.info(
                                f"Oferta duplicada omitida: {job_posting.title} - Email: {job_posting.email}"
                            )

                        # Calcular matches con CVs del usuario usando función async
                        matches = await async_calculate_matches(
                            user_profile, job_posting
                        )

                        for cv, match_result in matches:
                            # Solo guardar si supera el umbral
                            if match_result.score >= user_profile.match_threshold:
                                await async_save_match_score(
                                    user_profile.user, cv, job_posting, match_result
                                )
                                matches_found += 1
                                logger.info(
                                    f"Match encontrado: {match_result.score}% para {job_posting.title}"
                                )

                    except Exception as e:
                        logger.error(
                            f"Error procesando oferta {job_data.external_id}: {e}"
                        )
                        continue

                # Guardar log con cantidad de ofertas nuevas DESPUÉS del procesamiento completo
                await async_save_scraping_log(
                    user_id, self.request.id, f"Ofertas nuevas: {new_jobs}", "info"
                )

                # Actualizar estado: Finalizando
                logger.info("Enviando actualización de estado: Finalizando")
                self.update_state(
                    state="STARTED",
                    meta={
                        "current_step": "Finalizando",
                        "progress_info": "Completando proceso de scraping",
                        "progress_percentage": 90,
                    },
                )
                await asyncio.sleep(1)  # Pausa para que el frontend capture el estado

                # Guardar log en la base de datos
                await async_save_scraping_log(
                    user_id, self.request.id, "Finalizando", "info"
                )
                await async_save_scraping_log(
                    user_id, self.request.id, "Completando proceso de scraping", "info"
                )

                # Guardar resumen final con datos correctos
                await async_save_scraping_log(
                    user_id,
                    self.request.id,
                    "¡Scraping completado exitosamente!",
                    "success",
                )
                await async_save_scraping_log(
                    user_id,
                    self.request.id,
                    f"📊 Resumen: {len(job_postings_data)} ofertas encontradas, {saved_jobs} guardadas, {matches_found} matches encontrados",
                    "success",
                )

                return {
                    "success": True,
                    "user_id": user_id,
                    "total_jobs": len(job_postings_data),
                    "saved_jobs": saved_jobs,
                    "new_jobs": new_jobs,
                    "matches_found": matches_found,
                    "method": "playwright",
                    "message": "Scraping con Playwright completado exitosamente",
                }

        # Ejecutar la función async
        import asyncio

        result = asyncio.run(run_playwright_scraping())

        logger.info(
            f"Scraping con PLAYWRIGHT completado para usuario {user_id}: {result}"
        )
        return result

    except Exception as e:
        logger.error(f"Error en scraping con PLAYWRIGHT para usuario {user_id}: {e}")

        # No reintentar si el error es por credenciales incorrectas
        if "Credenciales incorrectas" in str(e) or "Error de autenticación" in str(e):
            logger.info(
                f"No reintentando scraping para usuario {user_id} - credenciales incorrectas"
            )
            return {
                "success": False,
                "user_id": user_id,
                "error": "Credenciales incorrectas",
                "message": "Login fallido en INTRANET DAVINCI - verifica usuario y contraseña",
            }

        # Reintentar solo para otros tipos de errores (red, timeout, etc.)
        if self.request.retries < self.max_retries:
            logger.info(
                f"Reintentando scraping con PLAYWRIGHT para usuario {user_id} (intento {self.request.retries + 1})"
            )
            raise self.retry(countdown=60 * (self.request.retries + 1))

        raise
