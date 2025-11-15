"""
Tareas de Celery limpias - solo con FlareSolverr
"""

import asyncio
import logging
from datetime import datetime

# Importar sync_to_async para usar ORM en contexto async
from asgiref.sync import sync_to_async
from celery import shared_task

from .models import JobPosting, ScrapingLog, UserCV, UserProfile
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

            async with DVCarrerasPlaywrightFlareSolverr(
                username=user_profile.get_dv_username(),
                password=user_profile.get_dv_password(),
                log_callback=log_callback,
            ) as client:

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
