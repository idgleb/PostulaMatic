"""
Tareas Celery para el scraper stealth de DV Carreras.
"""

import logging
import asyncio
from typing import Dict, Any

from celery import shared_task
from django.conf import settings
from asgiref.sync import async_to_sync

from matching.clients.dvcarreras_stealth import DVCarrerasStealth
from matching.models import JobPosting, ScrapingLog

logger = logging.getLogger(__name__)


async def _run_scraping_stealth(user_id: int, task_id: str = None) -> Dict[str, Any]:
    """
    Función asíncrona para ejecutar el scraping stealth.
    
    Args:
        user_id: ID del usuario
        task_id: ID de la tarea de Celery (para logging)
        
    Returns:
        Diccionario con resultados del scraping
    """
    logger.info(f"Iniciando scraping stealth para usuario {user_id}, task_id: {task_id}")
    
    # VERIFICACIÓN DE CANCELACIÓN: Verificar si la tarea fue cancelada
    from celery import current_app
    try:
        if task_id:
            # Verificar si la tarea fue revocada
            revoked_tasks = current_app.control.inspect().revoked() or {}
            for worker, tasks in revoked_tasks.items():
                if task_id in tasks:
                    logger.info(f"🛑 Tarea {task_id} fue cancelada, deteniendo scraping")
                    return {
                        'success': False,
                        'cancelled': True,
                        'message': 'Scraping cancelado por el usuario',
                        'user_id': user_id
                    }
    except Exception as e:
        logger.warning(f"⚠️ No se pudo verificar cancelación: {e}")
    
    # Crear cliente stealth con task_id
    client = DVCarrerasStealth(user_id=user_id, headless=True, task_id=task_id)
    
    try:
        # Iniciar navegador
        if not await client.start():
            return {
                'success': False,
                'error': 'No se pudo iniciar el navegador stealth',
                'user_id': user_id
            }
        
        # Realizar login
        if not await client.login():
            return {
                'success': False,
                'error': 'Login fallido',
                'user_id': user_id
            }
        
        # Scrapear ofertas
        jobs = await client.scrape_job_board(max_pages=1)
        
        # Procesar ofertas encontradas
        new_jobs = 0
        saved_jobs = 0
        
        for job_data in jobs:
            try:
                # Verificar si ya existe
                from asgiref.sync import sync_to_async
                import hashlib
                
                # Crear ID único basado en título + descripción
                unique_id = hashlib.md5(
                    f"{job_data['title']}_{job_data['description'][:100]}".encode()
                ).hexdigest()
                
                existing_job = await sync_to_async(JobPosting.objects.filter(
                    external_id=f"stealth_{unique_id}"
                ).first)()
                
                if not existing_job:
                    # Crear nueva oferta
                    await sync_to_async(JobPosting.objects.create)(
                        external_id=f"stealth_{unique_id}",
                        title=job_data['title'],
                        description=job_data['description'],
                        email=job_data.get('email_text', ''),
                        raw_html=job_data.get('raw_html', ''),
                        source='dvcarreras_stealth'
                    )
                    new_jobs += 1
                    saved_jobs += 1  # Solo contar las que realmente se guardaron
                else:
                    # La oferta ya existe, no contarla como guardada
                    logger.debug(f"Oferta duplicada omitida: {job_data['title'][:50]}")
                
            except Exception as e:
                logger.error(f"Error guardando oferta: {e}")
                continue
        
        # Calcular duplicadas
        duplicated_jobs = len(jobs) - saved_jobs
        
        logger.info(f"Scraping stealth completado para usuario {user_id}: {new_jobs} nuevas, {saved_jobs} guardadas, {duplicated_jobs} duplicadas")
        
        # Loggear resumen en la base de datos para que el usuario lo vea
        from asgiref.sync import sync_to_async
        try:
            # Crear mensaje más claro según el caso
            if saved_jobs == 0:
                summary_msg = f"📊 Resumen: {len(jobs)} ofertas encontradas, todas ya existían en la base de datos"
            elif duplicated_jobs > 0:
                summary_msg = f"📊 Resumen: {len(jobs)} ofertas encontradas, {saved_jobs} nuevas guardadas, {duplicated_jobs} duplicadas omitidas"
            else:
                summary_msg = f"📊 Resumen: {len(jobs)} ofertas encontradas, {saved_jobs} nuevas guardadas"
            
            await sync_to_async(ScrapingLog.objects.create)(
                user_id=user_id,
                message=summary_msg,
                log_type='success',
                task_id=task_id
            )
        except Exception:
            pass  # No crítico si falla el log
        
        return {
            'success': True,
            'new_jobs': new_jobs,
            'saved_jobs': saved_jobs,
            'total_found': len(jobs),
            'user_id': user_id
        }
        
    finally:
        # Cerrar navegador
        await client.close()


@shared_task(bind=True, max_retries=3)
def scrape_dvcarreras_jobs_stealth(self, user_id: int) -> Dict[str, Any]:
    """
    Tarea Celery para scrapear DV Carreras usando el cliente stealth.
    
    Args:
        user_id: ID del usuario
        
    Returns:
        Diccionario con resultados del scraping
    """
    try:
        # Obtener el task_id de Celery
        task_id = self.request.id
        logger.info(f"Tarea de scraping stealth iniciada: {task_id}")
        
        # Ejecutar la función asíncrona con el task_id
        return asyncio.run(_run_scraping_stealth(user_id, task_id=task_id))
            
    except Exception as e:
        logger.error(f"Error en scraping stealth para usuario {user_id}: {e}")
        
        # Reintentar si es posible
        if self.request.retries < self.max_retries:
            logger.info(f"Reintentando scraping stealth (intento {self.request.retries + 1})")
            raise self.retry(countdown=60 * (self.request.retries + 1))
        
        return {
            'success': False,
            'error': str(e),
            'user_id': user_id
        }


@shared_task(bind=True, max_retries=2)
def test_stealth_login(self, user_id: int) -> Dict[str, Any]:
    """
    Tarea para probar el login stealth.
    
    Args:
        user_id: ID del usuario
        
    Returns:
        Diccionario con resultado del test
    """
    try:
        logger.info(f"Probando login stealth para usuario {user_id}")
        
        # Crear cliente stealth
        client = DVCarrerasStealth(user_id=user_id, headless=True)
        
        try:
            # Iniciar navegador
            if not client.start():
                return {
                    'success': False,
                    'message': 'No se pudo iniciar el navegador stealth',
                    'user_id': user_id
                }
            
            # Realizar login
            if client.login():
                return {
                    'success': True,
                    'message': 'Login stealth exitoso',
                    'user_id': user_id
                }
            else:
                return {
                    'success': False,
                    'message': 'Login stealth fallido',
                    'user_id': user_id
                }
                
        finally:
            # Cerrar navegador
            client.close()
            
    except Exception as e:
        logger.error(f"Error en test de login stealth para usuario {user_id}: {e}")
        
        return {
            'success': False,
            'message': f'Error: {str(e)}',
            'user_id': user_id
        }
