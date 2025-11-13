"""
Tareas de Celery limpias - solo con FlareSolverr
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any

# Importar sync_to_async para usar ORM en contexto async
from asgiref.sync import sync_to_async
from celery import shared_task

from .models import JobPosting, MatchScore, ScrapingLog, UserCV, UserProfile
from .services.matching import matching_service

logger = logging.getLogger(__name__)


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

        # Función async para usar Playwright
        async def run_playwright_scraping():
            import asyncio

            from .clients.dvcarreras_playwright_flaresolverr import (
                DVCarrerasPlaywrightFlareSolverr,
            )

            # Actualizar estado: Iniciando navegador
            logger.info("Enviando actualización de estado: Iniciando navegador")
            self.update_state(
                state="STARTED",
                meta={
                    "current_step": "Iniciando navegador Playwright",
                    "progress_info": "Lanzando navegador real con FlareSolverr",
                    "progress_percentage": 20,
                },
            )

            # Función async para guardar logs
            async def async_save_scraping_log(
                user_id, task_id, message, log_type="info"
            ):
                await sync_to_async(ScrapingLog.objects.create)(
                    user_id=user_id,
                    task_id=task_id,
                    message=message,
                    log_type=log_type,
                    timestamp=datetime.now(),
                )

            async def log_callback(message: str, log_type: str = "info"):
                await async_save_scraping_log(
                    user_id, self.request.id, message, log_type
                )

            client = DVCarrerasPlaywrightFlareSolverr(
                username=user_profile.get_dv_username(),
                password=user_profile.get_dv_password(),
                log_callback=log_callback,
            )

            try:
                # Iniciar el cliente
                await client.start()

                # Intentar login - un solo intento como en el perfil
                login_success = await client.test_login()
                if not login_success:
                    logger.error(
                        f"Login con PLAYWRIGHT fallido para usuario {user_id} - credenciales incorrectas"
                    )
                    await async_save_scraping_log(
                        user_id,
                        self.request.id,
                        "❌ Error de conexión: Credenciales incorrectas",
                        "error",
                    )
                    return {"error": "Credenciales incorrectas"}

                # Actualizar estado: Login exitoso
                logger.info("Enviando actualización de estado: Login exitoso")
                self.update_state(
                    state="STARTED",
                    meta={
                        "current_step": "Login exitoso",
                        "progress_info": "Autenticado correctamente en INTRANET DAVINCI",
                        "progress_percentage": 40,
                    },
                )

                # Scrapear ofertas
                await async_save_scraping_log(
                    user_id, self.request.id, "🔍 Iniciando scraping de ofertas"
                )

                job_postings_data = await client.scrape_job_board(max_pages=3)

                logger.info(
                    f"Encontradas {len(job_postings_data)} ofertas para usuario {user_id}"
                )

                await async_save_scraping_log(
                    user_id,
                    self.request.id,
                    f"✅ Scraping completado: {len(job_postings_data)} ofertas encontradas",
                )

                # Actualizar estado: Procesando ofertas
                self.update_state(
                    state="STARTED",
                    meta={
                        "current_step": "Procesando ofertas",
                        "progress_info": f"Guardando {len(job_postings_data)} ofertas encontradas",
                        "progress_percentage": 60,
                    },
                )

                # Procesar y guardar ofertas
                saved_jobs = 0
                new_jobs = 0

                for job_data in job_postings_data:
                    try:
                        # Crear o actualizar JobPosting
                        job_posting, created = await sync_to_async(
                            JobPosting.objects.update_or_create
                        )(
                            external_id=job_data.external_id,
                            defaults={
                                "title": job_data.title,
                                "company": job_data.company,
                                "location": job_data.location,
                                "description": job_data.description,
                                "url": job_data.url,
                                "source": "dvcarreras",
                                "posted_at": job_data.posted_at,
                                "raw_html": job_data.raw_html,
                            },
                        )

                        saved_jobs += 1
                        if created:
                            new_jobs += 1
                            logger.info(f"Nueva oferta guardada: {job_posting.title}")

                        # Calcular matches con CVs del usuario
                        user_cvs = await sync_to_async(list)(
                            UserCV.objects.filter(user_id=user_id, is_processed=True)
                        )

                        if user_cvs:
                            cv = user_cvs[0]  # Usar el primer CV
                            match_result = await sync_to_async(
                                matching_service.calculate_matching_for_job
                            )(job_posting, cv)

                            if (
                                match_result
                                and match_result.score >= user_profile.match_threshold
                            ):
                                await sync_to_async(matching_service.save_match_score)(
                                    user_profile.user, cv, job_posting, match_result
                                )

                    except Exception as e:
                        logger.error(f"Error procesando oferta {job_data.title}: {e}")
                        continue

                logger.info(
                    f"Scraping completado para usuario {user_id}: {new_jobs} nuevas, {saved_jobs} existentes"
                )

                # Actualizar estado: Completado
                self.update_state(
                    state="SUCCESS",
                    meta={
                        "current_step": "Scraping completado",
                        "progress_info": f"{new_jobs} nuevas ofertas, {saved_jobs} total procesadas",
                        "progress_percentage": 100,
                        "new_jobs": new_jobs,
                        "saved_jobs": saved_jobs,
                        "total_found": len(job_postings_data),
                    },
                )

                return {
                    "success": True,
                    "new_jobs": new_jobs,
                    "saved_jobs": saved_jobs,
                    "total_found": len(job_postings_data),
                    "user_id": user_id,
                }

            finally:
                # Cerrar el cliente
                try:
                    await client.close()
                except Exception as e:
                    logger.warning(f"Error cerrando cliente: {e}")

        # Ejecutar la función async
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(run_playwright_scraping())
            return result
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Error en scraping con PLAYWRIGHT para usuario {user_id}: {e}")
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

        # COMENTADO: Procesamiento automático de CVs deshabilitado para evitar problemas de memoria
        # Los CVs se procesan solo cuando se suben, no automáticamente
        # for cv in pending_cvs:
        #     try:
        #         # Procesar CV directamente (sin tarea separada)
        #         from .services.cv_parser import cv_parser
        #         from .services.skills_extractor import skills_extractor
        #
        #         # Extraer texto del archivo
        #         parse_result = cv_parser.parse_cv(cv.original_file.path)
        #         parsed_text = parse_result["text"]

        #         # Verificar si el texto está vacío (error de IA)
        #         if not parsed_text or parsed_text.strip() == "":
        #             error_msg = f"CV {cv.id}: Texto vacío - Error de IA no disponible"
        #             logger.error(error_msg)
        #             errors.append(error_msg)
        #             continue

        #         # Detectar habilidades
        #         skills_data = skills_extractor.extract_skills(parsed_text)

        #         # Guardar resultados
        #         cv.parsed_text = parsed_text
        #         cv.skills = skills_data
        #         cv.is_processed = True
        #         cv.save()

        #         processed_count += 1
        #         logger.info(f"CV {cv.id} procesado exitosamente")

        #     except Exception as e:
        #         error_msg = f"Error procesando CV {cv.id}: {e}"
        #         logger.error(error_msg)
        #         errors.append(error_msg)

        # result = {
        #     "success": True,
        #     "processed_count": processed_count,
        #     "errors": errors,
        #     "total_pending": pending_cvs.count(),
        # }

        # logger.info(f"Procesamiento de CVs pendientes completado: {result}")
        # return result

        # Retornar resultado vacío ya que el procesamiento está deshabilitado
        result = {
            "success": True,
            "processed_count": 0,
            "errors": [],
            "total_pending": pending_cvs.count(),
            "message": "Procesamiento automático deshabilitado",
        }

        logger.info("Procesamiento automático de CVs deshabilitado")
        return result

    except Exception as e:
        logger.error(f"Error en procesamiento de CVs pendientes: {e}")
        return {"error": str(e)}


def _recalculate_matches_for_user_core(user_id: int):
    """
    Función core para recalcular matches (sin dependencias de Celery).
    Usa el mismo algoritmo que calculate_matches_view para garantizar consistencia.

    Args:
        user_id: ID del usuario

    Returns:
        Dict con estadísticas del recálculo
    """
    try:
        logger.info(f"Iniciando recálculo de matches para usuario {user_id}")

        # Obtener perfil del usuario
        user_profile = UserProfile.objects.get(user_id=user_id)

        # Obtener todas las ofertas de trabajo
        jobs = JobPosting.objects.all()

        if not jobs.exists():
            logger.warning(
                f"No hay ofertas de trabajo para calcular matches para usuario {user_id}"
            )
            return {
                "success": True,
                "user_id": user_id,
                "old_matches_count": 0,
                "new_matches_count": 0,
                "threshold": user_profile.match_threshold,
                "processed_jobs": 0,
                "total_jobs": 0,
                "message": "No hay ofertas de trabajo",
            }

        # Obtener CVs del usuario
        user_cvs = UserCV.objects.filter(
            user=user_profile.user, parsed_text__isnull=False
        ).exclude(parsed_text="")

        if not user_cvs.exists():
            logger.warning(
                f"Usuario {user_id} no tiene CVs procesados para calcular matches"
            )
            return {
                "success": True,
                "user_id": user_id,
                "old_matches_count": 0,
                "new_matches_count": 0,
                "threshold": user_profile.match_threshold,
                "processed_jobs": 0,
                "total_jobs": jobs.count(),
                "message": "No hay CVs procesados",
            }

        # Contadores
        matches_calculated = 0
        new_matches = 0
        removed_matches = 0
        total_matches_before = MatchScore.objects.filter(user=user_profile.user).count()

        # PASO 1: Eliminar TODOS los matches existentes del usuario
        logger.info(
            f"Eliminando {total_matches_before} matches existentes para recalcular con nuevo umbral"
        )
        MatchScore.objects.filter(user=user_profile.user).delete()

        # PASO 2: Recalcular matches para cada oferta con el nuevo umbral
        for job in jobs:
            try:
                # Calcular matches para todos los CVs del usuario contra esta oferta
                matches = matching_service.calculate_user_job_matches(user_profile, job)

                for cv, match_result in matches:
                    # Solo guardar si supera el umbral del usuario
                    if match_result.score >= user_profile.match_threshold:
                        # Crear nuevo match (ya no hay matches existentes)
                        matching_service.save_match_score(
                            user_profile, cv, job, match_result
                        )
                        new_matches += 1
                        matches_calculated += 1

                        logger.debug(
                            f"Match creado: {match_result.score}% para job {job.id} con CV {cv.id}"
                        )
                    else:
                        # Este match no supera el umbral - no se guarda
                        logger.debug(
                            f"Match descartado: {match_result.score}% < {user_profile.match_threshold}% para job {job.id}"
                        )

            except Exception as e:
                logger.error(f"Error recalculando matches para job {job.id}: {e}")
                continue

        # Obtener total de matches después del cálculo
        total_matches_after = MatchScore.objects.filter(user=user_profile.user).count()

        # Calcular matches eliminados
        removed_matches = total_matches_before - total_matches_after

        result = {
            "success": True,
            "user_id": user_id,
            "old_matches_count": total_matches_before,
            "new_matches_count": new_matches,
            "removed_matches_count": removed_matches,
            "matches_calculated": matches_calculated,
            "total_matches_after": total_matches_after,
            "threshold": user_profile.match_threshold,
            "processed_jobs": jobs.count(),
            "total_jobs": jobs.count(),
            "cvs_processed": user_cvs.count(),
        }

        logger.info(f"Recálculo completado para usuario {user_id}: {result}")
        return result

    except UserProfile.DoesNotExist:
        logger.error(f"Usuario {user_id} no tiene perfil configurado")
        return {"error": "Usuario sin perfil"}
    except Exception as e:
        logger.error(f"Error en recálculo para usuario {user_id}: {e}")
        return {"error": str(e)}


@shared_task(bind=True)
def recalculate_matches_for_all_users(self):
    """
    Tarea Celery para recalcular matches para TODOS los usuarios que tengan CVs.
    Se ejecuta automáticamente después del scraping global.

    Returns:
        Dict con estadísticas del recálculo global
    """
    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()

        logger.info("🌍 Iniciando recálculo de matches para TODOS los usuarios")

        # Actualizar progreso inicial
        self.update_state(
            state="PROGRESS",
            meta={
                "current_step": "Iniciando recálculo global",
                "progress_info": "Obteniendo usuarios con CVs",
                "progress_percentage": 5,
            },
        )

        # Obtener todos los usuarios que tengan al menos un CV procesado
        users_with_cvs = (
            User.objects.filter(cvs__parsed_text__isnull=False)
            .exclude(cvs__parsed_text="")
            .distinct()
        )

        total_users = users_with_cvs.count()

        if total_users == 0:
            logger.warning("No hay usuarios con CVs procesados para calcular matches")
            return {
                "success": True,
                "total_users": 0,
                "users_processed": 0,
                "total_matches_created": 0,
                "message": "No hay usuarios con CVs procesados",
            }

        logger.info(f"📊 Encontrados {total_users} usuarios con CVs procesados")

        # Contadores globales
        users_processed = 0
        total_matches_created = 0
        users_with_errors = 0

        # Procesar cada usuario
        for idx, user in enumerate(users_with_cvs, 1):
            try:
                # Actualizar progreso
                progress_percentage = 5 + int((idx / total_users) * 90)
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current_step": f"Procesando usuario {idx}/{total_users}",
                        "progress_info": f"Calculando matches para {user.username}",
                        "progress_percentage": progress_percentage,
                    },
                )

                logger.info(
                    f"🔄 [{idx}/{total_users}] Calculando matches para usuario {user.id} ({user.username})"
                )

                # Llamar función core para este usuario
                result = _recalculate_matches_for_user_core(user.id)

                if result.get("success"):
                    users_processed += 1
                    new_matches = result.get("new_matches_count", 0)
                    total_matches_created += new_matches
                    logger.info(
                        f"✅ Usuario {user.username}: {new_matches} matches creados"
                    )
                else:
                    users_with_errors += 1
                    logger.error(
                        f"❌ Error calculando matches para usuario {user.username}: {result.get('error')}"
                    )

            except Exception as e:
                users_with_errors += 1
                logger.error(f"❌ Error procesando usuario {user.id}: {e}")
                continue

        # Resultado final
        final_result = {
            "success": True,
            "total_users": total_users,
            "users_processed": users_processed,
            "users_with_errors": users_with_errors,
            "total_matches_created": total_matches_created,
            "message": f"Matches calculados para {users_processed}/{total_users} usuarios",
        }

        logger.info(f"🎉 Recálculo global completado: {final_result}")

        # Actualizar progreso final
        self.update_state(
            state="SUCCESS",
            meta={
                "current_step": "Recálculo completado",
                "progress_info": f"{total_matches_created} matches creados para {users_processed} usuarios",
                "progress_percentage": 100,
            },
        )

        return final_result

    except Exception as e:
        logger.error(f"❌ Error en recálculo global de matches: {e}")
        self.update_state(
            state="FAILURE",
            meta={
                "current_step": "Error en recálculo global",
                "progress_info": str(e),
                "progress_percentage": 0,
            },
        )
        return {"success": False, "error": str(e)}


@shared_task(bind=True)
def recalculate_matches_for_user(self, user_id: int):
    """
    Tarea Celery para recalcular matches con progreso.

    Args:
        user_id: ID del usuario

    Returns:
        Dict con estadísticas del recálculo
    """
    try:
        # Actualizar progreso inicial
        self.update_state(
            state="PROGRESS",
            meta={
                "current_step": "Iniciando recálculo",
                "progress_info": "Obteniendo perfil del usuario",
                "progress_percentage": 10,
            },
        )

        # Llamar función core
        result = _recalculate_matches_for_user_core(user_id)

        if result.get("success"):
            # No actualizar el estado final - dejar que Celery use el resultado real
            # El resultado ya contiene toda la información necesaria
            pass
        else:
            # Error
            self.update_state(
                state="FAILURE",
                meta={
                    "current_step": "Error en recálculo",
                    "progress_info": result.get("error", "Error desconocido"),
                    "progress_percentage": 0,
                },
            )

        return result

    except Exception as e:
        logger.error(f"Error en tarea de recálculo para usuario {user_id}: {e}")
        self.update_state(
            state="FAILURE",
            meta={
                "current_step": "Error en recálculo",
                "progress_info": str(e),
                "progress_percentage": 0,
            },
        )
        return {"error": str(e)}


@shared_task(bind=True)
def process_cv_async(
    self, user_id: int, file_path: str, original_filename: str, progress_id: str
):
    """
    Tarea Celery para procesar un CV de forma asíncrona con progreso en tiempo real.

    Args:
        user_id: ID del usuario
        file_path: Ruta al archivo temporal del CV
        original_filename: Nombre original del archivo
        progress_id: ID del tracker de progreso

    Returns:
        Dict con el resultado del procesamiento
    """
    from matching.services.cv_parser import CVParser
    from matching.services.skills_extractor import SkillsExtractor
    from matching.utils.progress_tracker import ProgressTracker
    from django.contrib.auth import get_user_model

    User = get_user_model()
    tracker = ProgressTracker(progress_id)

    try:
        logger.info(
            f"🚀 Iniciando procesamiento asíncrono de CV para usuario {user_id}"
        )
        tracker.update_step(
            "pdf_to_images", "in_progress", "Convirtiendo PDF a imágenes"
        )

        # Parsear CV
        cv_parser = CVParser()
        parse_result = cv_parser.parse_cv(file_path, progress_tracker=tracker)
        parsed_text = parse_result["text"]
        warning_message = parse_result.get("warning_message", "")

        # Verificar que el texto no esté vacío
        if not parsed_text or parsed_text.strip() == "":
            error_msg = "❌ Error de IA: No se pudo extraer texto del CV"
            logger.error(error_msg)
            tracker.set_error(error_msg)
            # Limpiar archivo temporal
            if os.path.exists(file_path):
                os.remove(file_path)
            return {"success": False, "error": error_msg}

        # Extraer habilidades
        tracker.update_step(
            "skills_extraction",
            "in_progress",
            "Analizando texto del CV con keywords...",
        )
        extractor = SkillsExtractor(use_ai=True)  # Habilitar detección con IA
        skills_data = extractor.extract_skills(parsed_text, progress_tracker=tracker)
        skills_count = len(skills_data.get("skills", []))
        extraction_method = skills_data.get("extraction_method", "unknown")
        ai_detected = skills_data.get("details", {}).get("ai_detected", 0)

        logger.info(
            f"✅ Habilidades extraídas: {skills_count} (método: {extraction_method})"
        )
        if ai_detected > 0:
            logger.info(
                f"   └─ {ai_detected} habilidades adicionales detectadas con IA"
            )

        tracker.update_step(
            "skills_extraction",
            "completed",
            f"{skills_count} habilidades detectadas ({extraction_method})",
        )

        # Crear registro en BD
        tracker.update_step(
            "db_save", "in_progress", "Creando registro en base de datos..."
        )
        user = User.objects.get(id=user_id)

        # Copiar archivo temporal a la ubicación final
        from django.core.files import File

        cv = UserCV(user=user)
        logger.info(f"📝 Guardando archivo: {original_filename}")
        with open(file_path, "rb") as f:
            cv.original_file.save(original_filename, File(f), save=False)

        cv.parsed_text = parsed_text
        cv.skills = skills_data
        cv.save()

        logger.info(f"✅ CV guardado en BD con ID: {cv.id}")
        tracker.update_step(
            "db_save", "completed", f"CV guardado exitosamente (ID: {cv.id})"
        )

        # Calcular matches automáticamente usando la misma tarea que el botón
        tracker.update_step(
            "matching", "in_progress", "Iniciando cálculo de coincidencias..."
        )
        try:
            logger.info(f"🔍 Iniciando recalculo de matches para usuario {user_id}")

            # Llamar a la misma tarea que usa el botón "Calcular Matches"
            # Nota: No usamos .delay() porque ya estamos en un worker de Celery
            # En su lugar, llamamos directamente a la función
            result = recalculate_matches_for_user.apply_async(
                args=[user_id],
                countdown=2,  # Esperar 2 segundos para que el CV esté completamente guardado
            )

            logger.info(f"✅ Tarea de recalculo iniciada: {result.id}")
            tracker.update_step(
                "matching",
                "completed",
                "Cálculo de coincidencias iniciado en background",
            )

        except Exception as e:
            logger.error(f"⚠️ Error iniciando recalculo de matches: {e}")
            tracker.update_step(
                "matching",
                "warning",
                f"No se pudo iniciar el cálculo automático de matches",
            )

        # Limpiar archivo temporal
        if os.path.exists(file_path):
            os.remove(file_path)

        # Marcar como completado
        if warning_message:
            tracker.set_warning(warning_message)
        tracker.set_complete("CV procesado exitosamente")

        logger.info(f"✅ CV procesado exitosamente: {cv.id}")

        return {
            "success": True,
            "cv_id": cv.id,
            "skills_count": len(skills_data.get("skills", [])),
            "matching_task_initiated": "result" in locals(),
            "warning_message": warning_message,
        }

    except Exception as e:
        logger.error(f"❌ Error procesando CV: {e}")
        tracker.set_error(str(e))

        # Limpiar archivo temporal
        if os.path.exists(file_path):
            os.remove(file_path)

        return {"success": False, "error": str(e)}
