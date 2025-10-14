"""
Tareas de Celery para envío automático de emails.
"""

import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from celery import shared_task
from celery.exceptions import Retry
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

from matching.models import UserCV, JobPosting, MatchScore, UserProfile, EmailSentLog
from .services.email_personalizer import email_personalization_service
from .services.cv_personalizer import cv_personalization_service
from .services.ai_service import ai_email_service

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_personalized_email_task(
    self, 
    user_id: int, 
    cv_id: int, 
    job_id: int, 
    email_template: str = 'base',
    ai_provider: str = 'openai'
) -> Dict:
    """
    Tarea para enviar email personalizado a un puesto específico.
    
    Args:
        user_id: ID del usuario
        cv_id: ID del CV a usar
        job_id: ID del puesto de trabajo
        email_template: Template de email a usar
        ai_provider: Proveedor de IA a usar
        
    Returns:
        Dict con resultado del envío
    """
    try:
        # Obtener objetos del modelo
        user = User.objects.get(id=user_id)
        user_cv = UserCV.objects.get(id=cv_id, user=user)
        job_posting = JobPosting.objects.get(id=job_id)
        
        logger.info(f"Iniciando envío de email para usuario {user_id}, CV {cv_id}, puesto {job_id}")
        
        # Verificar límites de envío diario
        daily_limit = check_daily_email_limit(user)
        if not daily_limit['can_send']:
            return {
                'success': False,
                'error': f"Límite diario alcanzado: {daily_limit['sent_today']}/{daily_limit['daily_limit']}",
                'retry_after': daily_limit['retry_after']
            }
        
        # Generar email personalizado
        email_result = generate_personalized_email(
            user, user_cv, job_posting, email_template, ai_provider
        )
        
        if not email_result['success']:
            return {
                'success': False,
                'error': f"Error generando email: {email_result['error']}",
                'retry': True
            }
        
        # Personalizar CV adjunto
        cv_result = cv_personalization_service.personalize_cv_for_job(
            user_cv, job_posting, email_result.get('user_profile')
        )
        
        # Enviar email
        send_result = send_email_with_attachments(
            user, job_posting, email_result, cv_result
        )
        
        if send_result['success']:
            # Registrar envío exitoso
            record_email_sent(user, user_cv, job_posting, email_result, send_result)
            
            # Aplicar pausa aleatoria para emular comportamiento humano
            apply_random_delay()
            
            return {
                'success': True,
                'message': 'Email enviado exitosamente',
                'email_id': send_result.get('email_id'),
                'sent_at': timezone.now().isoformat()
            }
        else:
            return {
                'success': False,
                'error': f"Error enviando email: {send_result['error']}",
                'retry': True
            }
            
    except User.DoesNotExist:
        logger.error(f"Usuario {user_id} no encontrado")
        return {'success': False, 'error': 'Usuario no encontrado'}
        
    except UserCV.DoesNotExist:
        logger.error(f"CV {cv_id} no encontrado para usuario {user_id}")
        return {'success': False, 'error': 'CV no encontrado'}
        
    except JobPosting.DoesNotExist:
        logger.error(f"Puesto {job_id} no encontrado")
        return {'success': False, 'error': 'Puesto no encontrado'}
        
    except Exception as e:
        logger.error(f"Error inesperado en envío de email: {e}")
        
        # Reintentar si es un error temporal
        if self.request.retries < self.max_retries:
            logger.info(f"Reintentando envío (intento {self.request.retries + 1})")
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        return {
            'success': False,
            'error': f"Error inesperado: {str(e)}",
            'retry': False
        }


