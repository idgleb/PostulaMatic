"""
Tareas de Celery para scraping avanzado de dvcarreras.davinci.edu.ar
Usa técnicas anti-detección y rotación de headers.
"""

import logging

from celery import shared_task

from .clients.dvcarreras_advanced import (DVCarrerasAdvancedClient)
from .models import JobPosting, UserCV, UserProfile
from .services.matching import matching_service

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def scrape_dvcarreras_jobs_advanced(self, user_id: int):
    """
    Tarea AVANZADA para scrapear ofertas de dvcarreras con técnicas anti-detección.

    Args:
        user_id: ID del usuario que tiene las credenciales

    Returns:
        Dict con estadísticas del scraping
    """
    try:
        logger.info(f"Iniciando scraping AVANZADO de dvcarreras para usuario {user_id}")

        # Obtener perfil del usuario
        try:
            user_profile = UserProfile.objects.get(user_id=user_id)
        except UserProfile.DoesNotExist:
            logger.error(f"Usuario {user_id} no tiene perfil configurado")
            raise Exception("Usuario sin perfil configurado")

        # Verificar credenciales
        if not user_profile.dv_username or not user_profile.dv_password:
            logger.error(
                f"Usuario {user_id} no tiene credenciales de dvcarreras configuradas"
            )
            raise Exception("Credenciales de dvcarreras no configuradas")

        # Realizar scraping con cliente avanzado
        with DVCarrerasAdvancedClient(
            username=user_profile.get_dv_username(),
            password=user_profile.get_dv_password(),
            use_proxies=False,  # Cambiar a True si tienes proxies configurados
        ) as client:

            # Login con técnicas avanzadas
            if not client.login():
                logger.error(f"Login AVANZADO fallido para usuario {user_id}")
                raise Exception("Login fallido en dvcarreras (método avanzado)")

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
                            "company": job_data.company,
                            "location": job_data.location,
                            "description": job_data.description,
                            "url": job_data.url,
                            "source": "dvcarreras_advanced",
                            "posted_at": job_data.posted_at,
                            "raw_html": job_data.raw_html,
                        },
                    )

                    saved_jobs += 1
                    if created:
                        new_jobs += 1
                        logger.info(
                            f"Nueva oferta guardada: {job_posting.title} en {job_posting.company}"
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


@shared_task(bind=True)
def process_cv_file_advanced(self, cv_id: int):
    """
    Tarea AVANZADA para procesar un CV específico.

    Args:
        cv_id: ID del CV a procesar

    Returns:
        Dict con resultado del procesamiento
    """
    try:
        logger.info(f"Iniciando procesamiento AVANZADO de CV {cv_id}")

        # Obtener el CV
        try:
            cv = UserCV.objects.get(id=cv_id)
        except UserCV.DoesNotExist:
            logger.error(f"CV {cv_id} no encontrado")
            raise Exception(f"CV {cv_id} no encontrado")

        # Procesar CV con técnicas avanzadas
        from .services.cv_parser import cv_parser
        from .services.skills_extractor import skills_extractor

        try:
            # Parsear CV
            parsed_text = cv_parser.parse_cv(cv.original_file.path)
            cv.parsed_text = parsed_text

            # Extraer habilidades
            skills = skills_extractor.extract_skills(parsed_text)
            cv.skills = skills

            # Marcar como procesado
            cv.is_processed = True
            cv.save()

            logger.info(f"CV {cv_id} procesado exitosamente (método avanzado)")

            return {
                "success": True,
                "cv_id": cv_id,
                "skills_extracted": len(skills.get("technical", [])),
                "method": "advanced",
                "message": "CV procesado con método avanzado",
            }

        except Exception as e:
            logger.error(f"Error procesando CV {cv_id}: {e}")
            raise

    except Exception as e:
        logger.error(f"Error en procesamiento AVANZADO de CV {cv_id}: {e}")
        raise
