"""
Tareas Celery para el scraper stealth de DV Carreras.
"""

import logging
import asyncio
from typing import Dict, Any, Optional

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from asgiref.sync import async_to_sync

from matching.clients.dvcarreras_stealth import DVCarrerasStealth
from matching.models import JobPosting, ScrapingLog, UserProfile

logger = logging.getLogger(__name__)


def get_next_user_for_scraping() -> Optional[int]:
    """
    Obtiene el siguiente usuario con credenciales válidas y verificadas en rotación (round-robin).
    Solo usa usuarios con dv_connection_status = 'verified'.
    
    Returns:
        ID del usuario o None si no hay usuarios con credenciales verificadas
    """
    # Obtener todos los usuarios con credenciales de DV configuradas Y VERIFICADAS
    users_with_credentials = UserProfile.objects.filter(
        dv_username__isnull=False,
        dv_password__isnull=False,
        dv_connection_status='verified'  # Solo usuarios verificados
    ).exclude(
        dv_username='',
        dv_password=''
    ).values_list('user_id', flat=True).order_by('user_id')
    
    if not users_with_credentials:
        logger.warning("⚠️ No hay usuarios con credenciales VERIFICADAS de DV")
        logger.warning("💡 Verifica las credenciales en el perfil de cada usuario")
        return None
    
    users_list = list(users_with_credentials)
    
    # Obtener el último usuario usado desde cache
    cache_key = 'scraper_last_user_id'
    last_user_id = cache.get(cache_key)
    
    # Encontrar el siguiente usuario en la lista
    if last_user_id and last_user_id in users_list:
        current_index = users_list.index(last_user_id)
        next_index = (current_index + 1) % len(users_list)
        next_user_id = users_list[next_index]
    else:
        # Si no hay último usuario o no está en la lista, usar el primero
        next_user_id = users_list[0]
    
    # Guardar el usuario usado en cache (expira en 1 día)
    cache.set(cache_key, next_user_id, 86400)
    
    logger.info(f"🔄 Rotación de usuarios: Usando usuario {next_user_id} de {len(users_list)} verificados disponibles")
    
    return next_user_id


