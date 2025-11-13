"""
Tareas avanzadas de Celery - DEPRECADAS
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def scrape_dvcarreras_jobs_advanced(self, user_id: int):
    """
    Tarea AVANZADA DEPRECADA para scrapear ofertas de INTRANET DAVINCI.
    Usar scrape_dvcarreras_jobs_playwright en su lugar.

    Args:
        user_id: ID del usuario que tiene las credenciales

    Returns:
        Dict con mensaje de redirección
    """
    logger.warning(
        f"scrape_dvcarreras_jobs_advanced está deprecada para usuario {user_id}"
    )
    return {
        "error": "Esta función está deprecada. Usar scrape_dvcarreras_jobs_playwright en su lugar.",
        "redirect_to": "scrape_dvcarreras_jobs_playwright",
    }
