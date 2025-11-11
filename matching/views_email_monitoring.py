"""
Vistas para monitoreo y gestión de emails automáticos.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import EmailSentLog, UserCV, JobPosting, MatchScore, UserProfile
from .tasks_email import (
    send_personalized_email_task,
    send_bulk_emails_task,
    process_matching_and_send_emails_task,
    cleanup_old_email_logs_task
)


@login_required
def email_monitoring_dashboard(request):
    """Dashboard principal de monitoreo de emails."""
    
    # Estadísticas generales
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    stats = {
        'total_emails_sent': EmailSentLog.objects.filter(user=request.user).count(),
        'emails_today': EmailSentLog.objects.filter(
            user=request.user, sent_at__date=today
        ).count(),
        'emails_this_week': EmailSentLog.objects.filter(
            user=request.user, sent_at__date__gte=week_ago
        ).count(),
        'success_rate': 0,
        'failed_emails': EmailSentLog.objects.filter(
            user=request.user, status='failed'
        ).count(),
    }
    
    # Calcular tasa de éxito
    total_sent = stats['total_emails_sent']
    if total_sent > 0:
        successful = EmailSentLog.objects.filter(
            user=request.user, status='sent'
        ).count()
        stats['success_rate'] = round((successful / total_sent) * 100, 1)
    
    # Emails recientes con paginación (20 por página)
    emails_query = EmailSentLog.objects.filter(
        user=request.user
    ).select_related('job_posting', 'cv').order_by('-sent_at')
    
    paginator = Paginator(emails_query, 20)
    page_number = request.GET.get('page', 1)
    emails_page = paginator.get_page(page_number)
    
    # Configuración del usuario
    try:
        user_profile = request.user.profile
        user_config = {
            'daily_limit': user_profile.daily_limit,
            'match_threshold': user_profile.match_threshold,
            'is_active': user_profile.is_active,
            'min_pause': user_profile.min_pause_seconds,
            'max_pause': user_profile.max_pause_seconds,
        }
    except UserProfile.DoesNotExist:
        user_config = {
            'daily_limit': 20,
            'match_threshold': 70,
            'is_active': False,
            'min_pause': 20,
            'max_pause': 90,
        }
    
    context = {
        'stats': stats,
        'emails_page': emails_page,
        'user_config': user_config,
        'page_title': 'Monitoreo de Emails',
    }
    
    return render(request, 'matching/email_monitoring_dashboard.html', context)


@login_required
def email_logs_list(request):
    """Lista paginada de todos los emails enviados."""
    
    # Filtros
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Query base
    logs_query = EmailSentLog.objects.filter(user=request.user)
    
    # Aplicar filtros
    if status_filter:
        logs_query = logs_query.filter(status=status_filter)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            logs_query = logs_query.filter(sent_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            logs_query = logs_query.filter(sent_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Paginación
    paginator = Paginator(logs_query.select_related('job_posting', 'cv'), 20)
    page_number = request.GET.get('page')
    logs_page = paginator.get_page(page_number)
    
    # Estadísticas por estado
    status_stats = EmailSentLog.objects.filter(user=request.user).values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    context = {
        'logs_page': logs_page,
        'status_stats': status_stats,
        'filters': {
            'status': status_filter,
            'date_from': date_from,
            'date_to': date_to,
        },
        'page_title': 'Historial de Emails',
    }
    
    return render(request, 'matching/email_logs_list.html', context)


@login_required
def email_log_detail(request, log_id):
    """Detalle de un email enviado."""
    
    email_log = get_object_or_404(
        EmailSentLog, 
        id=log_id, 
        user=request.user
    )
    
    context = {
        'email_log': email_log,
        'page_title': f'Detalle de Email - {email_log.job_posting.title}',
    }
    
    return render(request, 'matching/email_log_detail.html', context)


@login_required
@require_http_methods(["POST"])
def send_test_email(request):
    """Envía un email de prueba a un puesto específico."""
    
    try:
        data = json.loads(request.body)
        job_id = data.get('job_id')
        cv_id = data.get('cv_id')
        email_template = data.get('email_template', 'base')
        ai_provider = data.get('ai_provider', 'openai')
        
        if not job_id or not cv_id:
            return JsonResponse({
                'success': False,
                'error': 'Faltan parámetros requeridos'
            })
        
        # Verificar que el CV pertenece al usuario
        cv = get_object_or_404(UserCV, id=cv_id, user=request.user)
        
        # Verificar que el puesto existe
        job_posting = get_object_or_404(JobPosting, id=job_id)
        
        # Enviar tarea de email
        task_result = send_personalized_email_task.delay(
            user_id=request.user.id,
            cv_id=cv_id,
            job_id=job_id,
            email_template=email_template,
            ai_provider=ai_provider
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Email de prueba enviado',
            'task_id': task_result.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Datos JSON inválidos'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error enviando email: {str(e)}'
        })


@login_required
@require_http_methods(["POST"])
def send_bulk_emails(request):
    """Envía emails masivos a múltiples puestos."""
    from .tasks_bulk_email import send_bulk_emails_task
    
    try:
        data = json.loads(request.body)
        job_ids = data.get('job_ids', [])
        cv_id = data.get('cv_id')  # Nuevo: ID del CV seleccionado
        email_template = data.get('email_template', 'base')
        ai_provider = data.get('ai_provider', 'openai')
        batch_size = data.get('batch_size', 5)
        delay_between_batches = data.get('delay_between_batches', 300)
        
        if not job_ids:
            return JsonResponse({
                'success': False,
                'error': 'No se especificaron puestos'
            })
        
        # Verificar que el usuario tiene CV
        if cv_id:
            # Verificar que el CV especificado existe y pertenece al usuario
            try:
                user_cv = UserCV.objects.get(id=cv_id, user=request.user)
            except UserCV.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'CV seleccionado no encontrado'
                })
        else:
            # Si no se especifica CV, verificar que el usuario tiene al menos uno
            user_cv = UserCV.objects.filter(user=request.user).first()
            if not user_cv:
                return JsonResponse({
                    'success': False,
                    'error': 'Usuario no tiene CV'
                })
        
        # Enviar tarea masiva
        task_result = send_bulk_emails_task.delay(
            user_id=request.user.id,
            job_ids=job_ids,
            cv_id=cv_id,  # Nuevo: pasar el CV seleccionado
            email_template=email_template,
            ai_provider=ai_provider,
            batch_size=batch_size,
            delay_between_batches=delay_between_batches
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Enviando emails a {len(job_ids)} puestos',
            'task_id': task_result.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Datos JSON inválidos'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error iniciando envío masivo: {str(e)}'
        })


@login_required
@require_http_methods(["POST"])
def process_auto_matching(request):
    """Procesa matching automático y envía emails."""
    
    try:
        data = json.loads(request.body)
        min_match_score = data.get('min_match_score', 70)
        email_template = data.get('email_template', 'base')
        ai_provider = data.get('ai_provider', 'openai')
        
        # VALIDACIÓN 1: Verificar que existan puestos de trabajo
        total_jobs = JobPosting.objects.count()
        if total_jobs == 0:
            return JsonResponse({
                'success': False,
                'error': 'No hay puestos de trabajo en la base de datos. Ejecuta el scraper primero para obtener ofertas.'
            })
        
        # VALIDACIÓN 2: Verificar que el usuario tenga CV
        user_cv = UserCV.objects.filter(user=request.user, parsed_text__isnull=False).exclude(parsed_text="").first()
        if not user_cv:
            return JsonResponse({
                'success': False,
                'error': 'No tienes CV procesado. Sube y procesa un CV primero.'
            })
        
        # VALIDACIÓN 3: Verificar que existan matches
        existing_matches = MatchScore.objects.filter(cv__user=request.user).count()
        if existing_matches == 0:
            return JsonResponse({
                'success': False,
                'error': 'No hay matches calculados. Ejecuta "Calcular Matches" primero.'
            })
        
        # Enviar tarea de matching automático
        task_result = process_matching_and_send_emails_task.delay(
            user_id=request.user.id,
            min_match_score=min_match_score,
            email_template=email_template,
            ai_provider=ai_provider
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Procesando matching automático con score >= {min_match_score}% ({total_jobs} puestos, {existing_matches} matches)',
            'task_id': task_result.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Datos JSON inválidos'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error procesando matching automático: {str(e)}'
        })


@login_required
def email_statistics(request):
    """Estadísticas detalladas de emails."""
    
    # Estadísticas por día (últimos 30 días)
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    
    daily_stats = EmailSentLog.objects.filter(
        user=request.user,
        sent_at__date__gte=thirty_days_ago
    ).extra(
        select={'day': 'date(sent_at)'}
    ).values('day', 'status').annotate(
        count=Count('id')
    ).order_by('day')
    
    # Estadísticas por template
    template_stats = EmailSentLog.objects.filter(
        user=request.user
    ).values('email_template').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Estadísticas por proveedor de IA
    ai_provider_stats = EmailSentLog.objects.filter(
        user=request.user
    ).values('ai_provider').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Top puestos por envíos
    top_jobs = EmailSentLog.objects.filter(
        user=request.user
    ).values(
        'job_posting__title', 
        'job_posting__company'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    context = {
        'daily_stats': daily_stats,
        'template_stats': template_stats,
        'ai_provider_stats': ai_provider_stats,
        'top_jobs': top_jobs,
        'page_title': 'Estadísticas de Emails',
    }
    
    return render(request, 'matching/email_statistics.html', context)


@login_required
def task_status(request, task_id):
    """Obtiene el estado de una tarea de Celery."""
    
    try:
        from celery.result import AsyncResult
        
        result = AsyncResult(task_id)
        
        return JsonResponse({
            'success': True,
            'task_id': task_id,
            'status': result.status,
            'result': result.result if result.ready() else None,
            'info': result.info if hasattr(result, 'info') else None,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error obteniendo estado de tarea: {str(e)}'
        })


@login_required
@require_http_methods(["POST"])
def cleanup_email_logs(request):
    """Limpia logs de emails antiguos."""
    
    try:
        data = json.loads(request.body)
        days_to_keep = data.get('days_to_keep', 30)
        
        # Enviar tarea de limpieza
        task_result = cleanup_old_email_logs_task.delay(days_to_keep)
        
        return JsonResponse({
            'success': True,
            'message': f'Iniciando limpieza de logs de más de {days_to_keep} días',
            'task_id': task_result.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Datos JSON inválidos'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error iniciando limpieza: {str(e)}'
        })


@login_required
def email_settings(request):
    """Configuración de envío de emails."""
    
    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        # Actualizar configuración
        user_profile.daily_limit = int(request.POST.get('daily_limit', 20))
        user_profile.match_threshold = int(request.POST.get('match_threshold', 70))
        user_profile.min_pause_seconds = int(request.POST.get('min_pause_seconds', 20))
        user_profile.max_pause_seconds = int(request.POST.get('max_pause_seconds', 90))
        user_profile.is_active = request.POST.get('is_active') == 'on'
        user_profile.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Configuración actualizada'
        })
    
    context = {
        'user_profile': user_profile,
        'page_title': 'Configuración de Emails',
    }
    
    return render(request, 'matching/email_settings.html', context)


@login_required
@require_http_methods(["GET"])
def email_statistics_api(request):
    """API para obtener estadísticas en tiempo real."""
    today = timezone.now().date()
    
    # Estadísticas básicas
    total_emails = EmailSentLog.objects.filter(user=request.user).count()
    emails_today = EmailSentLog.objects.filter(user=request.user, sent_at__date=today).count()
    successful = EmailSentLog.objects.filter(user=request.user, status='sent').count()
    
    success_rate = 0
    if total_emails > 0:
        success_rate = round((successful / total_emails) * 100, 1)
    
    # Emails recientes (solo los primeros 10 para la actualización automática)
    recent_emails = EmailSentLog.objects.filter(
        user=request.user
    ).select_related('job_posting', 'cv').order_by('-sent_at')[:10]
    
    recent_emails_data = [{
        'id': email.id,
        'job_title': email.job_posting.title if email.job_posting else '[Oferta eliminada]',
        'sent_to': email.sent_to,
        'status': email.status,
        'sent_at': email.sent_at.strftime('%d/%m/%Y %H:%M'),
        'error_message': email.error_message or '',
        'email_subject': email.email_subject or '',
        'email_body': email.email_body or '',
        'cv_filename': email.cv.original_file.name.split('/')[-1] if email.cv and email.cv.original_file else '[CV eliminado]'
    } for email in recent_emails]
    
    # Configuración del usuario
    try:
        user_profile = request.user.profile
        daily_limit = user_profile.daily_limit
    except UserProfile.DoesNotExist:
        daily_limit = 20
    
    return JsonResponse({
        'success': True,
        'stats': {
            'total_emails': total_emails,
            'emails_today': emails_today,
            'success_rate': success_rate,
            'daily_limit': daily_limit
        },
        'recent_emails': recent_emails_data
    })


@login_required
@require_http_methods(["GET"])
def paginated_emails_api(request):
    """API para obtener emails paginados."""
    page_number = request.GET.get('page', 1)
    
    # Query base
    emails_query = EmailSentLog.objects.filter(
        user=request.user
    ).select_related('job_posting', 'cv').order_by('-sent_at')
    
    # Paginación
    paginator = Paginator(emails_query, 20)
    try:
        emails_page = paginator.get_page(page_number)
    except:
        emails_page = paginator.get_page(1)
    
    # Preparar datos de los emails
    emails_data = []
    for email in emails_page:
        emails_data.append({
            'id': email.id,
            'job_title': email.job_posting.title if email.job_posting else '[Oferta eliminada]',
            'sent_to': email.sent_to,
            'status': email.status,
            'status_display': email.get_status_display(),
            'sent_at': email.sent_at.strftime('%d/%m/%Y %H:%M'),
            'sent_at_date': email.sent_at.strftime('%d/%m/%Y'),
            'sent_at_time': email.sent_at.strftime('%H:%M'),
            'error_message': email.error_message or '',
            'email_subject': email.email_subject or '',
            'email_body': email.email_body or '',
            'cv_filename': email.cv.original_file.name.split('/')[-1] if email.cv and email.cv.original_file else '[CV eliminado]',
            'has_job_posting': bool(email.job_posting),
            'has_cv': bool(email.cv),
        })
    
    return JsonResponse({
        'success': True,
        'emails': emails_data,
        'pagination': {
            'current_page': emails_page.number,
            'total_pages': emails_page.paginator.num_pages,
            'has_previous': emails_page.has_previous(),
            'has_next': emails_page.has_next(),
            'previous_page': emails_page.previous_page_number() if emails_page.has_previous() else None,
            'next_page': emails_page.next_page_number() if emails_page.has_next() else None,
            'total_count': emails_page.paginator.count,
        }
    })


@login_required
@require_http_methods(["GET"])
def get_user_cvs_api(request):
    """API para obtener los CVs del usuario."""
    cvs = UserCV.objects.filter(user=request.user).order_by('-created_at')
    
    first_cv = cvs.first()
    
    cvs_data = [{
        'id': cv.id,
        'filename': cv.original_file.name.split('/')[-1] if cv.original_file else f'CV #{cv.id}',
        'uploaded_at': cv.created_at.strftime('%d/%m/%Y %H:%M'),
        'skills_count': cv.skills_count if hasattr(cv, 'skills_count') else len(cv.skills_list),
        'is_most_recent': cv.id == first_cv.id if first_cv else False
    } for cv in cvs]
    
    return JsonResponse({
        'success': True,
        'cvs': cvs_data
    })


@login_required
@require_http_methods(["GET"])
def get_email_detail(request, email_id):
    """API endpoint para obtener detalles completos de un email enviado."""
    try:
        email = get_object_or_404(
            EmailSentLog.objects.select_related('job_posting', 'cv', 'user'),
            id=email_id,
            user=request.user
        )
        
        # Preparar datos del email
        email_data = {
            'id': email.id,
            'email_subject': email.email_subject,
            'email_body': email.email_body,
            'sent_to': email.sent_to,
            'status': email.status,
            'status_display': email.get_status_display(),
            'sent_at': email.sent_at.strftime('%d/%m/%Y %H:%M:%S'),
            'email_template': email.email_template,
            'ai_provider': email.ai_provider,
            'error_message': email.error_message,
            'message_id': email.message_id,
            
            # Información del puesto (puede ser None si fue eliminado)
            'job_title': email.job_posting.title if email.job_posting else None,
            'job_company': 'N/A',  # JobPosting no tiene campo company
            'job_location': 'N/A',  # JobPosting no tiene campo location
            
            # Información del CV (puede ser None si fue eliminado)
            'cv_filename': email.cv.original_file.name.split('/')[-1] if email.cv and email.cv.original_file else None,
            'cv_id': email.cv.id if email.cv else None,
            
            # CV personalizado adjunto (nombre completo para tooltip)
            'personalized_cv_filename': email.personalized_cv_file.name.split('/')[-1] if email.personalized_cv_file else None,
            'has_personalized_cv': bool(email.personalized_cv_file),
        }
        
        return JsonResponse({
            'success': True,
            'email': email_data
        })
        
    except EmailSentLog.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Email no encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error obteniendo detalles del email: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def download_personalized_cv(request, email_id):
    """Descarga el CV personalizado adjunto a un email enviado."""
    import os
    from django.http import Http404, HttpResponse
    
    try:
        email = get_object_or_404(
            EmailSentLog,
            id=email_id,
            user=request.user
        )
        
        if not email.personalized_cv_file:
            raise Http404("CV personalizado no disponible para este email")
        
        # Obtener el path del archivo
        file_path = email.personalized_cv_file.path
        
        if not os.path.exists(file_path):
            raise Http404("Archivo CV personalizado no existe en el sistema")
        
        # Leer el archivo
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Obtener el nombre del archivo
        filename = os.path.basename(email.personalized_cv_file.name)
        
        # Crear respuesta HTTP
        response = HttpResponse(file_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(file_data)
        
        return response
        
    except EmailSentLog.DoesNotExist:
        raise Http404("Email no encontrado")
    except Exception as e:
        raise Http404(f"Error descargando CV personalizado: {str(e)}")


@login_required
@require_http_methods(["DELETE"])
def delete_email(request, email_id):
    """Elimina un email individual."""
    try:
        email = get_object_or_404(
            EmailSentLog,
            id=email_id,
            user=request.user
        )
        
        email.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Email eliminado correctamente'
        })
        
    except EmailSentLog.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Email no encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["DELETE"])
def delete_all_emails(request):
    """Elimina todos los emails del usuario."""
    try:
        deleted_count, _ = EmailSentLog.objects.filter(user=request.user).delete()
        
        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'{deleted_count} email(s) eliminado(s) correctamente'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