@shared_task(bind=True, max_retries=2)
def send_bulk_emails_task(
    self, 
    user_id: int, 
    job_ids: List[int], 
    email_template: str = 'base',
    ai_provider: str = 'openai',
    batch_size: int = 5,
    delay_between_batches: int = 300  # 5 minutos
) -> Dict:
    """
    Tarea para enviar emails masivos a múltiples puestos.
    
    Args:
        user_id: ID del usuario
        job_ids: Lista de IDs de puestos
        email_template: Template de email a usar
        ai_provider: Proveedor de IA a usar
        batch_size: Tamaño del lote por batch
        delay_between_batches: Delay entre batches en segundos
        
    Returns:
        Dict con resultado del envío masivo
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Obtener CV principal del usuario
        user_cv = UserCV.objects.filter(user=user).first()
        if not user_cv:
            return {'success': False, 'error': 'Usuario no tiene CV'}
        
        results = []
        successful_sends = 0
        failed_sends = 0
        
        # Procesar en batches
        for i in range(0, len(job_ids), batch_size):
            batch = job_ids[i:i + batch_size]
            
            logger.info(f"Procesando batch {i//batch_size + 1} con {len(batch)} puestos")
            
            for job_id in batch:
                try:
                    # Enviar email individual
                    result = send_personalized_email_task.delay(
                        user_id, user_cv.id, job_id, email_template, ai_provider
                    )
                    
                    results.append({
                        'job_id': job_id,
                        'task_id': result.id,
                        'status': 'queued'
                    })
                    
                except Exception as e:
                    logger.error(f"Error enviando email para puesto {job_id}: {e}")
                    results.append({
                        'job_id': job_id,
                        'status': 'failed',
                        'error': str(e)
                    })
                    failed_sends += 1
            
            # Pausa entre batches
            if i + batch_size < len(job_ids):
                logger.info(f"Esperando {delay_between_batches} segundos antes del siguiente batch")
                time.sleep(delay_between_batches)
        
        return {
            'success': True,
            'total_jobs': len(job_ids),
            'successful_queued': len(results) - failed_sends,
            'failed': failed_sends,
            'results': results,
            'completed_at': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en envío masivo: {e}")
        return {
            'success': False,
            'error': f"Error en envío masivo: {str(e)}"
        }


@shared_task
def process_matching_and_send_emails_task(
    user_id: int,
    min_match_score: int = 70,
    email_template: str = 'base',
    ai_provider: str = 'openai'
) -> Dict:
    """
    Tarea para procesar matching automático y enviar emails.
    
    Args:
        user_id: ID del usuario
        min_match_score: Score mínimo de coincidencia
        email_template: Template de email a usar
        ai_provider: Proveedor de IA a usar
        
    Returns:
        Dict con resultado del procesamiento
    """
    try:
        user = User.objects.get(id=user_id)
        user_cv = UserCV.objects.filter(user=user).first()
        
        if not user_cv:
            return {'success': False, 'error': 'Usuario no tiene CV'}
        
        # Obtener matches con score alto
        high_score_matches = MatchScore.objects.filter(
            cv__user=user,
            score__gte=min_match_score
        ).select_related('job_posting')
        
        job_ids = [match.job_posting.id for match in high_score_matches]
        
        if not job_ids:
            return {
                'success': True,
                'message': f'No se encontraron matches con score >= {min_match_score}',
                'total_jobs': 0
            }
        
        # Enviar emails masivos
        bulk_result = send_bulk_emails_task.delay(
            user_id, job_ids, email_template, ai_provider
        )
        
        return {
            'success': True,
            'message': f'Procesando {len(job_ids)} matches con score >= {min_match_score}',
            'total_jobs': len(job_ids),
            'bulk_task_id': bulk_result.id
        }
        
    except Exception as e:
        logger.error(f"Error procesando matching automático: {e}")
        return {
            'success': False,
            'error': f"Error procesando matching: {str(e)}"
        }


def generate_personalized_email(
    user: User, 
    user_cv: UserCV, 
    job_posting: JobPosting, 
    email_template: str,
    ai_provider: str
) -> Dict:
    """Genera email personalizado usando IA."""
    try:
        # Crear perfil de usuario
        user_profile = {
            'name': f"{user.first_name} {user.last_name}".strip() or user.username,
            'email': user.email,
            'experience_summary': f"Profesional con {len(user_cv.skills_list)} habilidades técnicas"
        }
        
        # Generar email personalizado
        result = email_personalization_service.generate_personalized_email(
            user=user,
            user_cv=user_cv,
            job_posting=job_posting,
            template_type=email_template,
            ai_provider=ai_provider
        )
        
        return {
            'success': True,
            'email_content': result,
            'user_profile': user_profile
        }
        
    except Exception as e:
        logger.error(f"Error generando email personalizado: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def send_email_with_attachments(
    user: User,
    job_posting: JobPosting,
    email_result: Dict,
    cv_result: Dict
) -> Dict:
    """Envía email con CV adjunto usando credenciales del usuario."""
    try:
        # Obtener perfil del usuario
        try:
            user_profile = user.profile
        except UserProfile.DoesNotExist:
            logger.error(f"Usuario {user.id} no tiene perfil configurado")
            return {
                'success': False,
                'error': 'Usuario no tiene perfil SMTP configurado'
            }
        
        # Verificar que tenga configuración SMTP
        if not user_profile.smtp_host or not user_profile.smtp_username:
            logger.error(f"Usuario {user.id} no tiene configuración SMTP completa")
            return {
                'success': False,
                'error': 'Configuración SMTP incompleta. Configura tu servidor SMTP en el perfil.'
            }
        
        # Obtener contenido del email (EmailContent object)
        email_content = email_result['email_content']
        
        # Configurar email
        subject = email_content.subject or f'Aplicación para {job_posting.title}'
        body_text = email_content.body or ''
        
        # Crear email
        email = EmailMultiAlternatives(
            subject=subject,
            body=body_text,
            from_email=user_profile.smtp_username,  # Usar email del perfil SMTP
            to=[job_posting.email] if job_posting.email else []
        )
        
        # Convertir texto plano a HTML básico
        body_html = body_text.replace('\n', '<br>')
        email.attach_alternative(body_html, "text/html")
        
        # Adjuntar CV personalizado si está disponible
        if cv_result['success'] and cv_result.get('personalized_file'):
            # Por ahora usar el archivo original
            # En el futuro se puede implementar generación de CV personalizado
            pass
        
        # Configurar conexión SMTP personalizada
        connection = get_user_smtp_connection(user_profile)
        
        # Enviar email con conexión personalizada
        email.send(connection=connection)
        
        return {
            'success': True,
            'message_id': email.extra_headers.get('Message-ID'),
            'sent_to': job_posting.email
        }
        
    except Exception as e:
        logger.error(f"Error enviando email: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def get_user_smtp_connection(user_profile: UserProfile):
    """Crea una conexión SMTP personalizada para el usuario."""
    from django.core.mail.backends.smtp import EmailBackend
    
    # Configuración SMTP del usuario
    smtp_config = {
        'host': user_profile.smtp_host,
        'port': user_profile.smtp_port,
        'username': user_profile.smtp_username,
        'password': user_profile.get_smtp_password(),  # Desencriptar contraseña
        'use_tls': user_profile.smtp_use_tls,
        'use_ssl': user_profile.smtp_use_ssl,
        'fail_silently': False,
    }
    
    logger.info(f"Configurando SMTP para {user_profile.smtp_username} en {user_profile.smtp_host}:{user_profile.smtp_port}")
    
    return EmailBackend(**smtp_config)


def check_daily_email_limit(user: User) -> Dict:
    """Verifica límites de envío diario."""
    try:
        # Obtener configuración del usuario (si existe)
        daily_limit = getattr(user, 'daily_email_limit', 50)  # Límite por defecto
        
        # Contar emails enviados hoy
        today = timezone.now().date()
        sent_today = EmailSentLog.objects.filter(
            user=user,
            sent_at__date=today
        ).count()
        
        can_send = sent_today < daily_limit
        retry_after = None
        
        if not can_send:
            # Calcular cuándo se puede enviar de nuevo (mañana)
            tomorrow = today + timedelta(days=1)
            retry_after = timezone.make_aware(datetime.combine(tomorrow, datetime.min.time()))
        
        return {
            'can_send': can_send,
            'sent_today': sent_today,
            'daily_limit': daily_limit,
            'remaining': daily_limit - sent_today,
            'retry_after': retry_after
        }
        
    except Exception as e:
        logger.error(f"Error verificando límite diario: {e}")
        return {
            'can_send': True,
            'sent_today': 0,
            'daily_limit': 50,
            'remaining': 50,
            'retry_after': None
        }


def apply_random_delay():
    """Aplica pausa aleatoria para emular comportamiento humano."""
    delay = random.uniform(30, 120)  # Entre 30 segundos y 2 minutos
    logger.info(f"Aplicando pausa aleatoria de {delay:.1f} segundos")
    time.sleep(delay)


def record_email_sent(
    user: User,
    user_cv: UserCV,
    job_posting: JobPosting,
    email_result: Dict,
    send_result: Dict
):
    """Registra el envío de email en el log."""
    try:
        from .models import EmailSentLog
        
        # Obtener contenido del email (EmailContent object)
        email_content = email_result['email_content']
        
        EmailSentLog.objects.create(
            user=user,
            cv=user_cv,
            job_posting=job_posting,
            email_subject=email_content.subject or '',
            email_body=email_content.body or '',
            sent_to=job_posting.email,
            message_id=send_result.get('message_id'),
            status='sent',
            sent_at=timezone.now()
        )
        
        logger.info(f"Email registrado en log para usuario {user.id}, puesto {job_posting.id}")
        
    except Exception as e:
        logger.error(f"Error registrando email en log: {e}")


@shared_task
def cleanup_old_email_logs_task(days_to_keep: int = 30):
    """Limpia logs de emails antiguos."""
    try:
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        from .models import EmailSentLog
        deleted_count = EmailSentLog.objects.filter(
            sent_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Limpiados {deleted_count} logs de emails antiguos")
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error limpiando logs antiguos: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def send_email_reminder_task(user_id: int, days_since_last_activity: int = 7):
    """Envía recordatorio para usuarios inactivos."""
    try:
        user = User.objects.get(id=user_id)
        
        # Verificar si el usuario ha tenido actividad reciente
        last_activity = timezone.now() - timedelta(days=days_since_last_activity)
        
        from .models import EmailSentLog
        recent_activity = EmailSentLog.objects.filter(
            user=user,
            sent_at__gte=last_activity
        ).exists()
        
        if not recent_activity:
            # Enviar email de recordatorio
            subject = "¿Listo para continuar con tus postulaciones?"
            message = f"""
            Hola {user.first_name or user.username},
            
            Hemos notado que no has enviado postulaciones recientemente.
            ¿Te gustaría revisar nuevos puestos de trabajo disponibles?
            
            Accede a tu dashboard: {settings.SITE_URL}/matching/
            
            ¡Sigue postulando!
            El equipo de PostulaMatic
            """
            
            from django.core.mail import send_mail
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False
            )
            
            logger.info(f"Recordatorio enviado a usuario {user_id}")
            
            return {
                'success': True,
                'message': 'Recordatorio enviado',
                'user_id': user_id
            }
        
        return {
            'success': True,
            'message': 'Usuario tiene actividad reciente, no se envía recordatorio',
            'user_id': user_id
        }
        
    except Exception as e:
        logger.error(f"Error enviando recordatorio: {e}")
        return {
            'success': False,
            'error': str(e)
        }