async def _run_scraping_stealth(user_id: int, task_id: str = None, requesting_user_id: int = None) -> Dict[str, Any]:
    """
    Función asíncrona para ejecutar el scraping stealth.
    
    Args:
        user_id: ID del usuario cuyas credenciales se usarán
        task_id: ID de la tarea de Celery (para logging)
        requesting_user_id: ID del usuario que inició el scraping (para logs duplicados)
        
    Returns:
        Diccionario con resultados del scraping
    """
    # Función helper para guardar logs globales (sin user_id específico)
    async def save_log(message: str, log_type: str = 'info'):
        """Guarda un log global para el task_id (visible para todos los admins)"""
        from asgiref.sync import sync_to_async
        
        # Guardar log con user_id del usuario cuyas credenciales se usan
        # (para mantener compatibilidad con el modelo, pero los admins verán todos los logs por task_id)
        await sync_to_async(ScrapingLog.objects.create)(
            user_id=user_id,
            message=message,
            log_type=log_type,
            task_id=task_id
        )
    
    # Separador visual
    logger.info("=" * 80)
    logger.info("🚀 NUEVA EJECUCIÓN DE SCRAPING")
    logger.info("=" * 80)
    
    # Obtener información del usuario para logging (solo en consola por ahora)
    from asgiref.sync import sync_to_async
    from django.contrib.auth.models import User
    
    try:
        user = await sync_to_async(User.objects.get)(id=user_id)
        profile = await sync_to_async(UserProfile.objects.get)(user_id=user_id)
        dv_username = profile.dv_username or "N/A"
        
        logger.info(f"👤 Usuario del Sistema: {user.get_full_name() or user.username} (ID: {user_id})")
        logger.info(f"📧 Email: {user.email}")
        logger.info(f"🎓 Login DAVINCI: {dv_username}")
        logger.info(f"📋 Task ID: {task_id}")
        
        # Si hay un requesting_user diferente, mostrarlo
        if requesting_user_id and requesting_user_id != user_id:
            requesting_user = await sync_to_async(User.objects.get)(id=requesting_user_id)
            requesting_name = requesting_user.get_full_name() or requesting_user.username
            logger.info(f"🖥️  Solicitado por: {requesting_name} (ID: {requesting_user_id})")
        
        logger.info("-" * 80)
    except Exception as e:
        logger.error(f"⚠️ Error obteniendo información del usuario: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
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
        
        # ⚡ GUARDAR LOG DE CREDENCIALES DESPUÉS de iniciar navegador
        try:
            user = await sync_to_async(User.objects.get)(id=user_id)
            profile = await sync_to_async(UserProfile.objects.get)(user_id=user_id)
            dv_username = profile.dv_username or "N/A"
            user_full_name = user.get_full_name() or user.username
            user_email = user.email or "N/A"
            
            info_message = f"🔐 Usando credenciales de: {user_full_name} (Email: {user_email}, Login DV: {dv_username})"
            
            # Si hay un requesting_user diferente, agregarlo al mensaje
            if requesting_user_id and requesting_user_id != user_id:
                requesting_user = await sync_to_async(User.objects.get)(id=requesting_user_id)
                requesting_name = requesting_user.get_full_name() or requesting_user.username
                info_message += f" | Solicitado por: {requesting_name}"
            
            await save_log(info_message, 'info')
            logger.info(f"✅ Log de credenciales guardado en BD: {info_message}")
        except Exception as e:
            logger.error(f"⚠️ Error guardando log de credenciales: {e}")
        
        # Realizar login
        login_result = await client.login()
        if not login_result:
            # Login falló - marcar credenciales como no verificadas
            from asgiref.sync import sync_to_async
            
            try:
                profile = await sync_to_async(UserProfile.objects.get)(user_id=user_id)
                await sync_to_async(profile.set_dv_connection_verified)(False)
                await sync_to_async(profile.save)()
                
                logger.error(f"❌ Login fallido para usuario {user_id} - Credenciales marcadas como NO VERIFICADAS")
                
                await save_log(
                    f"❌ Login fallido - Credenciales incorrectas. Usuario marcado como no verificado.",
                    'error'
                )
            except Exception as e:
                logger.error(f"Error actualizando estado de verificación: {e}")
            
            return {
                'success': False,
                'error': 'Login fallido - Credenciales incorrectas',
                'user_id': user_id,
                'credentials_marked_invalid': True
            }
        
        # Login exitoso - marcar credenciales como verificadas
        from asgiref.sync import sync_to_async
        try:
            profile = await sync_to_async(UserProfile.objects.get)(user_id=user_id)
            if profile.dv_connection_status != 'verified':
                await sync_to_async(profile.set_dv_connection_verified)(True)
                await sync_to_async(profile.save)()
                logger.info(f"✅ Credenciales verificadas para usuario {user_id}")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo actualizar estado de verificación: {e}")
        
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
            
            await save_log(summary_msg, 'success')
        except Exception:
            pass  # No crítico si falla el log
        
        # ✅ NUEVO: Iniciar cálculo automático de matches para TODOS los usuarios
        if saved_jobs > 0:  # Solo si se guardaron ofertas nuevas
            try:
                logger.info("🧮 Iniciando cálculo automático de matches para todos los usuarios...")
                await save_log("🧮 Iniciando cálculo de matches para todos los usuarios...", 'info')
                
                # Importar la nueva tarea
                from matching.tasks import recalculate_matches_for_all_users
                
                # Iniciar tarea en background (no esperar resultado)
                match_task = await sync_to_async(recalculate_matches_for_all_users.delay)()
                
                logger.info(f"✅ Tarea de cálculo de matches iniciada: {match_task.id}")
                await save_log(f"✅ Cálculo de matches iniciado en background (task: {match_task.id})", 'success')
                
            except Exception as e:
                logger.error(f"⚠️ Error iniciando cálculo de matches: {e}")
                await save_log(f"⚠️ No se pudo iniciar cálculo automático de matches: {str(e)}", 'warning')
        else:
            logger.info("ℹ️ No se guardaron ofertas nuevas, omitiendo cálculo de matches")
        
        # Separador final
        logger.info("=" * 80)
        logger.info("✅ SCRAPING COMPLETADO EXITOSAMENTE")
        logger.info("=" * 80)
        
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
def scrape_dvcarreras_jobs_stealth(self, user_id: int = None, requesting_user_id: int = None) -> Dict[str, Any]:
    """
    Tarea Celery para scrapear DV Carreras usando rotación automática de usuarios.
    Esta tarea usa las credenciales de diferentes usuarios en cada ejecución
    para distribuir la carga y evitar bloqueos.
    
    Args:
        user_id: ID del usuario cuyas credenciales se usarán (opcional, si no se proporciona usa rotación automática)
        requesting_user_id: ID del usuario que inició el scraping desde la UI (para logs)
        
    Returns:
        Diccionario con resultados del scraping
    """
    from matching.services.scraping_lock import scraping_lock
    
    # Obtener el task_id de Celery
    task_id = self.request.id
    
    # ============================================================
    # 🔒 LOCK GLOBAL: Adquirir lock antes de empezar
    # ============================================================
    lock_acquired = scraping_lock.acquire_lock(
        task_id=task_id,
        user_id=requesting_user_id,
        source='scheduled' if requesting_user_id is None else 'manual'
    )
    
    if not lock_acquired:
        logger.warning(f"⚠️ No se pudo adquirir lock para scraping (task={task_id})")
        return {
            'success': False,
            'error': 'Ya hay un scraping en curso',
            'locked': True,
            'user_id': None
        }
    
    try:
        # Si no se proporciona user_id, usar rotación automática
        if user_id is None:
            user_id = get_next_user_for_scraping()
            
            if not user_id:
                logger.error("No hay usuarios con credenciales disponibles para scraping")
                return {
                    'success': False,
                    'error': 'No hay usuarios con credenciales configuradas',
                    'user_id': None
                }
            
            logger.info(f"🔄 Usando rotación automática: Usuario {user_id}")
        else:
            logger.info(f"📌 Usando usuario específico: {user_id}")
        
        logger.info(f"🌍 Scraping iniciado con usuario {user_id} (task: {task_id})")
        
        # Ejecutar la función asíncrona con el task_id y requesting_user_id
        result = asyncio.run(_run_scraping_stealth(user_id, task_id=task_id, requesting_user_id=requesting_user_id))
        
        # Agregar información de rotación al resultado
        result['rotation_used'] = user_id is None
        result['credentials_from_user'] = user_id
        
        return result
            
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
    
    finally:
        # ============================================================
        # 🔓 LOCK GLOBAL: Liberar lock al terminar (éxito o error)
        # ============================================================
        scraping_lock.release_lock(task_id)
        logger.info(f"🔓 Lock liberado para task={task_id}")


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


@shared_task(bind=True)
def check_and_run_scheduled_scraping(self):
    """
    Tarea periódica que ejecuta el scraping programado.
    El CrontabSchedule de django-celery-beat maneja cuándo ejecutar esta tarea,
    por lo que ya no necesitamos verificar la hora manualmente.
    """
    from matching.models import ScheduledScraping
    from django.utils import timezone
    
    try:
        # Obtener configuración
        config = ScheduledScraping.objects.first()
        
        if not config or not config.is_enabled:
            logger.debug("Scraping programado desactivado o no configurado")
            return {
                'success': False,
                'message': 'Scraping programado desactivado o no configurado'
            }
        
        now = timezone.now()
        local_now = timezone.localtime(now)
        scheduled_time = config.scheduled_time
        
        # ============================================================
        # 🔍 VERIFICAR CONSISTENCIA: CrontabSchedule vs ScheduledScraping
        # ============================================================
        from django_celery_beat.models import PeriodicTask
        
        periodic_task = PeriodicTask.objects.filter(
            task='matching.tasks_stealth.check_and_run_scheduled_scraping'
        ).first()
        
        if periodic_task and periodic_task.crontab:
            expected_hour = config.scheduled_time.hour
            expected_minute = config.scheduled_time.minute
            actual_hour = int(periodic_task.crontab.hour)
            actual_minute = int(periodic_task.crontab.minute)
            
            if actual_hour != expected_hour or actual_minute != expected_minute:
                logger.warning(
                    f"⚠️ Inconsistencia detectada entre ScheduledScraping y CrontabSchedule: "
                    f"ScheduledScraping={expected_hour:02d}:{expected_minute:02d}, "
                    f"CrontabSchedule={actual_hour:02d}:{actual_minute:02d}"
                )
                # Opcional: Auto-corregir la inconsistencia
                # periodic_task.crontab = CrontabSchedule.objects.get_or_create(...)
        
        # ============================================================
        # 🔒 LOCK GLOBAL: Verificar si ya hay un scraping en curso
        # ============================================================
        from matching.services.scraping_lock import scraping_lock
        
        if scraping_lock.is_locked():
            active_scraping = scraping_lock.get_active_scraping()
            task_id = active_scraping.get('task_id') if active_scraping else 'unknown'
            logger.info(f"⏸️ Scraping programado omitido: ya hay un scraping activo (task={task_id})")
            return {
                'success': False,
                'message': f'Ya hay un scraping en curso (task={task_id})',
                'locked': True
            }
        
        # Verificar si ya se ejecutó hoy (prevenir ejecuciones duplicadas)
        if config.last_run:
            last_run_local = timezone.localtime(config.last_run)
            last_run_date = last_run_local.date()
            today = local_now.date()
            
            # Si ya se ejecutó hoy, no ejecutar de nuevo
            if last_run_date == today:
                logger.info(f"✋ Scraping ya ejecutado hoy a las {last_run_local.strftime('%H:%M:%S')}")
                return {
                    'success': False,
                    'message': f'Scraping ya ejecutado hoy a las {last_run_local.strftime("%H:%M:%S")}'
                }
        
        # Ejecutar scraping
        logger.info(f"🕒 Iniciando scraping programado a las {local_now.strftime('%H:%M:%S')}")
        
        # Llamar a la tarea de scraping global
        task = scrape_dvcarreras_jobs_stealth.delay()
        
        # Guardar task_id en cache para que todos los admins lo vean (legacy, ahora usa lock)
        from django.core.cache import cache as django_cache
        django_cache.set('current_scraping_task_id', task.id, timeout=3600)  # 1 hora
        
        # Actualizar última ejecución
        config.last_run = now
        config.save()
        
        logger.info(f"✅ Scraping programado iniciado exitosamente. Task ID: {task.id}")
        
        return {
            'success': True,
            'message': f'Scraping programado iniciado a las {local_now.strftime("%H:%M:%S")}',
            'task_id': task.id,
            'scheduled_time': scheduled_time.strftime('%H:%M')
        }
        
    except Exception as e:
        logger.error(f"❌ Error en scraping programado: {e}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }
